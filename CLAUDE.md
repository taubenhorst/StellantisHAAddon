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

## Stand
Skelett, siehe `stellantis_vehicles/CHANGELOG.md`. Import-Smoke-Test des Upstream-Clients
über den Shim läuft; Docker-Build und CI noch ungetestet.

## Nächste Schritte
1. `app/bridge/mqtt_bridge.py`: Discovery-Mapping aus den Upstream-Plattformdateien
   (sensor.py, binary_sensor.py, button.py, number.py, switch.py, text.py, time.py,
   device_tracker.py im Upstream-Repo) — Entity-Beschreibungen → Discovery-Payloads,
   Status → State-Topics, Command-Topics → `StellantisVehicles`-Aufrufe.
2. `app/web/server.py`: Login-Flow (browser/manual), SMS-Code + PIN für OTP,
   Statusseite mit `hass.notifications`.
3. `app/main.py`: Wiring gemäß TODO-Kommentar (get_user_vehicles → Coordinators →
   scheduled_tokens_refresh → connect_mqtt).
4. Docker-Build lokal, dann CI.

## Lokal starten
    cd stellantis_vehicles && pip install -r requirements.txt
    DATA_DIR=./data python app/main.py
