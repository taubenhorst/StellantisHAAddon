"""Own replacement for the upstream DataUpdateCoordinator.

Port of the coordinator half of the upstream ``base.py`` (commit 69fddda)
without anything Home-Assistant-specific. stellantis.py imports
``StellantisVehicleCoordinator`` from here and touches:
  - coordinator._vehicle / coordinator._commands_history
  - coordinator.async_refresh()
  - coordinator.update_command_history(correlation_id, result_code)

Entities do not exist here; the MQTT bridge registers a listener and reads
``data`` / ``_sensors`` exactly like the upstream entity classes did. The
``_sensors`` dict is shared state: the bridge writes the converted entity
values into it and the coordinator reads them back (charge limit, ABRP sync,
last trip detection) - same one-cycle lag as upstream.
"""
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Awaitable, Callable

from homeassistant.components import persistent_notification
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import (
    DOMAIN,
    EMPTY_STATUS_LIMIT,
    UPDATE_INTERVAL,
    VEHICLE_TYPE_ELECTRIC,
    VEHICLE_TYPE_HYBRID,
)
from .utils import get_datetime, rate_limit, time_from_pt_string

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
        self.last_update_success = False

        self._data: dict = {}
        self._sensors: dict = {}
        self._commands_history: dict = {}
        self._disabled_commands: list[str] = []
        self._last_trip = None
        self._manage_charge_limit_sent = False
        self._phase_offset = 0
        self._privacy_full_logged = False
        self._empty_status_count = 0
        self._vehicle_removed = False

        self._listeners: list[Listener] = []
        self._task: asyncio.Task | None = None
        self._refresh_lock = asyncio.Lock()
        # Called once when polling stops because the token is dead
        # (upstream: config_entry.async_start_reauth). Set by main.py.
        self.on_auth_failed: Callable[[], None] | None = None

        if self._stellantis.logger_filter:
            _LOGGER.addFilter(self._stellantis.logger_filter)

    # --- public API used by the bridge -------------------------------------
    @property
    def data(self) -> dict:
        return self._data

    @property
    def vehicle(self) -> dict:
        return self._vehicle

    @property
    def vin(self) -> str:
        return self._vehicle.get("vin", "")

    @property
    def vehicle_type(self) -> str:
        return self._vehicle["type"]

    @property
    def stellantis(self):
        return self._stellantis

    @property
    def config(self) -> dict:
        return self._config

    @property
    def disabled_commands(self) -> list[str]:
        return self._disabled_commands

    @property
    def last_trip(self):
        return self._last_trip

    def get_translation(self, path, default=None):
        return self._translations.get(path, default)

    def add_listener(self, listener: Listener) -> None:
        self._listeners.append(listener)

    def remove_listener(self, listener: Listener) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def start(self) -> None:
        """Start polling; also restarts a loop that ended after an auth failure."""
        if self._task is None or self._task.done():
            self._task = self._hass.loop.create_task(self._run(), name=f"{DOMAIN}:{self.vin}")

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    def stagger_first_poll(self, offset_seconds) -> None:
        """Push this vehicle's first poll back once so several vehicles do not all
        poll at the same instant after a restart."""
        offset_seconds = int(offset_seconds)
        if offset_seconds <= 0:
            return
        self._phase_offset = offset_seconds

    def async_update_listeners(self) -> None:
        """Upstream name: schedule a listener notification from sync code."""
        self._hass.loop.create_task(self._notify())

    # --- polling -------------------------------------------------------------
    async def _run(self) -> None:
        if self._phase_offset:
            await asyncio.sleep(self._phase_offset)
            self._phase_offset = 0
        while True:
            try:
                await self.async_refresh()
            except ConfigEntryAuthFailed:
                _LOGGER.error("Authentication failed for %s, stopping polling", self.vin)
                if self.on_auth_failed:
                    self.on_auth_failed()
                return
            await asyncio.sleep(self._current_interval())

    def _current_interval(self) -> float:
        refresh_interval = self._sensors.get("number_refresh_interval")
        if refresh_interval and refresh_interval > 0:
            self.update_interval = timedelta(seconds=refresh_interval)
        else:
            self.update_interval = timedelta(seconds=UPDATE_INTERVAL)
        return self.update_interval.total_seconds()

    async def async_refresh(self) -> None:
        async with self._refresh_lock:
            try:
                await self._async_update_data()
            except ConfigEntryAuthFailed:
                self.last_update_success = False
                await self._notify()
                raise
            except Exception as err:  # noqa: BLE001 - upstream raises UpdateFailed here
                _LOGGER.debug("Error communicating with Stellantis API: %s", err)
                self.last_update_success = False
                await self._notify()
                return
            self.last_update_success = True
            await self._notify()

    async def _async_update_data(self) -> None:
        """Update vehicle data from Stellantis (upstream logic, minus UpdateFailed)."""
        _LOGGER.debug("---------- START _async_update_data")
        new_data = await self._stellantis.get_vehicle_status(self._vehicle)

        if not new_data:
            # Keep the last known data instead of blanking every entity on a
            # single empty response (404 / empty body).
            self._empty_status_count += 1
            _LOGGER.debug("Empty vehicle status response (%s in a row), keeping last known data",
                          self._empty_status_count)
            if self._empty_status_count < EMPTY_STATUS_LIMIT:
                _LOGGER.debug("---------- END _async_update_data")
                return
            if self._empty_status_count % EMPTY_STATUS_LIMIT == 0 and not self._vehicle_removed:
                await self._reconcile_vehicle()
            _LOGGER.debug("---------- END _async_update_data")
            raise RuntimeError("Empty vehicle status response")

        self._empty_status_count = 0
        self._clear_vehicle_removed()
        self._log_privacy_mode(new_data.get("privacy", {}).get("state"))

        if "updatedAt" in new_data and "updatedAt" in self._data:
            try:
                current_dt = datetime.fromisoformat(self._data["updatedAt"])
                new_dt = datetime.fromisoformat(new_data["updatedAt"])
                if current_dt.tzinfo is None:
                    current_dt = current_dt.replace(tzinfo=UTC)
                if new_dt.tzinfo is None:
                    new_dt = new_dt.replace(tzinfo=UTC)
            except (ValueError, TypeError):
                _LOGGER.debug("Invalid updatedAt values, proceeding without timestamp comparison")
            else:
                if new_dt <= current_dt:
                    _LOGGER.debug("API did not return updated vehicle data, skipping sensor update")
                    _LOGGER.debug("---------- END _async_update_data")
                    return

        self._data = new_data
        await self.after_async_update_data()
        _LOGGER.debug("---------- END _async_update_data")

    def _log_privacy_mode(self, state) -> None:
        active = state == "Full"
        if active and not self._privacy_full_logged:
            self._privacy_full_logged = True
            _LOGGER.info("Private mode is enabled on vehicle %s, Stellantis has paused live data updates", self.vin)
        elif not active and self._privacy_full_logged:
            self._privacy_full_logged = False
            _LOGGER.info("Private mode is disabled on vehicle %s, live data updates resumed", self.vin)

    async def _reconcile_vehicle(self) -> None:
        """Re-fetch the account vehicle list to check whether this vehicle was unpaired."""
        try:
            live = await self._stellantis.get_user_vehicles(force=True)
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Could not refresh the vehicle list for %s: %s", self.vin, err)
            return
        live_vins = {vehicle.get("vin") for vehicle in live}
        if not live_vins or self.vin in live_vins:
            return
        self._vehicle_removed = True
        _LOGGER.warning("Vehicle %s is no longer linked to this Stellantis account", self.vin)
        # No repair issues without HA core: surface it as a notification instead.
        persistent_notification.async_create(
            self._hass,
            f"Vehicle {self.vin} is no longer linked to this Stellantis account.",
            title="Stellantis Vehicles",
            notification_id=f"vehicle_removed_{self.vin}",
        )

    def _clear_vehicle_removed(self) -> None:
        if not self._vehicle_removed:
            return
        self._vehicle_removed = False
        _LOGGER.info("Vehicle %s is reachable again", self.vin)

    async def _notify(self) -> None:
        for listener in list(self._listeners):
            try:
                result = listener(self)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as err:  # noqa: BLE001 - one broken listener must not stop polling
                _LOGGER.exception("Coordinator listener failed for %s: %s", self.vin, err)

    # --- command history -----------------------------------------------------
    @property
    def command_history(self) -> dict:
        if not self._commands_history:
            return {}
        history_items = []
        for action_id in self._commands_history:
            action_name = self._commands_history[action_id]["name"]
            for update in self._commands_history[action_id]["updates"]:
                status = update["info"]
                translation_path = f"component.stellantis_vehicles.entity.sensor.command_status.state.{status}"
                status = self.get_translation(translation_path, status)
                history_items.append((update["date"], f"{action_name}: {status}"))
        history_items.sort(key=lambda x: x[0], reverse=True)
        return {
            item[0].strftime("%d/%m/%y %H:%M:%S:%f")[:-4]: item[1]
            for item in history_items
        }

    @property
    def pending_action(self) -> bool:
        if not self._commands_history:
            return False
        last_action_id = list(self._commands_history.keys())[-1]
        return not self._commands_history[last_action_id]["updates"]

    async def update_command_history(self, action_id, update=None) -> None:
        if action_id not in self._commands_history:
            return
        if update:
            self._commands_history[action_id]["updates"].append({"info": update, "date": get_datetime()})
            if update == "not_compatible":
                self._disabled_commands.append(self._commands_history[action_id]["name"])
        await self._notify()

    def update_command_history_rate_limit(self, name) -> None:
        current_datetime = get_datetime()
        self._commands_history.update({
            current_datetime.time(): {"name": name, "updates": [{"info": "rate_limit", "date": current_datetime}]}
        })
        self.async_update_listeners()

    # --- commands ------------------------------------------------------------
    async def send_command(self, name, service, message) -> None:
        try:
            action_id = await self._stellantis.send_mqtt_message(service, message, self._vehicle)
            if action_id is not None:
                self._commands_history.update({action_id: {"name": name, "updates": []}})
                await self._notify()
        except ConfigEntryAuthFailed as e:
            _LOGGER.warning("Authentication failed while sending command '%s' to vehicle '%s': %s", name, self.vin, e)
            if self.on_auth_failed:
                self.on_auth_failed()
        except Exception as e:
            _LOGGER.error("Failed to send command %s: %s", name, e)
            raise

    @rate_limit(6, 1200)  # 6 per 20 min
    async def send_wakeup_command(self, button_name) -> None:
        await self.send_command(button_name, "/VehCharge/state", {"action": "state"})

    async def send_doors_command(self, button_name, action) -> None:
        await self.send_command(button_name, "/Doors", {"action": action})

    async def send_horn_command(self, button_name) -> None:
        await self.send_command(button_name, "/Horn", {"nb_horn": "2", "action": "activate"})

    async def send_lights_command(self, button_name) -> None:
        await self.send_command(button_name, "/Lights", {"duration": "10", "action": "activate"})

    async def send_charge_command(self, button_name, update_only_time=False, action="immediate") -> None:
        current_hour = self._sensors.get("time_battery_charging_start")
        if current_hour is None:
            _LOGGER.warning("Charge start time unknown, cannot send charge command")
            return
        if update_only_time:
            if self._sensors.get("battery_charging") != "InProgress":
                action = "delayed"
        await self.send_command(button_name, "/VehCharge", {
            "program": {"hour": current_hour.hour, "minute": current_hour.minute},
            "type": action,
        })

    def get_programs(self) -> dict:
        """Current preconditioning programs (API key spelled "preconditionning" upstream)."""
        default_programs = {
            "program1": {"day": [0, 0, 0, 0, 0, 0, 0], "hour": 34, "minute": 7, "on": 0},
            "program2": {"day": [0, 0, 0, 0, 0, 0, 0], "hour": 34, "minute": 7, "on": 0},
            "program3": {"day": [0, 0, 0, 0, 0, 0, 0], "hour": 34, "minute": 7, "on": 0},
            "program4": {"day": [0, 0, 0, 0, 0, 0, 0], "hour": 34, "minute": 7, "on": 0},
        }
        air_conditioning = (self._data.get("preconditionning") or {}).get("airConditioning") or {}
        for program in air_conditioning.get("programs") or []:
            if not program:
                continue
            occurence = program.get("occurence")
            if occurence and occurence.get("day") and program.get("start"):
                date = time_from_pt_string(program["start"])
                default_programs["program" + str(program["slot"])] = {
                    "day": [int(day in occurence["day"]) for day in ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")],
                    "hour": date.hour,
                    "minute": date.minute,
                    "on": int(program["enabled"]),
                }
        return default_programs

    async def send_preconditioning_command(self, button_name, action) -> None:
        await self.send_command(button_name, "/ThermalPrecond", {"asap": action, "programs": self.get_programs()})

    async def send_abrp_data(self) -> None:
        tlm = {
            "utc": int(get_datetime().astimezone(UTC).timestamp()),
            "soc": None,
            "power": None,
            "speed": None,
            "lat": None,
            "lon": None,
            "is_charging": False,
            "is_dcfc": False,
            "is_parked": False,
        }
        sensors = self._sensors
        position = self._data.get("lastPosition") or {}
        coordinates = (position.get("geometry") or {}).get("coordinates") or []
        if sensors.get("battery") is not None:
            tlm["soc"] = sensors.get("battery")
        if sensors.get("speed") is not None:
            tlm["speed"] = sensors.get("speed")
        if len(coordinates) >= 2:
            tlm["lat"] = float(coordinates[1])
            tlm["lon"] = float(coordinates[0])
        if sensors.get("battery_charging") is not None:
            tlm["is_charging"] = sensors.get("battery_charging") == "InProgress"
        if sensors.get("battery_charging_type") is not None:
            tlm["is_dcfc"] = tlm["is_charging"] and sensors.get("battery_charging_type") == "Quick"
        if sensors.get("battery_health_resistance") is not None:
            tlm["soh"] = float(sensors.get("battery_health_resistance"))
        if sensors.get("battery_health_capacity") is not None:
            tlm["soh"] = float(sensors.get("battery_health_capacity"))
        if (position.get("properties") or {}).get("heading") is not None:
            tlm["heading"] = float(position["properties"]["heading"])
        if len(coordinates) == 3:
            tlm["elevation"] = float(coordinates[2])
        if sensors.get("temperature") is not None:
            tlm["ext_temp"] = sensors.get("temperature")
        if sensors.get("mileage") is not None:
            tlm["odometer"] = sensors.get("mileage")
        if sensors.get("autonomy") is not None:
            tlm["est_battery_range"] = sensors.get("autonomy")

        params = {"tlm": json.dumps(tlm), "token": sensors.get("text_abrp_token")}
        await self._stellantis.send_abrp_data(params)

    async def after_async_update_data(self) -> None:
        """Apply changes and do actions after vehicle data update.

        Reads ``_sensors`` as filled by the bridge on the *previous* update,
        exactly like upstream (entities update after the coordinator).
        """
        sensors = self._sensors
        if self.vehicle_type in [VEHICLE_TYPE_ELECTRIC, VEHICLE_TYPE_HYBRID]:
            if "battery_charging" in sensors:
                if sensors.get("battery_charging") == "InProgress" and not self._manage_charge_limit_sent:
                    charge_limit_on = sensors.get("switch_battery_charging_limit", False)
                    charge_limit = sensors.get("number_battery_charging_limit", None)
                    if charge_limit_on and charge_limit and "battery" in sensors:
                        current_battery = sensors.get("battery")
                        if current_battery is not None and int(float(current_battery)) >= int(charge_limit):
                            button_name = self.get_translation("component.stellantis_vehicles.entity.button.charge_stop.name", "charge_stop")
                            await self.send_charge_command(button_name, False, "delayed")
                            self._manage_charge_limit_sent = True
                elif sensors.get("battery_charging") != "InProgress" and self._manage_charge_limit_sent:
                    self._manage_charge_limit_sent = False

            token = sensors.get("text_abrp_token")
            if sensors.get("switch_abrp_sync") and token and len(token) == 36:
                await self.send_abrp_data()

        current_engine_status = sensors.get("engine")
        new_engine_status = self._data.get("ignition", {}).get("type")
        if new_engine_status == "Stop" and current_engine_status not in (None, "Stop"):
            _LOGGER.debug("Engine status changed from %s to %s, fetching last trip data", current_engine_status, new_engine_status)
            await self.get_vehicle_last_trip()

    async def get_vehicle_last_trip(self) -> None:
        try:
            trips = await self._stellantis.get_vehicle_last_trip(self._vehicle)
            embedded = (trips or {}).get("_embedded", {}).get("trips")
            if embedded:
                if not self._last_trip or self._last_trip["id"] != embedded[-1]["id"]:
                    self._last_trip = embedded[-1]
        except Exception as e:  # noqa: BLE001
            _LOGGER.warning("Failed to fetch last trip data: %s", e)
