"""Ingress web UI.

One page (``/``) that renders whatever the setup flow needs next - login,
OTP or the status overview - plus POST endpoints that feed the flow and
redirect back. All links are relative so the page works behind the HA
ingress proxy (``/api/hassio_ingress/<token>/``) as well as on a bare port.
"""
import html
import logging
from datetime import datetime

from aiohttp import web

from .setup import STEP_DONE, STEP_LOGIN, STEP_OTP, SetupError, SetupFlow

_LOGGER = logging.getLogger(__name__)

TEXT = {
    "title": ("Stellantis Vehicles", "Stellantis Vehicles"),
    "login_h": ("Anmeldung beim Stellantis-Konto", "Sign in to the Stellantis account"),
    "login_browser": ("Die Anmeldung läuft lokal in einem headless Chromium im Add-on. E-Mail und Passwort "
                      "stammen aus den Add-on-Optionen, können hier aber überschrieben werden.",
                      "Login runs locally in a headless Chromium inside the add-on. E-mail and password come "
                      "from the add-on options but can be overridden here."),
    "login_manual": ("Manueller Modus: Anmeldung im eigenen Desktop-Browser, Netzwerk-Tab der DevTools (F12) "
                     "öffnen, nach dem Login die fehlgeschlagene Anfrage an <code>mym…://oauth2redirect/…?code=…</code> "
                     "suchen und die komplette URL (oder nur den Code) unten einfügen.",
                     "Manual mode: sign in with your desktop browser, open the DevTools network tab (F12), "
                     "after login look for the failed request to <code>mym…://oauth2redirect/…?code=…</code> "
                     "and paste the whole URL (or just the code) below."),
    "open_login": ("Anmeldeseite öffnen", "Open login page"),
    "email": ("E-Mail", "E-mail"),
    "password": ("Passwort", "Password"),
    "code": ("OAuth-Code oder Redirect-URL", "OAuth code or redirect URL"),
    "login_btn": ("Anmelden", "Sign in"),
    "code_btn": ("Code verwenden", "Use code"),
    "otp_h": ("Fernbefehle einrichten (OTP)", "Set up remote commands (OTP)"),
    "otp_p": ("Stellantis hat einen SMS-Code an die im Konto hinterlegte Nummer geschickt. Zusätzlich wird "
              "der PIN-Code aus der Fahrzeug-App benötigt.",
              "Stellantis sent an SMS code to the phone number of the account. The PIN code from the "
              "vehicle app is needed as well."),
    "sms_code": ("SMS-Code", "SMS code"),
    "pin_code": ("PIN-Code der App", "App PIN code"),
    "otp_btn": ("Einrichten", "Configure"),
    "sms_again": ("SMS erneut anfordern", "Resend SMS"),
    "skip_remote": ("Ohne Fernbefehle fortfahren", "Continue without remote commands"),
    "status_h": ("Status", "Status"),
    "vehicles_h": ("Fahrzeuge", "Vehicles"),
    "no_vehicles": ("Noch keine Fahrzeuge geladen.", "No vehicles loaded yet."),
    "account": ("Konto", "Account"),
    "oauth_expires": ("OAuth-Token gültig bis", "OAuth token valid until"),
    "mqtt_expires": ("MQTT-Token gültig bis", "MQTT token valid until"),
    "remote": ("Fernbefehle", "Remote commands"),
    "on": ("aktiv", "enabled"),
    "off": ("aus", "disabled"),
    "actions_h": ("Aktionen", "Actions"),
    "reauth": ("Neu anmelden", "Sign in again"),
    "reconf_remote": ("Fernbefehle neu einrichten", "Reconfigure remote commands"),
    "disable_remote": ("Fernbefehle deaktivieren", "Disable remote commands"),
    "notifications_h": ("Benachrichtigungen", "Notifications"),
    "dismiss": ("Alle schließen", "Dismiss all"),
    "busy": ("Vorgang läuft …", "Working …"),
    "back": ("Zurück zur Übersicht", "Back to overview"),
}

STYLE = """
body{font-family:system-ui,sans-serif;margin:0;background:#f4f5f7;color:#1f2937}
main{max-width:760px;margin:0 auto;padding:1.5rem}
h1{font-size:1.4rem}h2{font-size:1.1rem;margin-top:1.5rem}
.card{background:#fff;border-radius:8px;padding:1rem 1.25rem;margin:1rem 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.err{background:#fee2e2;border-left:4px solid #dc2626}.ok{background:#dcfce7;border-left:4px solid #16a34a}
.busy{background:#fef9c3;border-left:4px solid #ca8a04}
label{display:block;margin:.6rem 0 .2rem;font-weight:600}
input[type=text],input[type=email],input[type=password]{width:100%;padding:.5rem;border:1px solid #cbd5e1;border-radius:6px;box-sizing:border-box}
button{margin-top:.8rem;padding:.5rem 1rem;border:0;border-radius:6px;background:#2563eb;color:#fff;cursor:pointer}
button.secondary{background:#e5e7eb;color:#111}form.inline{display:inline}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:.3rem .4rem;border-bottom:1px solid #e5e7eb;vertical-align:top}
code{background:#f1f5f9;padding:0 .2rem;border-radius:3px}
"""


