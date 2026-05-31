"""Sensor entities for Traefik Gate — time remaining and ForwardAuth URLs."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import GateManager
from .const import DOMAIN, PROFILE_PROTECTED, PROFILE_PLEX


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    manager: GateManager = data["manager"]
    local_ip: str = data["local_ip"]
    port: int = data["port"]

    async_add_entities([
        TraefikGateTimerSensor(manager, entry, PROFILE_PROTECTED,
                               "Protected Time Remaining"),
        TraefikGateTimerSensor(manager, entry, PROFILE_PLEX,
                               "Plex Time Remaining"),
        TraefikGateUrlSensor(entry, PROFILE_PROTECTED,
                             "Protected ForwardAuth URL",
                             f"http://{local_ip}:{port}/auth/protected"),
        TraefikGateUrlSensor(entry, PROFILE_PLEX,
                             "Plex ForwardAuth URL",
                             f"http://{local_ip}:{port}/auth/plex"),
    ])


class TraefikGateTimerSensor(SensorEntity):
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


class TraefikGateUrlSensor(SensorEntity):
    """Static diagnostic sensor showing the ForwardAuth URL for a profile."""

    _attr_should_poll = False
    _attr_icon = "mdi:link"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        entry: ConfigEntry,
        profile: str,
        name: str,
        url: str,
    ) -> None:
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{profile}_url"
        self._url = url

    @property
    def native_value(self) -> str:
        return self._url
