# Chatterbox TTS Custom Component Services
# These services are automatically registered when the component loads

"""Services provided by the Chatterbox TTS custom component."""
import logging
import functools
import requests
import voluptuous as vol
import os
from datetime import datetime

from homeassistant.core import HomeAssistant, ServiceCall
import homeassistant.helpers.config_validation as cv
from homeassistant.const import ATTR_ENTITY_ID

from .const import DOMAIN, CONF_VOICE, CONF_TEMPERATURE, CONF_EXAGGERATION, CONF_CFG_WEIGHT, CONF_SEED, CONF_SPEED_FACTOR

_LOGGER = logging.getLogger(__name__)

SERVICE_SPEAK = "speak"
SERVICE_INTERRUPT = "interrupt"
SERVICE_SET_VOICE = "set_voice"

ATTR_MESSAGE = "message"
ATTR_VOICE = "voice"
ATTR_TEMPERATURE = "temperature"
ATTR_EXAGGERATION = "exaggeration"
ATTR_CFG_WEIGHT = "cfg_weight"
ATTR_SEED = "seed"
ATTR_SPEED_FACTOR = "speed_factor"

SPEAK_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_VOICE, default="Emily"): cv.string,
        vol.Optional(ATTR_TEMPERATURE, default=0.8): vol.Range(min=0.0, max=1.0),
        vol.Optional(ATTR_EXAGGERATION, default=1.0): vol.Range(min=0.0, max=2.0),
        vol.Optional(ATTR_CFG_WEIGHT, default=0.5): vol.Range(min=0.0, max=1.0),
        vol.Optional(ATTR_SEED, default=0): cv.positive_int,
        vol.Optional(ATTR_SPEED_FACTOR, default=1.0): vol.Range(min=0.5, max=1.5),
    }
)

VOICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_VOICE): cv.string,
    }
)

def async_setup_services(hass: HomeAssistant) -> None:
    """Set up services for Chatterbox TTS."""

    async def handle_speak(call: ServiceCall) -> None:
        """Handle the speak service call."""
        message = call.data.get(ATTR_MESSAGE)
        voice = call.data.get(ATTR_VOICE, "Emily")
        temperature = call.data.get(ATTR_TEMPERATURE, 0.8)
        exaggeration = call.data.get(ATTR_EXAGGERATION, 1.0)
        cfg_weight = call.data.get(ATTR_CFG_WEIGHT, 0.5)
        seed = call.data.get(ATTR_SEED, 0)
        speed_factor = call.data.get(ATTR_SPEED_FACTOR, 1.0)
        
        # Get the first config entry (assuming single instance)
        config_entries = hass.config_entries.async_entries(DOMAIN)
        if not config_entries:
            _LOGGER.error("No Chatterbox TTS configuration found")
            return
            
        config = hass.data[DOMAIN][config_entries[0].entry_id]
        base_url = config["base_url"]
        
        # Add .wav extension if not present
        voice_filename = voice if voice.endswith('.wav') else f"{voice}.wav"
        
        data = {
            "text": message,
            "voice_mode": "predefined",  # Required parameter
            "predefined_voice_id": voice_filename,
            "output_format": "wav",  # Request WAV format to match main entity
            "format": "wav",  # Try alternate parameter name
            "temperature": temperature,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "seed": seed,
            "speed_factor": speed_factor
        }
        
        try:
            url = f"{base_url}/tts"
            response = await hass.async_add_executor_job(
                functools.partial(
                    requests.post,
                    url,
                    json=data,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
            )
            
            if response.status_code == 200:
                _LOGGER.info("Chatterbox TTS spoke: %s (voice: %s)", message, voice)
                
                # Save the audio file permanently (not cache)
                try:
                    # Use www directory for permanent web-accessible storage
                    config_dir = hass.config.config_dir
                    output_dir = os.path.join(config_dir, "www", "chatterbox_tts")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    # Generate timestamp-based filename similar to server
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"tts_output_{timestamp}.wav"
                    filepath = os.path.join(output_dir, filename)
                    
                    # Save the audio data to file
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    _LOGGER.info("Audio saved permanently: %s (%d bytes)", filepath, len(response.content))
                    _LOGGER.info("File accessible at: /local/chatterbox_tts/%s", filename)
                    
                except Exception as save_error:
                    _LOGGER.error("Failed to save audio file: %s", save_error)
                    # Continue anyway - don't fail service just because saving failed
                    
            else:
                _LOGGER.error("Chatterbox TTS speak failed: %s", response.status_code)
                
        except Exception as ex:
            _LOGGER.error("Error calling Chatterbox TTS speak service: %s", ex)

    async def handle_interrupt(call: ServiceCall) -> None:
        """Handle the interrupt service call."""
        # Get the first config entry (assuming single instance)
        config_entries = hass.config_entries.async_entries(DOMAIN)
        if not config_entries:
            _LOGGER.error("No Chatterbox TTS configuration found")
            return
            
        config = hass.data[DOMAIN][config_entries[0].entry_id]
        base_url = config["base_url"]
        
        try:
            url = f"{base_url}/interrupt"
            response = await hass.async_add_executor_job(
                requests.post,
                url,
                {"timeout": 10}
            )
            
            if response.status_code == 200:
                _LOGGER.info("Chatterbox TTS interrupted")
            else:
                _LOGGER.error("Chatterbox TTS interrupt failed: %s", response.status_code)
                
        except Exception as ex:
            _LOGGER.error("Error calling Chatterbox TTS interrupt service: %s", ex)

    async def handle_set_voice(call: ServiceCall) -> None:
        """Handle the set voice service call."""
        voice = call.data.get(ATTR_VOICE)
        
        # Update input_select if it exists
        input_select_entity = "input_select.ha_chatterbox_voice"
        if hass.states.get(input_select_entity):
            await hass.services.async_call(
                "input_select",
                "select_option",
                {ATTR_ENTITY_ID: input_select_entity, "option": voice}
            )
        
        _LOGGER.info("Chatterbox TTS voice set to: %s", voice)

    # Register services
    hass.services.async_register(
        DOMAIN, SERVICE_SPEAK, handle_speak, schema=SPEAK_SCHEMA
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_INTERRUPT, handle_interrupt
    )
    
    hass.services.async_register(
        DOMAIN, SERVICE_SET_VOICE, handle_set_voice, schema=VOICE_SCHEMA
    )
