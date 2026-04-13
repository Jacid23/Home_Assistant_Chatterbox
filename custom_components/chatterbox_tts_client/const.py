"""
Constants for Chatterbox TTS Client custom component
"""
import logging
import requests

_LOGGER = logging.getLogger(__name__)

DOMAIN = "chatterbox_tts"
CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_VOICE = "voice"
CONF_SPEED = "speed"
CONF_URL = "url"
DEFAULT_URL = "http://localhost:8000/v1/audio/speech"
UNIQUE_ID = "unique_id"

MODELS = ["chatterbox", "chatterbox-turbo", "chatterbox-multilingual"]
VOICES = []  # Populated dynamically from server

SUPPORTED_LANGUAGES = ["en"]

# Chatterbox-specific generation parameters
CONF_TEMPERATURE = "temperature"
CONF_EXAGGERATION = "exaggeration"
CONF_CFG_WEIGHT = "cfg_weight"
CONF_SEED = "seed"

DEFAULT_TEMPERATURE = 0.8
DEFAULT_EXAGGERATION = 0.7
DEFAULT_CFG_WEIGHT = 0.5
DEFAULT_SEED = 0
DEFAULT_SPEED = 1.0


def fetch_voices_from_server(url: str) -> list[str]:
    """Fetch available voices from the Chatterbox TTS server."""
    try:
        base = url.split("/v1/")[0].rstrip("/")
        response = requests.get(f"{base}/v1/audio/voices", timeout=10)
        if response.status_code == 200:
            data = response.json()
            voices = data.get("voices", [])
            if voices:
                _LOGGER.debug("Fetched %d voices from server", len(voices))
                return sorted(voices)
    except Exception as ex:
        _LOGGER.warning("Could not fetch voices from server: %s", ex)
    return []

# Toggle to snapshot & restore volumes
CONF_VOLUME_RESTORE = "volume_restore"

# Toggle to pause/resume media playback
CONF_PAUSE_PLAYBACK = "pause_playback"

# Profile name for sub-entries
CONF_PROFILE_NAME = "profile_name"

# Key for storing message-to-duration cache in hass.data
MESSAGE_DURATIONS_KEY = "message_durations"