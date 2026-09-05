# Stellantis HA Add-ons

Home-Assistant-Add-on-Repository mit einem einzigen Add-on: **Stellantis Vehicles**.
Es fasst die HACS-Integration [homeassistant-stellantis-vehicles](https://github.com/andreadegiovine/homeassistant-stellantis-vehicles)
und den zugehörigen OAuth-Login-Worker in einem Container zusammen. Fahrzeugdaten
kommen per MQTT Discovery in Home Assistant an, der Browser-Login läuft lokal statt
auf einem fremden Server.

## Installation

Einstellungen → Add-ons → Add-on Store → ⋮ → Repositories →
`https://github.com/taubenhorst/StellantisHAAddon`

Voraussetzungen: Mosquitto-Broker-Add-on und MQTT-Integration in Home Assistant.

## Aufbau

```
stellantis_vehicles/
├── config.yaml / build.yaml / Dockerfile     Add-on-Packaging
├── rootfs/etc/services.d/stellantis/run     s6-Service
└── app/
    ├── main.py               Einstieg
    ├── hass_shim/            Minimal-Ersatz für das `homeassistant`-Paket
    ├── stellantis_vehicles/  Upstream-Code (unverändert, siehe UPSTREAM.md) + eigenes base.py
    ├── bridge/               MQTT-Discovery-Bridge
    ├── oauth_browser/        Playwright-Login (Clean-Room)
    └── web/                  Ingress-UI
```

Entwurfsprinzip: der Upstream-Code bleibt unverändert, die HA-Abhängigkeiten liefert
`hass_shim/`. Upstream-Fixes lassen sich damit durch Kopieren der Dateien übernehmen.

## Entwicklung

```bash
cd stellantis_vehicles
pip install -r requirements.txt
DATA_DIR=./data python app/main.py
```

Lokaler Image-Build: siehe `build.yaml`; CI baut aarch64 und amd64 nach GHCR.

## Status

Funktionsfähig (Login, OTP, Statusabruf, MQTT-Discovery), Images werden per CI nach GHCR gebaut —
siehe `stellantis_vehicles/CHANGELOG.md`. Noch nicht auf einem Pi im Dauerbetrieb getestet.

## Lizenz

MIT, siehe `LICENSE`. Upstream-Anteile ebenfalls MIT (Andrea De Giovine).
