"""Add-on entry point.

Wires together: shimmed `homeassistant` package -> vendored Stellantis client
-> setup flow + ingress UI -> vehicle runtime (coordinators) -> MQTT bridge.
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
from runtime import Runtime  # noqa: E402
from web import server as web_server  # noqa: E402
from web.setup import STEP_DONE, SetupFlow  # noqa: E402

# /data inside the add-on container; ../data next to app/ on a dev box
DATA_DIR = os.environ.get("DATA_DIR") or (
    "/data" if os.path.isdir("/data") else os.path.normpath(os.path.join(APP_DIR, "..", "data")))
OPTIONS_FILE = os.path.join(DATA_DIR, "options.json")
ADDON_VERSION = os.environ.get("ADDON_VERSION", "dev")
_LOGGER = logging.getLogger("stellantis_addon")


def load_options() -> dict:
    try:
        with open(OPTIONS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def mqtt_settings(options: dict) -> dict | None:
    """Broker from the add-on options, else from the Supervisor's MQTT service
    (rootfs/.../run exports it as STELLANTIS_MQTT_*)."""
    opts = options.get("mqtt") or {}
    host = opts.get("host") or os.environ.get("STELLANTIS_MQTT_HOST")
    if not host:
        return None
    return {
        "host": host,
        "port": int(opts.get("port") or os.environ.get("STELLANTIS_MQTT_PORT") or 1883),
        "username": opts.get("username") or os.environ.get("STELLANTIS_MQTT_USER") or None,
        "password": opts.get("password") or os.environ.get("STELLANTIS_MQTT_PASSWORD") or None,
    }


async def run() -> None:
    options = load_options()
    logging.basicConfig(
        level=getattr(logging, str(options.get("log_level", "info")).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    _LOGGER.info("Starting Stellantis Vehicles add-on %s", ADDON_VERSION)

    loop = asyncio.get_running_loop()
    hass = HomeAssistant(config_dir=DATA_DIR, language=options.get("language", "en"), loop=loop)
    state = {"vehicles": [], "mqtt": "not configured"}

    stellantis = StellantisVehicles(hass)
    # Same order as upstream async_setup_entry: runtime config from the stored
    # entry data, then attach the entry (stored-config access needs it).
    stellantis.save_config(hass.config_entries.entry.data)
    stellantis.set_entry(hass.config_entries.entry)

    bridge = None
    mqtt = mqtt_settings(options)
    if mqtt:
        bridge = MqttBridge(mqtt["host"], mqtt["port"], mqtt["username"], mqtt["password"],
                            loop=loop, addon_version=ADDON_VERSION)
        state["mqtt"] = f"connecting to {mqtt['host']}:{mqtt['port']}"

        def on_mqtt(connected: bool) -> None:
            state["mqtt"] = f"connected to {mqtt['host']}:{mqtt['port']}" if connected else "disconnected"

        bridge.on_connection_change = on_mqtt
        bridge.connect()
    else:
        _LOGGER.warning("No MQTT broker configured - vehicles are polled but nothing is published")

    runtime = None
    flow = None

    async def on_configured() -> None:
        _LOGGER.info("Setup complete, starting vehicles")
        await runtime.start()

    flow = SetupFlow(hass, stellantis, options, on_configured)
    runtime = Runtime(hass, stellantis, bridge, flow, state)
    web_runner = await web_server.start(state, flow, hass, int(options.get("ingress_port", 8099)))
    _LOGGER.info("Setup step: %s", flow.step)
    if flow.step == STEP_DONE:
        loop.create_task(runtime.start())

    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows dev box: Ctrl+C raises KeyboardInterrupt instead
            pass
    await stop.wait()

    _LOGGER.info("Shutting down")
    await runtime.stop()
    if bridge:
        bridge.disconnect()
    await stellantis.async_shutdown()
    await web_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(run())
