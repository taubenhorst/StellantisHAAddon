"""Own replacement for the upstream DataUpdateCoordinator.

stellantis.py imports `StellantisVehicleCoordinator` from here and calls:
  - coordinator._vehicle
  - coordinator.async_refresh()
  - coordinator.update_command_history(correlation_id, result_code)
Everything HA-specific (entities, RestoreEntity, translations) is gone;
state changes are handed to a listener (the MQTT bridge) via callbacks.
"""
import asyncio
import logging
from datetime import timedelta
from typing import Awaitable, Callable

from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

Listener = Callable[["StellantisVehicleCoordinator"], Awaitable[None] | None]


class StellantisVehicleCoordinator:
    def __init__(self, hass, config, vehicle, stellantis, translations, config_entry=None) -> None:
        self._hass = hass
        self._config = config
        self._vehicle = vehicle
        self._stellantis = stellantis
        self._translations = translations
        self._config_entry = config_entry
        self.name = DOMAIN
        self.update_interval = timedelta(seconds=UPDATE_INTERVAL)
        self.data: dict = {}
        self.last_update_success = False
        self._commands_history: dict = {}
        self._listeners: list[Listener] = []
        self._task: asyncio.Task | None = None
        self._refresh_lock = asyncio.Lock()

    # --- public API used by the bridge -------------------------------------
    @property
    def vehicle(self) -> dict:
        return self._vehicle

    @property
    def vin(self) -> str:
        return self._vehicle.get("vin", "")

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def start(self) -> None:
        if self._task is None:
            self._task = self._hass.loop.create_task(self._run(), name=f"{DOMAIN}:{self.vin}")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    # --- API used by stellantis.py -------------------------------------------
    async def async_refresh(self) -> None:
        async with self._refresh_lock:
            try:
                new_data = await self._stellantis.get_vehicle_status(self._vehicle)
            except ConfigEntryAuthFailed:
                self.last_update_success = False
                raise
            except Exception as err:  # noqa: BLE001 - upstream behaviour
                _LOGGER.warning("Error communicating with Stellantis API: %s", err)
                self.last_update_success = False
                await self._notify()
                return
            if new_data:
                self.data = new_data
            self.last_update_success = True
            await self._notify()

    async def update_command_history(self, correlation_id: str, result_code) -> None:
        self._commands_history[correlation_id] = result_code
        await self._notify()

    # --- internals -----------------------------------------------------------
    async def _run(self) -> None:
        while True:
            try:
                await self.async_refresh()
            except ConfigEntryAuthFailed:
                _LOGGER.error("Authentication failed for %s, stopping polling", self.vin)
                return
            await asyncio.sleep(self.update_interval.total_seconds())

    async def _notify(self) -> None:
        for listener in self._listeners:
            result = listener(self)
            if asyncio.iscoroutine(result):
                await result
