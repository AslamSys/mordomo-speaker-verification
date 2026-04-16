FROM python:3.11-slim

# libsndfile1 needed by soundfile for audio I/O
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# Install torch CPU-only first to avoid pulling the full CUDA variant (~2GB with CUDA)
RUN pip install --no-cache-dir --timeout 120 \
    "torch>=2.3,<3" "torchaudio>=2.3,<3" \
    --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Embeddings volume — persisted on the host
# Model cache volume — avoids re-downloading ECAPA-TDNN on every restart
VOLUME ["/data/embeddings", "/app/model"]

CMD ["python", "-m", "src.main"]
