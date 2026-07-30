# Changelog

## 1.0.6.12 — 2026-07-30
### Behoben
- 🗑️ **Sensor löschen:** Button war bei automatisch entdeckten Sensoren ausgeblendet — jetzt haben alle Sensoren einen Löschen-Button
- 🗑️ **Sensor löschen vollständig:** Löschen entfernt den Sensor jetzt sowohl aus der Konfigurationsdatei als auch aus dem Arbeitsspeicher (vorher kehrte der Sensor sofort zurück)
- 🖱️ **Modal schließt nicht mehr versehentlich:** Eingabemasken (Sensor hinzufügen/bearbeiten) schließen sich nicht mehr bei einem Klick neben das Formular — nur noch über ❌ oder Abbrechen (gilt für Dashboard und Sensoren-Seite)
- 🔧 **Blueprint-Decoder komplett neu implementiert:** Die bisherige Implementierung hatte ein falsches Schema und konnte keine echten Blueprint-Dateien lesen. Der Decoder versteht jetzt das offizielle mioty Blueprint-Format korrekt:
  - `size` wird in **Bit** gelesen (nicht Bytes) — ermöglicht 4-Bit-Nibble-Felder wie im Aion-Header
  - `func`-Formeln werden ausgewertet (`$ - 128`, `$ / 100`, etc.)
  - `hidden`-Felder werden intern geführt, aber nicht ausgegeben
  - `virtual`-Felder mit `condition` und `$feldname`-Referenzen (z. B. Alarm- und Status-Bits) werden berechnet
  - `type: int` (vorzeichenbehaftet) wird korrekt sign-extended
  - Little-Endian- und Big-Endian-Byte-Reihenfolge je Feld

## 1.0.6.10 — 2026-07-30
### Behoben
- 🖱️ **Modal-Fix Dashboard:** Sensor-Eingabemaske auf der Startseite schließt sich nicht mehr bei versehentlichem Klick außerhalb

## 1.0.6.9 — 2026-07-30
### Behoben
- 🔐 **SCACI TLS mit IP-Adresse:** Verbindung zu Service Center per IP-Adresse (z. B. `192.168.x.x`) schlug mit `UNEXPECTED_EOF_WHILE_READING` fehl — Ursache war SNI (Server Name Indication), das laut RFC 6066 keine IP-Adressen akzeptiert. SNI wird jetzt bei IP-Adressen automatisch deaktiviert
- 🔐 **TLS 1.2 Minimum:** TLS 1.2 als Mindestversion gesetzt für bessere Kompatibilität mit Embedded-Geräten

## 1.0.6.8 — 2026-07-26
### Neu
- 📊 **Service Center Status auf Dashboard:** Neue Statuskachel zeigt „Service Center: ✅ Verbunden" (SCACI oder MQTT) statt „MQTT Status ⚠️"
- 📡 **Status-Banner auf Startseite:** Kompakter Banner ganz oben zeigt immer den aktuellen Verbindungsstatus inkl. Verbindungsart (SCACI/MQTT) — aktualisiert sich alle 10 Sekunden
- 🔧 **Einheitlicher `service_center_connected`-Status:** API `/api/status` liefert jetzt ein einheitliches Feld, das SCACI und MQTT zusammenfasst

## 1.0.6.7 — 2026-07-26
### Behoben
- 📊 **Base Station CPU/Memory:** SCACI liefert `cpu`/`memory` als Prozentwert (0–100), die GUI erwartete eine Fraktion (0–1) — Werte werden jetzt korrekt umgerechnet und angezeigt

## 1.0.6.6 — 2026-07-25
### Behoben
- 🐛 **SCACI EUI als Hex-String:** Service Center sendet Base-Station-EUIs als Hex-String (z. B. `'502DF4000056A0BE'`), nicht als Integer wie in der Spec angegeben — Konvertierung behandelt jetzt beide Formate
- 🔍 **Besseres Fehler-Logging:** SCACI Status-Abfrage-Fehler zeigen jetzt den vollständigen Python-Traceback für einfachere Diagnose

## 1.0.6.5 — 2026-07-25
### Neu
- ✨ **SCACI Direktverbindung:** Direkte TLS-Verbindung zum mioty Service Center (SCACI v1.0.0) als Alternative zu MQTT — Konfiguration unter Einstellungen → „🔐 SCACI Direktverbindung"
- ✨ **AC-EUI Generator:** Application-Center-EUI aus frei wählbarem Namen erzeugen (16 Hex-Zeichen mit „AC"-Präfix)
- ✨ **Zertifikats-Upload:** ZIP mit CA, Client-Zertifikat und Schlüssel direkt in den Einstellungen hochladen
### Behoben
- 🐛 **SCACI Protokoll-Feldnamen:** `basestations` (lowercase), `rc`, `uptimeS`, `online`/`attached` laut Spezifikation korrigiert
- 🐛 **SNR/RSSI Parsing:** Uplink-Parser liest Felder jetzt aus oberster Ebene und `rxInfo`

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
