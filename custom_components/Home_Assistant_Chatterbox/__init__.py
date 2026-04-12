"""The Chatterbox TTS integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, DEFAULT_HOST, DEFAULT_PORT

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Chatterbox TTS component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Chatterbox TTS config entry."""
    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    port = entry.data.get(CONF_PORT, DEFAULT_PORT)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "host": host,
        "port": port,
        "base_url": f"http://{host}:{port}",
        "config_entry": entry
    }
    
    _LOGGER.info("Setting up Chatterbox TTS with host: %s, port: %s", host, port)
    
    # Test connection to server
    try:
        import requests
        url = f"http://{host}:{port}/health"
        response = await hass.async_add_executor_job(
            requests.get, url, {"timeout": 10}
        )
        if response.status_code != 200:
            _LOGGER.warning("Chatterbox TTS server not responding at %s, but continuing setup", url)
    except Exception as ex:
        _LOGGER.warning("Failed to connect to Chatterbox TTS server: %s, but continuing setup", ex)
    
    # Forward setup to TTS platform  
    await hass.config_entries.async_forward_entry_setups(entry, ["tts"])
    
    _LOGGER.info("Chatterbox TTS setup complete for entry: %s", entry.entry_id)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload TTS platform
    await hass.config_entries.async_unload_platforms(entry, ["tts"])
    
    # Clean up data
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
