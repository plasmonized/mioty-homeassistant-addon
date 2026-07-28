# Anleitung: Home Assistant Add-on mit Flask GUI, Versionierung & Release Notes

Diese Anleitung erklärt Schritt für Schritt, wie ein KI-Agent ein professionelles
Home Assistant Add-on erstellt — mit Web-GUI, Versionierung, Changelog und MQTT/TLS-Anbindung.

---

## 1. Projektstruktur

```
my-addon/
├── config.yaml            # HA Add-on Metadaten + Version
├── Dockerfile             # Docker-Image-Definition
├── CHANGELOG.md           # Release Notes (manuell gepflegt)
├── README.md
└── app/
    ├── main.py            # Haupt-Anwendungslogik (Add-on-Klasse)
    ├── web_gui.py         # Flask Web-GUI (alle Routes + HTML-Templates)
    ├── mqtt_manager.py    # MQTT-Client (paho-mqtt)
    ├── scaci_client.py    # TLS-Client (falls benötigt)
    └── templates/
        ├── index.html     # Dashboard (Jinja2 oder statisch)
        ├── sensors.html
        └── decoders.html
```

---

## 2. config.yaml (Pflichtfelder)

```yaml
name: "Mein Add-on"
version: "1.0.0.0"          # IMMER x.y.z.w Format — alle 4 Felder
slug: "my_addon"
description: "Kurzbeschreibung"
url: "https://github.com/user/repo"
arch:
  - aarch64
  - amd64
  - armhf
  - armv7
  - i386
startup: application
boot: auto
ingress: true               # Web-GUI über HA-Ingress
ingress_port: 5000
panel_icon: mdi:router-wireless
panel_title: "Mein Add-on"
options: {}
schema: {}
```

**Wichtig:** `version` in `config.yaml`, `Dockerfile`, `app/main.py`, `app/web_gui.py`
und `CHANGELOG.md` müssen IMMER identisch sein.

---

## 3. Dockerfile

```dockerfile
ARG BUILD_FROM
FROM $BUILD_FROM

LABEL \
    io.hass.name="Mein Add-on" \
    io.hass.description="Kurzbeschreibung" \
    io.hass.version="1.0.0.0" \
    io.hass.type="addon" \
    io.hass.arch="aarch64|amd64|armhf|armv7|i386"

RUN apk add --no-cache python3 py3-pip

COPY app/ /app/
WORKDIR /app

RUN pip3 install --no-cache-dir flask paho-mqtt msgpack

CMD ["python3", "main.py"]
```

---

## 4. Versionierungsschema

**Format:** `MAJOR.MINOR.PATCH.BUILD` (z. B. `1.0.6.8`)

| Stelle | Bedeutung                        | Wann erhöhen          |
|--------|----------------------------------|-----------------------|
| MAJOR  | Breaking Change / Neuarchitektur | Selten                |
| MINOR  | Neue Feature-Gruppe              | Neue Hauptfunktion    |
| PATCH  | Bugfixes + kleinere Features     | Regelmäßig            |
| BUILD  | Kleine Fixes, Hotfixes           | Oft (mehrmals/Woche)  |

**Regel für den Agenten:**
- Vor JEDEM Commit: Version in allen 5 Stellen gleichzeitig erhöhen
- Befehl: `sed -i 's/1\.0\.6\.7/1.0.6.8/g' config.yaml Dockerfile app/main.py app/web_gui.py CHANGELOG.md`
- Danach prüfen: `grep -r "1.0.6.8" config.yaml Dockerfile app/main.py`

---

## 5. CHANGELOG.md Struktur

```markdown
# Changelog

## [1.0.6.8] - 2026-07-26
### Neu
- Service Center Status auf Dashboard statt MQTT Status

### Verbessert
- Status-API gibt jetzt `service_center_connected` zurück

### Behoben
- CPU/Memory-Werte von SCACI korrekt normalisiert (0-100% → 0-1 Fraktion)

## [1.0.6.7] - 2026-07-25
### Neu
- Service Center Status Banner auf Startseite
...
```

**Regel:** Jede Version bekommt einen Eintrag. Agent schreibt Release Notes
BEVOR er die Version bumpt — dann ist der Kontext noch frisch.

---

## 6. Flask Web-GUI (web_gui.py) — Muster

```python
from flask import Flask, jsonify, request, render_template

class WebGUI:
    def __init__(self, addon, settings):
        self.app = Flask(__name__, template_folder='templates')
        self.addon = addon
        self.settings = settings
        self._register_routes()

    def _register_routes(self):
        @self.app.route('/')
        def index():
            ingress_path = request.headers.get('X-Ingress-Path', '')
            return render_template('index.html', ingress_path=ingress_path)

        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'sensor_count': len(self.addon.sensors),
                'service_center_connected': self._check_sc_connected(),
                'version': '1.0.6.8'
            })

    def _check_sc_connected(self):
        # SCACI oder MQTT verbunden?
        sc = getattr(self.addon, 'scaci_client', None)
        if sc and sc.get_connection_info().get('connected'):
            return True
        mqtt = getattr(self.addon, 'mqtt_manager', None)
        return bool(mqtt and mqtt.connected)

    def run(self, port=5000):
        self.app.run(host='0.0.0.0', port=port, debug=False)
```

