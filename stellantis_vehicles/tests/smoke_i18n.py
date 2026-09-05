"""Offline check of the translation loader: all vendored languages load,
partially translated files fall back to English per key, aliases resolve.

    .venv/Scripts/python tests/smoke_i18n.py
"""
import asyncio
import os
import sys

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app")
sys.path.insert(0, os.path.join(APP_DIR, "hass_shim"))
sys.path.insert(0, APP_DIR)

from homeassistant.helpers import translation  # noqa: E402

DOMAIN = "stellantis_vehicles"
LANGS = ["cz", "da", "de", "en", "es", "fi", "fr", "it", "nb", "nl", "no", "pl", "pt", "sv"]
BATTERY = f"component.{DOMAIN}.entity.sensor.battery.name"
OTP_ERR = f"component.{DOMAIN}.config.error.get_mqtt_access_token_nok_access"


def check(condition, message):
    print(("  ok   " if condition else "  FAIL ") + message)
    if not condition:
        check.failures += 1


check.failures = 0


async def main():
    en_entity = await translation.async_get_translations(None, "en", "entity", {DOMAIN})
    en_config = await translation.async_get_translations(None, "en", "config", {DOMAIN})
    check(en_entity[BATTERY] == "Battery" and OTP_ERR in en_config, "english base")

    print("all vendored languages")
    for lang in LANGS:
        entity = await translation.async_get_translations(None, lang, "entity", {DOMAIN})
        config = await translation.async_get_translations(None, lang, "config", {DOMAIN})
        # Every English key must exist (fallback); extra upstream keys are fine
        check(set(en_entity) <= set(entity) and set(en_config) <= set(config),
              f"{lang}: {len(entity)} entity / {len(config)} config keys (battery = {entity.get(BATTERY)!r})")

    print("fallback and aliases")
    fr = await translation.async_get_translations(None, "fr-FR", "entity", {DOMAIN})
    check(fr[BATTERY] == "Niveau batterie", "region code fr-FR -> fr")
    no = await translation.async_get_translations(None, "no", "config", {DOMAIN})
    check(no[OTP_ERR] == en_config[OTP_ERR], "untranslated key in no.json falls back to English text")
    cs = await translation.async_get_translations(None, "cs", "entity", {DOMAIN})
    check(cs[BATTERY] == "Baterie", "alias cs -> cz.json")
    xx = await translation.async_get_translations(None, "xx", "entity", {DOMAIN})
    check(xx[BATTERY] == "Battery", "unknown language -> English")

    print(f"\n{check.failures} failures")
    return check.failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
