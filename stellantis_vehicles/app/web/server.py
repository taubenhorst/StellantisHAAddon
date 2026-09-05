"""Ingress web UI (skeleton).

Planned pages:
  /          status: vehicles, token expiry, MQTT state, notifications
  /login     e-mail + password -> automatic (Chromium) or manual OAuth code
  /otp       SMS code + PIN for OTP enrolment
"""
import logging

from aiohttp import web

_LOGGER = logging.getLogger(__name__)


def build_app(state: dict) -> web.Application:
    app = web.Application()

    async def index(_request: web.Request) -> web.Response:
        lines = ["<h1>Stellantis Vehicles Add-on</h1>", "<ul>"]
        for key, value in state.items():
            lines.append(f"<li><b>{key}</b>: {value}</li>")
        lines.append("</ul>")
        return web.Response(text="\n".join(lines), content_type="text/html")

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok"})

    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    return app


async def start(state: dict, port: int) -> web.AppRunner:
    runner = web.AppRunner(build_app(state))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    _LOGGER.info("Ingress UI listening on port %s", port)
    return runner
