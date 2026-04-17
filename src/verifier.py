"""
Verifier — ECAPA-TDNN speaker embeddings via ONNX Runtime.

Model: ECAPA-TDNN exported to ONNX from speechbrain/spkrec-ecapa-voxceleb
  - Embedding dimension: 192D (L2-normalised)
  - EER on VoxCeleb1-O: ~0.87%

The cosine similarity scale for ECAPA-TDNN:
  - Same speaker:      typically 0.30 – 0.80
  - Different speaker: typically -0.10 – 0.25
  - Default threshold: VERIFICATION_THRESHOLD (env var, default 0.25)

⚠️  Embeddings are 192D — incompatible with previously stored 256D Resemblyzer files.
    All speakers must be re-enrolled after upgrading from Resemblyzer.
"""
import logging

import numpy as np
import onnxruntime as ort

from src.config import MODEL_SAVEDIR, VERIFICATION_THRESHOLD
from src.store import load_all_embeddings

logger = logging.getLogger(__name__)

_session: ort.InferenceSession | None = None
_embeddings: dict[str, np.ndarray] = {}


def load_encoder() -> None:
    """
    Load ECAPA-TDNN ONNX model from MODEL_SAVEDIR.
    Expects: MODEL_SAVEDIR/ecapa_tdnn.onnx
    """
    global _session
    model_path = f"{MODEL_SAVEDIR}/ecapa_tdnn.onnx"

    _session = ort.InferenceSession(
        model_path,
        providers=["CPUExecutionProvider"],
    )
    logger.info("ECAPA-TDNN (ONNX) loaded from %s", model_path)


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
    assert _session is not None, "Encoder not loaded — call load_encoder() first"
    audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
    # ONNX model expects [batch, time]
    wavs = audio.reshape(1, -1)
    wav_lens = np.array([1.0], dtype=np.float32)

    input_names = [inp.name for inp in _session.get_inputs()]
    feed = {input_names[0]: wavs}
    if len(input_names) > 1:
        feed[input_names[1]] = wav_lens

    outputs = _session.run(None, feed)
    embedding = outputs[0].squeeze()  # [192]
    return embedding


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
