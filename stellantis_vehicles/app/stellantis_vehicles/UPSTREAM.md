# Upstream-Herkunft

Dieses Paket ist ein unveränderter Vendor-Import aus
https://github.com/andreadegiovine/homeassistant-stellantis-vehicles
(MIT-Lizenz, siehe `LICENSE.upstream`).

- Commit: da32364fbf6836b7de65d8cbb2f89806eea06790 (`develop`, 25.09.2026; nach 2026.9.5-beta.1)
- Version: 2026.9.5-beta.1 (laut `manifest.json`)
- Vorher: 69fddda (2026.9.1)
- Übernommen: `stellantis.py`, `const.py`, `utils.py`, `exceptions.py`, `configs.json`, `manifest.json`, `otp/`, `translations/*.json` (alle 15 Sprachen)
- **Nicht** übernommen: `base.py`, `config_flow.py`, alle Plattform-Dateien (`sensor.py`, `button.py`, …), `frontend/`
- **Eigene Datei**: `base.py` — Ersatz für den HA-Coordinator, leitet an `bridge/` weiter

Beim Update auf da32364 im Shim nachgerüstet: `config_entries.ConfigEntry`,
`helpers.aiohttp_client.async_get_clientsession`, `ConfigEntry.async_start_reauth`
(→ Runtime „Login erforderlich“), `UnitOfTime.DAYS`, `SensorDeviceClass.DURATION`;
`async_update_entry` speichert jetzt selbst (Upstream ruft `_async_schedule_save` nicht mehr).

Regel: Dateien aus der Liste "Übernommen" nicht editieren. Alles, was HA erwartet,
liefert `hass_shim/`. Upstream-Update = Dateien neu kopieren, Commit-Hash hier nachziehen.
