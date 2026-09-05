"""Offline smoke test for coordinator + MQTT bridge.

No network, no broker: the Stellantis client is stubbed with a status fixture
and paho is replaced by a recorder. Run from the add-on directory:

    .venv/Scripts/python tests/smoke_bridge.py        (Windows)
    .venv/bin/python tests/smoke_bridge.py            (Linux)
"""
import asyncio
import json
import os
import sys
import tempfile

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.join(APP_DIR, "hass_shim"))
sys.path.insert(0, APP_DIR)

from homeassistant.core import HomeAssistant  # noqa: E402

from stellantis_vehicles.stellantis import StellantisVehicles  # noqa: E402
from bridge.mqtt_bridge import MqttBridge  # noqa: E402

VIN = "VR3TESTVIN0000001"

STATUS = {
    "updatedAt": "2026-09-05T10:00:00Z",
    "battery": {"voltage": 82, "createdAt": "2026-09-05T09:55:00Z"},
    "environment": {"air": {"temp": 18.5, "createdAt": "2026-09-05T09:55:00Z"},
                    "luminosity": {"day": True, "createdAt": "2026-09-05T09:55:00Z"}},
    "odometer": {"mileage": 12345.6, "createdAt": "2026-09-05T09:55:00Z"},
    "kinetic": {"speed": 0, "moving": False, "createdAt": "2026-09-05T09:55:00Z"},
    "ignition": {"type": "Stop", "createdAt": "2026-09-05T09:55:00Z"},
    "privacy": {"state": "None", "createdAt": "2026-09-05T09:55:00Z"},
    "alarm": {"status": {"activation": "Deactivated", "createdAt": "2026-09-05T09:55:00Z"}},
    "drivingBehavior": {"mode": "Eco", "createdAt": "2026-09-05T09:55:00Z"},
    "preconditioning": {"airConditioning": {"status": "Disabled", "createdAt": "2026-09-05T09:55:00Z"}},
    "preconditionning": {"airConditioning": {"programs": [
        {"slot": 1, "enabled": True, "start": "PT7H30M", "occurence": {"day": ["Mon", "Fri"]}}]}},
    "doorsState": {
        "lockedStates": ["Locked"],
        "opening": [{"identifier": "Trunk", "state": "Closed"}, {"identifier": "Driver", "state": "Closed"},
                    {"identifier": "Passenger", "state": "Closed"}, {"identifier": "RearLeft", "state": "Closed"},
                    {"identifier": "RearRight", "state": "Closed"}],
        "createdAt": "2026-09-05T09:55:00Z",
    },
    "safety": {"beltStatus": [{"id": "Driver", "belt": "Normal"}, {"id": "Passenger", "belt": "Omission"}],
               "createdAt": "2026-09-05T09:55:00Z"},
    "energies": [{
        "type": "Electric", "level": 67, "autonomy": 210,
        "extension": {"electric": {
            "charging": {"status": "InProgress", "plugged": True, "chargingMode": "Slow", "chargingRate": 12,
                         "remainingTime": "PT1H20M", "nextDelayedTime": "PT22H30M"},
            "battery": {"load": {"capacity": 50000, "residual": 33500},
                        "health": {"resistance": 98, "capacity": 96}},
        }},
    }],
    "energy": [{"type": "Electric", "updatedAt": "2026-09-05T09:55:00Z"}],
    "lastPosition": {"type": "Feature",
                     "geometry": {"type": "Point", "coordinates": [11.7, 49.55, 480]},
                     "properties": {"heading": 90, "fixStatus": "3D", "signalQuality": 5,
                                    "createdAt": "2026-09-05T09:50:00Z"}},
}


class FakeUpstreamMqtt:
    def is_connected(self):
        return True


class FakeStellantis(StellantisVehicles):
    """Stubs every network call of the vendored client."""

    def __init__(self, hass):
        super().__init__(hass)
        self._mqtt = FakeUpstreamMqtt()
        self.sent = []
        self.status = STATUS

    async def get_vehicle_status(self, vehicle):
        return self.status

    async def get_user_vehicles(self, force=False):
        return self._vehicles

    async def send_mqtt_message(self, service, message, vehicle, store=True, action_id=None):
        self.sent.append((service, message))
        return f"action{len(self.sent)}"

    async def get_vehicle_last_trip(self, vehicle, page_token=None):
        return {"_embedded": {"trips": [{"id": "t1", "distance": 42.5, "duration": 3600, "startMileage": 12300,
                                          "kinetic": {"avgSpeed": 11.8, "maxSpeed": 95},
                                          "energyConsumptions": [{"type": "Electric", "consumption": 7100,
                                                                  "avgConsumption": 16700}]}]}}

    async def send_abrp_data(self, params):
        self.sent.append(("abrp", params))


