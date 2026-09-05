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
- Offline-Smoke-Test `tests/smoke_bridge.py`
- Stub: Ingress-UI

Offen: Login-/OTP-Flow in der Ingress-UI, Wiring in `main.py`, CI-Build testen.
