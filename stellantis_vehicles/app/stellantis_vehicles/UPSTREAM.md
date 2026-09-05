# Upstream-Herkunft

Dieses Paket ist ein unveränderter Vendor-Import aus
https://github.com/andreadegiovine/homeassistant-stellantis-vehicles
(MIT-Lizenz, siehe `LICENSE.upstream`).

- Commit: 69fddda697fb5e81d8873db7410b23956f437fbb
- Version: 2026.9.1
- Übernommen: `stellantis.py`, `const.py`, `utils.py`, `exceptions.py`, `configs.json`, `manifest.json`, `otp/`, `translations/*.json` (alle 14 Sprachen)
- **Nicht** übernommen: `base.py`, `config_flow.py`, alle Plattform-Dateien (`sensor.py`, `button.py`, …), `frontend/`
- **Eigene Datei**: `base.py` — Ersatz für den HA-Coordinator, leitet an `bridge/` weiter

Regel: Dateien aus der Liste "Übernommen" nicht editieren. Alles, was HA erwartet,
liefert `hass_shim/`. Upstream-Update = Dateien neu kopieren, Commit-Hash hier nachziehen.
