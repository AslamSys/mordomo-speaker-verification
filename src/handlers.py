"""
NATS handlers for speaker-verification.

NATS subjects handled:
  mordomo.wake_word.detected    → triggers verification on the audio snippet
  mordomo.audio.snippet         → raw PCM audio to verify
  mordomo.speaker.enroll        → admin-initiated enrollment (admin-only gate)
  mordomo.speaker.enroll.delete → admin-initiated deletion (admin-only gate)
"""
import base64
import json
import logging
import uuid

import nats
from nats.aio.client import Client as NATS
from nats.aio.msg import Msg

from src import config
from src.store import (
    delete_embedding,
    has_admin,
    is_admin,
    list_speakers,
    save_embedding,
)
from src.verifier import embed_audio, reload_embeddings, verify

logger = logging.getLogger(__name__)


async def handle_audio_snippet(nc: NATS, msg: Msg) -> None:
    """
    Receives a short audio clip (base64 PCM) after wake word detection.
    Runs verification and publishes result.
    """
    try:
        data = json.loads(msg.data.decode())
        audio_b64: str = data.get("audio_b64", "")
        sample_rate: int = data.get("sample_rate", 16000)

        if not audio_b64:
            logger.warning("handle_audio_snippet: missing audio_b64")
            return

        pcm_bytes = base64.b64decode(audio_b64)
        speaker_id, confidence = verify(pcm_bytes, sample_rate)

        meta = list_speakers()

        if speaker_id:
            profile = meta.get(speaker_id, {})
            payload = json.dumps({
                "speaker_id": speaker_id,
                "person_id": profile.get("person_id"),
                "name": profile.get("name"),
                "role": profile.get("role"),
                "confidence": round(confidence, 4),
            }).encode()
            await nc.publish(config.SUBJECT_VERIFIED, payload)
        else:
            payload = json.dumps({
                "speaker_id": None,
                "confidence": round(confidence, 4),
                "reason": "below_threshold",
            }).encode()
            await nc.publish(config.SUBJECT_REJECTED, payload)

    except Exception as exc:
        logger.error("handle_audio_snippet error: %s", exc)


async def handle_enroll(nc: NATS, msg: Msg) -> None:
    """
    Enroll a new voice profile.

    Payload:
      {
        "requester_speaker_id": "renan-A1",   ← who is making the request (must be admin)
        "name": "Ana",                         ← name for the new person
        "role": "member",                      ← "admin" or "member"
        "audio_b64": "<base64 PCM>",           ← voice sample for the new person
        "sample_rate": 16000,
        "person_id": "<uuid>"                  ← optional, links to mordomo-people record
      }

    Bootstrap exception:
      If no admin exists yet AND (SETUP_MODE=true OR zero enrolled speakers),
      the first enrollment is allowed without a requester check.
      This is the one-time physical setup procedure.
    """
    try:
        data = json.loads(msg.data.decode())
        requester_id: str | None = data.get("requester_speaker_id")
        name: str = data.get("name", "unknown")
        role: str = data.get("role", "member")
        audio_b64: str = data.get("audio_b64", "")
        sample_rate: int = data.get("sample_rate", 16000)
        person_id: str = data.get("person_id") or str(uuid.uuid4())

        if not audio_b64:
            _reply_error(nc, msg, "missing audio_b64")
            return

        # ── Authorization gate ─────────────────────────────────────────────
        admin_exists = has_admin()

        if admin_exists:
            # Normal operation: only an enrolled admin can enroll new people
            if not requester_id or not is_admin(requester_id):
                logger.warning(
                    "Enrollment BLOCKED: requester '%s' is not an admin", requester_id
                )
                _reply_error(nc, msg, "unauthorized: only an admin can enroll new speakers")
                return
        else:
            # Bootstrap: no admin enrolled yet
            if config.SETUP_MODE:
                # Explicit setup mode — allow, but force role=admin for this first enrollment
                logger.warning(
                    "SETUP_MODE active — allowing bootstrap enrollment for '%s'. "
                    "Remove SETUP_MODE=true after this enrollment.",
                    name,
                )
                role = "admin"
            else:
                # Auto-bootstrap: allow ONE admin enrollment without SETUP_MODE
                # This covers the case where the container was just deployed
                # and SETUP_MODE was forgotten. Still forces role=admin.
                logger.warning(
                    "No admin enrolled yet — allowing automatic bootstrap enrollment for '%s'. "
                    "This is a one-time exception. Set SETUP_MODE=true explicitly for safety.",
                    name,
                )
                role = "admin"

        # ── Embed and store ────────────────────────────────────────────────
        pcm_bytes = base64.b64decode(audio_b64)
        embedding = embed_audio(pcm_bytes, sample_rate)

        speaker_id = f"{name.lower().replace(' ', '-')}-{str(uuid.uuid4())[:8]}"
        save_embedding(speaker_id, embedding, person_id=person_id, name=name, role=role)
        reload_embeddings()

        # ── Notify people service ──────────────────────────────────────────
        await nc.publish(
            config.SUBJECT_PEOPLE_UPSERT,
            json.dumps({
                "person_id": person_id,
                "name": name,
                "voice_profile_id": speaker_id,
                "permissions": {
                    "is_owner": role == "admin",
                    "can_authorize_pix": role == "admin",
                    "max_pix_amount": 999999.0 if role == "admin" else 500.0,
                },
            }).encode(),
        )

        # ── Reply ──────────────────────────────────────────────────────────
        result = json.dumps({
            "ok": True,
            "speaker_id": speaker_id,
            "person_id": person_id,
            "name": name,
            "role": role,
        }).encode()
        if msg.reply:
            await nc.publish(msg.reply, result)

        await nc.publish(config.SUBJECT_ENROLLED, result)
        logger.info("Enrolled: speaker_id=%s name=%s role=%s", speaker_id, name, role)

    except Exception as exc:
        logger.error("handle_enroll error: %s", exc)
        _reply_error(nc, msg, str(exc))


async def handle_enroll_delete(nc: NATS, msg: Msg) -> None:
    """
    Delete a voice profile. Admin-only.

    Payload:
      {
        "requester_speaker_id": "renan-A1",
        "target_speaker_id": "ana-abc12345"
      }
    """
    try:
        data = json.loads(msg.data.decode())
        requester_id: str | None = data.get("requester_speaker_id")
        target_id: str = data.get("target_speaker_id", "")

        if not is_admin(requester_id):
            logger.warning("Delete BLOCKED: requester '%s' is not an admin", requester_id)
            _reply_error(nc, msg, "unauthorized: only an admin can delete speakers")
            return

        existed = delete_embedding(target_id)
        reload_embeddings()

        result = json.dumps({"ok": existed, "deleted": target_id}).encode()
        if msg.reply:
            await nc.publish(msg.reply, result)

    except Exception as exc:
        logger.error("handle_enroll_delete error: %s", exc)
        _reply_error(nc, msg, str(exc))


def _reply_error(nc: NATS, msg: Msg, detail: str) -> None:
    if msg.reply:
        import asyncio
        asyncio.create_task(
            nc.publish(msg.reply, json.dumps({"ok": False, "error": detail}).encode())
        )
