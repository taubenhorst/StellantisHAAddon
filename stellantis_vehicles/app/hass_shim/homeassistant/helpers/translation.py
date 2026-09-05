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


# Upstream file names that differ from the usual language codes
_ALIASES = {"cs": "cz", "nb-no": "nb", "no-no": "no", "pt-br": "pt", "pt-pt": "pt"}


def _read(lang: str, domain: str) -> dict | None:
    path = os.path.join(_TRANSLATIONS_DIR, f"{lang}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        out: dict = {}
        _flatten(f"component.{domain}", json.load(f), out)
        return out


@lru_cache(maxsize=16)
def _load(language: str, domain: str) -> dict:
    """English as base, the requested language on top: keys missing in a
    partially translated upstream file fall back to English, not to the key."""
    result = _read("en", domain) or {}
    lang = language.lower()
    candidates = (lang, _ALIASES.get(lang, ""), lang.split("-")[0], _ALIASES.get(lang.split("-")[0], ""))
    for candidate in candidates:
        if candidate and candidate != "en":
            overlay = _read(candidate, domain)
            if overlay is not None:
                result.update(overlay)
                return result
    if lang.split("-")[0] != "en":
        _LOGGER.warning("No translation file found for %s, using English", language)
    return result


async def async_get_translations(hass, language: str, category: str, integrations=None, **_) -> dict:
    result: dict = {}
    for domain in (integrations or ()):
        result.update({k: v for k, v in _load(language, domain).items()
                       if k.startswith(f"component.{domain}.{category}.")})
    return result
