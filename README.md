# Stellantis HA Add-ons

Home Assistant add-on repository with a single add-on: **Stellantis Vehicles**.
It bundles the HACS integration [homeassistant-stellantis-vehicles](https://github.com/andreadegiovine/homeassistant-stellantis-vehicles)
and its OAuth login worker in one container. Vehicle data reaches Home Assistant via
MQTT discovery; the browser login runs locally inside the add-on instead of on a
third-party server.

Supported brands are the ones the upstream integration supports: Peugeot, Citroën, DS,
Opel and Vauxhall (the former PSA apps). Fiat, Jeep, Alfa Romeo and the other FCA brands
use a different backend and are not covered.

## Disclaimer

This is an unofficial community project. It is not affiliated with, endorsed by or
supported by Stellantis or any of its brands, and it uses the same non-public vehicle
APIs as the upstream integration, which may change or stop working at any time.
Stellantis, Peugeot, Citroën, DS, Opel, Vauxhall and all other brand names and logos
mentioned here are trademarks of Stellantis N.V. and its subsidiaries. Use at your own risk.

## Installation

Settings → Add-ons → Add-on Store → ⋮ → Repositories →
`https://github.com/taubenhorst/StellantisHAAddon`

Requirements: the Mosquitto broker add-on and the MQTT integration in Home Assistant,
Home Assistant 2025.10 or newer.

## Layout

```
stellantis_vehicles/
├── config.yaml / build.yaml / Dockerfile     add-on packaging
├── rootfs/etc/services.d/stellantis/run     s6 service
├── tests/                                   offline smoke tests
└── app/
    ├── main.py               entry point
    ├── runtime.py            vehicles, coordinators, bridge wiring
    ├── hass_shim/            minimal stand-in for the `homeassistant` package
    ├── stellantis_vehicles/  upstream code (unchanged, see UPSTREAM.md) + own base.py
    ├── bridge/               MQTT discovery bridge
    ├── oauth_browser/        Playwright login (clean-room)
    └── web/                  ingress UI (login, OTP, status)
```

Design principle: the upstream code stays untouched, its Home Assistant dependencies are
provided by `hass_shim/`. Upstream fixes can therefore be taken over by copying files.

## Development

```bash
cd stellantis_vehicles
pip install -r requirements.txt
python -m playwright install chromium
python app/main.py          # uses ./data as data directory, UI on http://localhost:8099/
```

Offline tests (no network, no broker):

```bash
python tests/smoke_bridge.py
python tests/smoke_web.py
python tests/smoke_runtime.py
```

Local image build: `docker build --build-arg BUILD_VERSION=0.1.0 -t stellantis-vehicles:dev stellantis_vehicles`.
CI builds aarch64 and amd64 images and pushes them to GHCR.

## Status

Working end to end (login, OTP, vehicle status, MQTT discovery), images are built by CI —
see `stellantis_vehicles/CHANGELOG.md`. Not yet tested in long-term operation on a Pi.

## License

MIT, see `LICENSE`. Upstream parts are MIT as well (Andrea De Giovine).
