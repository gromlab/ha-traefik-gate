"""Standalone aiohttp ForwardAuth server on a dedicated port."""
from __future__ import annotations

import ipaddress
import logging
from typing import TYPE_CHECKING

from aiohttp import web

from .const import PRIVATE_CIDRS

if TYPE_CHECKING:
    from . import GateManager

_LOGGER = logging.getLogger(__name__)

_PRIVATE_NETWORKS = [ipaddress.ip_network(cidr) for cidr in PRIVATE_CIDRS]


def _is_private(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return any(ip in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return False


def _client_ip(request: web.Request) -> str:
    if real_ip := request.headers.get("X-Real-IP"):
        return real_ip.strip()
    if xff := request.headers.get("X-Forwarded-For"):
        return xff.split(",")[0].strip()
    return request.remote or ""


class ForwardAuthServer:
    def __init__(self, manager: GateManager, port: int) -> None:
        self._manager = manager
        self._port = port
        self._runner: web.AppRunner | None = None

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/auth/protected", self._handle_protected)
        app.router.add_get("/auth/plex", self._handle_plex)
        app.router.add_get("/healthz", self._handle_healthz)

        self._runner = web.AppRunner(app, access_log=None)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        _LOGGER.info("ForwardAuth server listening on :%s", self._port)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None

    async def _handle_healthz(self, request: web.Request) -> web.Response:
        return web.Response(text="ok")

    async def _handle_protected(self, request: web.Request) -> web.Response:
        return self._auth(request, "protected")

    async def _handle_plex(self, request: web.Request) -> web.Response:
        return self._auth(request, "plex")

    def _auth(self, request: web.Request, profile: str) -> web.Response:
        client_ip = _client_ip(request)

        if _is_private(client_ip):
            _LOGGER.debug("auth profile=%s client=%s bypass=lan", profile, client_ip)
            return web.Response(status=200, text="ok")

        allowed = self._manager.check(profile)
        if allowed:
            _LOGGER.debug("auth profile=%s client=%s decision=allow", profile, client_ip)
            return web.Response(status=200, text="ok")

        _LOGGER.debug("auth profile=%s client=%s decision=deny", profile, client_ip)
        return web.Response(status=403, text="blocked")
