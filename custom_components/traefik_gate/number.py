"""Number entities for Traefik Gate session duration configuration."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
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
        TraefikGateNumber(manager, entry, PROFILE_PROTECTED,
                          "Protected Default Duration"),
        TraefikGateNumber(manager, entry, PROFILE_PLEX,
                          "Plex Default Duration"),
    ])


class TraefikGateNumber(NumberEntity):
    _attr_should_poll = False
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = "h"
    _attr_icon = "mdi:timer-cog"

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
        self._attr_unique_id = f"{entry.entry_id}_{profile}_duration"
        ps = manager.profile_state(profile)
        self._attr_native_min_value = ps.min_hours
        self._attr_native_max_value = ps.max_hours
        self._attr_native_step = ps.step_hours

    async def async_added_to_hass(self) -> None:
        self._manager.register_listener(self._on_state_change)

    async def async_will_remove_from_hass(self) -> None:
        self._manager.unregister_listener(self._on_state_change)

    @callback
    def _on_state_change(self) -> None:
        self.async_write_ha_state()

    @property
    def native_value(self) -> float:
        return float(self._manager.profile_state(self._profile).default_duration_hours)

    async def async_set_native_value(self, value: float) -> None:
        await self._manager.async_set_duration(self._profile, int(value))
