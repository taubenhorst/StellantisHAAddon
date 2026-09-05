# Projektkontext für Claude Code

Home-Assistant-Add-on (ein einziges), das die HACS-Integration
homeassistant-stellantis-vehicles und deren Playwright-OAuth-Worker in einem
Container zusammenfasst. Fahrzeuge kommen per MQTT Discovery nach HA.

## Regeln
- `stellantis_vehicles/app/stellantis_vehicles/` ist unveränderter Upstream-Code
  (siehe UPSTREAM.md dort). Nicht editieren — fehlende HA-Symbole in
  `app/hass_shim/` nachrüsten. Ausnahme: `base.py` ist eigen.
- Kein Code aus `homeassistant-stellantis-vehicles-worker-v2` übernehmen (keine Lizenz);
  `app/oauth_browser/` ist Clean-Room und bleibt es.
- Inline-Kommentare im Code auf Englisch, Doku auf Deutsch.
- Base-Image Debian (Playwright braucht glibc), Images werden per CI vorgebaut.

## Weitere Doku
- `docs/PLANUNG.md`: vollständiges Planungsprotokoll mit Analyse, Entscheidungen, Risiken
- `stellantis_vehicles/DOCS.md`: Nutzerdoku inkl. MQTT-Topic-Schema

## Aufbau der Bridge (Schritt 1, fertig)
- `app/stellantis_vehicles/base.py`: Port des Upstream-Coordinators (Polling, updatedAt-Vergleich,
  Leerantworten, Command-History, send_*-Kommandos, Ladelimit, ABRP, letzte Fahrt). Kein HA.
  `_sensors` ist der gemeinsame Zustand mit der Bridge — gleiche Ein-Zyklus-Verzögerung wie Upstream.
- `app/bridge/entities.py`: Ersatz für die Upstream-Plattformdateien. Jede Entity kennt Discovery-
  Felder, `update()` (Wert aus `coordinator.data`, schreibt `_sensors`) und `handle_command()`.
  Reihenfolge = Upstream-PLATFORMS (binary_sensor vor sensor!), sonst hinkt `last_charge` nach.
- `app/bridge/mqtt_bridge.py`: paho-Client, Discovery pro Entity, State/Attribute/Availability,
  Command-Dispatch (seriell). paho-Callbacks laufen im Netzwerk-Thread → `run_coroutine_threadsafe`.
- Abweichungen zu Upstream, durch MQTT erzwungen: keine `time`-Plattform → `battery_charging_start`
  ist ein `text` mit `HH:MM`; number/switch/text/last_charge persistieren in der Stored Config
  (`/data/config_entry.json`, Knoten `vehicles.<vin>`); Topics/unique_ids enthalten die Komponente,
  weil `battery_charging_limit` als number *und* switch existiert. `default_entity_id` braucht HA ≥ 2025.10.
- Offline-Test: `cd stellantis_vehicles && ../.venv/Scripts/python tests/smoke_bridge.py`
  (Fake-Client + Recorder statt paho, 52 Checks). Vor jeder Änderung an Bridge/Coordinator laufen lassen.

## Ingress-UI (Schritt 2, fertig)
- `app/web/setup.py`: `SetupFlow` = Ersatz für die Upstream-`config_flow.py`, ohne HTML. Schritte
  `login` → `otp` → `done`, abgeleitet aus der Stored Config (`_derive_step`). Lange Aktionen
  (Chromium-Login, Token-Requests) laufen als Task, die Seite pollt (`meta refresh`, solange `busy`).
  Speichert exakt die Upstream-Entry-Felder (`oauth`, `mqtt`, `customer_id`, `remote_commands`,
  `notifications`, `anonymize_logs`, `mobile_app`, `country_code`) über `_store()` = `save_config` +
  `update_stored_config`. Fehlertexte aus `translations/<lang>.json` (`config.error.*`).
- `app/web/server.py`: eine Seite `/`, rendert je nach Schritt; POST-Endpunkte `login`, `otp`, `sms`,
  `remote/disable`, `remote/reconfigure`, `reauth`, `notifications/dismiss`; `GET /api/state`, `/health`.
  Nur relative URLs (Ingress-Proxy). `state["vehicles"]` erwartet Dicts `{vin, type, ok, updated_at}`.
