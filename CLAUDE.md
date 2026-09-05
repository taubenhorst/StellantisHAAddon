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

## Stand
Schritt 1 (Discovery-Mapping) umgesetzt und offline getestet. Docker-Build und CI ungetestet.
Bekannte Lücke: `entity_picture` des Fahrzeugs wird nicht gesetzt (HA verlangt absolute URL).

## Nächste Schritte
2. `app/web/server.py`: Login-Flow (browser/manual), SMS-Code + PIN für OTP,
   Statusseite mit `hass.notifications`.
3. `app/main.py`: Wiring — Stored Config aus `hass.config_entries.entry.data` in `stellantis.save_config`,
   `get_user_vehicles` → `async_get_coordinator` → `bridge.attach` → `coordinator.start()`,
   `scheduled_tokens_refresh`, `connect_mqtt`; `coordinator.on_auth_failed` an die UI hängen;
   MQTT-Zugang aus `STELLANTIS_MQTT_*` (setzt `rootfs/.../run`) lesen, nicht nur aus `options.mqtt`.
4. Docker-Build lokal, dann CI.

## Lokal starten
    cd stellantis_vehicles && pip install -r requirements.txt
    DATA_DIR=./data python app/main.py
