# Changelog

## 1.0.6.7

- ✨ **SCACI Direktverbindung:** Das Add-on kann sich jetzt zusätzlich zu MQTT direkt per TLS mit dem mioty Service Center verbinden (offizieller SCACI-Standard v1.0.0). Konfiguration unter Einstellungen → „🔐 SCACI Direktverbindung": Host, Port (Standard 16017), AC-EUI und optionale TLS-Testoption
- ✨ **AC-EUI Generator:** Auf Wunsch wird eine Application-Center-EUI aus einem frei wählbaren Namen erzeugt (16 Hex-Zeichen mit „AC"-Präfix)
- ✨ **Zertifikats-Upload:** ZIP-Datei aus dem Service-Center-Generator (ca_cert.pem, Client-Zertifikat, privater Schlüssel) kann direkt in den Einstellungen hochgeladen werden — Ablage unter certs/ac_&lt;eui&gt;/
- 🐛 **SCACI Protokoll-Korrekturen (Feldnamen laut Spezifikation):**
  - `statusRsp`: Basisstationen stehen in `basestations` (komplett lowercase), nicht `baseStations` → Basisstationen werden jetzt korrekt empfangen und angezeigt
  - `statusRsp`: Felder heißen `rc` (nicht `code`), `uptimeS` (nicht `uptime`), `timeNs` (nicht `time`)
  - `epStat`: Status-Felder heißen `online` und `attached` (bool), nicht `epStatus` → Online-/Offline-Status der Sensoren wird jetzt korrekt ausgewertet
  - Fehler-Nachrichten: Feld heißt `rc` (nicht `code`) — Fehlermeldungen werden nun korrekt interpretiert
- 🐛 **SNR/RSSI aus realem SC-Payload:** Der Uplink-Parser liest SNR, RSSI, Base-Station-EUI und Empfangszeit jetzt sowohl von der obersten Nachrichtenebene als auch aus `rxInfo`; Paketzähler als `cnt` oder `packetCnt`, Nutzdaten als `userData` oder `data`
- ✨ **Voller SCACI-Funktionsumfang:** Uplink-Empfang (fließt in die normale Sensor-Pipeline inkl. Decoder & Home Assistant Discovery), End-Point-Status, Base-Station-Status-Abfrage (alle 60 s), Registrierung/Deregistrierung, Downlink-Queue, Ping/Keepalive, automatischer Reconnect mit Session-Fortsetzung

## 1.0.5.8

- ✨ **Neu anlernen:** Neue Buttons auf der Sensoren-Seite — jeder Sensor kann einzeln über „🔄 Neu anlernen" erneut am Service Center registriert werden, oder alle auf einmal über „🔄 Alle neu anlernen". Nutzt gespeicherten Network Key & Short Address; Ergebnis pro Sensor mit Broker-Bestätigung
- ✨ **IO-Link Adapter:** Beim Registrieren eines Adapters kann der Sensor jetzt bequem aus einem Dropdown (EUI + Gerätename) ausgewählt werden statt die EUI abzutippen — manuelle Eingabe bleibt als Option verfügbar
- ✨ **Decoder zuweisen:** Auch bei der Decoder-Zuweisung wird der Sensor jetzt aus einem Dropdown (EUI + Gerätename) ausgewählt statt die EUI einzutippen — manuelle Eingabe bleibt als Option verfügbar
- 🐛 **Bugfix:** „Decoder hinzufügen"-Link im Dashboard führte unter Home Assistant Ingress auf eine 404-Seite — Link nutzt jetzt die korrekte Ingress-Navigation
- ✨ **Neuer Adaptertyp ifm EIO240:** Beim Registrieren eines IO-Link Adapters kann jetzt der Gerätetyp gewählt werden (Sentinum AION oder ifm EIO240). Die Payload-Auswertung erfolgt automatisch passend zum Typ — EIO240-Format: 1 Byte Header (ProtlV/MessT), 2 Byte VendorID, 3 Byte DeviceID, danach Prozessdaten. Bestehende Adapter laufen unverändert als Sentinum AION weiter
- 🐛 **Versionsanzeige:** Veraltete Versionsnummer (v1.0.5.7.2) aus dem Header der Sensorverwaltung und dem Seitentitel des Dashboards entfernt. Die aktuelle Version steht jetzt unter Einstellungen im neuen Bereich „ℹ️ Über"
- ✨ **Duty Cycle Anzeige:** Base-Station-Übersicht im Dashboard zeigt jetzt den Duty Cycle als 0–100 % Balkenanzeige (grün < 50 %, gelb < 80 %, rot ≥ 80 %) mit Prozentwert

## 1.0.5.7.10

- 🐛 **Bugfix:** Sensor-Registrierung konnte „Erfolg" melden, obwohl die MQTT-Nachricht das Service Center nie erreichte — Registrierungen werden jetzt mit QoS 1 gesendet und auf Broker-Bestätigung (PUBACK) gewartet. Ohne Bestätigung wird ein Fehler angezeigt
- 📋 **Logging:** Jeder Registrierungs-Publish protokolliert jetzt Broker, Port und Topic, damit Zustellprobleme sofort sichtbar sind

## 1.0.5.7.9

- 🐛 **Bugfix:** Sensor-Registrierung schlug fehl mit `'NoneType' object has no attribute 'strip'`, wenn optionale Felder (Application Key, Hersteller, Modell, Gerätename) leer gelassen wurden — alle optionalen Felder sind jetzt null-sicher

## 1.0.5.7.8

- 🐛 **Bugfix:** Home Assistant Fehler `Value error while updating state of sensor...uptime` behoben — die Uptime-Entität liefert jetzt numerische Sekunden (device_class `duration`) statt Text wie „17h 18m"
- ✨ **BSSCI v1.1.0 Unterstützung:** Neue optionale Status-Felder werden automatisch als Entitäten angelegt, wenn die Base Station sie liefert: Temperatur (°C), Rauschleistungsdichte (dBm/Hz), Standort
- 🛡️ **Robustheit:** Optionale Status-Felder (memLoad, cpuLoad, dutyCycle, uptime) dürfen fehlen oder null sein — kompatibel mit BSSCI v1.0 und v1.1

## 1.0.5.7.7

- 🐛 **Bugfix:** Docker-Build-Fehler `base name ($BUILD_FROM) should not be blank` behoben — Supervisor 2026.04+ übergibt `BUILD_FROM` nicht mehr, das Base-Image wird jetzt direkt im Dockerfile referenziert (`ghcr.io/home-assistant/${BUILD_ARCH}-base:3.19`)
- ✅ Alle 5 Architekturen (amd64, aarch64, armv7, armhf, i386) weiterhin unterstützt

## 1.0.5.7.6

- 🔧 Build-Konfiguration: `build_from` nach `config.yaml` verschoben (Zwischenschritt)

## 1.0.5.7.5

- 🐛 **Bugfix:** Neue Sensoren werden jetzt korrekt ans Service Center gepusht (MQTT `register`-Topic) statt nur lokal gespeichert
- 🐛 **Bugfix:** LoRa/OMS Protokoll-Filter funktioniert korrekt — Sensortyp wird aus dem MQTT-Payload übernommen
- 🔄 **MQTT Auto-Reconnect** mit exponentiellem Backoff (5s bis 300s)
- 🗑️ Deprecated `build.yaml` entfernt

## 1.0.5.7.4

- ✨ Multi-Protokoll-Unterstützung: mioty, LoRa und OMS Sensoren mit Protokoll-Filter in der Sensor-Übersicht
- ✨ IO-Link Adapter Verwaltung mit IODD-Zuweisung pro Adapter
- ✨ Neue Decoder-Seite mit 3 Bereichen: Decoder, IO-Link Adapter, IODD-Verwaltung
- ✨ Integrierter IoddProcessParser für automatische IODD-Interpretation
