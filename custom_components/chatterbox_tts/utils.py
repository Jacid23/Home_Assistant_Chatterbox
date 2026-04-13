"""
Utility functions for Chatterbox TTS integration.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

import asyncio
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.typing import StateType
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.components.media_player import (
    ATTR_MEDIA_VOLUME_LEVEL,
    DOMAIN as MP_DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


def get_media_duration(file_path: str) -> float:
    """
    Get the duration of a media file in seconds.
    First tries to read from metadata, then falls back to ffprobe.
    
    Args:
        file_path: Path to the media file
        
    Returns:
        Duration in seconds as float
    """
    try:
        # First try to get duration from metadata
        cmd_metadata = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            file_path
        ]
        result = subprocess.run(cmd_metadata, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        
        if result.stdout:
            import json
            data = json.loads(result.stdout)
            # Check for our custom metadata
            if "format" in data and "tags" in data["format"]:
                tags = data["format"]["tags"]
                # Look for our duration metadata
                for key, value in tags.items():
                    if "tts_duration_ms" in key:
                        _LOGGER.debug("Found duration in metadata: %s ms", value)
                        return float(value) / 1000.0
        
        # Fallback to standard duration detection
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duration_str = result.stdout.strip()
        return float(duration_str) if duration_str else 0.0
    except Exception as e:
        _LOGGER.error("Error getting media duration: %s", e)
        return 0.0


def normalize_entity_ids(entity_ids: Union[str, List[str]]) -> List[str]:
    """
    Normalize entity IDs to always be a list.
    
    Args:
        entity_ids: Entity ID or list of entity IDs
        
    Returns:
        List of entity IDs
    """
    if not entity_ids:
        return []
    
    if isinstance(entity_ids, str):
        return [entity_ids]
    
    return entity_ids

async def get_media_player_state(
    hass: HomeAssistant, 
    entity_id: str
) -> Tuple[Optional[StateType], Optional[Dict]]:
    """
    Get media player state and attributes if available.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to get state for
        
    Returns:
        Tuple of (state, attributes) or (None, None) if unavailable
    """
    state = hass.states.get(entity_id)
    if state is None or state.state in [STATE_UNAVAILABLE, STATE_UNKNOWN]:
        return None, None
    return state.state, state.attributes


async def set_media_player_volume(
    hass: HomeAssistant, 
    entity_id: str, 
    volume_level: float,
    retries: int = 3,
    retry_delay: float = 0.7
) -> bool:
    """
    Set volume for a media player.
    
    Args:
        hass: Home Assistant instance
        entity_id: Entity ID to set volume for
        volume_level: Volume level to set (0.0-1.0)
        retries: Number of retries
        retry_delay: Delay between retries
        
    Returns:
        Whether volume was successfully set
    """
    # Skip if entity is not available
    state, attributes = await get_media_player_state(hass, entity_id)
    if state is None or attributes is None:
        _LOGGER.debug("Media player %s state not available", entity_id)
        return False
    
    # Skip if entity doesn't have a volume level attribute
    current_volume = attributes.get(ATTR_MEDIA_VOLUME_LEVEL)
    if current_volume is None:
        # For Google speakers, they might not report volume when off
        # Try to set volume anyway and let the device handle it
        _LOGGER.debug("Media player %s has no volume attribute (state: %s), attempting to set volume anyway", 
                      entity_id, state)
        # Don't return False here - continue with volume setting
    
    # Skip if already at target volume (with small tolerance)
    if current_volume is not None and abs(float(current_volume) - volume_level) < 0.01:
        _LOGGER.debug("Volume already at desired level %.2f for %s", volume_level, entity_id)
        return True
    
    # Set volume
    if current_volume is not None:
        _LOGGER.debug("Setting volume for %s from %.2f to %.2f", entity_id, float(current_volume), volume_level)
    else:
        _LOGGER.debug("Setting volume for %s to %.2f (current volume unknown)", entity_id, volume_level)
    
    for attempt in range(1, retries + 1):
        try:
            await hass.services.async_call(
                MP_DOMAIN,
                "volume_set",
                {
                    ATTR_ENTITY_ID: entity_id,
                    ATTR_MEDIA_VOLUME_LEVEL: volume_level,
                },
                blocking=True,
            )
            
            # Brief wait for volume change
            await asyncio.sleep(0.3)
            
            # Verify volume
            new_state, new_attributes = await get_media_player_state(hass, entity_id)
            if new_state is not None and new_attributes is not None:
                new_volume = new_attributes.get(ATTR_MEDIA_VOLUME_LEVEL)
                if new_volume is not None:
                    # Tolerance for volume verification
                    tolerance = 0.1
                    
                    if abs(float(new_volume) - volume_level) < tolerance:
                        _LOGGER.debug(
                            "Successfully set volume for %s to %.2f (actual: %.2f)",
                            entity_id, volume_level, float(new_volume)
                        )
                        return True
                    else:
                        _LOGGER.debug(
                            "Volume not set correctly for %s: target=%.2f, actual=%.2f (difference: %.2f)",
                            entity_id, volume_level, float(new_volume), abs(float(new_volume) - volume_level)
                        )
            
            if attempt < retries:
                # Shorter retry delay
                delay = 0.3
                _LOGGER.debug("Volume change not effective yet, retrying %d/%d after %.1f seconds", 
                             attempt, retries, delay)
                await asyncio.sleep(delay)
            
        except Exception as err:
            _LOGGER.error("Failed to set volume for %s: %s", entity_id, err)
            if attempt < retries:
                await asyncio.sleep(0.3)
    
    # Even if we couldn't verify the volume was set, return True
    # Sometimes devices update their state but don't report it back immediately
    _LOGGER.warning("Could not verify volume was set for %s, continuing anyway", entity_id)
    return True

def get_cascaded_config_value(
    options: Dict[str, Any], 
    data: Dict[str, Any], 
    service_data: Dict[str, Any],
    key: str, 
    default: Any = None
) -> Any:
    """
    Get a configuration value with proper cascade priority:
    service_data > options > data > default
    
    Args:
        options: Component options
        data: Component data
        service_data: Service call data
        key: Key to retrieve
        default: Default value if not found
        
    Returns:
        The value with proper priority
    """
    return service_data.get(
        key, 
        options.get(
            key, 
            data.get(key, default)
        )
    )

async def call_media_player_service(
    hass: HomeAssistant,
    service: str,
    entity_id: Union[str, List[str]],
    extra_data: Optional[Dict[str, Any]] = None,
    blocking: bool = True
) -> None:
    """
    Call a media player service with standardized error handling.
    
    Args:
        hass: Home Assistant instance
        service: Service to call
        entity_id: Entity ID or list of entity IDs
        extra_data: Additional service data
        blocking: Whether to wait for service completion
    """
    service_data = {ATTR_ENTITY_ID: entity_id}
    
    if extra_data:
        service_data.update(extra_data)
    
    try:
        await hass.services.async_call(
            MP_DOMAIN,
            service,
            service_data,
            blocking=blocking,
        )
    except Exception as err:
        entity_ids = normalize_entity_ids(entity_id)
        _LOGGER.error("Failed to call %s for %s: %s", service, ", ".join(entity_ids), err)