---

## 7. Ingress-Kompatibilität (WICHTIG für HA)

HA liefert die Add-on-GUI über einen Reverse-Proxy (Ingress). Alle API-Aufrufe
aus dem Frontend müssen den Ingress-Pfad kennen:

```javascript
// In jeder HTML-Seite:
const INGRESS_PATH = '{{ ingress_path }}' || '';
const BASE_URL = INGRESS_PATH || window.location.origin;

// Dann alle fetch-Calls so:
fetch(BASE_URL + '/api/status')
```

```python
# Im Flask-Route den Pfad weitergeben:
@app.route('/')
def index():
    ingress_path = request.headers.get('X-Ingress-Path', '')
    return render_template('index.html', ingress_path=ingress_path)
```

**Cache-Busting** für HA-Ingress (verhindert veraltete API-Antworten):
```javascript
function addCacheBuster(url) {
    return url + (url.includes('?') ? '&' : '?') + 'cb=' + Date.now();
}
const originalFetch = window.fetch;
window.fetch = function(url, options = {}) {
    if (typeof url === 'string' && url.startsWith('/api/')) {
        url = addCacheBuster(url);
    }
    options.cache = 'no-store';
    return originalFetch(url, options);
};
```

---

## 8. MQTT-Manager (mqtt_manager.py) — Muster

```python
import paho.mqtt.client as mqtt
import logging

class MQTTManager:
    def __init__(self, broker, port, username=None, password=None):
        self.broker = broker
        self.port = port
        self.connected = False
        self.client = mqtt.Client()
        if username:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info("✅ MQTT verbunden")
            client.subscribe("ep/+/ul")      # Uplinks
            client.subscribe("bs/+/status")  # Base Station Status
        else:
            logging.warning(f"⚠️ MQTT Verbindungsfehler: rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        logging.warning(f"⚠️ MQTT getrennt: rc={rc}")

    def start(self):
        self.client.connect_async(self.broker, self.port)
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()
        self.client.disconnect()
```

---

## 9. SCACI/TLS-Client — Besonderheiten

Falls das Add-on direkt per TLS mit einem Service Center spricht:

- **Framing:** `MIOTYA01` (8 Bytes) + uint32 Big-Endian Länge + msgpack-Payload
- **EUI-Format:** Service Center schickt EUIs als Hex-Strings (`'502DF4000056A0BE'`),
  NICHT als Integer wie die Spec behauptet. `int(eui, 16)` verwenden, nicht `int(eui)`.
- **Feldnamen in statusRsp:** `basestations` (lowercase), `rc` (nicht `code`),
  `uptimeS` (nicht `uptime`), CPU kommt als `cpu: 30.0` (Prozent 0-100, nicht 0-1 Fraktion)
- **connect_completed:** Erst nach erfolgreichem `connectRsp` auf `True` setzen —
  Status-Poll-Thread erst dann starten

---

## 10. GitHub-Repository-Struktur für HACS

Damit das Add-on per HACS installierbar ist:

```
repository-root/
├── README.md
├── repository.json         # HACS Metadata
└── my-addon/               # Add-on-Verzeichnis (wie oben)
    ├── config.yaml
    ├── Dockerfile
    └── app/
```

`repository.json`:
```json
{
  "name": "Mein Add-on Repository",
  "url": "https://github.com/user/repo",
  "maintainer": "user"
}
```

---

## 11. Release-Workflow für den Agenten

1. Feature/Fix implementieren und testen
2. `CHANGELOG.md` aktualisieren (neue Version + Beschreibung)
3. Version in allen Dateien erhöhen (sed-Befehl)
4. `replit.md` / README aktualisieren (Version + Kurzbeschreibung)
5. Commit (Replit erstellt automatisch Checkpoint)
6. User pusht zu GitHub → HA kann updaten

---

## 12. Design-Leitlinien (Orange/Grau-Schema)

```css
:root {
    --primary: #E87722;      /* mioty/Sentinum Orange */
    --primary-dark: #c5621a;
    --bg-dark: #2d2d2d;      /* Navbar-Hintergrund */
    --bg-light: #f5f5f5;
    --text-light: #ffffff;
}

.navbar { background: var(--bg-dark); }
.btn    { background: var(--primary); color: white; border: none; border-radius: 5px; }
.stat-card {
    background: white;
    border-radius: 12px;
    padding: 20px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    text-align: center;
}
.stat-number { font-size: 2.5em; font-weight: bold; color: var(--primary); }
```

---

## Zusammenfassung: Was macht dieses Add-on so gut?

| Feature | Umsetzung |
|---|---|
| Klare Versionierung | `x.y.z.w` in 5 Dateien gleichzeitig |
| Release Notes | CHANGELOG.md mit Datum + Kategorien |
| Web-GUI | Flask + Jinja2-Templates + REST-API |
| HA-Integration | Ingress-Proxy + Cache-Busting |
| Robustheit | Logging mit Emoji-Präfixen, try/except überall |
| Dual-Mode | MQTT **und** SCACI/TLS gleichzeitig möglich |
| Status-Anzeige | Einheitliches `service_center_connected`-Flag |
