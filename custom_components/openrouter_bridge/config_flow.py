"""Config flow for OpenRouter Bridge."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_DEFAULT_MODEL,
    CONF_ALLOW_MODEL_OVERRIDE,
    DEFAULT_MODEL,
    DOMAIN,
    OPENROUTER_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


async def _fetch_models(hass, api_key: str) -> list[str]:
    """Fetch model IDs from OpenRouter. Returns empty list on failure."""
    try:
        session = async_get_clientsession(hass)
        async with session.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                return []
            data = await resp.json()
            models = [m["id"] for m in (data.get("data") or []) if m.get("id")]
            return sorted(models)
    except Exception:  # noqa: BLE001
        return []


async def _validate_api_key(hass, api_key: str) -> str | None:
    """Return error key or None if key is valid."""
    if not api_key or len(api_key) < 8:
        return "invalid_api_key"
    try:
        session = async_get_clientsession(hass)
        async with session.get(
            f"{OPENROUTER_BASE_URL}/models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 401:
                return "invalid_api_key"
            if resp.status not in (200, 403):
                return "cannot_connect"
            return None
    except aiohttp.ClientConnectorError:
        return "cannot_connect"
    except aiohttp.ClientError:
        return "cannot_connect"


class OpenRouterBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenRouter Bridge."""

    VERSION = 1

    def __init__(self) -> None:
        """Init."""
        self._api_key: str = ""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: API key + default model."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY].strip()
            error = await _validate_api_key(self.hass, api_key)
            if error:
                errors["base"] = error
            else:
                return self.async_create_entry(
                    title="OpenRouter Bridge",
                    data={
                        CONF_API_KEY: api_key,
                        CONF_DEFAULT_MODEL: user_input.get(CONF_DEFAULT_MODEL, DEFAULT_MODEL).strip(),
                        CONF_ALLOW_MODEL_OVERRIDE: user_input.get(CONF_ALLOW_MODEL_OVERRIDE, False),
                    },
                )

        schema = vol.Schema({
            vol.Required(CONF_API_KEY, description={"suggested_value": self._api_key}): str,
            vol.Optional(CONF_DEFAULT_MODEL, default=DEFAULT_MODEL): str,
            vol.Optional(CONF_ALLOW_MODEL_OVERRIDE, default=False): bool,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "openrouter_url": "https://openrouter.ai/keys",
                "free_model": "meta-llama/llama-3.3-70b-instruct:free",
                "claude_model": "anthropic/claude-3.5-sonnet",
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return options flow."""
        return OpenRouterBridgeOptionsFlow()


class OpenRouterBridgeOptionsFlow(OptionsFlow):
    """Options flow for OpenRouter Bridge."""

    def __init__(self) -> None:
        """Init."""
        self._models: list[str] = []

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show options form with live model dropdown."""
        errors: dict[str, str] = {}
        current = self.config_entry.data

        # Fetch model list for dropdown
        if not self._models:
            self._models = await _fetch_models(self.hass, current.get(CONF_API_KEY, ""))

        if user_input is not None:
            new_model = user_input.get(CONF_DEFAULT_MODEL, current.get(CONF_DEFAULT_MODEL, DEFAULT_MODEL)).strip()

            # Merge changes into entry data (options flow updates data)
            updated_data = {
                **current,
                CONF_DEFAULT_MODEL: new_model,
                CONF_ALLOW_MODEL_OVERRIDE: user_input.get(CONF_ALLOW_MODEL_OVERRIDE, False),
            }

            # Update API key only if provided and non-empty
            new_key = user_input.get(CONF_API_KEY, "").strip()
            if new_key:
                error = await _validate_api_key(self.hass, new_key)
                if error:
                    errors["base"] = error
                else:
                    updated_data[CONF_API_KEY] = new_key

            if not errors:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=updated_data
                )
                return self.async_create_entry(title="", data={})

        # Build model selector
        if self._models:
            model_options = {m: m for m in self._models}
            model_field = vol.In(model_options)
        else:
            model_field = str

        schema = vol.Schema({
            vol.Optional(CONF_API_KEY, description={"suggested_value": ""}): str,
            vol.Optional(
                CONF_DEFAULT_MODEL,
                default=current.get(CONF_DEFAULT_MODEL, DEFAULT_MODEL),
            ): model_field,
            vol.Optional(
                CONF_ALLOW_MODEL_OVERRIDE,
                default=current.get(CONF_ALLOW_MODEL_OVERRIDE, False),
            ): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "model_count": str(len(self._models)),
            },
        )
