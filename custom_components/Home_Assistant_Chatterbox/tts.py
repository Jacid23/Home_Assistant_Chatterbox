"""Chatterbox TTS Provider Platform for Home Assistant."""
import logging
import requests
import functools
import voluptuous as vol

from homeassistant.components.tts import Provider, PLATFORM_SCHEMA, TtsAudioType
from homeassistant.const import CONF_NAME, CONF_HOST, CONF_PORT
import homeassistant.helpers.config_validation as cv
from .const import (
    DOMAIN,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_VOICE,
    DEFAULT_TEMPERATURE,
    DEFAULT_EXAGGERATION,
    DEFAULT_CFG_WEIGHT,
    DEFAULT_SEED,
    DEFAULT_SPEED_FACTOR,
    CONF_VOICE,
    CONF_TEMPERATURE,
    CONF_EXAGGERATION,
    CONF_CFG_WEIGHT,
    CONF_SEED,
    CONF_SPEED_FACTOR,
    fetch_voices_from_server,
)

_LOGGER = logging.getLogger(__name__)

# Platform schema for TTS configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default="Chatterbox TTS"): cv.string,
})


class ChatterboxTTSProvider(Provider):
    """Chatterbox TTS Provider."""

    def __init__(self, hass, host, port, base_url, config_entry):
        """Initialize the TTS provider."""
        self.hass = hass
        self._host = host
        self._port = port
        self._base_url = base_url
        self._config_entry = config_entry
        self._voices_cache = None

        # Get configuration from config entry
        opts = (config_entry.options if config_entry else {})
        data = (config_entry.data if config_entry else {})
        self._language = data.get("language", "en-US")
        self._voice = opts.get(CONF_VOICE, data.get(CONF_VOICE, DEFAULT_VOICE))
        self._temperature = opts.get(CONF_TEMPERATURE, data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))
        self._exaggeration = opts.get(CONF_EXAGGERATION, data.get(CONF_EXAGGERATION, DEFAULT_EXAGGERATION))
        self._cfg_weight = opts.get(CONF_CFG_WEIGHT, data.get(CONF_CFG_WEIGHT, DEFAULT_CFG_WEIGHT))
        self._seed = opts.get(CONF_SEED, data.get(CONF_SEED, DEFAULT_SEED))
        self._speed_factor = opts.get(CONF_SPEED_FACTOR, data.get(CONF_SPEED_FACTOR, DEFAULT_SPEED_FACTOR))

        _LOGGER.info("ChatterboxTTSProvider initialized for %s:%s", host, port)

    def _get_voices(self):
        """Get voices from server, caching the result."""
        if self._voices_cache is None:
            self._voices_cache = fetch_voices_from_server(self._host, self._port)
        return self._voices_cache or [DEFAULT_VOICE]

    @property
    def default_language(self):
        """Return the default language."""
        return "en-US"

    @property
    def supported_languages(self):
        """Return list of supported languages."""
        return ["en", "en-US"]

    @property
    def supported_options(self):
        """Return list of supported options."""
        return [CONF_VOICE, CONF_TEMPERATURE, CONF_EXAGGERATION, CONF_CFG_WEIGHT, CONF_SEED, CONF_SPEED_FACTOR]

    @property
    def default_options(self):
        """Return a dict including default options."""
        voices = self._get_voices()
        return {
            CONF_VOICE: voices[0] if voices else DEFAULT_VOICE,
            CONF_TEMPERATURE: self._temperature,
            CONF_EXAGGERATION: self._exaggeration,
            CONF_CFG_WEIGHT: self._cfg_weight,
            CONF_SEED: self._seed,
            CONF_SPEED_FACTOR: self._speed_factor,
        }

    @property
    def supported_voices(self):
        """Return list of supported voices."""
        return self._get_voices()

    @property
    def default_voice(self):
        """Return the default voice."""
        voices = self._get_voices()
        return voices[0] if voices else DEFAULT_VOICE

    @property
    def name(self):
        """Return the name of the TTS provider."""
        return "Chatterbox TTS"

    async def async_get_tts_audio(self, message, language, options=None) -> TtsAudioType:
        """Load TTS from Chatterbox server."""
        options = options or {}
        selected_voice = options.get(CONF_VOICE, self._voice)
        temperature = options.get(CONF_TEMPERATURE, self._temperature)
        exaggeration = options.get(CONF_EXAGGERATION, self._exaggeration)
        cfg_weight = options.get(CONF_CFG_WEIGHT, self._cfg_weight)
        seed = options.get(CONF_SEED, self._seed)
        speed_factor = options.get(CONF_SPEED_FACTOR, self._speed_factor)

        data = {
            "text": message,
            "predefined_voice_id": selected_voice,
            "temperature": temperature,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "seed": seed,
            "speed_factor": speed_factor,
            "output_format": "wav",
        }

        _LOGGER.debug("Chatterbox TTS request: %s", data)

        try:
            url = f"{self._base_url}/tts"
            response = await self.hass.async_add_executor_job(
                functools.partial(
                    requests.post,
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
            )
            if response.status_code == 200:
                return ("wav", response.content)
            else:
                _LOGGER.error("Chatterbox TTS request failed: %s %s", response.status_code, response.text)
                return ("wav", b"")
        except Exception as ex:
            _LOGGER.error("Error connecting to Chatterbox TTS: %s", ex)
            return ("wav", b"")


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up TTS platform from config entry."""
    _LOGGER.debug("Setting up TTS platform from config entry: %s", config_entry.entry_id)

    # Get domain data
    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(config_entry.entry_id)

    if not entry_data:
        _LOGGER.error("No entry data found for config entry: %s", config_entry.entry_id)
        return False

    # Create provider
    provider = ChatterboxTTSProvider(
        hass=hass,
        host=entry_data["host"],
        port=entry_data["port"],
        base_url=entry_data["base_url"],
        config_entry=config_entry,
    )

    # Store provider in hass data for async_get_engine to find
    hass.data[DOMAIN][f"{config_entry.entry_id}_provider"] = provider
    _LOGGER.debug("TTS Provider stored in hass.data")

    return True


async def async_get_engine(hass, config, discovery_info=None):
    """Get the TTS engine."""
    _LOGGER.debug("async_get_engine called")

    # Find our stored provider
    domain_data = hass.data.get(DOMAIN, {})
    for key, value in domain_data.items():
        if key.endswith("_provider") and isinstance(value, ChatterboxTTSProvider):
            _LOGGER.debug("Found and returning TTS provider")
            return value

    _LOGGER.debug("No TTS provider found, creating default")
    return ChatterboxTTSProvider(
        hass=hass,
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        base_url=f"http://{DEFAULT_HOST}:{DEFAULT_PORT}",
        config_entry=None,
    )
