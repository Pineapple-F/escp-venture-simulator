"""Export an existing, trusted ESCP SGL checkpoint for CPU recommendation.

No optimizer steps or training run here. Online serving needs only NumPy and the
exported vectors; torch/pandas/scipy are offline export dependencies.
"""
from __future__ import annotations

import argparse
import ast
import configparser
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp
import torch


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def ordered_ids(folder, shape):
    path = folder / 'mapping.json'
    if path.exists():
        m = read_json(path)
        return m['user_ids'], m['item_ids'], {'mapping.json': sha256(path)}
    users = pd.read_parquet(folder / 'investors.parquet').sort_values('user_index')
    items = pd.read_parquet(folder / 'companies.parquet').sort_values('item_index')
    assert np.array_equal(users.user_index, np.arange(shape[0]))
    assert np.array_equal(items.item_index, np.arange(shape[1]))
    return users.investor_id.tolist(), items.company_id.tolist(), {
        name: sha256(folder / name) for name in ('investors.parquet', 'companies.parquet')}


def map_legacy_users(source_ids, degree, crosswalk):
    """Conservative aliases; never invent an ik ID or average trained vectors."""
    if all(x.startswith('ik_') for x in source_ids):
        return source_ids, np.arange(len(source_ids)), {'identity_mapping': True}
    if crosswalk is None:
        raise ValueError('Legacy investor_id:iv_* requires --legacy-crosswalk')
    d = pd.read_parquet(crosswalk, columns=['investor_id_anon', 'investor_key_anon'])
    aliases = d.dropna().drop_duplicates().groupby('investor_id_anon').investor_key_anon.apply(list).to_dict()
    choices, rejected = {}, []
    for index, sid in enumerate(source_ids):
        if sid.startswith('investor_key:ik_'):
            matches, exact = [sid.split(':', 1)[1]], True
        elif sid.startswith('investor_id:iv_'):
            matches, exact = aliases.get(sid.split(':', 1)[1], []), False
        else:
            matches, exact = [], False
        if len(matches) != 1:
            rejected.append({'source_id': sid, 'reason': 'ambiguous' if matches else 'missing'})
            continue
        choices.setdefault(matches[0], []).append((index, exact))
    ids, rows, collisions = [], [], []
    for key in sorted(choices):
        options = choices[key]
        # Preserve an exact ik checkpoint row if present; otherwise the most
        # observed uniquely mapped source row. No vector averaging/fitting.
        chosen = sorted(options, key=lambda x: (-int(x[1]), -int(degree[x[0]]), source_ids[x[0]]))[0][0]
        ids.append(key); rows.append(chosen)
        if len(options) > 1:
            collisions.append({'investor_id': key, 'selected_source_id': source_ids[chosen],
                               'other_source_ids': [source_ids[i] for i, _ in options if i != chosen]})
    return ids, np.asarray(rows, dtype=np.int64), {
        'identity_mapping': False,
        'policy': 'exact investor_key row first, else greatest training degree among unambiguous iv aliases; lexical tie',
        'crosswalk_sha256': sha256(crosswalk), 'rejected_source_rows': rejected,
        'alias_collisions': collisions,
    }


def original_encoder(source_file, state, train, layers):
    """Use the exact upstream class without importing its CUDA training shell."""
    tree = ast.parse(source_file.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_LightGCN')
    namespace = {'torch': torch, 'torch_sp': torch.sparse, 'nn': torch.nn,
                 'F': torch.nn.functional, 'np': np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source_file), 'exec'), namespace)
    adjacency = sp.bmat([[None, train], [train.T, None]], format='csr', dtype=np.float32)
    degrees = np.asarray(adjacency.sum(1)).ravel()
    inv = np.zeros_like(degrees)
    np.power(degrees, -.5, out=inv, where=degrees > 0)
    adjacency = (sp.diags(inv) @ adjacency @ sp.diags(inv)).tocoo()
    sparse = torch.sparse_coo_tensor(torch.as_tensor(np.stack([adjacency.row, adjacency.col]), dtype=torch.long),
                                    torch.as_tensor(adjacency.data), adjacency.shape).coalesce()
    dim = state['user_embeddings.weight'].shape[1]
    model = namespace['_LightGCN'](train.shape[0], train.shape[1], dim, sparse, layers)
    model.load_state_dict(state, strict=True)
    with torch.no_grad():
        model.eval()
        users = model._user_embeddings_final.detach().numpy().copy()
        items = model._item_embeddings_final.detach().numpy().copy()
        # Independent SciPy propagation checks the exported inference formula.
        layer = np.concatenate([state['user_embeddings.weight'].numpy(), state['item_embeddings.weight'].numpy()])
        levels = [layer]
        for _ in range(layers):
            layer = adjacency @ layer
            levels.append(layer)
        independent = np.stack(levels, axis=1).mean(axis=1)
        maximum = float(np.max(np.abs(independent - np.concatenate([users, items]))))
        np.testing.assert_allclose(np.concatenate([users, items]), independent, atol=2e-6, rtol=2e-5)
        query = np.linspace(0, len(users) - 1, min(64, len(users)), dtype=int)
        expected = model.predict(torch.as_tensor(query)).numpy()
        actual = users[query] @ items.T
        score_error = float(np.max(np.abs(expected - actual)))
        np.testing.assert_allclose(actual, expected, atol=2e-5, rtol=2e-5)
    return users, items, {'upstream_class': '_LightGCN', 'upstream_file_sha256': sha256(source_file),
                          'cpu_graph_propagation_max_abs_error': maximum,
                          'cpu_dot_product_max_abs_error': score_error,
                          'scoring_equivalence_verified': True}


