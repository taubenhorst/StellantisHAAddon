# Stellantis Vehicles

## Einrichtung

1. Mosquitto-Broker-Add-on installieren und die MQTT-Integration in Home Assistant einrichten.
2. Add-on-Optionen ausfüllen: App (`mobile_app`), Ländercode, E-Mail und Passwort des Stellantis-Kontos.
3. Add-on starten und die Ingress-Seite öffnen. Der Login läuft im Add-on über ein
   headless Chromium (`oauth_mode: browser`). Alternativ `manual`: Login im eigenen
   Browser, die `mym…://…code=`-URL wird in der Ingress-Seite eingetragen.
4. Für Fernbefehle (Laden starten, Klima, Türen) folgt die OTP-Einrichtung per SMS-Code und PIN.

Die Fahrzeuge erscheinen anschließend als Geräte der MQTT-Integration (ein Gerät pro VIN).
Benötigt Home Assistant ≥ 2025.10 (MQTT-Discovery mit `default_entity_id`).

## Optionen

| Option | Bedeutung |
|---|---|
| `mobile_app` | Marken-App des Fahrzeugs |
| `country_code` | Zweistelliger Ländercode des Kontos |
| `email`, `password` | Stellantis-Zugangsdaten, nur lokal verwendet |
| `oauth_mode` | `browser` (automatisch) oder `manual` |
| `remote_commands` | Fernbefehle aktivieren (OTP nötig) |
| `mqtt.*` | Leer lassen, dann wird der Supervisor-Broker verwendet |

## Entities

Die Entities entsprechen der HACS-Integration homeassistant-stellantis-vehicles
(Sensoren, Binärsensoren, Buttons, Ladelimit, Aktualisierungsintervall, ABRP, Standort).
Entity-IDs: `<plattform>.stellantis_<vin>_<schlüssel>`, z. B. `sensor.stellantis_vr3…_battery`.

Abweichungen gegenüber der Integration:

- **Ladestartzeit** (`text.…_battery_charging_start`): HA-MQTT hat keine Zeit-Entities,
  daher ein Textfeld im Format `HH:MM`.
- **Befehlsstatus** (`sensor.…_command_status`): der letzte Status als Zustand, die letzten
  20 Einträge als Attribute.
- **Letzte Ladung**, Ladelimit, ABRP-Token usw. werden im Add-on gespeichert (siehe Datenablage),
  nicht über den HA-Zustandsspeicher.
- Kein Fahrzeugbild am Standort-Tracker.

## MQTT-Topics

Präfix `stellantis`, alle Zustände retained:

| Topic | Inhalt |
|---|---|
| `stellantis/status` | `online`/`offline` des Add-ons (Last Will) |
| `stellantis/<vin>/available` | `online`, wenn die letzte Abfrage bei Stellantis erfolgreich war |
| `stellantis/<vin>/<komponente>/<schlüssel>/state` | Zustand; `None` = unbekannt |
| `stellantis/<vin>/<komponente>/<schlüssel>/attributes` | Attribute als JSON (u. a. Zeitstempel der Daten) |
| `stellantis/<vin>/<komponente>/<schlüssel>/available` | nur bei Entities mit eigenen Regeln (Buttons, Ladelimit-Schalter …) |
| `stellantis/<vin>/<komponente>/<schlüssel>/set` | Befehl: `PRESS` (button), Zahl (number), `ON`/`OFF` (switch), Text |

Discovery: `homeassistant/<komponente>/stellantis_<vin>/<schlüssel>/config`.

## Datenablage

Tokens, OTP-Daten und Fahrzeugkonfiguration liegen unter `/data` des Add-ons und
sind Teil des Add-on-Backups.
