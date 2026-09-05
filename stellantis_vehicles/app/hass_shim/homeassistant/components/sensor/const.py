from enum import StrEnum


class SensorDeviceClass(StrEnum):
    BATTERY = "battery"
    DISTANCE = "distance"
    ENERGY_STORAGE = "energy_storage"
    SPEED = "speed"
    TEMPERATURE = "temperature"
    TIMESTAMP = "timestamp"


class SensorStateClass(StrEnum):
    MEASUREMENT = "measurement"
    TOTAL = "total"
    TOTAL_INCREASING = "total_increasing"
