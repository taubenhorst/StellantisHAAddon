## 0.1.0

Skelett — noch nicht lauffähig als Add-on.

- Repo-Struktur, `config.yaml`, Debian-basiertes Dockerfile mit Playwright/Chromium
- Upstream-Code (stellantis.py, otp, const, utils) unverändert vendored, Commit 69fddda
- `hass_shim`: Ersatz für die genutzten `homeassistant`-Imports
- Eigener Coordinator (`base.py`) ohne HA-Entities
- Clean-Room-Playwright-Login in `oauth_browser/`
- Stubs: MQTT-Discovery-Bridge, Ingress-UI

Offen: Discovery-Mapping der Entities, Login-/OTP-Flow in der Ingress-UI,
Wiring in `main.py`, CI-Build testen.
