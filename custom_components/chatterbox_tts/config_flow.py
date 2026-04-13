# config_flow.py
"""
Config flow for Chatterbox TTS.
"""
from __future__ import annotations
from typing import Any
import voluptuous as vol
import logging
from urllib.parse import urlparse
import uuid
import aiohttp

from homeassistant import data_entry_flow
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigSubentryFlow,
    ConfigEntry,
    ConfigFlowResult,
    SubentryFlowResult,
)
from homeassistant.helpers.selector import selector, TemplateSelector
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import callback

from .const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_VOICE,
    CONF_SPEED,
    CONF_URL,
    DEFAULT_URL,
    DOMAIN,
    MODELS,
    UNIQUE_ID,
    CONF_PROFILE_NAME,
    CONF_TEMPERATURE,
    CONF_EXAGGERATION,
    CONF_CFG_WEIGHT,
    CONF_SEED,
    DEFAULT_TEMPERATURE,
    DEFAULT_EXAGGERATION,
    DEFAULT_CFG_WEIGHT,
    DEFAULT_SEED,
    DEFAULT_SPEED,
    fetch_voices_from_server,
)

SUBENTRY_TYPE_PROFILE = "profile"

_LOGGER = logging.getLogger(__name__)

# Custom exceptions for API validation
class InvalidAPIKey(HomeAssistantError):
    """Error to indicate invalid API key."""

class CannotConnect(HomeAssistantError):
    """Error to indicate connection failure."""


def generate_entry_id() -> str:
    return str(uuid.uuid4())


