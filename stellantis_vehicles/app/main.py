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
from web.setup import SetupFlow  # noqa: E402

# /data inside the add-on container; ../data next to app/ on a dev box
DATA_DIR = os.environ.get("DATA_DIR") or (
    "/data" if os.path.isdir("/data") else os.path.normpath(os.path.join(APP_DIR, "..", "data")))
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
    state = {"vehicles": [], "mqtt": "not connected"}

    stellantis = StellantisVehicles(hass)
    # Same order as upstream async_setup_entry: runtime config from the stored
    # entry data, then attach the entry (stored-config access needs it).
    stellantis.save_config(hass.config_entries.entry.data)
    stellantis.set_entry(hass.config_entries.entry)

    async def on_configured() -> None:
        # TODO (step 3): start vehicles here, see below
        _LOGGER.info("Setup complete, stored config ready")

    flow = SetupFlow(hass, stellantis, options, on_configured)
    web_runner = await web_server.start(state, flow, hass, int(options.get("ingress_port", 8099)))
    _LOGGER.info("Setup step: %s", flow.step)

    # TODO (step 3): when flow.step == "done" (now or via on_configured):
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
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows dev box: Ctrl+C raises KeyboardInterrupt instead
            pass
    await stop.wait()

    _LOGGER.info("Shutting down")
    if bridge:
        bridge.disconnect()
    await stellantis.async_shutdown()
    await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run())
