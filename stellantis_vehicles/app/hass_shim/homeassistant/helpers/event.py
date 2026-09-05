"""asyncio replacement for async_track_point_in_time."""
import asyncio
import inspect
from datetime import datetime
from typing import Callable

from ..core import HassJob


def async_track_point_in_time(hass, job: HassJob | Callable, point_in_time: datetime) -> Callable[[], None]:
    loop = hass.loop
    target = job.target if isinstance(job, HassJob) else job
    now = datetime.now(point_in_time.tzinfo) if point_in_time.tzinfo else datetime.now()
    delay = max(0.0, (point_in_time - now).total_seconds())

    def _fire() -> None:
        result = target(point_in_time)
        if inspect.isawaitable(result):
            loop.create_task(result)

    handle = loop.call_later(delay, _fire)
    return handle.cancel
