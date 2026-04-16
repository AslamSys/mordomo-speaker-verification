"""
Verifier — cosine similarity between a live audio embedding and stored profiles.
"""
import logging

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
import io

from src.config import VERIFICATION_THRESHOLD
from src.store import load_all_embeddings

logger = logging.getLogger(__name__)

_encoder: VoiceEncoder | None = None
_embeddings: dict[str, np.ndarray] = {}


def load_encoder() -> None:
    """Load Resemblyzer model into memory. Called once at startup."""
    global _encoder
    _encoder = VoiceEncoder()
    logger.info("VoiceEncoder loaded")


def reload_embeddings() -> None:
    """Reload all stored embeddings into memory. Call after enroll/delete."""
    global _embeddings
    _embeddings = load_all_embeddings()
    logger.info("Embeddings reloaded: %d profiles", len(_embeddings))


def embed_audio(pcm_bytes: bytes, sample_rate: int = 16000) -> np.ndarray:
    """
    Convert raw PCM bytes to a 256D voice embedding.
    Expects: mono, 16-bit, 16kHz PCM.
    """
    assert _encoder is not None, "Encoder not loaded — call load_encoder() first"
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    wav = preprocess_wav(audio, source_sr=sample_rate)
    return _encoder.embed_utterance(wav)


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
        # Cosine similarity
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
