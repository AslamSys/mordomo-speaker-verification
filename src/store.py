"""
Embedding store — persists voice profiles as .npy files on a bound volume.

Layout:
  /data/embeddings/
    metadata.json          ← index: speaker_id → { person_id, name, role, enrolled_at }
    {speaker_id}.npy       ← 256D Resemblyzer embedding (float32)

The metadata.json is the source of truth for which speaker_ids exist.
The .npy files are the actual biometric data.
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from src.config import EMBEDDINGS_PATH

logger = logging.getLogger(__name__)

_META_FILE = Path(EMBEDDINGS_PATH) / "metadata.json"


def _load_meta() -> dict:
    if _META_FILE.exists():
        with open(_META_FILE) as f:
            return json.load(f)
    return {}


def _save_meta(meta: dict) -> None:
    Path(EMBEDDINGS_PATH).mkdir(parents=True, exist_ok=True)
    with open(_META_FILE, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def list_speakers() -> dict:
    """Returns the full metadata dict: { speaker_id: { person_id, name, role, enrolled_at } }"""
    return _load_meta()


def has_admin() -> bool:
    """Returns True if at least one speaker with role=admin is enrolled."""
    meta = _load_meta()
    return any(v.get("role") == "admin" for v in meta.values())


def is_admin(speaker_id: str) -> bool:
    meta = _load_meta()
    entry = meta.get(speaker_id)
    return entry is not None and entry.get("role") == "admin"


def save_embedding(
    speaker_id: str,
    embedding: np.ndarray,
    person_id: str,
    name: str,
    role: str = "member",
) -> None:
    """Persist a voice embedding and update metadata."""
    Path(EMBEDDINGS_PATH).mkdir(parents=True, exist_ok=True)
    npy_path = Path(EMBEDDINGS_PATH) / f"{speaker_id}.npy"
    np.save(str(npy_path), embedding.astype(np.float32))

    meta = _load_meta()
    meta[speaker_id] = {
        "person_id": person_id,
        "name": name,
        "role": role,
        "enrolled_at": datetime.now(timezone.utc).isoformat(),
        "embedding_path": str(npy_path),
    }
    _save_meta(meta)
    logger.info("Embedding saved: speaker_id=%s name=%s role=%s", speaker_id, name, role)


def delete_embedding(speaker_id: str) -> bool:
    """Delete a voice profile. Returns True if it existed."""
    meta = _load_meta()
    if speaker_id not in meta:
        return False

    npy_path = Path(EMBEDDINGS_PATH) / f"{speaker_id}.npy"
    if npy_path.exists():
        npy_path.unlink()

    del meta[speaker_id]
    _save_meta(meta)
    logger.info("Embedding deleted: speaker_id=%s", speaker_id)
    return True


def load_all_embeddings() -> dict[str, np.ndarray]:
    """Load all embeddings into memory. Called once at startup."""
    meta = _load_meta()
    result = {}
    for speaker_id in meta:
        npy_path = Path(EMBEDDINGS_PATH) / f"{speaker_id}.npy"
        if npy_path.exists():
            result[speaker_id] = np.load(str(npy_path))
        else:
            logger.warning("Missing .npy for speaker_id=%s — skipping", speaker_id)
    return result