- Stolpersteine: `hass_notify()` schweigt ohne `notifications: true` in der Stored Config → Flow persistiert
  die Defaults im Konstruktor; `get_otp_code()` macht `os.mkdir` auf `<config>/.storage/<domain>` →
  `.storage` wird vor dem OTP-Schritt angelegt; `reconfigure` setzt `remote_commands=False`, daher `_force_otp`.
- Offline-Test: `tests/smoke_web.py` (aiohttp-TestClient, Fake-Client, 44 Checks).

## Runtime (Schritt 3, fertig)
- `app/runtime.py`: `Runtime.start()` = Rest von Upstream-`async_setup_entry`: `scheduled_tokens_refresh` →
  `get_user_vehicles` → `prune_stored_vehicle_configs` → Coordinator je Fahrzeug → `bridge.attach` →
  `stagger_first_poll` → `coordinator.start()`. Idempotent; API-Fehler → Retry nach 60 s; Auth-Fehler
  (`coordinator.on_auth_failed`) → `flow.reauth()` + Notification, nach Neu-Login startet `on_configured`
  die gestoppten Coordinators wieder (`coordinator.start()` startet beendete Loops neu).
- `app/main.py`: MQTT-Zugang aus `options.mqtt` oder `STELLANTIS_MQTT_*` (Supervisor-Service via `run`);
  ohne Broker läuft alles, nur ohne Publishing. `ADDON_VERSION` kommt aus `BUILD_VERSION` (Dockerfile).
- Offline-Test: `tests/smoke_runtime.py`.

## Erkenntnisse aus dem echten Login (05.09.2026)
- Die Playwright-Headless-Shell wird vom Stellantis-IdP erkannt: Gigya-Login klappt, aber der
  ForgeRock-Schritt `POST /am/json/authenticate` endet nach 30 s auf `#failedLogin`. Mit echtem
  Chromium im neuen Headless-Modus (`channel="chromium"`, kein gefälschter UA) kommt der Code.
- `browser.close()` hängt unter Windows/Python 3.14 grundsätzlich → alle Teardown-Schritte sind auf
  10 s begrenzt, `pw.stop()` räumt auf. Im Linux-Container nicht beobachtet.
- Diagnose ohne Add-on: `python app/oauth_browser/login.py --email …` (fragt Passwort ab, listet URLs).

## Docker (Schritt 4, lokal verifiziert 05.09.2026)
- Lokaler Build (Docker Desktop, amd64): `docker build --build-arg BUILD_VERSION=0.1.0 -t stellantis-vehicles:dev stellantis_vehicles`
  (`BUILD_FROM` hat einen amd64-Default; der HA-Builder überschreibt ihn). Build ~2 min, Image **1,92 GB**
  (volles Chromium + Headless-Shell + X11/GTK-Libs; die 600 MB aus der Planung waren zu optimistisch).
- Im Container: `channel="chromium"` startet (151.0.7922.34), s6-Start liefert nach ~7 s `/health`.
  Ohne Supervisor meckert bashio im `run`-Skript („Could not resolve host: supervisor") — harmlos.
- Test-Setup: temporäres `/data` mit `options.json` mounten, `docker run -d -p 8099:8099 -v <dir>:/data …`;
  Chromium-Check per `docker run --rm --entrypoint python3 … /data/chromium_check.py`.
- `.dockerignore` hält `data/` (Tokens, OTP-Pickle) und `tests/` aus dem Build-Kontext.

## Stand
Schritte 1–4 umgesetzt: offline getestet, echter Login + Statusabruf des e-Rifters verifiziert,
Image lokal gebaut und gestartet. Offen: CI-Build/GHCR und Installation auf dem Pi.

## Nächste Schritte
5. GitHub-Repo `taubenhorst/StellantisHAAddon` anlegen, pushen, Workflow-Lauf prüfen; GHCR-Pakete auf
   „public" stellen, sonst kann der Supervisor nicht pullen. aarch64-Build nur in der CI möglich.
6. Auf dem Pi installieren; dort die HACS-Integration `stellantis_vehicles` deaktivieren (doppeltes Polling,
   OTP-Gerätelimit). Erster Lauf mit Supervisor-MQTT prüfen (`services: mqtt:want`).
7. Optional Image verkleinern (`playwright install chromium --no-shell` spart ~150 MB, dann greift der
   Fallback in `_launch` nicht mehr).

## Lokal starten
    cd stellantis_vehicles && pip install -r requirements.txt
    DATA_DIR=./data python app/main.py
