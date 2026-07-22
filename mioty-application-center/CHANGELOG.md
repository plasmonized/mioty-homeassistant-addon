# Changelog

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
