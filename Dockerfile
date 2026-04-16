FROM python:3.11-slim

# ffmpeg needed by resemblyzer for audio loading
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/

# Embeddings volume — persisted on the host
VOLUME ["/data/embeddings"]

CMD ["python", "-m", "src.main"]
