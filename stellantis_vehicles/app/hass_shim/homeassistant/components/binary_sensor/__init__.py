from enum import StrEnum


class BinarySensorDeviceClass(StrEnum):
    BATTERY_CHARGING = "battery_charging"
    DOOR = "door"
    LIGHT = "light"
    LOCK = "lock"
    MOVING = "moving"
    PLUG = "plug"
    POWER = "power"
    RUNNING = "running"
    SAFETY = "safety"
