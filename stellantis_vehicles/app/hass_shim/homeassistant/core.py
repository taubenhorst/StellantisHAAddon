"""Replacement for homeassistant.core: a tiny object that carries the event
loop, config paths and a persistent JSON store for the config entry."""
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable

_LOGGER = logging.getLogger(__name__)


@dataclass
class HassJob:
    target: Callable
    name: str | None = None
    cancel_on_shutdown: bool = False


class Config:
    def __init__(self, config_dir: str, language: str = "en"):
        self.config_dir = config_dir
        self.language = language

    def path(self, *parts: str) -> str:
        return os.path.join(self.config_dir, *parts)


@dataclass
class ConfigEntry:
    """Mirrors the fields stellantis.py touches on a HA config entry."""
    data: dict = field(default_factory=dict)
    entry_id: str = "addon"
    # Called by async_start_reauth; the runtime points it at its own
    # "login required" handling (HA would start a reauth config flow).
    on_reauth: Callable[[], None] | None = None

    def async_start_reauth(self, hass: Any = None, **_: Any) -> None:
        if self.on_reauth is None:
            _LOGGER.warning("Reauthentication requested, but no handler is registered")
            return
        self.on_reauth()


class ConfigEntries:
    """Persists the single config entry as JSON under the add-on data dir."""

    def __init__(self, store_path: str):
        self._store_path = store_path
        self.entry = ConfigEntry(data=self._load())

    def _load(self) -> dict:
        try:
            with open(self._store_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def async_update_entry(self, entry: ConfigEntry, data: dict | None = None, **_: Any) -> bool:
        """Like HA: update the entry and persist it (upstream no longer calls
        the private _async_schedule_save itself since 2026.9.2)."""
        if data is not None:
            entry.data = data
            if entry is self.entry:
                self._async_schedule_save()
        return True

    def _async_schedule_save(self) -> None:
        os.makedirs(os.path.dirname(self._store_path), exist_ok=True)
        tmp = self._store_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.entry.data, f, indent=2)
        os.replace(tmp, self._store_path)


class HomeAssistant:
    def __init__(self, config_dir: str, language: str = "en",
                 loop: asyncio.AbstractEventLoop | None = None):
        self.loop = loop or asyncio.get_event_loop()
        self.config = Config(config_dir, language)
        self.config_entries = ConfigEntries(os.path.join(config_dir, "config_entry.json"))
        self.notifications: list[dict] = []

    def async_add_executor_job(self, func: Callable, *args: Any) -> asyncio.Future:
        return self.loop.run_in_executor(None, func, *args)
