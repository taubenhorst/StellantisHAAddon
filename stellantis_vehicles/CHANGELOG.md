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
- Runtime (`runtime.py`): Fahrzeuge laden, Coordinators starten, Bridge anbinden, Retry bei
  API-Fehlern, Neu-Login bei abgelaufener Anmeldung ohne Neustart
- MQTT-Broker aus den Optionen oder vom Supervisor (`services: mqtt`)
- Offline-Smoke-Tests `tests/smoke_bridge.py`, `tests/smoke_web.py`, `tests/smoke_runtime.py`
- `mobile_app` auf die vom Upstream unterstützten Apps beschränkt

- Echter Login und Statusabruf verifiziert; Fahrzeugbild als `entity_picture`
- Docker-Image lokal gebaut und gestartet (amd64, 1,9 GB); `.dockerignore`

- CI baut amd64 und aarch64 nach GHCR

Offen: Installation auf dem Pi.
