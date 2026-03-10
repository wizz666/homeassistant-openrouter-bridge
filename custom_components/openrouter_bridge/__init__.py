"""OpenRouter Bridge – Anthropic-compatible proxy for OpenRouter."""
from __future__ import annotations

import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import OpenRouterMessagesView, OpenRouterModelsView, OpenRouterHealthView
from .const import DOMAIN, OPENROUTER_BASE_URL, STATS_KEY

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

# Views are registered once per HA instance, not per config entry.
_VIEWS_REGISTERED = False


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the OpenRouter Bridge component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up OpenRouter Bridge from a config entry."""
    global _VIEWS_REGISTERED  # noqa: PLW0603

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)

    # Validate API key on setup (quick connectivity check)
    api_key: str = entry.data.get("api_key", "")
    if api_key:
        try:
            session = hass.helpers.aiohttp_client.async_get_clientsession()
            async with session.get(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 401:
                    _LOGGER.error("OpenRouter Bridge: invalid API key")
                    raise ConfigEntryNotReady("Invalid OpenRouter API key")
        except aiohttp.ClientConnectorError as exc:
            raise ConfigEntryNotReady(f"Cannot reach OpenRouter: {exc}") from exc
        except aiohttp.ClientError as exc:
            _LOGGER.warning("OpenRouter connectivity check failed: %s", exc)

    # Register HTTP views once (they survive config entry reloads)
    if not _VIEWS_REGISTERED:
        hass.http.register_view(OpenRouterHealthView(hass))
        hass.http.register_view(OpenRouterMessagesView(hass))
        hass.http.register_view(OpenRouterModelsView(hass))
        _VIEWS_REGISTERED = True
        _LOGGER.info(
            "OpenRouter Bridge proxy active at /api/openrouter_bridge – "
            "set ANTHROPIC_BASE_URL=http://<ha-ip>:8123/api/openrouter_bridge"
        )

    # Initialise stats storage
    hass.data[DOMAIN].setdefault(STATS_KEY, {
        "total_requests": 0,
        "last_model": "",
        "requests_by_model": {},
    })

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload when options change
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    hass.data[DOMAIN][entry.entry_id] = dict(entry.data)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
