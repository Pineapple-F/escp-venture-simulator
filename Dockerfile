FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY demo ./demo
COPY scripts ./scripts
COPY processed ./processed

EXPOSE 8080

CMD ["python", "scripts/demo_backend.py"]
