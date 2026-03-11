"""Sensors for OpenRouter Bridge."""
from __future__ import annotations

import logging
from datetime import timedelta

import aiohttp

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, OPENROUTER_BASE_URL, STATS_KEY

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = OpenRouterCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([
        OpenRouterStatusSensor(coordinator, entry),
        OpenRouterRequestsSensor(coordinator, entry),
        OpenRouterModelCountSensor(coordinator, entry),
        OpenRouterLastModelSensor(hass, entry),
    ])


class OpenRouterCoordinator(DataUpdateCoordinator):
    """Fetch OpenRouter model count and status."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Init coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry

    async def _async_update_data(self) -> dict:
        """Fetch model list from OpenRouter."""
        api_key = self.entry.data.get("api_key", "")
        if not api_key:
            return {"status": "unconfigured", "model_count": 0, "free_model_count": 0}

        try:
            session = async_get_clientsession(self.hass)
            async with session.get(
                f"{OPENROUTER_BASE_URL}/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status == 401:
                    return {"status": "invalid_key", "model_count": 0, "free_model_count": 0}
                if resp.status != 200:
                    raise UpdateFailed(f"OpenRouter returned {resp.status}")
                data = await resp.json()
        except aiohttp.ClientError as exc:
            raise UpdateFailed(f"Cannot reach OpenRouter: {exc}") from exc

        models = data.get("data") or []
        free_count = sum([1 for m in models if ":free" in m.get("id", "")])
        return {
            "status": "ok",
            "model_count": len(models),
            "free_model_count": free_count,
        }


class _BaseSensor(SensorEntity):
    """Shared base for OpenRouter sensors."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self.__class__.__name__}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "OpenRouter Bridge",
            "manufacturer": "OpenRouter",
            "model": "API Proxy",
            "entry_type": "service",
        }


class OpenRouterStatusSensor(_BaseSensor):
    """Proxy / API key status."""

    _attr_name = "Status"
    _attr_icon = "mdi:api"

    def __init__(self, coordinator: OpenRouterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._coordinator = coordinator

    @property
    def native_value(self) -> str:
        return (self._coordinator.data or {}).get("status", "unknown")

    @property
    def available(self) -> bool:
        return self._coordinator.last_update_success

    async def async_update(self) -> None:
        await self._coordinator.async_request_refresh()


class OpenRouterRequestsSensor(_BaseSensor):
    """Total requests proxied this session."""

    _attr_name = "Total Requests"
    _attr_icon = "mdi:counter"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "requests"

    def __init__(self, coordinator: OpenRouterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._coordinator = coordinator

    @property
    def native_value(self) -> int:
        stats = self._coordinator.hass.data.get(DOMAIN, {}).get(STATS_KEY, {})
        return stats.get("total_requests", 0)

    @property
    def extra_state_attributes(self) -> dict:
        stats = self._coordinator.hass.data.get(DOMAIN, {}).get(STATS_KEY, {})
        return {"requests_by_model": stats.get("requests_by_model", {})}


class OpenRouterModelCountSensor(_BaseSensor):
    """Number of available models on OpenRouter."""

    _attr_name = "Available Models"
    _attr_icon = "mdi:robot"
    _attr_native_unit_of_measurement = "models"

    def __init__(self, coordinator: OpenRouterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._coordinator = coordinator

    @property
    def native_value(self) -> int:
        return (self._coordinator.data or {}).get("model_count", 0)

    @property
    def extra_state_attributes(self) -> dict:
        data = self._coordinator.data or {}
        return {
            "free_models": data.get("free_model_count", 0),
            "default_model": self._entry.data.get("default_model", ""),
        }


class OpenRouterLastModelSensor(_BaseSensor):
    """Last model used via the proxy."""

    _attr_name = "Last Used Model"
    _attr_icon = "mdi:brain"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(entry)
        self._hass = hass

    @property
    def native_value(self) -> str:
        stats = self._hass.data.get(DOMAIN, {}).get(STATS_KEY, {})
        return stats.get("last_model", "none")
