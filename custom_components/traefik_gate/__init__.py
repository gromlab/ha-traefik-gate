"""Traefik Gate — ForwardAuth access control for Home Assistant."""
from __future__ import annotations

import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import storage
from homeassistant.util import dt as dt_util
from homeassistant.helpers.event import async_track_point_in_time

from .const import (
    DOMAIN,
    CONF_LISTEN_PORT,
    CONF_PROTECTED_MIN_HOURS, CONF_PROTECTED_MAX_HOURS,
    CONF_PROTECTED_STEP_HOURS, CONF_PROTECTED_DEFAULT_HOURS,
    CONF_PLEX_MIN_HOURS, CONF_PLEX_MAX_HOURS,
    CONF_PLEX_STEP_HOURS, CONF_PLEX_DEFAULT_HOURS,
    STORAGE_KEY, STORAGE_VERSION,
    PROFILE_PROTECTED, PROFILE_PLEX,
)
from .http_server import ForwardAuthServer

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch", "number", "sensor"]


def get_local_ip() -> str:
    """Return the LAN IP this host uses to reach the outside world."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


@dataclass
class ProfileState:
    enabled: bool = False
    expires_at: datetime | None = None
    default_duration_hours: int = 1
    min_hours: int = 1
    max_hours: int = 24
    step_hours: int = 1


@dataclass
class GateState:
    protected: ProfileState = field(default_factory=ProfileState)
    plex: ProfileState = field(default_factory=ProfileState)


class GateManager:
    """Owns all profile state and timer logic."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._store = storage.Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._state = GateState()
        self._cancel_timers: dict[str, Callable] = {}
        self._listeners: list[Callable] = []

        cfg = entry.data
        self._state.protected = ProfileState(
            default_duration_hours=cfg.get(CONF_PROTECTED_DEFAULT_HOURS, 1),
            min_hours=cfg.get(CONF_PROTECTED_MIN_HOURS, 1),
            max_hours=cfg.get(CONF_PROTECTED_MAX_HOURS, 24),
            step_hours=cfg.get(CONF_PROTECTED_STEP_HOURS, 1),
        )
        self._state.plex = ProfileState(
            default_duration_hours=cfg.get(CONF_PLEX_DEFAULT_HOURS, 24),
            min_hours=cfg.get(CONF_PLEX_MIN_HOURS, 24),
            max_hours=cfg.get(CONF_PLEX_MAX_HOURS, 168),
            step_hours=cfg.get(CONF_PLEX_STEP_HOURS, 24),
        )

    def register_listener(self, cb: Callable) -> None:
        self._listeners.append(cb)

    def unregister_listener(self, cb: Callable) -> None:
        self._listeners.remove(cb)

    @callback
    def _notify(self) -> None:
        for cb in self._listeners:
            cb()

    async def async_load(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        for profile in (PROFILE_PROTECTED, PROFILE_PLEX):
            saved = data.get(profile, {})
            if not saved:
                continue
            ps = self._profile(profile)
            ps.enabled = saved.get("enabled", False)
            ps.default_duration_hours = saved.get(
                "default_duration_hours", ps.default_duration_hours
            )
            raw_exp = saved.get("expires_at")
            if raw_exp:
                exp = dt_util.parse_datetime(raw_exp)
                if exp and exp > dt_util.utcnow():
                    ps.expires_at = exp
                    self._schedule_expiry(profile, exp)
                else:
                    ps.enabled = False
                    ps.expires_at = None

    async def _save(self) -> None:
        data = {}
        for profile in (PROFILE_PROTECTED, PROFILE_PLEX):
            ps = self._profile(profile)
            data[profile] = {
                "enabled": ps.enabled,
                "expires_at": ps.expires_at.isoformat() if ps.expires_at else None,
                "default_duration_hours": ps.default_duration_hours,
            }
        await self._store.async_save(data)

    def check(self, profile: str) -> bool:
        ps = self._profile(profile)
        if not ps.enabled or ps.expires_at is None:
            return False
        return dt_util.utcnow() < ps.expires_at

    def remaining_minutes(self, profile: str) -> int:
        ps = self._profile(profile)
        if ps.expires_at is None:
            return 0
        delta = ps.expires_at - dt_util.utcnow()
        mins = int(delta.total_seconds() / 60)
        return max(0, mins)

    async def async_turn_on(self, profile: str) -> None:
        ps = self._profile(profile)
        ps.enabled = True
        ps.expires_at = dt_util.utcnow() + timedelta(hours=ps.default_duration_hours)
        self._schedule_expiry(profile, ps.expires_at)
        await self._save()
        self._notify()

    async def async_turn_off(self, profile: str) -> None:
        ps = self._profile(profile)
        ps.enabled = False
        ps.expires_at = None
        self._cancel_timer(profile)
        await self._save()
        self._notify()

    async def async_set_duration(self, profile: str, hours: int) -> None:
        ps = self._profile(profile)
        hours = max(ps.min_hours, min(ps.max_hours, hours))
        if ps.step_hours > 1:
            hours = (hours // ps.step_hours) * ps.step_hours
            hours = max(ps.min_hours, hours)
        ps.default_duration_hours = hours
        await self._save()
        self._notify()

    def profile_state(self, profile: str) -> ProfileState:
        return self._profile(profile)

    def _profile(self, profile: str) -> ProfileState:
        if profile == PROFILE_PROTECTED:
            return self._state.protected
        if profile == PROFILE_PLEX:
            return self._state.plex
        raise ValueError(f"Unknown profile: {profile}")

    def _schedule_expiry(self, profile: str, at: datetime) -> None:
        self._cancel_timer(profile)

        @callback
        def _on_expire(now):  # noqa: ANN001
            self.hass.async_create_task(self.async_turn_off(profile))

        self._cancel_timers[profile] = async_track_point_in_time(
            self.hass, _on_expire, at
        )

    def _cancel_timer(self, profile: str) -> None:
        if cancel := self._cancel_timers.pop(profile, None):
            cancel()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    manager = GateManager(hass, entry)
    await manager.async_load()

    port = entry.data[CONF_LISTEN_PORT]
    server = ForwardAuthServer(manager, port)
    await server.start()

    local_ip = await hass.async_add_executor_job(get_local_ip)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "manager": manager,
        "server": server,
        "local_ip": local_ip,
        "port": port,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    data = hass.data[DOMAIN].pop(entry.entry_id)
    await data["server"].stop()

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    return unloaded
