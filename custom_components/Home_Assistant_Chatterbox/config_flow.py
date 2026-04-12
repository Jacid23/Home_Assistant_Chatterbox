"""Config flow for Home Assistant Chatterbox TTS integration."""
import logging
import voluptuous as vol
import requests

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PORT

from .const import (
    DOMAIN,
    DEFAULT_HOST,
    DEFAULT_PORT,
    CONF_VOICE,
    DEFAULT_VOICE,
    DEFAULT_TEMPERATURE,
    DEFAULT_EXAGGERATION,
    DEFAULT_CFG_WEIGHT,
    DEFAULT_SEED,
    DEFAULT_SPEED_FACTOR,
    CONF_TEMPERATURE,
    CONF_EXAGGERATION,
    CONF_CFG_WEIGHT,
    CONF_SEED,
    CONF_SPEED_FACTOR,
    fetch_voices_from_server,
)

_LOGGER = logging.getLogger(__name__)


class HaChatterboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Assistant Chatterbox TTS."""

    VERSION = 1

    def __init__(self):
        self._host = None
        self._port = None
        self._name = None
        self._voices = []

    async def async_step_user(self, user_input=None):
        """Step 1: Server connection details."""
        errors = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()
            try:
                is_valid = await self._test_connection(host, port)
                if is_valid:
                    self._host = host
                    self._port = port
                    self._name = f"Chatterbox TTS ({host}:{port})"
                    # Fetch voices from the server
                    self._voices = await self.hass.async_add_executor_job(
                        fetch_voices_from_server, host, port
                    )
                    return await self.async_step_settings()
                else:
                    errors["base"] = "cannot_connect"
            except requests.RequestException:
                _LOGGER.error("Connection error to Chatterbox TTS server")
                errors["base"] = "cannot_connect"
            except Exception as ex:
                _LOGGER.error("Unexpected error connecting to Chatterbox TTS: %s", ex)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
                }
            ),
            errors=errors,
        )

    async def async_step_settings(self, user_input=None):
        """Step 2: Voice and TTS settings (voices populated from server)."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._name,
                data={
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_VOICE: user_input.get(CONF_VOICE, DEFAULT_VOICE),
                    CONF_TEMPERATURE: user_input.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE),
                    CONF_EXAGGERATION: user_input.get(CONF_EXAGGERATION, DEFAULT_EXAGGERATION),
                    CONF_CFG_WEIGHT: user_input.get(CONF_CFG_WEIGHT, DEFAULT_CFG_WEIGHT),
                    CONF_SEED: user_input.get(CONF_SEED, DEFAULT_SEED),
                    CONF_SPEED_FACTOR: user_input.get(CONF_SPEED_FACTOR, DEFAULT_SPEED_FACTOR),
                }
            )

        # Build voice selector — dropdown if we got voices, free text if not
        if self._voices:
            voice_schema = vol.In(self._voices)
            default_voice = self._voices[0] if DEFAULT_VOICE not in self._voices else DEFAULT_VOICE
        else:
            voice_schema = str
            default_voice = DEFAULT_VOICE

        return self.async_show_form(
            step_id="settings",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_VOICE, default=default_voice): voice_schema,
                    vol.Optional(CONF_TEMPERATURE, default=DEFAULT_TEMPERATURE): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                    ),
                    vol.Optional(CONF_EXAGGERATION, default=DEFAULT_EXAGGERATION): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=2.0)
                    ),
                    vol.Optional(CONF_CFG_WEIGHT, default=DEFAULT_CFG_WEIGHT): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                    ),
                    vol.Optional(CONF_SEED, default=DEFAULT_SEED): vol.Coerce(int),
                    vol.Optional(CONF_SPEED_FACTOR, default=DEFAULT_SPEED_FACTOR): vol.All(
                        vol.Coerce(float), vol.Range(min=0.5, max=2.0)
                    ),
                }
            ),
        )

    async def _test_connection(self, host: str, port: int) -> bool:
        url = f"http://{host}:{port}/health"
        def _make_request():
            try:
                response = requests.get(url, timeout=10)
                return response.status_code == 200
            except requests.RequestException as ex:
                _LOGGER.error("Connection test failed: %s", ex)
                raise
        return await self.hass.async_add_executor_job(_make_request)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HAChatterboxOptionsFlowHandler(config_entry)


class HAChatterboxOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_tts_options(user_input)

    async def async_step_tts_options(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        data = self.config_entry.data
        current_voice = options.get(CONF_VOICE, data.get(CONF_VOICE, DEFAULT_VOICE))
        current_temperature = options.get(CONF_TEMPERATURE, data.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))
        current_exaggeration = options.get(CONF_EXAGGERATION, data.get(CONF_EXAGGERATION, DEFAULT_EXAGGERATION))
        current_cfg_weight = options.get(CONF_CFG_WEIGHT, data.get(CONF_CFG_WEIGHT, DEFAULT_CFG_WEIGHT))
        current_seed = options.get(CONF_SEED, data.get(CONF_SEED, DEFAULT_SEED))
        current_speed = options.get(CONF_SPEED_FACTOR, data.get(CONF_SPEED_FACTOR, DEFAULT_SPEED_FACTOR))

        # Fetch voices live from the server
        host = data.get(CONF_HOST, DEFAULT_HOST)
        port = data.get(CONF_PORT, DEFAULT_PORT)
        voices = await self.hass.async_add_executor_job(
            fetch_voices_from_server, host, port
        )

        if voices:
            voice_schema = vol.In(voices)
            if current_voice not in voices:
                current_voice = voices[0]
        else:
            voice_schema = str

        return self.async_show_form(
            step_id="tts_options",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_VOICE, default=current_voice): voice_schema,
                    vol.Optional(CONF_TEMPERATURE, default=current_temperature): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                    ),
                    vol.Optional(CONF_EXAGGERATION, default=current_exaggeration): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=2.0)
                    ),
                    vol.Optional(CONF_CFG_WEIGHT, default=current_cfg_weight): vol.All(
                        vol.Coerce(float), vol.Range(min=0.0, max=1.0)
                    ),
                    vol.Optional(CONF_SEED, default=current_seed): vol.Coerce(int),
                    vol.Optional(CONF_SPEED_FACTOR, default=current_speed): vol.All(
                        vol.Coerce(float), vol.Range(min=0.5, max=2.0)
                    ),
                }
            ),
        )
