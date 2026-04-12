"""Constants for the Chatterbox TTS integration."""
import logging
import requests

_LOGGER = logging.getLogger(__name__)

DOMAIN = "Home_Assistant_Chatterbox"

# Default connection settings
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8005

# Default voice and TTS settings
DEFAULT_VOICE = "Emily.wav"
DEFAULT_TEMPERATURE = 0.8
DEFAULT_EXAGGERATION = 0.7
DEFAULT_CFG_WEIGHT = 0.5
DEFAULT_SEED = 0
DEFAULT_SPEED_FACTOR = 1.0

# Configuration keys
CONF_VOICE = "voice"
CONF_TEMPERATURE = "temperature"
CONF_EXAGGERATION = "exaggeration"
CONF_CFG_WEIGHT = "cfg_weight"
CONF_SEED = "seed"
CONF_SPEED_FACTOR = "speed_factor"


def fetch_voices_from_server(host: str, port: int) -> list[str]:
    """Fetch available voices from the Chatterbox TTS server."""
    try:
        url = f"http://{host}:{port}/v1/audio/voices"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            voices = data.get("voices", [])
            if voices:
                _LOGGER.debug("Fetched %d voices from server", len(voices))
                return sorted(voices)
    except Exception as ex:
        _LOGGER.warning("Could not fetch voices from server: %s", ex)
    return []
