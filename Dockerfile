# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MARKET_HOST=0.0.0.0 \
    MARKET_PORT=8080 \
    COOKIE_SECURE=1 \
    MODEL_DEVICE=cpu \
    MODEL_CPU_THREADS=1 \
    MODEL_PRELOAD_SEMANTIC=0 \
    MODEL_ALLOW_DOWNLOAD=0

WORKDIR /app/market-simulator

COPY market-simulator/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
      torch==2.8.0 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY market-simulator/ /app/market-simulator/
COPY scripts/live_model_worker.py /app/scripts/live_model_worker.py
COPY model-runtime/ /app/model-runtime/
COPY processed/cleaned/ /app/processed/cleaned/
RUN --mount=type=cache,target=/root/.cache/huggingface \
    rm -f /app/model-runtime/research/enterprise_path_finance_knowledge/pretrained/FinBERT2-large/model.safetensors && \
    HF_HUB_OFFLINE=0 TRANSFORMERS_OFFLINE=0 python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="valuesimplex-ai-lab/FinBERT2-large",
    revision="5928de1860ce5eb5f1f2dd23c08d2b9dcc1b0686",
    local_dir="/app/model-runtime/research/enterprise_path_finance_knowledge/pretrained/FinBERT2-large",
)
PY
RUN rm -f /app/market-simulator/runtime/saves.sqlite3 \
          /app/market-simulator/runtime/model-worker.log

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8080

CMD ["python", "server.py"]
