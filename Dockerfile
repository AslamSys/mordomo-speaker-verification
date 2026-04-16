FROM python:3.11-slim

# ffmpeg needed by resemblyzer for audio loading
# gcc + python3-dev needed to compile webrtcvad (C extension required by resemblyzer)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 gcc python3-dev \
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
VOLUME ["/data/embeddings"]

CMD ["python", "-m", "src.main"]
