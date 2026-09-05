## 0.1.0

Skelett — noch nicht lauffähig als Add-on.

- Repo-Struktur, `config.yaml`, Debian-basiertes Dockerfile mit Playwright/Chromium
- Upstream-Code (stellantis.py, otp, const, utils) unverändert vendored, Commit 69fddda
- `hass_shim`: Ersatz für die genutzten `homeassistant`-Imports
- Eigener Coordinator (`base.py`): Port der Upstream-Logik ohne HA (Polling, Command-History,
  Fernbefehle, Ladelimit, ABRP, letzte Fahrt)
- MQTT-Discovery-Bridge (`bridge/`): alle Upstream-Entities (sensor, binary_sensor, button,
  number, switch, text, device_tracker) als HA-Gerät pro Fahrzeug; Command-Topics für Buttons,
  Zahlen, Schalter, Texte und die Ladestartzeit
- Clean-Room-Playwright-Login in `oauth_browser/`
- Ingress-UI (`web/`): Login (Chromium im Add-on oder manuell per Code/URL), OTP-Einrichtung
  per SMS-Code + PIN, Statusseite mit Token-Laufzeiten, Fahrzeugen, Benachrichtigungen;
  Fernbefehle deaktivieren/neu einrichten, Neu-Anmeldung
- Offline-Smoke-Tests `tests/smoke_bridge.py`, `tests/smoke_web.py`
- `mobile_app` auf die vom Upstream unterstützten Apps beschränkt

Offen: Wiring in `main.py` (Fahrzeuge starten), CI-Build testen.
