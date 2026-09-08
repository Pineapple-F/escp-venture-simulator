FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MARKET_HOST=0.0.0.0 \
    MARKET_PORT=8080

WORKDIR /app/market-simulator

COPY market-simulator/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY market-simulator/ ./
COPY processed/cleaned/ /app/processed/cleaned/

EXPOSE 8080

CMD ["python", "server.py"]
