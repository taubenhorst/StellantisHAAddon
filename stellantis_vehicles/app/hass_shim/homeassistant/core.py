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
        if data is not None:
            entry.data = data
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
