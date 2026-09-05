"""Units and enums used by const.py of the vendored integration.

Values are the exact strings HA uses, so they can be reused verbatim in MQTT
discovery payloads (unit_of_measurement, device_class, entity_category).
"""
from enum import StrEnum

PERCENTAGE = "%"


class UnitOfTemperature(StrEnum):
    CELSIUS = "°C"
    FAHRENHEIT = "°F"


class UnitOfLength(StrEnum):
    KILOMETERS = "km"
    MILES = "mi"
    METERS = "m"


class UnitOfEnergy(StrEnum):
    KILO_WATT_HOUR = "kWh"
    WATT_HOUR = "Wh"


class UnitOfSpeed(StrEnum):
    KILOMETERS_PER_HOUR = "km/h"
    MILES_PER_HOUR = "mph"


class UnitOfVolume(StrEnum):
    LITERS = "L"
    GALLONS = "gal"


class EntityCategory(StrEnum):
    CONFIG = "config"
    DIAGNOSTIC = "diagnostic"


CONF_EMAIL = "email"
CONF_PASSWORD = "password"
