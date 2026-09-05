# Stellantis Vehicles

## Setup

1. Install the Mosquitto broker add-on and set up the MQTT integration in Home Assistant.
2. Fill in the add-on options: app (`mobile_app`), country code, e-mail and password of the
   Stellantis account.
3. Start the add-on and open the ingress page (sidebar entry "Stellantis"). The login runs
   inside the add-on in a headless Chromium (`oauth_mode: browser`); e-mail and password from
   the options are pre-filled. Alternative `manual`: open the login page via the link, sign in
   with your own browser, look for the failed `mym…://oauth2redirect/…?code=…` request in the
   network tab of the browser DevTools and paste the URL (or just the code) on the ingress page.
4. With `remote_commands: true` the OTP step follows immediately: Stellantis sends an SMS code,
   which is entered together with the PIN code of the vehicle app. "Resend SMS" and
   "Continue without remote commands" are available as a way out.
5. The status page shows account, token expiry, vehicles and notifications; from there remote
   commands can be reconfigured or disabled and a new login can be started.

The vehicles then appear as devices of the MQTT integration (one device per VIN).
Requires Home Assistant 2025.10 or newer (MQTT discovery with `default_entity_id`).

## Options

| Option | Meaning |
|---|---|
| `mobile_app` | Brand app of the vehicle (MyPeugeot, MyCitroen, MyDS, MyOpel, MyVauxhall) |
| `country_code` | Two-letter country code of the account |
| `email`, `password` | Stellantis credentials, used locally only |
| `oauth_mode` | `browser` (automatic) or `manual` |
| `remote_commands` | Enable remote commands (requires OTP) |
| `language` | Language of the entity names and the ingress page |
| `mqtt.*` | Leave empty to use the broker provided by the Supervisor |

## Entities

The entities match the HACS integration homeassistant-stellantis-vehicles (sensors, binary
sensors, buttons, charge limit, refresh interval, ABRP, location).
Entity IDs: `<platform>.stellantis_<vin>_<key>`, e.g. `sensor.stellantis_vr3…_battery`.

Differences to the integration:

- **Charge start time** (`text.…_battery_charging_start`): HA MQTT has no time entities,
  so this is a text field in `HH:MM` format.
- **Command status** (`sensor.…_command_status`): the latest status as state, the last
  20 entries as attributes.
- **Last charge**, charge limit, ABRP token etc. are stored inside the add-on (see Data),
  not via the HA state restore.

## MQTT topics

Prefix `stellantis`, all states retained:

| Topic | Content |
|---|---|
| `stellantis/status` | `online`/`offline` of the add-on (last will) |
| `stellantis/<vin>/available` | `online` when the last Stellantis poll succeeded |
| `stellantis/<vin>/<component>/<key>/state` | state; `None` = unknown |
| `stellantis/<vin>/<component>/<key>/attributes` | attributes as JSON (including the data timestamp) |
| `stellantis/<vin>/<component>/<key>/available` | only for entities with their own rules (buttons, charge limit switch, …) |
| `stellantis/<vin>/<component>/<key>/set` | command: `PRESS` (button), number (number), `ON`/`OFF` (switch), text |

Discovery: `homeassistant/<component>/stellantis_<vin>/<key>/config`.

## Data

Tokens, OTP data and vehicle configuration live under `/data` of the add-on and are part of
the add-on backup.
