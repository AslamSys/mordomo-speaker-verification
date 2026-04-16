"""
Verifier — ECAPA-TDNN speaker embeddings via SpeechBrain.

Model: speechbrain/spkrec-ecapa-voxceleb
  - Trained on VoxCeleb1 + VoxCeleb2 (~1.2M utterances, 7000+ speakers)
  - Architecture: ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation)
  - Embedding dimension: 192D (L2-normalised)
  - EER on VoxCeleb1-O: ~0.87%  (vs ~5-7% for GE2E/Resemblyzer)

The cosine similarity scale for ECAPA-TDNN differs from Resemblyzer:
  - Same speaker:      typically 0.30 – 0.80
  - Different speaker: typically -0.10 – 0.25
  - Default threshold: VERIFICATION_THRESHOLD (env var, default 0.25)

⚠️  Embeddings are 192D — incompatible with previously stored 256D Resemblyzer files.
    All speakers must be re-enrolled after upgrading from Resemblyzer.
"""
import logging

import numpy as np
import torch

from src.config import MODEL_SAVEDIR, VERIFICATION_THRESHOLD
from src.store import load_all_embeddings

logger = logging.getLogger(__name__)

_classifier = None
_embeddings: dict[str, np.ndarray] = {}


def load_encoder() -> None:
    """
    Load ECAPA-TDNN model from HuggingFace (cached in MODEL_SAVEDIR after first download).
    Called once at startup.
    """
    global _classifier
    from speechbrain.pretrained import EncoderClassifier

    _classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir=MODEL_SAVEDIR,
        run_opts={"device": "cpu"},
    )
    logger.info("ECAPA-TDNN (SpeechBrain) loaded from %s", MODEL_SAVEDIR)


def reload_embeddings() -> None:
    """Reload all stored embeddings into memory. Call after enroll/delete."""
    global _embeddings
    _embeddings = load_all_embeddings()
    logger.info("Embeddings reloaded: %d profiles", len(_embeddings))


def embed_audio(pcm_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Convert raw PCM bytes to a 192D ECAPA-TDNN voice embedding.
    Expects: mono, 16-bit, 16kHz PCM.
    """
    assert _classifier is not None, "Encoder not loaded — call load_encoder() first"
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    wavs = torch.tensor(audio).unsqueeze(0)       # [1, T]
    wav_lens = torch.tensor([1.0])                 # relative length = full
    with torch.no_grad():
        embeddings = _classifier.encode_batch(wavs, wav_lens)  # [1, 1, 192]
    return embeddings.squeeze().cpu().numpy()      # [192]


def verify(pcm_bytes: bytes, sample_rate: int = 16000) -> tuple[str | None, float]:
    """
    Verify a voice against all enrolled speakers.

    Returns:
        (speaker_id, confidence)  if similarity >= VERIFICATION_THRESHOLD
        (None, best_score)        if no match
    """
    if not _embeddings:
        logger.warning("No enrolled speakers — verification impossible")
        return None, 0.0

    live_emb = embed_audio(pcm_bytes, sample_rate)

    best_id: str | None = None
    best_score: float = -1.0

    for speaker_id, stored_emb in _embeddings.items():
        # Cosine similarity (ECAPA-TDNN embeddings are L2-normalised, so dot ≈ cosine)
        score = float(
            np.dot(live_emb, stored_emb)
            / (np.linalg.norm(live_emb) * np.linalg.norm(stored_emb) + 1e-9)
        )
        if score > best_score:
            best_score = score
            best_id = speaker_id

    if best_score >= VERIFICATION_THRESHOLD:
        logger.info("Verified: speaker_id=%s confidence=%.3f", best_id, best_score)
        return best_id, best_score

    logger.info("Rejected: best_match=%s score=%.3f threshold=%.3f", best_id, best_score, VERIFICATION_THRESHOLD)
    return None, best_score
