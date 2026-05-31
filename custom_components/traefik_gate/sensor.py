"""Sensor entities for Traefik Gate time remaining."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GateManager
from .const import DOMAIN, PROFILE_PROTECTED, PROFILE_PLEX


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    manager: GateManager = hass.data[DOMAIN][entry.entry_id]["manager"]
    async_add_entities([
        TraefikGateSensor(manager, entry, PROFILE_PROTECTED,
                          "Protected Time Remaining"),
        TraefikGateSensor(manager, entry, PROFILE_PLEX,
                          "Plex Time Remaining"),
    ])


class TraefikGateSensor(SensorEntity):
    _attr_should_poll = False
    _attr_native_unit_of_measurement = "min"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_icon = "mdi:timer"

    def __init__(
        self,
        manager: GateManager,
        entry: ConfigEntry,
        profile: str,
        name: str,
    ) -> None:
        self._manager = manager
        self._profile = profile
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{profile}_remaining"

    async def async_added_to_hass(self) -> None:
        self._manager.register_listener(self._on_state_change)

    async def async_will_remove_from_hass(self) -> None:
        self._manager.unregister_listener(self._on_state_change)

    @callback
    def _on_state_change(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> int:
        return self._manager.remaining_minutes(self._profile)
