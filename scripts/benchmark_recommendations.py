"""Benchmark real CPU recommendations and HTTP routing without touching user saves.

Run: python scripts/benchmark_recommendations.py --output <report.json>
No training, model inference worker or GPU is started.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import http.cookiejar
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import threading
from time import perf_counter
import urllib.error
import urllib.request


def summary(times):
    ordered = sorted(times)
    return dict(count=len(times), median_ms=round(statistics.median(times), 3),
                p95_ms=round(ordered[min(len(times) - 1, int(len(times) * .95))], 3),
                max_ms=round(max(times), 3))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'market-simulator'))
    with tempfile.TemporaryDirectory(prefix='escp-recommendation-benchmark-') as temp:
        os.environ['SAVE_DB_PATH'] = str(Path(temp) / 'saves.sqlite3')
        os.environ['MODEL_WARM_ON_START'] = '0'
        os.environ['COOKIE_SECURE'] = '0'
        os.environ.pop('SAVE_STORE_URL', None)
        started = perf_counter()
        import server
        startup_ms = (perf_counter() - started) * 1000
        svc = server.RECOMMENDER
        assert not svc.model_error, svc.model_error
        trained = sorted(set(svc.subjects) & set(svc.user_index))
        unseen = sorted(set(svc.subjects) - set(svc.user_index))
        assert trained and unseen
        report = dict(model_version=svc.manifest['model_version'], device='CPU',
                      server_import_ms=round(startup_ms, 3),
                      investor_count=len(svc.subjects), trained_in_app=len(trained),
                      popularity_in_app=len(unseen), candidate_count=len(svc.candidate_ids),
                      model_users=len(svc.user_ids), model_items=len(svc.item_ids),
                      history_cutoff=svc.history_cutoff,
                      excludes='full source history plus application disclosed history',
                      cold_container_included=False)
        for name, ids, method in [('sgl', trained, 'sgl'), ('mostpop', unseen, 'mostpop')]:
            durations = []
            for iid in ids[:200]:
                start = perf_counter()
                result = svc.recommend(iid)
                durations.append((perf_counter() - start) * 1000)
                assert result['method'] == method
                assert result['count'] == 10, (iid, result['count'])
                assert len({r['id'] for r in result['items']}) == 10
                assert not ({r['id'] for r in result['items']} & svc.history[iid])
                assert all(r['id'] in svc.companies for r in result['items'])
            report[name] = summary(durations)
        with ThreadPoolExecutor(max_workers=8) as pool:
            concurrent = list(pool.map(svc.recommend, (trained[:100] + unseen[:100])))
        report['eight_concurrent_requests'] = summary([r['elapsed_ms'] for r in concurrent])

        class Quiet(server.Handler):
            def log_message(self, *args):
                pass

        httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), Quiet)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        base = 'http://127.0.0.1:' + str(httpd.server_address[1])
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

        def request(path, body=None):
            data = json.dumps(body).encode() if body is not None else None
            headers = {'Origin': base, 'Content-Type': 'application/json'}
            with client.open(urllib.request.Request(base + path, data, headers), timeout=10) as response:
                return json.load(response)

        def expect_status(path, expected):
            try:
                request(path)
            except urllib.error.HTTPError as error:
                assert error.code == expected, (path, error.code)
            else:
                raise AssertionError((path, expected))

        try:
            expect_status('/api/recommendations?investor_id=' + trained[0], 401)
            account = request('/api/new', {'name': 'Temporary recommendation benchmark', 'investor_id': trained[0]})['game']
            expect_status('/api/recommendations?investor_id=visitor', 403)
            expect_status('/api/recommendation-investors?page=bad', 400)
            times = []
            for iid in trained[:40] + unseen[:40]:
                account = request('/api/investor', {'investor_id': iid, 'revision': account['revision']})['game']
                before = request('/api/legacy-export')
                start = perf_counter()
                result = request('/api/recommendations')
                times.append((perf_counter() - start) * 1000)
                assert result['count'] == 10
                after = request('/api/legacy-export')
                assert before == after, 'Read-only recommendations changed account state'
            report['http_including_session_and_json'] = summary(times)
            report['api_contract_checks'] = 'passed: 401/400/403, saved identity, both methods, Top10, read-only recommendations'
            assert max(times) < 10000
        finally:
            httpd.shutdown()
            httpd.server_close()
            thread.join()
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
