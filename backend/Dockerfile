FROM python:3.12-slim

WORKDIR /app

# 先装 CPU 版 torch（体积小、无需显卡），再装其余依赖
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# samples 由 docker-compose 以只读卷挂载到 /samples
ENV DATA_DIR=/app/data \
    SAMPLES_DIR=/samples

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
