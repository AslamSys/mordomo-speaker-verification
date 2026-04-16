import os

NATS_URL: str = os.getenv("NATS_URL", "nats://nats:4222")

# Path to the embeddings volume (bind-mounted from host)
EMBEDDINGS_PATH: str = os.getenv("EMBEDDINGS_PATH", "/data/embeddings")

# People service — used to link voice profiles to person records
SUBJECT_PEOPLE_UPSERT:   str = "mordomo.people.upsert"
SUBJECT_PEOPLE_RESOLVE:  str = "mordomo.people.resolve"

# Inbound — audio for verification
SUBJECT_WAKE_WORD:       str = "mordomo.wake_word.detected"
SUBJECT_AUDIO_SNIPPET:   str = "mordomo.audio.snippet"   # short clip after wake word

# Inbound — enrollment (admin-initiated only)
SUBJECT_ENROLL_REQUEST:  str = "mordomo.speaker.enroll"
SUBJECT_ENROLL_DELETE:   str = "mordomo.speaker.enroll.delete"

# Outbound — verification result (gate signal for the rest of the pipeline)
SUBJECT_VERIFIED:        str = "mordomo.speaker.verified"
SUBJECT_REJECTED:        str = "mordomo.speaker.rejected"

# Outbound — enrollment confirmation
SUBJECT_ENROLLED:        str = "mordomo.speaker.enrolled"

# Verification
VERIFICATION_THRESHOLD: float = float(os.getenv("VERIFICATION_THRESHOLD", "0.75"))

# ── Bootstrap / Setup mode ─────────────────────────────────────────────────
#
# SETUP_MODE controls whether enrollment via NATS is allowed.
#
# SETUP_MODE=false (default, production):
#   - Enrollment via NATS is BLOCKED unless the requester is a known admin.
#   - Admin is the person with is_owner=True in mordomo-people.
#   - If NO admin exists yet (empty embeddings store), SETUP_MODE is
#     automatically activated for ONE enrollment only — this is the bootstrap.
#
# SETUP_MODE=true (explicit, for initial setup):
#   - Set via environment variable on first boot.
#   - Allows a single enrollment without any prior admin check.
#   - Should be removed from the environment after the admin is enrolled.
#   - The container will log a loud WARNING every 60s if this is still set.
#
# Physical setup procedure:
#   1. Set SETUP_MODE=true in docker-compose (or .env) for first boot
#   2. Send one mordomo.speaker.enroll message with role=admin
#   3. Remove SETUP_MODE=true from docker-compose and restart
#   4. From now on, only the enrolled admin can enroll other people
#
SETUP_MODE: bool = os.getenv("SETUP_MODE", "false").lower() == "true"
