"""
Web GUI für BSSCI mioty Add-on
Flask-basierte Benutzeroberfläche für Sensor-Management
"""

import logging
import json
from typing import Any, Dict
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_cors import CORS
from settings_manager import SettingsManager


class WebGUI:
    """Web-Benutzeroberfläche für das Add-on."""
    
    def __init__(self, port: int = 8080, addon_instance=None):
        """Initialisiere Web GUI."""
        self.port = port
        self.addon = addon_instance
        self.settings = SettingsManager()
        
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Routen definieren
        self.setup_routes()
        
        logging.info(f"Web GUI initialisiert auf Port {port}")
    
    def setup_routes(self):
        """Definiere Web-Routen."""
        
        @self.app.route('/')
        def index():
            """Hauptseite."""
            return render_template_string(self.get_main_template())
        
        @self.app.route('/settings')
        def settings():
            """Einstellungsseite."""
            return render_template_string(self.get_settings_template())
        
        @self.app.route('/api/sensors')
        def get_sensors():
            """API: Liste aller Sensoren."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            sensors = self.addon.get_sensor_list()
            return jsonify(sensors)
        
        @self.app.route('/api/basestations')
        def get_basestations():
            """API: Liste aller Base Stations."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            basestations = self.addon.get_basestation_list()
            return jsonify(basestations)
        
        @self.app.route('/api/sensor/add', methods=['POST'])
        def add_sensor():
            """API: Neuen Sensor hinzufügen."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            data = request.get_json()
            
            # Validierung
            required_fields = ['sensor_eui', 'network_key', 'short_addr']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({"error": f"Feld '{field}' ist erforderlich"}), 400
            
            # Sensor hinzufügen
            result = self.addon.add_sensor(
                sensor_eui=data['sensor_eui'],
                network_key=data['network_key'],
                short_addr=data['short_addr'],
                bidirectional=data.get('bidirectional', False)
            )
            
            if result:
                return jsonify({"success": True, "message": "Sensor erfolgreich hinzugefügt"})
            else:
                return jsonify({"error": "Sensor konnte nicht hinzugefügt werden"}), 500
        
        @self.app.route('/api/sensor/remove', methods=['POST'])
        def remove_sensor():
            """API: Sensor entfernen."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            data = request.get_json()
            
            if 'sensor_eui' not in data:
                return jsonify({"error": "sensor_eui ist erforderlich"}), 400
            
            result = self.addon.remove_sensor(data['sensor_eui'])
            
            if result:
                return jsonify({"success": True, "message": "Sensor erfolgreich entfernt"})
            else:
                return jsonify({"error": "Sensor konnte nicht entfernt werden"}), 500
        
        @self.app.route('/api/settings')
        def get_settings():
            """API: Aktuelle Einstellungen abrufen."""
            settings = self.settings.get_all_settings()
            # Passwort aus Sicherheitsgründen nicht zurückgeben
            settings['mqtt_password'] = '***' if settings.get('mqtt_password') else ''
            return jsonify(settings)
        
        @self.app.route('/api/settings', methods=['POST'])
        def update_settings():
            """API: Einstellungen aktualisieren."""
            data = request.get_json()
            
            # Validierung
            required_fields = ['mqtt_broker', 'mqtt_port', 'base_topic']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({"error": f"Feld '{field}' ist erforderlich"}), 400
            
            # Passwort nur aktualisieren wenn es nicht *** ist
            if data.get('mqtt_password') == '***':
                data.pop('mqtt_password', None)
            
            # Port zu Integer konvertieren
            try:
                data['mqtt_port'] = int(data['mqtt_port'])
            except ValueError:
                return jsonify({"error": "MQTT Port muss eine Zahl sein"}), 400
            
            # Einstellungen speichern
            if self.settings.update_settings(data):
                # Add-on über Änderungen benachrichtigen
                if self.addon and hasattr(self.addon, 'reload_settings'):
                    self.addon.reload_settings()
                    
                return jsonify({"success": True, "message": "Einstellungen gespeichert. Starten Sie das Add-on neu um Änderungen zu übernehmen."})
            else:
                return jsonify({"error": "Fehler beim Speichern der Einstellungen"}), 500
    
    def get_main_template(self) -> str:
        """Hauptseiten-Template."""
        return '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mioty Application Center für Homeassistant</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .nav {
            background: #6c757d;
            padding: 0;
            display: flex;
            justify-content: center;
        }
        
        .nav-item {
            color: white;
            text-decoration: none;
            padding: 15px 30px;
            display: block;
            transition: background-color 0.3s ease;
        }
        
        .nav-item:hover, .nav-item.active {
            background: #ff6b35;
            color: white;
            text-decoration: none;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            color: #333;
            border-bottom: 3px solid #ff6b35;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #555;
        }
        
        .form-group input[type="text"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input[type="text"]:focus {
            outline: none;
            border-color: #ff6b35;
        }
        
        .form-group input[type="checkbox"] {
            transform: scale(1.2);
            margin-right: 10px;
        }
        
        .btn {
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease;
            margin-right: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn-danger {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        }
        
        .sensor-list {
            display: grid;
            gap: 20px;
        }
        
        .sensor-card {
            border: 2px solid #eee;
            border-radius: 12px;
            padding: 20px;
            transition: border-color 0.3s ease;
        }
        
        .sensor-card:hover {
            border-color: #ff6b35;
        }
        
        .sensor-header {
            display: flex;
            justify-content: between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .sensor-eui {
            font-family: monospace;
            font-size: 1.2em;
            font-weight: 600;
            color: #333;
        }
        
        .sensor-status {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4CAF50;
        }
        
        .sensor-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        
        .detail-item {
            display: flex;
            flex-direction: column;
        }
        
        .detail-label {
            font-weight: 600;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }
        
        .detail-value {
            color: #333;
            font-family: monospace;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        @media (max-width: 768px) {
            .container {
                margin: 10px;
                border-radius: 10px;
            }
            
            .content {
                padding: 20px;
            }
            
            .sensor-details {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 mioty Application Center</h1>
            <p>für Home Assistant</p>
        </div>
        
        <div class="nav">
            <a href="/" class="nav-item active">📊 Sensoren</a>
            <a href="/settings" class="nav-item">⚙️ Einstellungen</a>
        </div>
        
        <div class="content">
            <div id="alerts"></div>
            
            <!-- Sensor hinzufügen -->
            <div class="section">
                <h2>📡 Neuen Sensor hinzufügen</h2>
                <form id="addSensorForm">
                    <div class="form-group">
                        <label for="sensor_eui">Sensor EUI (16 Hex-Zeichen):</label>
                        <input type="text" id="sensor_eui" name="sensor_eui" placeholder="fca84a0300001234" pattern="[0-9a-fA-F]{16}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="network_key">Netzwerk-Schlüssel (32 Hex-Zeichen):</label>
                        <input type="text" id="network_key" name="network_key" placeholder="0011223344556677889AABBCCDDEEFF00" pattern="[0-9a-fA-F]{32}" required>
                    </div>
                    
                    <div class="form-group">
                        <label for="short_addr">Kurze Adresse (4 Hex-Zeichen):</label>
                        <input type="text" id="short_addr" name="short_addr" placeholder="1234" pattern="[0-9a-fA-F]{4}" required>
                    </div>
                    
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="bidirectional" name="bidirectional">
                            Bidirektionale Kommunikation aktivieren
                        </label>
                    </div>
                    
                    <button type="submit" class="btn">Sensor hinzufügen</button>
                </form>
            </div>
            
            <!-- Sensor-Liste -->
            <div class="section">
                <h2>📊 Registrierte Sensoren</h2>
                <div id="sensorList" class="loading">Lade Sensoren...</div>
            </div>
            
            <!-- Base Station Status -->
            <div class="section">
                <h2>🏗️ Base Stations</h2>
                <div id="baseStationList" class="loading">Lade Base Stations...</div>
            </div>
        </div>
    </div>
    
    <script>
        // DOM Elemente
        const addSensorForm = document.getElementById('addSensorForm');
        const sensorList = document.getElementById('sensorList');
        const baseStationList = document.getElementById('baseStationList');
        const alerts = document.getElementById('alerts');
        
        // Sensor-Daten laden
        async function loadSensors() {
            try {
                const response = await fetch('/api/sensors');
                const sensors = await response.json();
                
                if (Object.keys(sensors).length === 0) {
                    sensorList.innerHTML = '<p>Noch keine Sensoren registriert.</p>';
                    return;
                }
                
                let html = '<div class="sensor-list">';
                for (const [eui, data] of Object.entries(sensors)) {
                    html += createSensorCard(eui, data);
                }
                html += '</div>';
                
                sensorList.innerHTML = html;
                
            } catch (error) {
                sensorList.innerHTML = '<p>Fehler beim Laden der Sensoren.</p>';
                console.error('Fehler:', error);
            }
        }
        
        // Base Station Daten laden
        async function loadBaseStations() {
            try {
                const response = await fetch('/api/basestations');
                const stations = await response.json();
                
                if (Object.keys(stations).length === 0) {
                    baseStationList.innerHTML = '<p>Keine Base Stations erkannt.</p>';
                    return;
                }
                
                let html = '<div class="sensor-list">';
                for (const [eui, data] of Object.entries(stations)) {
                    html += createBaseStationCard(eui, data);
                }
                html += '</div>';
                
                baseStationList.innerHTML = html;
                
            } catch (error) {
                baseStationList.innerHTML = '<p>Fehler beim Laden der Base Stations.</p>';
                console.error('Fehler:', error);
            }
        }
        
        // Sensor-Karte erstellen
        function createSensorCard(eui, data) {
            const lastSeen = data.last_seen ? new Date(data.last_seen * 1000).toLocaleString() : 'Nie';
            
            return `
                <div class="sensor-card">
                    <div class="sensor-header">
                        <div class="sensor-eui">${eui}</div>
                        <div class="sensor-status">
                            <div class="status-indicator"></div>
                            <span>Online</span>
                        </div>
                    </div>
                    
                    <div class="sensor-details">
                        <div class="detail-item">
                            <div class="detail-label">Kurze Adresse</div>
                            <div class="detail-value">${data.short_addr || 'N/A'}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Bidirektional</div>
                            <div class="detail-value">${data.bidirectional ? 'Ja' : 'Nein'}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Signalqualität</div>
                            <div class="detail-value">${data.signal_quality || 'Unbekannt'}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Zuletzt gesehen</div>
                            <div class="detail-value">${lastSeen}</div>
                        </div>
                    </div>
                    
                    <button class="btn btn-danger" onclick="removeSensor('${eui}')">Sensor entfernen</button>
                </div>
            `;
        }
        
        // Base Station Karte erstellen
        function createBaseStationCard(eui, data) {
            const lastSeen = data.last_seen ? new Date(data.last_seen * 1000).toLocaleString() : 'Nie';
            const status = data.status || {};
            
            return `
                <div class="sensor-card">
                    <div class="sensor-header">
                        <div class="sensor-eui">${eui}</div>
                        <div class="sensor-status">
                            <div class="status-indicator"></div>
                            <span>Online</span>
                        </div>
                    </div>
                    
                    <div class="sensor-details">
                        <div class="detail-item">
                            <div class="detail-label">CPU Auslastung</div>
                            <div class="detail-value">${((status.cpuLoad || 0) * 100).toFixed(1)}%</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Memory Auslastung</div>
                            <div class="detail-value">${((status.memLoad || 0) * 100).toFixed(1)}%</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Duty Cycle</div>
                            <div class="detail-value">${((status.dutyCycle || 0) * 100).toFixed(1)}%</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Zuletzt gesehen</div>
                            <div class="detail-value">${lastSeen}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Alert anzeigen
        function showAlert(message, type = 'success') {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            
            alerts.appendChild(alert);
            
            setTimeout(() => {
                alert.remove();
            }, 5000);
        }
        
        // Sensor hinzufügen
        addSensorForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(addSensorForm);
            const data = {
                sensor_eui: formData.get('sensor_eui'),
                network_key: formData.get('network_key'),
                short_addr: formData.get('short_addr'),
                bidirectional: formData.get('bidirectional') === 'on'
            };
            
            try {
                const response = await fetch('/api/sensor/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showAlert(result.message, 'success');
                    addSensorForm.reset();
                    loadSensors(); // Liste neu laden
                } else {
                    showAlert(result.error, 'error');
                }
                
            } catch (error) {
                showAlert('Fehler beim Hinzufügen des Sensors', 'error');
                console.error('Fehler:', error);
            }
        });
        
        // Sensor entfernen
        async function removeSensor(eui) {
            if (!confirm(`Sensor ${eui} wirklich entfernen?`)) {
                return;
            }
            
            try {
                const response = await fetch('/api/sensor/remove', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({sensor_eui: eui})
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showAlert(result.message, 'success');
                    loadSensors(); // Liste neu laden
                } else {
                    showAlert(result.error, 'error');
                }
                
            } catch (error) {
                showAlert('Fehler beim Entfernen des Sensors', 'error');
                console.error('Fehler:', error);
            }
        }
        
        // Daten regelmäßig aktualisieren
        function startAutoRefresh() {
            loadSensors();
            loadBaseStations();
            
            setInterval(() => {
                loadSensors();
                loadBaseStations();
            }, 30000); // Alle 30 Sekunden
        }
        
        // Start
        document.addEventListener('DOMContentLoaded', () => {
            startAutoRefresh();
        });
    </script>
</body>
</html>
        '''
    
    def run(self):
        """Starte Flask Server."""
        try:
            self.app.run(
                host='0.0.0.0',
                port=self.port,
                debug=False,
                use_reloader=False,
                threaded=True
            )
        except Exception as e:
            logging.error(f"Fehler beim Starten der Web GUI: {e}")
    
    def shutdown(self):
        """Beende Web Server."""
        # Flask Server kann nicht sauber beendet werden ohne Werkzeug
        # In einer echten Implementation würde hier ein Thread-Safe Shutdown stehen
        pass
    
    def get_settings_template(self) -> str:
        """Einstellungsseiten-Template."""
        return '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mioty Application Center Einstellungen</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        .nav {
            background: #6c757d;
            padding: 0;
            display: flex;
            justify-content: center;
        }
        
        .nav-item {
            color: white;
            text-decoration: none;
            padding: 15px 30px;
            display: block;
            transition: background-color 0.3s ease;
        }
        
        .nav-item:hover, .nav-item.active {
            background: #ff6b35;
            color: white;
            text-decoration: none;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 30px;
        }
        
        .section {
            margin-bottom: 40px;
        }
        
        .section h2 {
            color: #333;
            border-bottom: 3px solid #ff6b35;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 5px;
            color: #555;
        }
        
        .form-group input[type="text"], .form-group input[type="password"], .form-group input[type="number"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s ease;
        }
        
        .form-group input:focus {
            outline: none;
            border-color: #ff6b35;
        }
        
        .form-group input[type="checkbox"] {
            transform: scale(1.2);
            margin-right: 10px;
        }
        
        .btn {
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s ease;
            margin-right: 10px;
        }
        
        .btn:hover {
            transform: translateY(-2px);
        }
        
        .btn-secondary {
            background: #6c757d;
        }
        
        .alert {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .help-text {
            font-size: 0.9em;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚙️ mioty Application Center</h1>
            <p>Einstellungen</p>
        </div>
        
        <div class="nav">
            <a href="/" class="nav-item">📊 Sensoren</a>
            <a href="/settings" class="nav-item active">⚙️ Einstellungen</a>
        </div>
        
        <div class="content">
            <div id="alerts"></div>
            
            <!-- MQTT Konfiguration -->
            <div class="section">
                <h2>🔌 MQTT Broker Konfiguration</h2>
                <form id="settingsForm">
                    <div class="form-group">
                        <label for="mqtt_broker">MQTT Broker:</label>
                        <input type="text" id="mqtt_broker" name="mqtt_broker" placeholder="core-mosquitto" required>
                        <div class="help-text">Hostname oder IP-Adresse des MQTT Brokers (Standard: core-mosquitto)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="mqtt_port">MQTT Port:</label>
                        <input type="number" id="mqtt_port" name="mqtt_port" placeholder="1883" min="1" max="65535" required>
                        <div class="help-text">Port des MQTT Brokers (Standard: 1883)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="mqtt_username">MQTT Benutzername:</label>
                        <input type="text" id="mqtt_username" name="mqtt_username" placeholder="Optional">
                        <div class="help-text">Benutzername für MQTT Authentication (Optional)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="mqtt_password">MQTT Passwort:</label>
                        <input type="password" id="mqtt_password" name="mqtt_password" placeholder="Passwort">
                        <div class="help-text">Passwort für MQTT Authentication (Leer lassen um nicht zu ändern)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="base_topic">Basis Topic:</label>
                        <input type="text" id="base_topic" name="base_topic" placeholder="bssci" required>
                        <div class="help-text">MQTT Topic-Präfix für BSSCI Nachrichten (Standard: bssci)</div>
                    </div>
                    
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="auto_discovery" name="auto_discovery">
                            Home Assistant Auto-Discovery aktivieren
                        </label>
                        <div class="help-text">Neue Sensoren automatisch in Home Assistant registrieren</div>
                    </div>
                    
                    <button type="submit" class="btn">💾 Einstellungen speichern</button>
                    <button type="button" class="btn btn-secondary" onclick="loadSettings()">🔄 Neu laden</button>
                </form>
            </div>
            
            <!-- Verbindungsstatus -->
            <div class="section">
                <h2>📡 Verbindungsstatus</h2>
                <div id="connectionStatus" class="loading">Lade Verbindungsstatus...</div>
            </div>
        </div>
    </div>
    
    <script>
        // DOM Elemente
        const settingsForm = document.getElementById('settingsForm');
        const alerts = document.getElementById('alerts');
        const connectionStatus = document.getElementById('connectionStatus');
        
        // Einstellungen laden
        async function loadSettings() {
            try {
                const response = await fetch('/api/settings');
                const settings = await response.json();
                
                // Formular mit aktuellen Werten füllen
                document.getElementById('mqtt_broker').value = settings.mqtt_broker || '';
                document.getElementById('mqtt_port').value = settings.mqtt_port || 1883;
                document.getElementById('mqtt_username').value = settings.mqtt_username || '';
                document.getElementById('mqtt_password').value = settings.mqtt_password || '';
                document.getElementById('base_topic').value = settings.base_topic || 'bssci';
                document.getElementById('auto_discovery').checked = settings.auto_discovery || false;
                
            } catch (error) {
                showAlert('Fehler beim Laden der Einstellungen', 'error');
                console.error('Fehler:', error);
            }
        }
        
        // Alert anzeigen
        function showAlert(message, type = 'success') {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            
            alerts.appendChild(alert);
            
            setTimeout(() => {
                alert.remove();
            }, 5000);
        }
        
        // Einstellungen speichern
        settingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(settingsForm);
            const data = {
                mqtt_broker: formData.get('mqtt_broker'),
                mqtt_port: formData.get('mqtt_port'),
                mqtt_username: formData.get('mqtt_username'),
                mqtt_password: formData.get('mqtt_password'),
                base_topic: formData.get('base_topic'),
                auto_discovery: formData.get('auto_discovery') === 'on'
            };
            
            try {
                const response = await fetch('/api/settings', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    showAlert(result.message, 'success');
                } else {
                    showAlert(result.error, 'error');
                }
                
            } catch (error) {
                showAlert('Fehler beim Speichern der Einstellungen', 'error');
                console.error('Fehler:', error);
            }
        });
        
        // Verbindungsstatus laden
        async function loadConnectionStatus() {
            try {
                connectionStatus.innerHTML = `
                    <div style="padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 12px; height: 12px; background: #28a745; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>Web-GUI: Online</strong>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 12px; height: 12px; background: #dc3545; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>MQTT: Getrennt (Demo-Modus)</strong>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 12px; height: 12px; background: #ffc107; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>BSSCI Service: Nicht verfügbar (Demo)</strong>
                        </div>
                    </div>
                `;
                
            } catch (error) {
                connectionStatus.innerHTML = '<p>Fehler beim Laden des Verbindungsstatus.</p>';
                console.error('Fehler:', error);
            }
        }
        
        // Initialisierung
        document.addEventListener('DOMContentLoaded', () => {
            loadSettings();
            loadConnectionStatus();
        });
    </script>
</body>
</html>
        '''