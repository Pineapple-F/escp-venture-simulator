"""Frozen financial text encoder; enterprise text never leaves this machine."""
import os
from pathlib import Path

import numpy as np
import torch
from torch import nn


MODEL_ID = "valuesimplex-ai-lab/FinBERT2-large"
REVISION = "5928de1860ce5eb5f1f2dd23c08d2b9dcc1b0686"
LOCAL_MODEL = Path(__file__).with_name("pretrained") / "FinBERT2-large"


class FinancialTextEncoder:
    def __init__(self, device="cpu"):
        from transformers import AutoModel, AutoTokenizer

        weight = LOCAL_MODEL / "model.safetensors"
        if not weight.is_file():
            if os.environ.get("MODEL_ALLOW_DOWNLOAD", "1") == "0":
                raise FileNotFoundError(
                    f"FinBERT2 weight is missing at {weight}. See model-runtime/README.md.")
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=MODEL_ID,
                revision=REVISION,
                local_dir=LOCAL_MODEL,
                allow_patterns=(
                    "*.json", "*.txt", "*.safetensors", "tokenizer.model",
                ),
            )

        self.tokenizer = AutoTokenizer.from_pretrained(
            LOCAL_MODEL, local_files_only=True, trust_remote_code=False)
        self.model = AutoModel.from_pretrained(
            LOCAL_MODEL, local_files_only=True, trust_remote_code=False)
        self.device = torch.device(device)
        self.model.to(self.device).eval().requires_grad_(False)
        self.dimension = int(self.model.config.hidden_size)
        self.window = min(int(self.model.config.max_position_embeddings), 512)

    def encode(self, texts, batch_size=32):
        """CLS pooling and L2 normalization; long event text is not silently truncated."""
        if not texts:
            return np.zeros((0, self.dimension), np.float32)
        items, owners = [], []
        capacity = self.window - self.tokenizer.num_special_tokens_to_add(pair=False)
        for owner, text in enumerate(texts):
            tokens = self.tokenizer.encode(
                text, add_special_tokens=False, truncation=False, verbose=False)
            for start in range(0, max(1, len(tokens)), capacity):
                items.append(self.tokenizer.prepare_for_model(
                    tokens[start:start + capacity], add_special_tokens=True,
                    return_attention_mask=True, truncation=False))
                owners.append(owner)
        order = sorted(range(len(items)), key=lambda i: len(items[i]["input_ids"]))
        items = [items[i] for i in order]
        owners = [owners[i] for i in order]
        totals = np.zeros((len(texts), self.dimension), np.float32)
        counts = np.zeros(len(texts), np.int32)
        with torch.no_grad():
            for start in range(0, len(items), batch_size):
                encoded = self.tokenizer.pad(
                    items[start:start + batch_size], padding=True, return_tensors="pt")
                encoded = {key: value.to(self.device) for key, value in encoded.items()}
                vectors = self.model(**encoded).last_hidden_state[:, 0]
                vectors = nn.functional.normalize(vectors, p=2, dim=1).cpu().numpy()
                for owner, vector in zip(owners[start:start + batch_size], vectors):
                    totals[owner] += vector
                    counts[owner] += 1
        totals /= counts[:, None]
        totals /= np.maximum(np.linalg.norm(totals, axis=1, keepdims=True), 1e-12)
        return totals.astype(np.float32)
