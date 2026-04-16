"""
mordomo-speaker-verification — entrypoint.

Startup sequence:
  1. Load VoiceEncoder model (Resemblyzer, PyTorch)
  2. Load all stored embeddings into memory
  3. Connect to NATS
  4. Subscribe to verification + enrollment subjects
  5. Log setup mode warning if active

SETUP_MODE warning:
  If SETUP_MODE=true, logs a loud warning every 60s as a reminder
  to disable it after the admin is enrolled.
"""
import asyncio
import logging
import signal

import nats

from src import config
from src.handlers import (
    handle_audio_snippet,
    handle_enroll,
    handle_enroll_delete,
)
from src.verifier import load_encoder, reload_embeddings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mordomo-speaker-verification")

_shutdown = asyncio.Event()


def _handle_signal(sig):
    logger.info("Signal %s received — shutting down", sig.name)
    _shutdown.set()


async def _setup_mode_nag() -> None:
    """Logs a warning every 60s while SETUP_MODE is active."""
    while not _shutdown.is_set():
        logger.warning(
            "⚠️  SETUP_MODE=true IS ACTIVE. "
            "Remove this env var after admin enrollment is complete!"
        )
        await asyncio.sleep(60)


async def run() -> None:
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: _handle_signal(s))

    # 1. Load ML model + stored embeddings
    logger.info("Loading VoiceEncoder (Resemblyzer)...")
    load_encoder()
    reload_embeddings()
    logger.info("Speaker verification ready")

    if config.SETUP_MODE:
        asyncio.create_task(_setup_mode_nag())
        logger.warning("SETUP_MODE=true — bootstrap enrollment is open. Enroll admin then disable.")

    # 2. NATS connection with reconnect
    nc = None
    while not _shutdown.is_set():
        try:
            nc = await nats.connect(
                config.NATS_URL,
                name="mordomo-speaker-verification",
                reconnect_time_wait=2,
                max_reconnect_attempts=-1,
            )
            logger.info("Connected to NATS at %s", config.NATS_URL)

            async def _on_snippet(msg):
                await handle_audio_snippet(nc, msg)

            async def _on_enroll(msg):
                await handle_enroll(nc, msg)

            async def _on_enroll_delete(msg):
                await handle_enroll_delete(nc, msg)

            await nc.subscribe(config.SUBJECT_AUDIO_SNIPPET, cb=_on_snippet)
            await nc.subscribe(config.SUBJECT_ENROLL_REQUEST, cb=_on_enroll)
            await nc.subscribe(config.SUBJECT_ENROLL_DELETE, cb=_on_enroll_delete)

            logger.info(
                "Subscribed to: %s | %s | %s",
                config.SUBJECT_AUDIO_SNIPPET,
                config.SUBJECT_ENROLL_REQUEST,
                config.SUBJECT_ENROLL_DELETE,
            )

            await _shutdown.wait()

        except Exception as exc:
            logger.error("NATS connection error: %s — retrying in 5s", exc)
            await asyncio.sleep(5)
        finally:
            if nc and not nc.is_closed:
                await nc.drain()

    logger.info("Speaker verification stopped")


if __name__ == "__main__":
    asyncio.run(run())