def _fmt_time(value) -> str:
    if not value:
        return "–"
    try:
        return datetime.fromisoformat(str(value)).strftime("%d.%m.%Y %H:%M")
    except ValueError:
        return str(value)


class Pages:
    def __init__(self, flow: SetupFlow, hass, state: dict) -> None:
        self._flow = flow
        self._hass = hass
        self._state = state
        self._de = hass.config.language.startswith("de")

    def t(self, key: str) -> str:
        return TEXT[key][0 if self._de else 1]

    def render(self) -> str:
        flow = self._flow
        snap = flow.snapshot()
        parts = [f"<h1>{self.t('title')}</h1>"]
        if snap["busy"]:
            parts.append(f"<div class='card busy'>{self.t('busy')}</div>")
        if snap["error"]:
            parts.append(f"<div class='card err'>{html.escape(snap['error'])}</div>")
        if snap["message"]:
            parts.append(f"<div class='card ok'>{html.escape(snap['message'])}</div>")

        if snap["step"] == STEP_LOGIN:
            parts.append(self._login(snap))
        elif snap["step"] == STEP_OTP:
            parts.append(self._otp(snap))
        else:
            parts.append(self._status(snap))
        parts.append(self._notifications())

        refresh = "<meta http-equiv='refresh' content='3'>" if snap["busy"] else ""
        return (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>"
                f"<title>{self.t('title')}</title>{refresh}<style>{STYLE}</style></head>"
                f"<body><main>{''.join(parts)}</main></body></html>")

    def _login(self, snap: dict) -> str:
        e = html.escape
        head = (f"<h2>{self.t('login_h')}</h2><p>{e(snap['mobile_app'])} · {e(snap['country_code'])}</p>")
        if snap["oauth_mode"] == "manual":
            link = f"<p><a href='{e(snap['oauth_url'] or '#')}' target='_blank' rel='noopener'>{self.t('open_login')}</a></p>" if snap["oauth_url"] else ""
            form = (f"<p>{self.t('login_manual')}</p>{link}"
                    f"<form method='post' action='login'><label>{self.t('code')}</label>"
                    f"<input type='text' name='code' autocomplete='off' required>"
                    f"<button type='submit'>{self.t('code_btn')}</button></form>")
        else:
            form = (f"<p>{self.t('login_browser')}</p>"
                    f"<form method='post' action='login'>"
                    f"<label>{self.t('email')}</label><input type='email' name='email' value='{e(snap['email'])}'>"
                    f"<label>{self.t('password')}</label><input type='password' name='password' placeholder='••••••••'>"
                    f"<button type='submit'>{self.t('login_btn')}</button></form>")
        return f"<div class='card'>{head}{form}</div>"

    def _otp(self, snap: dict) -> str:
        return (f"<div class='card'><h2>{self.t('otp_h')}</h2><p>{self.t('otp_p')}</p>"
                f"<form method='post' action='otp'>"
                f"<label>{self.t('sms_code')}</label><input type='text' name='sms_code' autocomplete='one-time-code' required>"
                f"<label>{self.t('pin_code')}</label><input type='password' name='pin_code' required>"
                f"<button type='submit'>{self.t('otp_btn')}</button></form>"
                f"<form class='inline' method='post' action='sms'><button class='secondary' type='submit'>{self.t('sms_again')}</button></form> "
                f"<form class='inline' method='post' action='remote/disable'><button class='secondary' type='submit'>{self.t('skip_remote')}</button></form>"
                f"</div>")

    def _status(self, snap: dict) -> str:
        e = html.escape
        remote = self.t("on") if snap["remote_commands_ready"] else self.t("off")
        rows = [
            (self.t("account"), f"{e(snap['mobile_app'])} · {e(snap['country_code'])} · {e(snap['email'])}"),
            (self.t("oauth_expires"), _fmt_time(snap["oauth_expires"])),
            (self.t("remote"), remote),
        ]
        if snap["remote_commands_ready"]:
            rows.append((self.t("mqtt_expires"), _fmt_time(snap["mqtt_expires"])))
        for key, value in self._state.items():
            if key == "vehicles":
                continue
            rows.append((e(str(key)), e(str(value))))
        table = "".join(f"<tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows)

        vehicles = self._state.get("vehicles") or []
        if vehicles:
            vrows = "".join(
                f"<tr><td><code>{e(str(v.get('vin', '')))}</code></td><td>{e(str(v.get('type', '')))}</td>"
                f"<td>{'✓' if v.get('ok') else '✗'}</td><td>{_fmt_time(v.get('updated_at'))}</td></tr>"
                for v in vehicles)
            vehicles_html = f"<table>{vrows}</table>"
        else:
            vehicles_html = f"<p>{self.t('no_vehicles')}</p>"

        actions = (f"<form class='inline' method='post' action='reauth'><button class='secondary' type='submit'>{self.t('reauth')}</button></form> "
                   f"<form class='inline' method='post' action='remote/reconfigure'><button class='secondary' type='submit'>{self.t('reconf_remote')}</button></form> ")
        if snap["remote_commands"] is not False:
            actions += f"<form class='inline' method='post' action='remote/disable'><button class='secondary' type='submit'>{self.t('disable_remote')}</button></form>"
        return (f"<div class='card'><h2>{self.t('status_h')}</h2><table>{table}</table></div>"
                f"<div class='card'><h2>{self.t('vehicles_h')}</h2>{vehicles_html}</div>"
                f"<div class='card'><h2>{self.t('actions_h')}</h2>{actions}</div>")

    def _notifications(self) -> str:
        notes = self._hass.notifications
        if not notes:
            return ""
        items = "".join(
            f"<li><b>{html.escape(str(n.get('title') or ''))}</b> {html.escape(str(n.get('message') or ''))}"
            f" <small>{_fmt_time(n.get('created'))}</small></li>" for n in reversed(notes[-20:]))
        return (f"<div class='card'><h2>{self.t('notifications_h')}</h2><ul>{items}</ul>"
                f"<form method='post' action='notifications/dismiss'><button class='secondary' type='submit'>{self.t('dismiss')}</button></form></div>")


def build_app(state: dict, flow: SetupFlow, hass) -> web.Application:
    app = web.Application()
    pages = Pages(flow, hass, state)

    def back() -> web.Response:
        return web.HTTPSeeOther("./")

    def run(action) -> web.Response:
        try:
            action()
        except SetupError as err:
            flow.error = str(err)
        return back()

    async def index(_request: web.Request) -> web.Response:
        return web.Response(text=pages.render(), content_type="text/html")

    async def login(request: web.Request) -> web.Response:
        form = await request.post()
        code = form.get("code")
        if code is not None:
            return run(lambda: flow.start_login(code=code))
        return run(lambda: flow.start_login(form.get("email") or None, form.get("password") or None))

    async def otp(request: web.Request) -> web.Response:
        form = await request.post()
        return run(lambda: flow.start_otp(form.get("sms_code", ""), form.get("pin_code", "")))

    async def sms(_request: web.Request) -> web.Response:
        return run(flow.start_sms)

    async def remote_disable(_request: web.Request) -> web.Response:
        return run(flow.disable_remote_commands)

    async def remote_reconfigure(_request: web.Request) -> web.Response:
        return run(flow.reconfigure_remote_commands)

    async def reauth(_request: web.Request) -> web.Response:
        return run(flow.reauth)

    async def dismiss(_request: web.Request) -> web.Response:
        hass.notifications.clear()
        return back()

    async def api_state(_request: web.Request) -> web.Response:
        return web.json_response({"flow": flow.snapshot(), "state": state, "notifications": hass.notifications})

    async def health(_request: web.Request) -> web.Response:
        return web.json_response({"status": "ok", "step": flow.step})

    app.router.add_get("/", index)
    app.router.add_post("/login", login)
    app.router.add_post("/otp", otp)
    app.router.add_post("/sms", sms)
    app.router.add_post("/remote/disable", remote_disable)
    app.router.add_post("/remote/reconfigure", remote_reconfigure)
    app.router.add_post("/reauth", reauth)
    app.router.add_post("/notifications/dismiss", dismiss)
    app.router.add_get("/api/state", api_state)
    app.router.add_get("/health", health)
    return app


async def start(state: dict, flow: SetupFlow, hass, port: int) -> web.AppRunner:
    runner = web.AppRunner(build_app(state, flow, hass))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    _LOGGER.info("Ingress UI listening on port %s", port)
    return runner


__all__ = ["build_app", "start", "STEP_DONE", "STEP_LOGIN", "STEP_OTP"]
