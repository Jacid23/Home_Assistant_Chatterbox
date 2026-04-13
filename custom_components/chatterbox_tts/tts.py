"""Chatterbox TTS Entity Platform for Home Assistant."""
import logging
import requests
import functools

from homeassistant.components.tts import TextToSpeechEntity, TtsAudioType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Chatterbox TTS entity from a config entry."""
    _LOGGER.debug("Setting up TTS entity for config entry: %s", config_entry.entry_id)

    domain_data = hass.data.get(DOMAIN, {})
    entry_data = domain_data.get(config_entry.entry_id)

    if not entry_data:
        _LOGGER.error("No entry data found for config entry: %s", config_entry.entry_id)
        return

    entity = ChatterboxTTSEntity(hass, config_entry, entry_data)
    async_add_entities([entity])
    _LOGGER.info("Chatterbox TTS entity created for %s:%s", entry_data["host"], entry_data["port"])


class ChatterboxTTSEntity(TextToSpeechEntity):
    """Chatterbox TTS Entity."""

    _attr_has_entity_name = True
    _attr_name = "Chatterbox TTS"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, entry_data: dict):
        """Initialize the TTS entity."""
        self.hass = hass
        self._config_entry = config_entry
        self._host = entry_data["host"]
        self._port = entry_data["port"]
        self._base_url = entry_data["base_url"]
        self._voices_cache = None

        self._attr_unique_id = f"chatterbox_tts_{self._host}_{self._port}"

        # Get configuration from config entry
        opts = config_entry.options or {}
        data = config_entry.data or {}
        self._voice = opts.get(CONF_VOICE, data.get(CONF_VOICE, DEFAULT_VOICE))
        self._temperature = opts.get(CONF_TEMPERATURE, data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))
        self._exaggeration = opts.get(CONF_EXAGGERATION, data.get(CONF_EXAGGERATION, DEFAULT_EXAGGERATION))
        self._cfg_weight = opts.get(CONF_CFG_WEIGHT, data.get(CONF_CFG_WEIGHT, DEFAULT_CFG_WEIGHT))
        self._seed = opts.get(CONF_SEED, data.get(CONF_SEED, DEFAULT_SEED))
        self._speed_factor = opts.get(CONF_SPEED_FACTOR, data.get(CONF_SPEED_FACTOR, DEFAULT_SPEED_FACTOR))

    def _get_voices(self):
        """Get voices from server, caching the result."""
        if self._voices_cache is None:
            self._voices_cache = fetch_voices_from_server(self._host, self._port)
        return self._voices_cache or [DEFAULT_VOICE]

    @property
    def default_language(self) -> str:
        return "en"

    @property
    def supported_languages(self) -> list[str]:
        return ["en", "en-US"]

    @property
    def supported_options(self) -> list[str]:
        return [CONF_VOICE, CONF_TEMPERATURE, CONF_EXAGGERATION, CONF_CFG_WEIGHT, CONF_SEED, CONF_SPEED_FACTOR]

    @property
    def default_options(self) -> dict:
        return {
            CONF_VOICE: self._voice,
            CONF_TEMPERATURE: self._temperature,
            CONF_EXAGGERATION: self._exaggeration,
            CONF_CFG_WEIGHT: self._cfg_weight,
            CONF_SEED: self._seed,
            CONF_SPEED_FACTOR: self._speed_factor,
        }

    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, f"{self._host}:{self._port}")},
            "name": "Chatterbox TTS Server",
            "manufacturer": "Chatterbox",
            "model": "TTS Server",
            "configuration_url": f"http://{self._host}:{self._port}",
        }

    async def async_get_tts_audio(self, message: str, language: str, options: dict | None = None) -> TtsAudioType:
        """Generate TTS audio from the Chatterbox server."""
        options = options or {}
        selected_voice = options.get(CONF_VOICE, self._voice)
        temperature = options.get(CONF_TEMPERATURE, self._temperature)
        exaggeration = options.get(CONF_EXAGGERATION, self._exaggeration)
        cfg_weight = options.get(CONF_CFG_WEIGHT, self._cfg_weight)
        seed = options.get(CONF_SEED, self._seed)
        speed_factor = options.get(CONF_SPEED_FACTOR, self._speed_factor)

        data = {
            "model": "chatterbox-turbo",
            "input": message,
            "voice": selected_voice,
            "response_format": "wav",
            "speed": speed_factor,
            "temperature": temperature,
            "seed": seed,
        }

        _LOGGER.debug("Chatterbox TTS request: %s", data)

        try:
            url = f"{self._base_url}/v1/audio/speech"
            headers = {"Content-Type": "application/json"}
            response = await self.hass.async_add_executor_job(
                functools.partial(
                    requests.post,
                    url,
                    json=data,
                    headers=headers,
                    timeout=120
                )
            )
            if response.status_code == 200:
                _LOGGER.info("Chatterbox TTS generated %d bytes for voice %s", len(response.content), selected_voice)
                return ("wav", response.content)
            else:
                _LOGGER.error("Chatterbox TTS request failed: %s %s", response.status_code, response.text)
                return (None, None)
        except Exception as ex:
            _LOGGER.error("Error connecting to Chatterbox TTS: %s", ex)
            return (None, None)
