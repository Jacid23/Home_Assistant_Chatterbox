"""
Chatterbox TTS Sensor Platform for Home Assistant

Provides sensors for monitoring Chatterbox TTS server status and queue.
"""
import logging
import requests
from datetime import timedelta

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 8005
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST, default=DEFAULT_HOST): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    }
)

def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the Chatterbox TTS sensor platform."""
    host = config.get(CONF_HOST, DEFAULT_HOST)
    port = config.get(CONF_PORT, DEFAULT_PORT)
    scan_interval = config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    
    base_url = f"http://{host}:{port}"
    
    sensors = [
       ChatterboxTTSQueueSensor(base_url, scan_interval),
       ChatterboxTTSStatusSensor(base_url, scan_interval),
    ]
    
    add_entities(sensors, True)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Chatterbox TTS sensors from a config entry."""
    _LOGGER.debug("Setting up Chatterbox TTS sensors from config entry")
    
    # Get the stored configuration from the integration
    data = hass.data[DOMAIN][entry.entry_id]
    base_url = data["base_url"]
    
    # Create sensors with default scan interval
    scan_interval = DEFAULT_SCAN_INTERVAL
    
    sensors = [
        ChatterboxTTSQueueSensor(base_url, scan_interval),
        ChatterboxTTSStatusSensor(base_url, scan_interval),
    ]
    
    async_add_entities(sensors, True)
    _LOGGER.debug("Added %d Chatterbox TTS sensors", len(sensors))

class ChatterboxTTSStatusSensor(Entity):
    """Representation of Chatterbox TTS server status sensor."""

    def __init__(self, base_url, scan_interval):
        """Initialize the sensor."""
        self._base_url = base_url
        self._scan_interval = scan_interval
        self._state = None
        self._attributes = {}
        self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Chatterbox TTS Status"

    @property
    def unique_id(self):
        """Return unique ID for this sensor."""
        return "chatterbox_tts_status"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    def update(self):
        """Update the sensor."""
        try:
            url = f"{self._base_url}/health"
            response = requests.get(url, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                self._state = data.get("status", "unknown")
                self._attributes = {
                    "message": data.get("message", ""),
                    "version": data.get("version", ""),
                    "character": data.get("character", ""),
                    "components": data.get("components", {}),
                }
                self._available = True
            else:
                self._state = "error"
                self._available = False
                
        except requests.exceptions.RequestException:
            self._state = "unavailable" 
            self._available = False
            _LOGGER.warning("Could not connect to Chatterbox TTS server")

class ChatterboxTTSQueueSensor(Entity):
    """Representation of Chatterbox TTS queue sensor."""

    def __init__(self, base_url, scan_interval):
        """Initialize the sensor."""
        self._base_url = base_url
        self._scan_interval = scan_interval
        self._state = None
        self._attributes = {}
        self._available = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return "Chatterbox TTS Queue"

    @property
    def unique_id(self):
        """Return unique ID for this sensor."""
        return "Chatterbox_tts_queue"

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def available(self):
        """Return True if entity is available."""
        return self._available

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "items"

    def update(self):
        """Update the sensor."""
        try:
            url = f"{self._base_url}/queue/status"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self._state = data.get("queue_size", 0)
                self._attributes = {
                    "queue_enabled": data.get("queue_enabled", False),
                    "is_playing": data.get("is_playing", False),
                    "current_item": data.get("current_item", None),
                    "estimated_wait_seconds": data.get("estimated_wait_seconds", 0),
                }
                self._available = True
            else:
                self._state = None
                self._available = False
                
        except requests.exceptions.RequestException:
            self._state = None
            self._available = False
            _LOGGER.warning("Could not get Chatterbox TTS queue status")
