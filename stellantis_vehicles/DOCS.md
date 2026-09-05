# Stellantis Vehicles

## Einrichtung

1. Mosquitto-Broker-Add-on installieren und die MQTT-Integration in Home Assistant einrichten.
2. Add-on-Optionen ausfüllen: App (`mobile_app`), Ländercode, E-Mail und Passwort des Stellantis-Kontos.
3. Add-on starten und die Ingress-Seite öffnen. Der Login läuft im Add-on über ein
   headless Chromium (`oauth_mode: browser`). Alternativ `manual`: Login im eigenen
   Browser, die `mym…://…code=`-URL wird in der Ingress-Seite eingetragen.
4. Für Fernbefehle (Laden starten, Klima, Türen) folgt die OTP-Einrichtung per SMS-Code und PIN.

Die Fahrzeuge erscheinen anschließend als Geräte der MQTT-Integration.

## Optionen

| Option | Bedeutung |
|---|---|
| `mobile_app` | Marken-App des Fahrzeugs |
| `country_code` | Zweistelliger Ländercode des Kontos |
| `email`, `password` | Stellantis-Zugangsdaten, nur lokal verwendet |
| `oauth_mode` | `browser` (automatisch) oder `manual` |
| `remote_commands` | Fernbefehle aktivieren (OTP nötig) |
| `mqtt.*` | Leer lassen, dann wird der Supervisor-Broker verwendet |

## Datenablage

Tokens, OTP-Daten und Fahrzeugkonfiguration liegen unter `/data` des Add-ons und
sind Teil des Add-on-Backups.
