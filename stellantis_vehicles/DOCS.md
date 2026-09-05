# Stellantis Vehicles

## Einrichtung

1. Mosquitto-Broker-Add-on installieren und die MQTT-Integration in Home Assistant einrichten.
2. Add-on-Optionen ausfüllen: App (`mobile_app`), Ländercode, E-Mail und Passwort des Stellantis-Kontos.
3. Add-on starten und die Ingress-Seite (Seitenleiste „Stellantis") öffnen. Der Login läuft im
   Add-on über ein headless Chromium (`oauth_mode: browser`); E-Mail/Passwort aus den Optionen
   sind vorausgefüllt. Alternativ `manual`: Anmeldeseite über den Link öffnen, im Netzwerk-Tab
   der Browser-DevTools die fehlgeschlagene `mym…://oauth2redirect/…?code=…`-Anfrage suchen und
   die URL (oder nur den Code) auf der Ingress-Seite einfügen.
4. Bei `remote_commands: true` folgt direkt die OTP-Einrichtung: Stellantis schickt einen SMS-Code,
   dazu kommt der PIN-Code aus der Fahrzeug-App. „SMS erneut anfordern" und „Ohne Fernbefehle
   fortfahren" stehen als Ausweg bereit.
5. Die Statusseite zeigt Konto, Token-Laufzeiten, Fahrzeuge und Benachrichtigungen; dort lassen
   sich Fernbefehle neu einrichten oder abschalten und eine Neu-Anmeldung starten.

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
| `language` | Sprache der Entity-Namen und der Ingress-Seite |

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
