# Sentinum Cloud / Datahub: Mobilfunk-Sensoren

## Einrichtung

Unter **Einstellungen → Sentinum Cloud**:

1. Die Verbindung aktivieren.
2. Die von Sentinum bereitgestellten MQTT-Zugangsdaten eintragen. Broker
   `broker.sentinum.de` und TLS-Port `8883` sind fest vorgegeben und nicht
   bearbeitbar. Die Zugangsdaten sind unabhängig vom my.sentinum.de-Login.
3. Das Topic leer lassen, wenn der MQTT-Benutzername dem Kunden-Topic entspricht.
   Dann wird `datahub/<username>/+/+/+/up` abonniert.
4. Falls erforderlich, das konkrete Kunden-Topic eintragen, etwa
   `datahub/meine_firma/+/+/+/up`. Für den Legacy-Mirror:
   `devices/meine_firma/+/+/+/up`.
   Auch Kunden-Präfixe wie `devices/meine_firma/#` oder `datahub/meine_firma`
   sind möglich. Sie werden automatisch auf die zugehörigen `/up`-Sensordaten
   eingegrenzt; der tatsächlich gespeicherte Filter erscheint nach dem Speichern.
5. Speichern. Die Verbindung wird ohne Add-on-Neustart aufgebaut.

TLS mit Prüfung des Serverzertifikats ist immer aktiv. Nach erfolgreicher
Broker-Anmeldung und bestätigtem Abonnement erscheint „Verbunden“.
Eine Ablehnung der Anmeldung oder des Topics wird im Status angezeigt.
Nur Telemetrie wird gelesen; es werden keine Downlinks oder Konfigurationsänderungen
an Sensoren gesendet.

Zum Abschalten den Aktivierungsschalter ausschalten und speichern. Der Client wird
getrennt und sein Hintergrunddienst beendet. Gespeicherte Zugangsdaten und bereits
empfangene Daten bleiben erhalten. Das Passwort kann bei deaktiviertem Dienst
über „Gespeichertes Passwort löschen“ entfernt werden.

## Sensordaten und Decoder

Topic-Schema: `datahub/<Kunde>/<Serie>/<Untertyp>/<Serie>_cellular_<IMEI>/up`
(alternativ `devices/…`). LoRa-/mioty-Geräte desselben Kontos werden ignoriert.
Die IMEI einschließlich führender Nullen dient als stabile Sensor-ID.

Eos, Febris, Aion, Apollon, Hyperion und Juno nutzen die bereits eingebauten
Blueprints. Eine vorhandene manuelle Decoder-Zuweisung hat Vorrang.
Weitere Decoder lassen sich wie bisher über die Decoder-Seite zuweisen.

Die JSON-Nachricht kann Rohdaten als Hex-String (`payload`, `payload_hex`,
`payloadHex`, `rawPayload`, `data`) oder Bytearray (`payload`, `data`) liefern.
Base64 erfordert `encoding: "base64"` beziehungsweise `payloadEncoding: "base64"`;
`frm_payload` wird als Base64 behandelt.
`payload: {"raw": "...", "encoding": "hex"}` wird ebenfalls unterstützt.
Optional: `deviceId`, `timestamp` (ISO 8601 oder Unix-Zeit in s/ms/µs/ns),
`metadata`, `rssi`, `snr`.

Bereits dekodierte flache Messwerte können unter `measurements`, `decoded`
oder `data` stehen: `{"temperature": {"value": 22.5, "unit": "°C"}}`
oder `{"temperature": 22.5}`. Unbekannte/fehlerhafte Formate werden nicht als
erfolgreicher Empfang gezählt und verursachen eine sichtbare Fehlermeldung.
Für abweichende Kontenformate ist ein anonymisiertes Beispiel einer vollständigen
MQTT-Nachricht einschließlich Topic erforderlich.

Die Werte erscheinen in der bestehenden Sensorübersicht und den Live-Daten.
Home Assistant erhält sie über die bereits konfigurierte HA-MQTT-Verbindung.
Ohne diese Verbindung funktioniert die lokale Anzeige weiterhin.

Passwörter werden nicht an den Browser zurückgeliefert und nicht protokolliert.
Wie bestehende MQTT-Zugangsdaten liegen sie lokal in der nicht versionierten
Einstellungsdatei, nun mit Dateirechten `0600`; sie sind dort nicht verschlüsselt.
Die Oberfläche sollte nur über geschützten Home-Assistant-Ingress oder ein
anderweitig abgesichertes Netz erreichbar sein.

## Offline-Prüfung

```sh
python3 -m unittest discover -s mioty-application-center/tests -v
```

Die Tests verwenden keine echten Zugangsdaten und verbinden sich nicht mit Sentinum.
Ein produktiver Empfang kann erst mit einem autorisierten Cloud-Konto und einer
Sensorübertragung bestätigt werden.

## Quellen

- https://docs.sentinum.de/en/new-integration-guide
- https://sentinum.de/en/datahub
- Sentinum Datahub 2.0 User Guide, 23.06.2026:
  https://raw.githack.com/bellaminemo81172/sentinum_documentation/8cf19341ffea6af3d72dbc8f46a07207557abc12/Datahub_User_Guide/Datahub_user_Guide_EN.pdf
