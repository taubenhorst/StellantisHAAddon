"""Loads translations/<lang>.json of the vendored integration and flattens it
to HA-style keys: component.<domain>.<category>.<...>."""
import json
import logging
import os
from functools import lru_cache

_LOGGER = logging.getLogger(__name__)
# helpers/ -> homeassistant/ -> hass_shim/ -> app/
_APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_TRANSLATIONS_DIR = os.path.join(_APP_DIR, "stellantis_vehicles", "translations")


def _flatten(prefix: str, node, out: dict) -> None:
    if isinstance(node, dict):
        for k, v in node.items():
            _flatten(f"{prefix}.{k}", v, out)
    else:
        out[prefix] = node


@lru_cache(maxsize=8)
def _load(language: str, domain: str) -> dict:
    for lang in (language, language.split("-")[0], "en"):
        path = os.path.join(_TRANSLATIONS_DIR, f"{lang}.json")
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                out: dict = {}
                _flatten(f"component.{domain}", json.load(f), out)
                return out
    _LOGGER.warning("No translation file found for %s", language)
    return {}


async def async_get_translations(hass, language: str, category: str, integrations=None, **_) -> dict:
    result: dict = {}
    for domain in (integrations or ()):
        result.update({k: v for k, v in _load(language, domain).items()
                       if k.startswith(f"component.{domain}.{category}.")})
    return result
