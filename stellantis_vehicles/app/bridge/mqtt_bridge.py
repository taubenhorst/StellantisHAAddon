"""MQTT discovery bridge (skeleton).

Responsibilities, to be implemented in the next step:
  1. Connect to the HA broker using credentials from the add-on config
     (bashio `services mqtt`), with LWT on `<prefix>/status`.
  2. For every vehicle publish one HA device and its entities via MQTT
     discovery (`homeassistant/<component>/<vin>_<key>/config`), mapping
     the entity descriptions from the upstream platform files
     (sensor.py, binary_sensor.py, button.py, number.py, switch.py, ...).
  3. On every coordinator update publish the state topics.
  4. Subscribe to command topics and forward them to
     `StellantisVehicles.send_mqtt_message()` / the button/number handlers.
"""
import json
import logging

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger(__name__)


class MqttBridge:
    def __init__(self, host: str, port: int, username: str | None, password: str | None,
                 discovery_prefix: str = "homeassistant", topic_prefix: str = "stellantis") -> None:
        self._host, self._port = host, port
        self._discovery_prefix = discovery_prefix
        self._prefix = topic_prefix
        self._client = mqtt.Client(client_id="stellantis-addon", protocol=mqtt.MQTTv311)
        if username:
            self._client.username_pw_set(username, password)
        self._client.will_set(f"{self._prefix}/status", "offline", retain=True)

    def connect(self) -> None:
        _LOGGER.info("Connecting to MQTT broker %s:%s", self._host, self._port)
        self._client.connect(self._host, self._port, keepalive=60)
        self._client.loop_start()
        self._client.publish(f"{self._prefix}/status", "online", retain=True)

    def disconnect(self) -> None:
        self._client.publish(f"{self._prefix}/status", "offline", retain=True)
        self._client.loop_stop()
        self._client.disconnect()

    async def on_coordinator_update(self, coordinator) -> None:
        # TODO: map coordinator.data to state topics; publish discovery on first update
        topic = f"{self._prefix}/{coordinator.vin}/state"
        self._client.publish(topic, json.dumps(coordinator.data, default=str), retain=True)