async def async_validate_connection(url: str, api_key: str = "") -> bool:
    """Check if the Chatterbox TTS server's /health endpoint is reachable.

    Returns True if the server responds with 200, False otherwise.
    Never raises — a missing or unreachable /health endpoint is non-fatal;
    the actual TTS request in async_validate_api_key will confirm connectivity.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    base = url.split("/v1/")[0].rstrip("/")
    health_url = f"{base}/health"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                health_url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status == 200:
                    _LOGGER.debug("Server connection validated via /health")
                    return True
                _LOGGER.debug(
                    "Server /health returned %d — skipping health check",
                    response.status,
                )
                return False
    except Exception as err:
        _LOGGER.debug("Server /health not reachable (%s) — skipping health check", err)
        return False


async def async_validate_api_key(api_key: str, url: str) -> bool:
    """Validate the API key by making a minimal test TTS request.

    Args:
        api_key: The API key to validate
        url: The API endpoint URL

    Returns:
        True if validation succeeds

    Raises:
        InvalidAPIKey: If the API key is invalid (401/403)
        CannotConnect: If unable to connect to the API
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    payload = {
        "model": "chatterbox",
        "input": ".",
        "voice": "default",
        "response_format": "mp3",
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                if response.status == 401:
                    _LOGGER.error("API key validation failed: Unauthorized (401)")
                    raise InvalidAPIKey("Invalid API key")
                elif response.status == 403:
                    _LOGGER.error("API key validation failed: Forbidden (403)")
                    raise InvalidAPIKey("API key does not have required permissions")
                elif response.status >= 400:
                    _LOGGER.error("API validation failed with status %d", response.status)
                    raise CannotConnect(f"API returned status {response.status}")

                _LOGGER.debug("API key validation successful")
                return True

    except aiohttp.ClientError as err:
        _LOGGER.error("Connection error during API validation: %s", err)
        raise CannotConnect(f"Cannot connect to API: {err}") from err
    except TimeoutError as err:
        _LOGGER.error("Timeout during API validation")
        raise CannotConnect("Connection timed out") from err

class ChatterboxTTSConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Chatterbox TTS."""

    VERSION = 2
    MINOR_VERSION = 1

    data_schema = vol.Schema(
        {
            vol.Optional(CONF_API_KEY, default=""): str,
            vol.Optional(CONF_URL, default=DEFAULT_URL): str,
        }
    )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step — server URL and optional API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                api_key = user_input.get(CONF_API_KEY, "")
                api_url = user_input.get(CONF_URL, DEFAULT_URL)

                # Check for duplicate URL
                for entry in self._async_current_entries():
                    if entry.data.get(CONF_URL) == api_url:
                        errors["base"] = "already_configured"
                        return self.async_show_form(
                            step_id="user",
                            data_schema=self.data_schema,
                            errors=errors,
                        )

                # Check for duplicate API key
                if api_key:
                    for entry in self._async_current_entries():
                        if entry.data.get(CONF_API_KEY) == api_key:
                            errors["base"] = "duplicate_api_key"
                            return self.async_show_form(
                                step_id="user",
                                data_schema=self.data_schema,
                                errors=errors,
                            )

                # Best-effort health check (non-fatal if /health is absent)
                await async_validate_connection(api_url, api_key)

                # Validate API key if provided
                if api_key:
                    await async_validate_api_key(api_key, api_url)

                # Generate unique ID from URL
                import hashlib

                url_hash = hashlib.sha256(api_url.encode()).hexdigest()[:16]
                unique_id = f"chatterbox_tts_{url_hash}"
                user_input[UNIQUE_ID] = unique_id
                await self.async_set_unique_id(unique_id)

                hostname = urlparse(api_url).hostname
                return self.async_create_entry(
                    title=f"Chatterbox TTS ({hostname})",
                    data=user_input,
                )
            except data_entry_flow.AbortFlow:
                return self.async_abort(reason="already_configured")
            except InvalidAPIKey:
                errors["base"] = "invalid_api_key"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="user",
            data_schema=self.data_schema,
            errors=errors,
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentry types — always supported."""
        return {SUBENTRY_TYPE_PROFILE: ChatterboxTTSProfileSubentryFlow}

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle reauthorization flow triggered by auth failure."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context.get("entry_id")
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reauthorization confirmation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                api_key = user_input.get(CONF_API_KEY)
                api_url = self._reauth_entry.data.get(CONF_URL, DEFAULT_URL)

                await async_validate_api_key(api_key, api_url)

                self.hass.config_entries.async_update_entry(
                    self._reauth_entry,
                    data={**self._reauth_entry.data, CONF_API_KEY: api_key},
                )
                await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")

            except InvalidAPIKey:
                errors["base"] = "invalid_api_key"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during reauth")
                errors["base"] = "unknown_error"

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({
                vol.Required(CONF_API_KEY): str,
            }),
            errors=errors,
            description_placeholders={
                "title": self._reauth_entry.title if self._reauth_entry else "Chatterbox TTS"
            },
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the parent entry."""
        errors: dict[str, str] = {}

        entry_id = self.context.get("entry_id")
        if not entry_id:
            return self.async_abort(reason="unknown_error")

        reconfigure_entry = self.hass.config_entries.async_get_entry(entry_id)
        if not reconfigure_entry:
            return self.async_abort(reason="unknown_error")

        if user_input is not None:
            try:
                api_url = user_input.get(CONF_URL, DEFAULT_URL)
                api_key = user_input.get(CONF_API_KEY, "")

                # Check for duplicate URL (exclude current entry)
                for entry in self._async_current_entries():
                    if (
                        entry.entry_id != reconfigure_entry.entry_id
                        and entry.data.get(CONF_URL) == api_url
                    ):
                        errors["base"] = "already_configured"
                        break

                # Check for duplicate API key (exclude current entry)
                if not errors and api_key:
                    for entry in self._async_current_entries():
                        if (
                            entry.entry_id != reconfigure_entry.entry_id
                            and entry.data.get(CONF_API_KEY) == api_key
                        ):
                            errors["base"] = "duplicate_api_key"
                            break

                if not errors:
                    # Best-effort health check (non-fatal if /health is absent)
                    await async_validate_connection(api_url, api_key)

                    if api_key:
                        await async_validate_api_key(api_key, api_url)

                    await self.async_set_unique_id(reconfigure_entry.unique_id)
                    self._abort_if_unique_id_mismatch()

                    hostname = urlparse(api_url).hostname
                    return self.async_update_reload_and_abort(
                        reconfigure_entry,
                        data_updates=user_input,
                        title=f"Chatterbox TTS ({hostname})",
                    )

            except InvalidAPIKey:
                errors["base"] = "invalid_api_key"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown_error"

        current_data = reconfigure_entry.data
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_URL,
                    description={
                        "suggested_value": current_data.get(CONF_URL, DEFAULT_URL)
                    },
                ): str,
                vol.Optional(
                    CONF_API_KEY,
                    description={
                        "suggested_value": current_data.get(CONF_API_KEY, "")
                    },
                ): str,
            }
        )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )


def _build_voice_options(url: str) -> list[str]:
    """Build voice options list — dynamic from server, with fallback."""
    voices = fetch_voices_from_server(url)
    return voices if voices else ["default"]


def _profile_schema(
    voices: list[str],
    defaults: dict[str, Any] | None = None,
    include_name: bool = True,
) -> vol.Schema:
    """Build the shared schema for profile create/reconfigure.

    Args:
        voices: List of voice names from server.
        defaults: Existing data for reconfigure (None for create).
        include_name: Whether to include profile_name field.
    """
    d = defaults or {}
    fields: dict = {}

    if include_name:
        fields[vol.Required(CONF_PROFILE_NAME)] = str

    fields[vol.Required(CONF_MODEL, default=d.get(CONF_MODEL, MODELS[0]))] = selector(
        {
            "select": {
                "options": MODELS,
                "mode": "dropdown",
                "sort": True,
                "custom_value": True,
            }
        }
    )

    fields[vol.Required(CONF_VOICE, default=d.get(CONF_VOICE, voices[0] if voices else "default"))] = selector(
        {
            "select": {
                "options": voices,
                "mode": "dropdown",
                "sort": True,
                "custom_value": True,
            }
        }
    )

    fields[vol.Optional(CONF_SPEED, default=d.get(CONF_SPEED, DEFAULT_SPEED))] = selector(
        {"number": {"min": 0.25, "max": 4.0, "step": 0.05, "mode": "slider"}}
    )

    fields[vol.Optional(CONF_TEMPERATURE, default=d.get(CONF_TEMPERATURE, DEFAULT_TEMPERATURE))] = selector(
        {"number": {"min": 0.0, "max": 1.5, "step": 0.05, "mode": "slider"}}
    )

    fields[vol.Optional(CONF_EXAGGERATION, default=d.get(CONF_EXAGGERATION, DEFAULT_EXAGGERATION))] = selector(
        {"number": {"min": 0.25, "max": 2.0, "step": 0.05, "mode": "slider"}}
    )

    fields[vol.Optional(CONF_CFG_WEIGHT, default=d.get(CONF_CFG_WEIGHT, DEFAULT_CFG_WEIGHT))] = selector(
        {"number": {"min": 0.2, "max": 1.0, "step": 0.05, "mode": "slider"}}
    )

    fields[vol.Optional(CONF_SEED, default=d.get(CONF_SEED, DEFAULT_SEED))] = selector(
        {"number": {"min": 0, "max": 2147483647, "step": 1, "mode": "box"}}
    )

    return vol.Schema(fields)


class ChatterboxTTSProfileSubentryFlow(ConfigSubentryFlow):
    """Handle a subentry flow for Chatterbox TTS profiles."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle profile creation."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                profile_name = user_input.get(CONF_PROFILE_NAME, "")
                if not profile_name:
                    raise ValueError("Profile name is required")

                # Duplicate name check
                parent_entry = self._get_entry()
                if hasattr(parent_entry, "subentries") and parent_entry.subentries:
                    for sub in parent_entry.subentries.values():
                        if sub.data.get(CONF_PROFILE_NAME) == profile_name:
                            raise ValueError("Profile name already exists")

                user_input[UNIQUE_ID] = generate_entry_id()

                return self.async_create_entry(
                    title=profile_name,
                    data=user_input,
                )

            except ValueError as e:
                _LOGGER.exception(str(e))
                errors["base"] = str(e)
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown_error"

        # Fetch voices from server
        parent = self._get_entry()
        url = parent.data.get(CONF_URL, DEFAULT_URL)
        voices = await self.hass.async_add_executor_job(_build_voice_options, url)

        return self.async_show_form(
            step_id="user",
            data_schema=_profile_schema(voices, include_name=True),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Handle profile reconfiguration."""
        errors: dict[str, str] = {}

        try:
            subentry = self._get_reconfigure_subentry()
        except Exception:
            return self.async_abort(reason="subentry_not_found")

        if not subentry:
            return self.async_abort(reason="subentry_not_found")

        if user_input is not None:
            try:
                # Preserve profile name and unique ID from existing subentry
                updated_data = {**subentry.data, **user_input}

                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    data=updated_data,
                )
            except Exception:
                _LOGGER.exception("Unexpected error")
                errors["base"] = "unknown_error"

        # Fetch voices from server
        parent = self._get_entry()
        url = parent.data.get(CONF_URL, DEFAULT_URL)
        voices = await self.hass.async_add_executor_job(_build_voice_options, url)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_profile_schema(
                voices, defaults=dict(subentry.data), include_name=False
            ),
            errors=errors,
        )


__all__ = ["ChatterboxTTSConfigFlow", "ChatterboxTTSProfileSubentryFlow"]