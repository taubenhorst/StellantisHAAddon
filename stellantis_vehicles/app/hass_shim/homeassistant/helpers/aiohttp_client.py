"""Replacement for homeassistant.helpers.aiohttp_client: one shared client
session per hass object, closed by main.py on shutdown."""
import aiohttp


def async_get_clientsession(hass) -> aiohttp.ClientSession:
    session = getattr(hass, "_client_session", None)
    if session is None or session.closed:
        session = aiohttp.ClientSession()
        hass._client_session = session
    return session


async def async_close_clientsession(hass) -> None:
    session = getattr(hass, "_client_session", None)
    if session is not None and not session.closed:
        await session.close()
