import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_LISTEN_PORT,
    CONF_PROTECTED_MIN_HOURS, CONF_PROTECTED_MAX_HOURS,
    CONF_PROTECTED_STEP_HOURS, CONF_PROTECTED_DEFAULT_HOURS,
    CONF_PLEX_MIN_HOURS, CONF_PLEX_MAX_HOURS,
    CONF_PLEX_STEP_HOURS, CONF_PLEX_DEFAULT_HOURS,
    DEFAULT_LISTEN_PORT,
    DEFAULT_PROTECTED_MIN_HOURS, DEFAULT_PROTECTED_MAX_HOURS,
    DEFAULT_PROTECTED_STEP_HOURS, DEFAULT_PROTECTED_DEFAULT_HOURS,
    DEFAULT_PLEX_MIN_HOURS, DEFAULT_PLEX_MAX_HOURS,
    DEFAULT_PLEX_STEP_HOURS, DEFAULT_PLEX_DEFAULT_HOURS,
)

STEP_SCHEMA = vol.Schema({
    vol.Required(CONF_LISTEN_PORT, default=DEFAULT_LISTEN_PORT): vol.All(
        int, vol.Range(min=1024, max=65535)
    ),
    vol.Required(CONF_PROTECTED_DEFAULT_HOURS, default=DEFAULT_PROTECTED_DEFAULT_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PROTECTED_MIN_HOURS, default=DEFAULT_PROTECTED_MIN_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PROTECTED_MAX_HOURS, default=DEFAULT_PROTECTED_MAX_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PROTECTED_STEP_HOURS, default=DEFAULT_PROTECTED_STEP_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PLEX_DEFAULT_HOURS, default=DEFAULT_PLEX_DEFAULT_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PLEX_MIN_HOURS, default=DEFAULT_PLEX_MIN_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PLEX_MAX_HOURS, default=DEFAULT_PLEX_MAX_HOURS): vol.All(int, vol.Range(min=1)),
    vol.Required(CONF_PLEX_STEP_HOURS, default=DEFAULT_PLEX_STEP_HOURS): vol.All(int, vol.Range(min=1)),
})


class TraefikGateConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            port = user_input[CONF_LISTEN_PORT]
            if await _port_in_use(self.hass, port):
                errors[CONF_LISTEN_PORT] = "port_in_use"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Traefik Gate", data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )


async def _port_in_use(hass: HomeAssistant, port: int) -> bool:
    import asyncio
    loop = asyncio.get_event_loop()
    try:
        server = await loop.create_server(asyncio.Protocol, "0.0.0.0", port)
        server.close()
        await server.wait_closed()
        return False
    except OSError:
        return True
