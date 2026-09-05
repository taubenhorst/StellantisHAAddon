"""Add-on entry point.

Wires together: shimmed `homeassistant` package -> vendored Stellantis client
-> coordinators -> MQTT bridge, plus the ingress web UI.
"""
import asyncio
import json
import logging
import os
import signal
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
# The shim must shadow any real `homeassistant` package before the vendored
# integration is imported.
sys.path.insert(0, os.path.join(APP_DIR, "hass_shim"))
sys.path.insert(0, APP_DIR)

from homeassistant.core import HomeAssistant  # noqa: E402  (shim)

from stellantis_vehicles.stellantis import StellantisVehicles  # noqa: E402
from bridge.mqtt_bridge import MqttBridge  # noqa: E402
from web import server as web_server  # noqa: E402

DATA_DIR = os.environ.get("DATA_DIR", "/data")
OPTIONS_FILE = os.path.join(DATA_DIR, "options.json")
_LOGGER = logging.getLogger("stellantis_addon")


def load_options() -> dict:
    try:
        with open(OPTIONS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


async def run() -> None:
    options = load_options()
    logging.basicConfig(
        level=getattr(logging, str(options.get("log_level", "info")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _LOGGER.info("Starting Stellantis Vehicles add-on")

    loop = asyncio.get_running_loop()
    hass = HomeAssistant(config_dir=DATA_DIR, language=options.get("language", "en"), loop=loop)
    state = {"vehicles": 0, "mqtt": "not connected", "auth": "not configured"}

    web_runner = await web_server.start(state, int(options.get("ingress_port", 8099)))

    stellantis = StellantisVehicles(hass)
    # Upstream expects a config entry to be attached before any stored-config access.
    stellantis.set_entry(hass.config_entries.entry)
    # TODO: restore stored config from hass.config_entries.entry.data,
    #       run OAuth/OTP setup via web UI if missing, then:
    #   vehicles = await stellantis.get_user_vehicles()
    #   for vehicle in vehicles:
    #       coordinator = await stellantis.async_get_coordinator(vehicle)
    #       coordinator.add_listener(bridge.on_coordinator_update)
    #       coordinator.start()
    #   await stellantis.scheduled_tokens_refresh()
    #   await stellantis.connect_mqtt()

    mqtt_opts = options.get("mqtt", {})
    bridge = None
    if mqtt_opts.get("host"):
        bridge = MqttBridge(mqtt_opts["host"], int(mqtt_opts.get("port", 1883)),
                            mqtt_opts.get("username"), mqtt_opts.get("password"))
        bridge.connect()
        state["mqtt"] = f"connected to {mqtt_opts['host']}"

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)
    await stop.wait()

    _LOGGER.info("Shutting down")
    if bridge:
        bridge.disconnect()
    await stellantis.async_shutdown()
    await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run())