def main(a):
    dataset, checkpoint, output = a.dataset.resolve(), a.checkpoint.resolve(), a.output.resolve()
    source_config = a.knowledge_root / 'SGL-official/conf/SGL.ini'
    hyperparameters = configparser.ConfigParser()
    hyperparameters.read(source_config, encoding='utf-8')
    if a.layers != hyperparameters.getint('hyperparameters', 'n_layers'):
        raise ValueError('Propagation layers differ from the source training configuration')
    train = sp.load_npz(dataset / 'train.npz').tocsr().astype(np.float32)
    train.sum_duplicates(); train.eliminate_zeros()
    if np.any(train.data != 1):
        raise ValueError('Expected binary SGL training graph')
    dataset_manifest = read_json(dataset / 'manifest.json')
    result = read_json(checkpoint.parent / 'result.json')
    if result.get('status') != 'completed' or result.get('model') != 'SGL':
        raise ValueError('Require completed SGL result alongside checkpoint')
    # This is an explicitly supplied trusted local training artifact, never a
    # file supplied through an HTTP request. Optimizer/RNG state is not exported.
    saved = torch.load(checkpoint, map_location='cpu', weights_only=False)
    modern = 'adapter' in saved
    if modern:
        state = saved['adapter']['model']
        if saved['config']['model'] != 'SGL':
            raise ValueError('Checkpoint is not SGL')
        for name in ('train.npz', 'mapping.json'):
            if saved['config']['input_hashes'][name] != sha256(dataset / name):
                raise ValueError('Training input differs from checkpoint: ' + name)
        if saved['epoch'] != result['selected_epoch']:
            raise ValueError('Use validation-selected best.pt, not last.pt')
        epoch, seed = saved['epoch'], saved['config']['seed']
    else:
        state = saved
        epoch, seed = result['epochs'], 42
        if not str(result.get('protocol', '')).startswith('2022 NDCG@20'):
            raise ValueError('Unrecognized legacy SGL checkpoint provenance')
    source_ids, item_ids, mapping_hashes = ordered_ids(dataset, train.shape)
    if (len(source_ids), len(item_ids)) != train.shape:
        raise ValueError('ID map dimensions differ from training graph')
    if len(set(source_ids)) != len(source_ids) or len(set(item_ids)) != len(item_ids):
        raise ValueError('Duplicate canonical IDs')
    if tuple(state['user_embeddings.weight'].shape[:1]) != (len(source_ids),) or state['item_embeddings.weight'].shape[0] != len(item_ids):
        raise ValueError('Checkpoint cardinalities differ from ID map')
    torch.set_num_threads(1)
    users, items, checks = original_encoder(a.knowledge_root / 'SGL-official/model/general_recommender/SGL.py', state, train, a.layers)
    degree = np.diff(train.indptr)
    user_ids, selected, alias_audit = map_legacy_users(source_ids, degree, a.legacy_crosswalk)
    if np.any(degree[selected] == 0):
        raise ValueError('Cannot export untrained zero-degree investor as known')
    seen = sp.load_npz(dataset / 'seen.npz').tocsr()[selected]
    # All existing source relationships are exclusion-only. Validation/test
    # observations never enter propagation or optimization.
    for name in ('valid.npz', 'test.npz'):
        if (dataset / name).exists():
            seen = seen + sp.load_npz(dataset / name).tocsr()[selected]
    scope = ['source seen.npz', 'source valid.npz', 'source test.npz']
    if a.all_history:
        history = pd.read_parquet(a.all_history, columns=['investor_id', 'company_id'])
        ulookup, ilookup = {x: i for i, x in enumerate(user_ids)}, {x: i for i, x in enumerate(item_ids)}
        uid, iid = history.investor_id.map(ulookup), history.company_id.map(ilookup)
        mask = uid.notna() & iid.notna()
        seen = seen + sp.csr_matrix((np.ones(mask.sum()), (uid[mask].astype(int), iid[mask].astype(int))), shape=seen.shape)
        scope.append('all source investment history, including held-out relationships, exclusion only')
    seen = seen.tocsr(); seen.sum_duplicates(); seen.eliminate_zeros(); seen.sort_indices()
    history = pd.read_parquet(dataset / 'investment_history.parquet', columns=['event_date'])
    max_event_date = str(pd.to_datetime(history.event_date).max().date())
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output / 'embeddings.npz',
                        user_embeddings=np.asarray(users[selected], dtype=np.float32),
                        item_embeddings=np.asarray(items, dtype=np.float32),
                        seen_indptr=seen.indptr.astype(np.int64), seen_indices=seen.indices.astype(np.int32),
                        train_degrees=degree[selected].astype(np.int32))
    notes = ['Already-trained SGL; no fitting or optimizer steps during export.',
             'Online score is the dot product of final 3-layer mean-propagated embeddings; no popularity blending.',
             'Only companies present in the app catalogue may be returned.',
             'Known-investment masking uses all observed production history, not the experimental evaluation mask.']
    if not modern:
        notes += ['Provisional legacy 2025 rolling model: newer 20261026 checkpoint not available locally at export.',
                  'Legacy investor aliases were conservatively resolved; inspect legacy_alias_audit.json.']
    else:
        notes += ['Static random historical link completion experiment; these metrics are not future investment forecasting accuracy.']
    manifest = {'schema_version': 1, 'model': 'SGL',
                'model_version': a.model_version or (f'dual-20261026-{dataset.name}-s{seed}-e{epoch}' if modern else f'legacy-20261012-{dataset.name}-s{seed}-e{epoch}'),
                'split': dataset.name, 'seed': seed, 'selected_epoch': int(epoch), 'n_layers': a.layers,
                'user_ids': user_ids, 'item_ids': item_ids, 'embedding_dimension': int(items.shape[1]),
                'history_cutoff': dataset_manifest.get('cutoff'), 'max_source_event_date': max_event_date,
                'source_checkpoint_sha256': sha256(checkpoint),
                'source_hyperparameters_sha256': sha256(source_config),
                'dataset_mapping_sha256': mapping_hashes.get('mapping.json') or hashlib.sha256(json.dumps(mapping_hashes, sort_keys=True).encode()).hexdigest(),
                'dataset_mapping_files': mapping_hashes, 'source_train_sha256': sha256(dataset / 'train.npz'),
                'embeddings_sha256': sha256(output / 'embeddings.npz'), 'source_notes': notes,
                'seen_scope': scope, 'seen_pairs': int(seen.nnz),
                'source_checkpoint': str(checkpoint), 'source_dataset': str(dataset),
                'source_shape': list(train.shape), 'exported_users': len(user_ids), 'exported_items': len(item_ids),
                'source_result_sha256': sha256(checkpoint.parent / 'result.json'),
                'source_result_metrics': result.get('metrics'), 'verification': checks,
                'production_alias_policy': alias_audit.get('policy', 'canonical identity'),
                'provisional_legacy': not modern,
                'exported_at': datetime.now(timezone.utc).isoformat()}
    if a.all_history:
        manifest['all_history_sha256'] = sha256(a.all_history)
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if not modern:
        (output / 'legacy_alias_audit.json').write_text(json.dumps(alias_audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    elif (output / 'legacy_alias_audit.json').exists():
        (output / 'legacy_alias_audit.json').unlink()
    print(json.dumps({k: v for k, v in manifest.items() if k not in ('user_ids', 'item_ids', 'source_notes')}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--dataset', type=Path, required=True)
    p.add_argument('--knowledge-root', type=Path, required=True)
    p.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1] / 'market-simulator/recommendation-assets/sgl')
    p.add_argument('--legacy-crosswalk', type=Path)
    p.add_argument('--all-history', type=Path)
    p.add_argument('--layers', type=int, default=3)
    p.add_argument('--model-version')
    main(p.parse_args())
