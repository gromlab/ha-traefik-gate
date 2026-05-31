"""Switch entities for Traefik Gate access profiles."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
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
        TraefikGateSwitch(manager, entry, PROFILE_PROTECTED,
                          "Protected External Access", "mdi:shield-lock"),
        TraefikGateSwitch(manager, entry, PROFILE_PLEX,
                          "Plex External Access", "mdi:plex"),
    ])


class TraefikGateSwitch(SwitchEntity):
    _attr_should_poll = False

    def __init__(
        self,
        manager: GateManager,
        entry: ConfigEntry,
        profile: str,
        name: str,
        icon: str,
    ) -> None:
        self._manager = manager
        self._profile = profile
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{profile}_switch"

    async def async_added_to_hass(self) -> None:
        self._manager.register_listener(self._on_state_change)

    async def async_will_remove_from_hass(self) -> None:
        self._manager.unregister_listener(self._on_state_change)

    @callback
    def _on_state_change(self) -> None:
        self.async_write_ha_state()

    @property
    def is_on(self) -> bool:
        return self._manager.check(self._profile)

    async def async_turn_on(self, **kwargs) -> None:
        await self._manager.async_turn_on(self._profile)

    async def async_turn_off(self, **kwargs) -> None:
        await self._manager.async_turn_off(self._profile)
