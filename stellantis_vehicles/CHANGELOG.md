## 0.1.0

First working version.

- Repository layout, `config.yaml`, Debian based Dockerfile with Playwright/Chromium
- Upstream code (stellantis.py, otp, const, utils) vendored unchanged, commit 69fddda
- `hass_shim`: stand-in for the `homeassistant` imports the upstream code uses
- Own coordinator (`base.py`): port of the upstream logic without HA (polling, command
  history, remote commands, charge limit, ABRP, last trip)
- MQTT discovery bridge (`bridge/`): all upstream entities (sensor, binary_sensor, button,
  number, switch, text, device_tracker) as one HA device per vehicle; command topics for
  buttons, numbers, switches, texts and the charge start time
- Ingress UI (`web/`): login (Chromium inside the add-on or manual via code/URL), OTP setup
  with SMS code + PIN, status page with token expiry, vehicles, notifications; disable or
  reconfigure remote commands, re-login
- Runtime (`runtime.py`): load vehicles, start coordinators, attach the bridge, retry on API
  errors, re-login after an expired session without restart
- MQTT broker from the options or from the Supervisor (`services: mqtt`)
- Clean-room Playwright login in `oauth_browser/`; real Chromium in the new headless mode
  (the headless shell is rejected by the Stellantis identity provider)
- Offline smoke tests `tests/smoke_bridge.py`, `tests/smoke_web.py`, `tests/smoke_runtime.py`
- `mobile_app` restricted to the apps supported upstream
- Real login and status retrieval verified; vehicle picture as `entity_picture`
- Docker image built and started locally (amd64, 1.9 GB); `.dockerignore`
- CI builds amd64 and aarch64 images to GHCR
- All 14 upstream translations, per-key English fallback, browser locale from the app configuration

Open: installation on the Pi.