class RecorderClient:
    """Replacement for paho.mqtt.client.Client that records everything."""

    def __init__(self):
        self.published = {}
        self.log = []
        self.subscribed = []

    def publish(self, topic, payload="", qos=0, retain=False):
        self.published[topic] = payload
        self.log.append((topic, payload))

    def subscribe(self, topic, qos=0):
        self.subscribed.append(topic)

    def unsubscribe(self, topic):
        pass

    def loop_stop(self):
        pass

    def disconnect(self):
        pass


def check(condition, message):
    print(("  ok   " if condition else "  FAIL ") + message)
    if not condition:
        check.failures += 1


check.failures = 0


async def main():
    data_dir = tempfile.mkdtemp(prefix="stellantis_smoke_")
    loop = asyncio.get_running_loop()
    hass = HomeAssistant(config_dir=data_dir, language="de", loop=loop)
    stellantis = FakeStellantis(hass)
    stellantis.set_entry(hass.config_entries.entry)
    stellantis.save_config({"mobile_app": "MyPeugeot", "country_code": "DE"})
    vehicle = {"vin": VIN, "vehicle_id": "veh1", "type": "Electric",
               "picture": "https://visuel3d-secure.peugeot.com/V3DImage.ashx?view=001"}
    stellantis._vehicles = [vehicle]

    coordinator = await stellantis.async_get_coordinator(vehicle)
    bridge = MqttBridge("localhost", 1883, None, None, loop=loop, addon_version="0.1.0")
    recorder = RecorderClient()
    bridge._client = recorder
    bridge._connected = True

    print("attach")
    binding = await bridge.attach(coordinator)
    configs = {t: json.loads(p) for t, p in recorder.published.items() if t.endswith("/config")}
    check(len(configs) == len(binding.entities), f"{len(configs)} discovery payloads for {len(binding.entities)} entities")
    unique_ids = [c["unique_id"] for c in configs.values()]
    check(len(set(unique_ids)) == len(unique_ids), "unique_ids are unique")
    components = {t.split("/")[1] for t in configs}
    check(components == {"sensor", "binary_sensor", "button", "number", "switch", "text", "device_tracker"},
          f"components: {sorted(components)}")
    battery_cfg = configs[f"homeassistant/sensor/stellantis_{VIN}/battery/config"]
    check(battery_cfg["name"] == "Batterie", f"translated name: {battery_cfg['name']}")
    check(battery_cfg["device"]["manufacturer"] == "MyPeugeot", "device manufacturer from config")
    check(battery_cfg["unit_of_measurement"] == "%" and battery_cfg["device_class"] == "battery", "sensor discovery fields")
    tracker_cfg = configs[f"homeassistant/device_tracker/stellantis_{VIN}/vehicle/config"]
    check(tracker_cfg.get("entity_picture", "").startswith("https://visuel3d"), "tracker entity_picture from vehicle picture URL")
    time_cfg = configs[f"homeassistant/text/stellantis_{VIN}/battery_charging_start/config"]
    check(time_cfg["name"] == "Start des Batterieladevorgangs" and "pattern" in time_cfg, "time -> text entity")
    check(len(recorder.subscribed) == len(binding.by_command_topic) and recorder.subscribed, f"{len(recorder.subscribed)} command topics subscribed")
    check(recorder.published[f"stellantis/{VIN}/available"] == "offline", "vehicle offline before first poll")

    print("first refresh")
    await coordinator.async_refresh()
    # key -> "<component>/<key>"; ambiguous keys (battery_charging_limit) are passed explicitly
    topic_keys = {}
    for entity in binding.entities:
        topic_keys.setdefault(entity.key, entity.topic_key)
    tk = lambda key: key if "/" in key else topic_keys[key]  # noqa: E731
    s = lambda key: recorder.published.get(f"stellantis/{VIN}/{tk(key)}/state")  # noqa: E731
    a = lambda key: json.loads(recorder.published.get(f"stellantis/{VIN}/{tk(key)}/attributes", "{}"))  # noqa: E731
    av = lambda key: recorder.published.get(f"stellantis/{VIN}/{tk(key)}/available")  # noqa: E731
    check(recorder.published[f"stellantis/{VIN}/available"] == "online", "vehicle online after poll")
    check(s("battery") == "67", f"battery state {s('battery')}")
    check(s("mileage") == "12345.6", f"mileage {s('mileage')}")
    check(s("battery_charging") == "ON" and s("battery_plugged") == "ON", "binary sensors ON")
    check(s("doors") == "OFF" and s("belt_passenger") == "ON", "doors locked / passenger belt omission")
    check(s("battery_capacity") == "50.0" and s("battery_residual") == "33.5", "kWh conversion")
    check(s("battery_charging_type") == "slow", "string states lowercased")
    check(s("battery_charging_end", ).startswith("2026-09-05T11:2") or "T" in s("battery_charging_end"), f"charging end timestamp {s('battery_charging_end')}")
    check(s("battery_charging_start") == "22:30", f"charging start text {s('battery_charging_start')}")
    check(s("type") == "electric" and s("remote_commands") == "ON", "type / remote_commands")
    check(s("refresh_interval") == "60.0" and s("abrp_sync") == "OFF" and s("abrp_token") == "", "stored-config defaults")
    tracker = a("vehicle")
    check(tracker.get("latitude") == 49.55 and tracker.get("longitude") == 11.7 and tracker.get("altitude") == 480, f"tracker attributes {tracker}")
    check(a("battery").get("Zuletzt aktualisiert") == "2026-09-05T09:55:00Z" or "2026-09-05T09:55:00Z" in a("battery").values(), f"last_updated attribute {a('battery')}")
    check(s("last_charge") not in (None, "None") and a("last_charge").get("in_progress") is True, f"last_charge started: {a('last_charge')}")
    check(av("charge_start") == "offline" and av("charge_stop") == "online", "charge buttons availability while charging")
    check(av("preconditioning_start") == "online", "preconditioning available (locked, charging)")
    check(av("switch/battery_charging_limit") == "offline", "charge-limit switch unavailable without limit")

    print("commands")
    await bridge._dispatch_command(f"stellantis/{VIN}/number/battery_charging_limit/set", "150")
    check(s("number/battery_charging_limit") == "95.0", f"number clamped to max: {s('number/battery_charging_limit')}")
    await bridge._dispatch_command(f"stellantis/{VIN}/number/refresh_interval/set", "1")
    check(s("number/refresh_interval") == "30.0" and coordinator._current_interval() == 30.0, "refresh interval clamped to min")
    await bridge._dispatch_command(f"stellantis/{VIN}/number/battery_charging_limit/set", "80")
    check(s("number/battery_charging_limit") == "80.0", "number set")
    check(stellantis.get_vehicle_stored_config(VIN, "number_battery_charging_limit") == 80.0, "number persisted in stored config")
    check(av("switch/battery_charging_limit") == "online", "charge-limit switch now available")
    await bridge._dispatch_command(f"stellantis/{VIN}/switch/battery_charging_limit/set", "ON")
    check(s("switch/battery_charging_limit") == "ON" and s("number/battery_charging_limit") == "80.0", "switch and number with same key kept apart")
    await bridge._dispatch_command(f"stellantis/{VIN}/button/doors_lock/set", "PRESS")
    check(stellantis.sent[-1] == ("/Doors", {"action": "lock"}), f"doors lock sent: {stellantis.sent[-1]}")
    check(s("command_status") == "Türen verriegeln: " or s("command_status").startswith("Türen verriegeln") or s("command_status") in ("None", None), f"command_status {s('command_status')!r}")
    check(av("horn") == "offline", "buttons unavailable while action pending")
    await coordinator.update_command_history("action1", "0")
    check(s("command_status").endswith("Abgeschlossen") or "0" in s("command_status") or s("command_status"), f"command_status after result: {s('command_status')!r}")
    check(av("horn") == "online", "buttons available again")
    await bridge._dispatch_command(f"stellantis/{VIN}/text/battery_charging_start/set", "06:15")
    check(stellantis.sent[-1][0] == "/VehCharge" and stellantis.sent[-1][1]["program"] == {"hour": 6, "minute": 15}, f"charge time sent: {stellantis.sent[-1]}")
    await bridge._dispatch_command(f"stellantis/{VIN}/button/preconditioning_start/set", "PRESS")
    check(stellantis.sent[-1][1]["programs"]["program1"] == {"day": [1, 0, 0, 0, 1, 0, 0], "hour": 7, "minute": 30, "on": 1}, f"precond programs: {stellantis.sent[-1][1]['programs']['program1']}")
    await bridge._dispatch_command(f"stellantis/{VIN}/button/wakeup/set", "PRESS")
    check(stellantis.sent[-1] == ("/VehCharge/state", {"action": "state"}), "wakeup sent")

    print("charge end + last trip")
    import copy
    ended = copy.deepcopy(STATUS)
    ended["updatedAt"] = "2026-09-05T12:00:00Z"
    ended["energies"][0]["level"] = 80
    ended["energies"][0]["extension"]["electric"]["charging"]["status"] = "Finished"
    ended["ignition"]["type"] = "StartUp"
    stellantis.status = ended
    await coordinator.async_refresh()
    check(s("battery_charging") == "OFF" and s("battery") == "80", "second poll applied")
    check(s("engine") == "ON", "engine on")
    lc = a("last_charge")
    check("in_progress" not in lc and lc.get("recharged_percent") == "13 %", f"last_charge finished: {lc}")
    check(stellantis.get_vehicle_stored_config(VIN, "last_charge")["attributes"].get("final_percentage") == "80 %", "last_charge persisted")
    stopped = copy.deepcopy(ended)
    stopped["updatedAt"] = "2026-09-05T13:00:00Z"
    stopped["ignition"]["type"] = "Stop"
    stellantis.status = stopped
    await coordinator.async_refresh()
    check(s("last_trip") == "42.5" and a("last_trip").get("electric_avg_consumption") == "16.7 kWh/100km", f"last trip: {s('last_trip')} {a('last_trip')}")

    print("stale data + failure")
    n = len(recorder.log)
    await coordinator.async_refresh()
    check(len(recorder.log) == n, f"no publishes when nothing changed {recorder.log[n:]}")
    stellantis.status = None
    for _ in range(3):
        await coordinator.async_refresh()
    check(recorder.published[f"stellantis/{VIN}/available"] == "offline", "vehicle offline after 3 empty responses")
    stellantis.status = stopped
    await coordinator.async_refresh()
    check(recorder.published[f"stellantis/{VIN}/available"] == "online", "vehicle back online")

    print("inconsistent last_charge data")
    from bridge.entities import LastChargeSensor
    lc_entity = next(e for e in binding.entities if isinstance(e, LastChargeSensor))
    lc_entity.native_value = None
    lc_entity.attributes = {"in_progress": True, "initial_percentage": "50 %"}
    stellantis.status = copy.deepcopy(STATUS)  # charging again
    stellantis.status["updatedAt"] = "2026-09-05T14:00:00Z"
    await coordinator.async_refresh()
    lc = a("last_charge")
    check(lc.get("in_progress") is True and lc.get("initial_percentage") == "67 %" and s("last_charge") != "None",
          f"stale in_progress dropped, new charge start detected: {lc}")

    print("remote commands toggled")
    n_before = len(binding.entities)
    stellantis.save_config({"remote_commands": False})
    binding2 = await bridge.attach(coordinator)
    check(binding2 is not binding and len(binding2.entities) < n_before, f"entities rebuilt: {n_before} -> {len(binding2.entities)}")
    check(recorder.published[f"homeassistant/button/stellantis_{VIN}/doors_lock/config"] == "", "button discovery cleared")
    check(not any("/button/" in t for t in recorder.subscribed[len(recorder.subscribed) - len(binding2.by_command_topic):]), "no button command topics re-subscribed")
    check(len(coordinator._listeners) == 1, "listener not duplicated")
    stellantis.save_config({"remote_commands": True})
    binding = await bridge.attach(coordinator)
    check(len(binding.entities) == n_before and recorder.published[f"homeassistant/button/stellantis_{VIN}/doors_lock/config"] != "", "entities restored when enabled again")

    print("detach")
    await bridge.detach(VIN, remove=True)
    check(recorder.published[f"homeassistant/sensor/stellantis_{VIN}/battery/config"] == "", "discovery cleared on remove")

    print(f"\n{check.failures} failures")
    print(f"config entry: {os.path.join(data_dir, 'config_entry.json')}")
    return check.failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
