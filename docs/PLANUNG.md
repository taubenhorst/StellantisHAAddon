# Planungsprotokoll (Übergabe aus dem Chat, 05.09.2026)

## Ausgangslage
- HA OS auf Raspberry Pi 4 (aarch64), später evtl. Proxmox (amd64)
- Fahrzeuge: Peugeot e-Rifter, Citroën ë-C3 in Überlegung
- Ursprüngliche Idee: Add-on-Repo mit psa_car_controller + Worker → verworfen,
  psacc ist seit 2024 unmaintained

## Analyse der Upstream-Repos
### homeassistant-stellantis-vehicles (Commit 69fddda, v2026.9.1, MIT)
- `stellantis.py` (~1000 Zeilen): OAuth, OTP-Login, Token-Refresh, HTTP-Client,
  Stellantis-MQTT-Broker für Remote-Kommandos inkl. MSS-Workaround (TCP-Payload > 1456 B)
- HA-Kopplung nur über: `HomeAssistant`/`HassJob`, `translation`, `ConfigEntryAuthFailed`,
  `persistent_notification`, `async_track_point_in_time`, `util.ssl.client_context`,
  `util.dt`, Enums/Units in `const.py`, `config_entries` (Speichern der Entry-Daten)
- `base.py` (Coordinator + Entity-Basisklassen) und alle Plattformdateien sind HA-spezifisch
  → werden durch MQTT-Discovery-Bridge ersetzt
- `config_flow.py` → durch Ingress-UI ersetzt
- OTP-Code (`otp/`) ist reines Python (pycryptodome)

### homeassistant-stellantis-vehicles-worker-v2 (KEINE Lizenz)
- FastAPI + Playwright/Chromium, ~80 Zeilen Fachlogik
- Macht den Gigya-Login (E-Mail/Passwort) auf der OAuth-Seite und fängt den `code`
  aus dem `mym*://`-Redirect ab (taucht als `requestfailed` auf)
- Wird von der Integration nur in `get_oauth_code()` aufgerufen — beim Setup und
  wenn der Refresh-Token stirbt. Default zeigt auf die Render-Instanz des Autors,
  d. h. Zugangsdaten gehen an einen fremden Server → Hauptmotivation für das Add-on
- Ohne Lizenz = alle Rechte vorbehalten → Clean-Room-Neuimplementierung in
  `app/oauth_browser/`. Selektoren (`#gigya-login-form input[name=username]` usw.)
  und Ablauf sind Fakten über die Stellantis-Seite, kein Copy-Paste.
- Optional: Issue beim Autor, ob er eine Lizenz nachreicht

## Entscheidungen
1. Ein einziges Add-on, ein Container, ein Python-Prozess (asyncio)
2. Upstream-Code unverändert vendoren + `hass_shim/` statt Port → Upstream-Fixes
   durch Kopieren übernehmbar
3. Entities per MQTT Discovery (HA-Integration "MQTT" legt Gerät/Entities an);
   Broker-Zugang via `services: [mqtt:want]` aus dem Mosquitto-Add-on
4. Chromium nur on demand pro Login starten (RAM auf dem Pi), nicht dauerhaft
5. Debian-Base statt Alpine (Playwright braucht glibc); Image ~600 MB;
   prebuilt Images per GitHub Actions → GHCR sind Pflicht, Build auf dem Pi ausgeschlossen
6. Manueller OAuth-Fallback (URL aus eigenem Browser einfügen) bleibt in der Ingress-UI,
   damit Selektor-/Captcha-Änderungen nicht aussperren
7. Lizenz des eigenen Repos: MIT
8. Lovelace-Card aus dem Upstream vorerst weglassen

## Aufwandsschätzung
Discovery-Mapping 1 Tag, Ingress-UI mit Login/OTP 1 Tag, Wiring + Packaging/CI 0,5–1 Tag

## Risiken
- Abkopplung vom Upstream: API-Änderungen von Stellantis müssen selbst nachgezogen werden
- Gigya-Login-Seite kann Selektoren ändern oder Captcha einführen
- CI mit `home-assistant/builder` und Debian-Base ist ungetestet

## Verifiziert (Smoke-Test im Chat)
- Upstream-Client instanziierbar über den Shim, `set_entry()` vor jedem Zugriff auf Stored Config nötig
- OAuth-URL-Aufbau, Übersetzungen aus JSON, Config-Persistenz nach `/data/config_entry.json`
- Code-Parsing aus `mym://…?code=`, aiohttp-Ingress-Server startet
- `hass_notify()` bricht ab, solange Stored Config `notifications` nicht `true` ist (Upstream-Verhalten)
