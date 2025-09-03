"""
Web GUI für BSSCI mioty Add-on
Flask-basierte Benutzeroberfläche für Sensor-Management
"""

import logging
import json
import time
from typing import Any, Dict
from flask import Flask, render_template, render_template_string, request, jsonify, redirect, url_for
from flask_cors import CORS
from settings_manager import SettingsManager


class WebGUI:
    """Web-Benutzeroberfläche für das Add-on."""
    
    def __init__(self, port: int = 8080, addon_instance=None):
        """Initialisiere Web GUI."""
        self.port = port
        self.addon = addon_instance
        self.settings = SettingsManager()
        
        # KRITISCH: Korrekter Template-Pfad für app/templates/
        import os
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.app = Flask(__name__, template_folder=template_path)
        
        # KRITISCH: Flask Template-Caching deaktivieren
        self.app.config['TEMPLATES_AUTO_RELOAD'] = True
        self.app.jinja_env.auto_reload = True
        self.app.jinja_env.cache = {}
        
        CORS(self.app)
        
        # Erweiterte HTTP-Protokollierung aktivieren
        self.setup_logging()
        
        # Routen definieren
        self.setup_routes()
        
        logging.info(f"Web GUI initialisiert auf Port {port}")
    
    def setup_logging(self):
        """Konfiguriere erweiterte HTTP-Protokollierung für Debugging."""
        
        @self.app.before_request
        def log_request_details():
            """Protokolliere detaillierte Request-Informationen."""
            logging.info("=" * 80)
            logging.info("🔍 HTTP REQUEST DEBUGGING")
            logging.info("-" * 40)
            logging.info(f"📍 Method: {request.method}")
            logging.info(f"📍 URL: {request.url}")
            logging.info(f"📍 Path: {request.path}")
            logging.info(f"📍 Remote IP: {request.remote_addr}")
            logging.info(f"📍 User Agent: {request.headers.get('User-Agent', 'N/A')}")
            
            # Home Assistant Ingress Header Analysis
            logging.info("-" * 40)
            logging.info("🏠 HOME ASSISTANT INGRESS ANALYSIS")
            ha_headers = [
                'X-Ingress-Path',
                'X-Real-IP', 
                'X-Forwarded-For',
                'X-Forwarded-Host',
                'X-Forwarded-Proto',
                'Host',
                'Origin',
                'Referer'
            ]
            
            for header in ha_headers:
                value = request.headers.get(header, 'NICHT GESETZT')
                if value != 'NICHT GESETZT':
                    logging.info(f"📧 {header}: {value}")
                else:
                    logging.warning(f"⚠️  {header}: NICHT GESETZT")
            
            # Alle Header für vollständige Analyse
            logging.info("-" * 40)
            logging.info("📧 ALLE REQUEST HEADERS:")
            for key, value in request.headers:
                logging.info(f"   {key}: {value}")
            
            # Query Parameters
            if request.args:
                logging.info("-" * 40)
                logging.info("🔗 QUERY PARAMETERS:")
                for key, value in request.args.items():
                    logging.info(f"   {key}: {value}")
            
            logging.info("=" * 80)
        
        @self.app.after_request
        def log_response_details(response):
            """Protokolliere Response-Details und setze Cache-Control Headers."""
            
            # HOME ASSISTANT INGRESS AGGRESSIVE CACHE-BUSTING
            is_ingress = (request.headers.get('X-Ingress-Path') or 
                         'hassio_ingress' in request.headers.get('Referer', '') or
                         'homeassistant' in request.headers.get('User-Agent', '').lower())
            
            if hasattr(request, 'path') and request.path and (request.path.endswith(('.html', '.css', '.js')) or request.path in ['/', '/settings', '/decoders']):
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
                response.headers['Vary'] = '*'
                # Eindeutige ETag für jeden Request
                import time
                response.headers['ETag'] = f'"{int(time.time() * 1000)}"'
                
                # Extra Headers für Home Assistant Ingress
                if is_ingress:
                    response.headers['X-Accel-Expires'] = '0'
                    response.headers['X-Proxy-Cache'] = 'BYPASS'
                    response.headers['Surrogate-Control'] = 'no-store'
                    logging.info("🏠 HA Ingress Cache-Control Headers gesetzt")
                else:
                    logging.info("🚫 Standard Cache-Control Headers gesetzt")
            
            logging.info("📤 RESPONSE DETAILS:")
            logging.info(f"   Status: {response.status}")
            logging.info(f"   Content-Type: {response.content_type}")
            logging.info(f"   Content-Length: {response.content_length}")
            
            # Response Headers für Ingress-Debugging
            logging.info("📧 RESPONSE HEADERS:")
            for key, value in response.headers:
                logging.info(f"   {key}: {value}")
            
            return response
        
        # HTTP Error Handler
        @self.app.errorhandler(404)
        def handle_404(error):
            """Handle 404 Fehler mit detailliertem Logging."""
            logging.error("❌ 404 ERROR - PAGE NOT FOUND")
            logging.error(f"   Requested URL: {request.url}")
            logging.error(f"   Requested Path: {request.path}")
            logging.error(f"   Method: {request.method}")
            logging.error(f"   Remote IP: {request.remote_addr}")
            return jsonify({"error": "Page not found", "path": request.path}), 404
        
        @self.app.errorhandler(500)
        def handle_500(error):
            """Handle 500 Fehler mit detailliertem Logging."""
            logging.error("❌ 500 ERROR - INTERNAL SERVER ERROR")
            logging.error(f"   Error: {str(error)}")
            logging.error(f"   URL: {request.url}")
            logging.error(f"   Method: {request.method}")
            return jsonify({"error": "Internal server error"}), 500
        
        @self.app.errorhandler(Exception)
        def handle_exception(error):
            """Handle alle unbehandelten Ausnahmen."""
            logging.error("💥 UNHANDLED EXCEPTION")
            logging.error(f"   Exception Type: {type(error).__name__}")
            logging.error(f"   Exception Message: {str(error)}")
            logging.error(f"   URL: {request.url}")
            logging.error(f"   Method: {request.method}")
            import traceback
            logging.error(f"   Traceback: {traceback.format_exc()}")
            return jsonify({"error": "Application error", "details": str(error)}), 500
    
    def setup_routes(self):
        """Definiere Web-Routen."""
        
        @self.app.route('/')
        def index():
            """Hauptseite."""
            # Get the ingress path from Home Assistant header
            ingress_path = request.headers.get('X-Ingress-Path', '')
            
            # Spezielle Ingress-Debugging für Hauptseite
            logging.info("🏠 INDEX PAGE INGRESS DEBUGGING")
            logging.info(f"   X-Ingress-Path: {ingress_path}")
            logging.info(f"   Host Header: {request.headers.get('Host', 'N/A')}")
            logging.info(f"   Request URL: {request.url}")
            logging.info(f"   Base URL: {request.base_url}")
            logging.info(f"   URL Root: {request.url_root}")
            
            # Home Assistant Ingress Detection
            is_ha_ingress = bool(ingress_path) or 'hassio' in request.headers.get('Host', '').lower()
            environment = "Home Assistant Ingress" if is_ha_ingress else "Development/External"
            
            logging.info(f"🔍 ENVIRONMENT DETECTION: {environment}")
            if not is_ha_ingress:
                logging.warning("⚠️  Nicht in Home Assistant Ingress! Add-on läuft in externer Umgebung.")
                logging.info("💡 Für volle Home Assistant Integration: Add-on in HA installieren")
            
            # DEBUGGING: Template-Auswahl protokollieren
            template_path = self.app.template_folder
            index_exists = False
            try:
                import os
                index_file = os.path.join(template_path, 'index.html')
                index_exists = os.path.exists(index_file)
                logging.info(f"🔍 TEMPLATE DEBUGGING:")
                logging.info(f"   Template Folder: {template_path}")
                logging.info(f"   Index.html exists: {index_exists}")
                logging.info(f"   Index.html path: {index_file}")
            except Exception as e:
                logging.error(f"Template debugging error: {e}")
            
            # KRITISCH: Verwende IMMER die aktuelle externe Template-Datei
            if index_exists:
                logging.info("✅ Verwende AKTUELLE index.html Template-Datei (Version 1.0.4.6)")
                return render_template('index.html', ingress_path=ingress_path)
            else:
                logging.error("❌ CRITICAL ERROR: index.html Template-Datei nicht gefunden!")
                logging.error("   Template Fallback wurde entfernt um veraltete Versionen zu verhindern")
                return "❌ Template Error: index.html nicht gefunden", 500
        
        @self.app.route('/settings')
        def settings():
            """Einstellungsseite."""
            # Get the ingress path from Home Assistant header
            ingress_path = request.headers.get('X-Ingress-Path', '')
            
            # Spezielle Ingress-Debugging für Einstellungsseite
            logging.info("⚙️ SETTINGS PAGE INGRESS DEBUGGING")
            logging.info(f"   X-Ingress-Path: {ingress_path}")
            logging.info(f"   Request URL: {request.url}")
            
            return render_template_string(self.get_settings_template(), ingress_path=ingress_path)
        
        @self.app.route('/decoders')
        def decoders():
            """Decoder-Verwaltungsseite."""
            # Get the ingress path from Home Assistant header
            ingress_path = request.headers.get('X-Ingress-Path', '')
            
            # Spezielle Ingress-Debugging für Decoder-Seite
            logging.info("🔧 DECODERS PAGE INGRESS DEBUGGING")
            logging.info(f"   X-Ingress-Path: {ingress_path}")
            logging.info(f"   Request URL: {request.url}")
            
            return render_template_string(self.get_decoders_template(), ingress_path=ingress_path)
        
        @self.app.route('/api/sensors')
        def get_sensors():
            """API: Liste aller Sensoren."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            sensors_dict = self.addon.get_sensor_list()
            
            # Konvertiere Dictionary zu Liste für Frontend
            sensor_list = []
            for eui, data in sensors_dict.items():
                sensor_info = {
                    'eui': eui,
                    'sensor_type': 'mioty IoT Sensor',
                    'last_update': self._format_timestamp(data.get('last_seen', 0)),
                    'snr': data.get('data', {}).get('snr', 'N/A'),
                    'rssi': data.get('data', {}).get('rssi', 'N/A'),
                    'signal_quality': data.get('signal_quality', 'Unknown')
                }
                sensor_list.append(sensor_info)
            
            return jsonify(sensor_list)
        
        @self.app.route('/api/basestations')
        def get_basestations():
            """API: Liste aller Base Stations."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            basestations_dict = self.addon.get_basestation_list()
            
            # Konvertiere Dictionary zu Liste für Frontend
            bs_list = []
            for eui, data in basestations_dict.items():
                # Sichere Zugriffe auf Base Station-Daten
                status_data = data.get('data', {}) if isinstance(data.get('data'), dict) else {}
                
                bs_info = {
                    'eui': eui,
                    'status': data.get('status', 'Online'),
                    'last_update': self._format_timestamp(data.get('last_seen', 0)),
                    'cpu_usage': status_data.get('cpu_usage', 'N/A'),
                    'memory_usage': status_data.get('memory_usage', 'N/A')
                }
                bs_list.append(bs_info)
            
            return jsonify(bs_list)
        
        @self.app.route('/api/status')
        def get_status():
            """API: System- und Verbindungsstatus."""
            if not self.addon:
                return jsonify({"error": "Add-on nicht verfügbar"}), 500
            
            # mioty MQTT Status
            mqtt_connected = False
            mqtt_broker = 'Unbekannt'
            
            # Home Assistant MQTT Status
            ha_mqtt_connected = False
            ha_mqtt_broker = 'Unbekannt'
            
            if hasattr(self.addon, 'mqtt_manager') and self.addon.mqtt_manager:
                # mioty MQTT Client Status
                mqtt_connected = self.addon.mqtt_manager.connected
                mqtt_broker = f"{self.addon.mqtt_manager.broker}:{self.addon.mqtt_manager.port}"
                
                # Home Assistant MQTT Client Status
                ha_mqtt_connected = self.addon.mqtt_manager.ha_connected
                ha_mqtt_broker = f"{self.addon.mqtt_manager.ha_broker}:{self.addon.mqtt_manager.ha_port}"
            
            status = {
                'mqtt_connected': mqtt_connected,
                'mqtt_broker': mqtt_broker,
                'ha_mqtt_connected': ha_mqtt_connected,
                'ha_mqtt_broker': ha_mqtt_broker,
                'sensor_count': len(self.addon.sensors) if hasattr(self.addon, 'sensors') else 0,
                'basestation_count': len(self.addon.base_stations) if hasattr(self.addon, 'base_stations') else 0
            }
            
            return jsonify(status)
        
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
            # Aktuelle Laufzeit-Konfiguration vom Add-on abrufen
            if self.addon and hasattr(self.addon, 'config'):
                settings = {
                    'mqtt_broker': self.addon.config.get('mqtt_broker', 'localhost'),
                    'mqtt_port': self.addon.config.get('mqtt_port', 1883),
                    'mqtt_username': self.addon.config.get('mqtt_username', ''),
                    'mqtt_password': '***' if self.addon.config.get('mqtt_password') else '',
                    'base_topic': self.addon.config.get('base_topic', 'bssci'),
                    'auto_discovery': self.addon.config.get('auto_discovery', True),
                    'ha_mqtt_broker': self.addon.config.get('ha_mqtt_broker', 'core-mosquitto'),
                    'ha_mqtt_port': self.addon.config.get('ha_mqtt_port', 1883),
                    'ha_mqtt_username': self.addon.config.get('ha_mqtt_username', ''),
                    'ha_mqtt_password': '***' if self.addon.config.get('ha_mqtt_password') else ''
                }
            else:
                # Fallback zu gespeicherten Einstellungen
                settings = self.settings.get_all_settings()
                settings['mqtt_password'] = '***' if settings.get('mqtt_password') else ''
                settings['ha_mqtt_password'] = '***' if settings.get('ha_mqtt_password') else ''
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
        
        @self.app.route('/api/ha-settings', methods=['POST'])
        def update_ha_settings():
            """API: Home Assistant MQTT Einstellungen aktualisieren."""
            data = request.get_json()
            
            # Validierung
            required_fields = ['ha_mqtt_broker', 'ha_mqtt_port']
            for field in required_fields:
                if field not in data or not data[field]:
                    return jsonify({"error": f"Feld '{field}' ist erforderlich"}), 400
            
            # Passwort nur aktualisieren wenn es nicht *** ist
            if data.get('ha_mqtt_password') == '***':
                data.pop('ha_mqtt_password', None)
            
            # Port zu Integer konvertieren
            try:
                data['ha_mqtt_port'] = int(data['ha_mqtt_port'])
            except ValueError:
                return jsonify({"error": "HA MQTT Port muss eine Zahl sein"}), 400
            
            # Einstellungen speichern
            if self.settings.update_settings(data):
                # Add-on über Änderungen benachrichtigen
                if self.addon and hasattr(self.addon, 'reload_settings'):
                    self.addon.reload_settings()
                    
                return jsonify({"success": True, "message": "HA MQTT Einstellungen gespeichert. Starten Sie das Add-on neu um Änderungen zu übernehmen."})
            else:
                return jsonify({"error": "Fehler beim Speichern der HA MQTT Einstellungen"}), 500
        
        @self.app.route('/api/decoders')
        def get_decoders():
            """API: Liste aller Decoder."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            decoders = self.addon.decoder_manager.get_available_decoders()
            assignments = self.addon.decoder_manager.get_sensor_assignments()
            
            return jsonify({
                "decoders": decoders,
                "assignments": assignments
            })
        
        @self.app.route('/api/decoder/upload', methods=['POST'])
        def upload_decoder():
            """API: Decoder-Datei hochladen."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            if 'file' not in request.files:
                return jsonify({"error": "Keine Datei ausgewählt"}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "Kein Dateiname"}), 400
            
            if file and file.filename and file.filename.endswith(('.js', '.json', '.xml')):
                try:
                    content = file.read()
                    result = self.addon.decoder_manager.upload_decoder_file(file.filename, content)
                    
                    if result['success']:
                        return jsonify({"success": True, "message": result['message']})
                    else:
                        return jsonify({"error": result['error']}), 400
                        
                except Exception as e:
                    return jsonify({"error": f"Upload-Fehler: {str(e)}"}), 500
            else:
                return jsonify({"error": "Nur .js, .json und .xml (IODD) Dateien werden unterstützt"}), 400
        
        @self.app.route('/api/decoder/assign', methods=['POST'])
        def assign_decoder():
            """API: Decoder einem Sensor zuweisen."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            data = request.get_json()
            
            if not data.get('sensor_eui') or not data.get('decoder_name'):
                return jsonify({"error": "sensor_eui und decoder_name sind erforderlich"}), 400
            
            success = self.addon.decoder_manager.assign_decoder_to_sensor(
                data['sensor_eui'], data['decoder_name']
            )
            
            if success:
                return jsonify({"success": True, "message": "Decoder erfolgreich zugewiesen"})
            else:
                return jsonify({"error": "Fehler beim Zuweisen des Decoders"}), 500
        
        @self.app.route('/api/decoder/unassign', methods=['POST'])
        def unassign_decoder():
            """API: Decoder-Zuweisung entfernen."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            data = request.get_json()
            
            if not data.get('sensor_eui'):
                return jsonify({"error": "sensor_eui ist erforderlich"}), 400
            
            success = self.addon.decoder_manager.remove_sensor_assignment(data['sensor_eui'])
            
            if success:
                return jsonify({"success": True, "message": "Decoder-Zuweisung entfernt"})
            else:
                return jsonify({"error": "Fehler beim Entfernen der Decoder-Zuweisung"}), 500
        
        @self.app.route('/api/decoder/test', methods=['POST'])
        def test_decoder():
            """API: Decoder mit Test-Payload testen."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            data = request.get_json()
            
            if not data.get('decoder_name') or not data.get('test_payload'):
                return jsonify({"error": "decoder_name und test_payload sind erforderlich"}), 400
            
            try:
                # Konvertiere Hex-String zu Byte-Array
                if isinstance(data['test_payload'], str):
                    # Entferne Leerzeichen und 0x Präfixe
                    hex_str = data['test_payload'].replace(' ', '').replace('0x', '')
                    test_payload = [int(hex_str[i:i+2], 16) for i in range(0, len(hex_str), 2)]
                else:
                    test_payload = data['test_payload']
                
                result = self.addon.decoder_manager.test_decoder(data['decoder_name'], test_payload)
                return jsonify(result)
                
            except Exception as e:
                return jsonify({
                    "decoded": False,
                    "reason": f"Test-Fehler: {str(e)}",
                    "raw_data": data.get('test_payload', [])
                })
        
        @self.app.route('/api/decoder/delete', methods=['POST'])
        def delete_decoder():
            """API: Decoder löschen."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            data = request.get_json()
            
            if not data.get('decoder_name'):
                return jsonify({"error": "decoder_name ist erforderlich"}), 400
            
            success = self.addon.decoder_manager.delete_decoder(data['decoder_name'])
            
            if success:
                return jsonify({"success": True, "message": "Decoder erfolgreich gelöscht"})
            else:
                return jsonify({"error": "Fehler beim Löschen des Decoders"}), 500
        
        @self.app.route('/api/iolink/assign', methods=['POST'])
        def assign_iodd_to_iolink():
            """API: IODD einem IO-Link Adapter zuweisen basierend auf Vendor/Device ID."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            data = request.get_json()
            
            required_fields = ['sensor_eui', 'vendor_id', 'device_id', 'iodd_name']
            if not all(data.get(field) for field in required_fields):
                return jsonify({"error": "sensor_eui, vendor_id, device_id und iodd_name sind erforderlich"}), 400
            
            success = self.addon.decoder_manager.assign_iodd_to_iolink_adapter(
                data['sensor_eui'], data['vendor_id'], data['device_id'], data['iodd_name']
            )
            
            if success:
                return jsonify({"success": True, "message": "IODD erfolgreich dem IO-Link Adapter zugewiesen"})
            else:
                return jsonify({"error": "Fehler beim Zuweisen der IODD"}), 500
        
        @self.app.route('/api/iolink/adapters')
        def get_iolink_adapters():
            """API: Liste aller erkannten IO-Link Adapter mit Vendor/Device IDs."""
            if not self.addon or not hasattr(self.addon, 'decoder_manager'):
                return jsonify({"error": "Decoder Manager nicht verfügbar"}), 500
            
            adapters = self.addon.decoder_manager.get_iolink_adapters()
            return jsonify({"adapters": adapters})
    
    def get_main_template(self) -> str:
        """Hauptseiten-Template - SYNCHRONISIERT mit app/templates/index.html."""
        return '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>mioty Application Center für Homeassistant v1.0.4.6</title>
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
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 50%;
            right: 30px;
            transform: translateY(-50%);
            width: 60px;
            height: 60px;
            background-image: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cGF0aCBkPSJNMTUgMTVMMzAgMEw0NSAxNUwzMCAzMFoiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4xKSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIHN0cm9rZS13aWR0aD0iMiIvPgogIDxwYXRoIGQ9Ik0wIDMwTDE1IDE1TDMwIDMwTDE1IDQ1WiIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4yKSIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHBhdGggZD0iTTMwIDMwTDQ1IDE1TDYwIDMwTDQ1IDQ1WiIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjA1KSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMykiIHN0cm9rZS13aWR0aD0iMiIvPgo8L3N2Zz4K');
            background-size: contain;
            background-repeat: no-repeat;
            opacity: 0.15;
            z-index: 1;
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
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        
        .logo-icon {
            font-size: 0.8em;
            background: rgba(255,255,255,0.2);
            padding: 10px 12px;
            border-radius: 50%;
            backdrop-filter: blur(10px);
        }
        
        .nav-icon {
            font-size: 1.2em;
            margin-right: 8px;
            opacity: 0.8;
        }
        
        .section-icon {
            display: inline-block;
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            text-align: center;
            line-height: 24px;
            border-radius: 50%;
            margin-right: 12px;
            font-size: 14px;
            font-weight: bold;
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
            <h1><span class="logo-icon">⚡</span> mioty Application Center</h1>
            <p>für Home Assistant <span style="opacity: 0.6; font-size: 0.8em;">• powered by Sentinum</span></p>
        </div>
        
        <div class="nav">
            <a id="nav-sensors" href="#" class="nav-item active" onclick="navigateTo('/')"><span class="nav-icon">●</span> Sensoren</a>
            <a id="nav-decoders" href="#" class="nav-item" onclick="navigateTo('/decoders')"><span class="nav-icon">◆</span> Decoder</a>
            <a id="nav-settings" href="#" class="nav-item" onclick="navigateTo('/settings')"><span class="nav-icon">▲</span> Einstellungen</a>
        </div>
        
        <div class="content">
            <div id="alerts"></div>
            
            <!-- Sensor hinzufügen -->
            <div class="section">
                <h2><span class="section-icon">+</span> Neuen Sensor hinzufügen</h2>
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
                <h2><span class="section-icon">●</span> Registrierte Sensoren</h2>
                <div id="sensorList" class="loading">Lade Sensoren...</div>
            </div>
            
            <!-- Base Station Status -->
            <div class="section">
                <h2><span class="section-icon">■</span> Base Stations</h2>
                <div id="baseStationList" class="loading">Lade Base Stations...</div>
            </div>
        </div>
    </div>
    
    <script>
        // Use server-provided ingress path from X-Ingress-Path header
        const INGRESS_PATH = '{{ ingress_path }}' || '';
        const BASE_URL = INGRESS_PATH || window.location.origin;
        console.log('Ingress path from server:', INGRESS_PATH);
        console.log('BASE_URL resolved:', BASE_URL);
        console.log('Current pathname:', window.location.pathname);
        console.log('Is embedded (iframe):', window.parent !== window);
        
        // HOME ASSISTANT INGRESS CACHE-BUSTING LÖSUNG
        function addCacheBuster(url) {
            const separator = url.includes('?') ? '&' : '?';
            return url + separator + 'cb=' + Date.now() + '&t=' + Math.random();
        }
        
        // Erkenne Home Assistant Ingress Environment  
        const isHomeAssistantIngress = window.location.pathname.includes('/api/hassio_ingress/') || 
                                      document.referrer.includes('homeassistant') || 
                                      window.parent !== window;
        
        if (isHomeAssistantIngress) {
            console.log('🏠 HOME ASSISTANT INGRESS ERKANNT - Cache-Busting aktiviert!');
            
            // Überschreibe fetch mit automatischem Cache-Busting
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (typeof url === 'string' && (url.startsWith('/api/') || url.startsWith(BASE_URL + '/api/'))) {
                    url = addCacheBuster(url);
                    console.log('⚙️ Cache-Buster URL:', url);
                }
                // Aggressive no-cache headers für Home Assistant
                options.cache = 'no-store';
                options.headers = {
                    ...options.headers,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Requested-With': 'XMLHttpRequest'
                };
                return originalFetch(url, options);
            };
        }
        
        // Simplified navigation for embedded mode
        const navigateTo = (path) => {
            const fullUrl = BASE_URL + path;
            console.log('Navigating to:', fullUrl);
            console.log('Path requested:', path);
            
            // Simple approach - just use window.location.href
            // This should work in both embedded and direct access
            window.location.href = fullUrl;
        };
        
        // DOM Elemente
        const addSensorForm = document.getElementById('addSensorForm');
        const sensorList = document.getElementById('sensorList');
        const baseStationList = document.getElementById('baseStationList');
        const alerts = document.getElementById('alerts');
        
        // Sensor-Daten laden
        async function loadSensors() {
            try {
                const response = await fetch(BASE_URL + '/api/sensors');
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
                const response = await fetch(BASE_URL + '/api/basestations');
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
                const response = await fetch(BASE_URL + '/api/sensor/add', {
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
                const response = await fetch(BASE_URL + '/api/sensor/remove', {
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
    
    def _format_timestamp(self, timestamp):
        """Formatiere Unix Timestamp zu lesbarem String."""
        if timestamp and timestamp > 0:
            try:
                return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
            except:
                return "Unbekannt"
        return "Nie"

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
    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <title>mioty Application Center Einstellungen v1.0.4.6.1</title>
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
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: 50%;
            right: 30px;
            transform: translateY(-50%);
            width: 60px;
            height: 60px;
            background-image: url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KICA8cGF0aCBkPSJNMTUgMTVMMzAgMEw0NSAxNUwzMCAzMFoiIGZpbGw9InJnYmEoMjU1LDI1NSwyNTUsMC4xKSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMikiIHN0cm9rZS13aWR0aD0iMiIvPgogIDxwYXRoIGQ9Ik0wIDMwTDE1IDE1TDMwIDMwTDE1IDQ1WiIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjEpIiBzdHJva2U9InJnYmEoMjU1LDI1NSwyNTUsMC4yKSIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPHBhdGggZD0iTTMwIDMwTDQ1IDE1TDYwIDMwTDQ1IDQ1WiIgZmlsbD0icmdiYSgyNTUsMjU1LDI1NSwwLjA1KSIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMykiIHN0cm9rZS13aWR0aD0iMiIvPgo8L3N2Zz4K');
            background-size: contain;
            background-repeat: no-repeat;
            opacity: 0.15;
            z-index: 1;
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
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }
        
        .logo-icon {
            font-size: 0.8em;
            background: rgba(255,255,255,0.2);
            padding: 10px 12px;
            border-radius: 50%;
            backdrop-filter: blur(10px);
        }
        
        .nav-icon {
            font-size: 1.2em;
            margin-right: 8px;
            opacity: 0.8;
        }
        
        .section-icon {
            display: inline-block;
            width: 24px;
            height: 24px;
            background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%);
            color: white;
            text-align: center;
            line-height: 24px;
            border-radius: 50%;
            margin-right: 12px;
            font-size: 14px;
            font-weight: bold;
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
            <h1><span class="logo-icon">⚡</span> mioty Application Center</h1>
            <p>Einstellungen <span style="opacity: 0.6; font-size: 0.8em;">• powered by Sentinum</span></p>
        </div>
        
        <div class="nav">
            <a id="nav-sensors" href="#" class="nav-item" onclick="navigateTo('/')">📊 Sensoren</a>
            <a id="nav-decoders" href="#" class="nav-item" onclick="navigateTo('/decoders')">📝 Decoder</a>
            <a id="nav-settings" href="#" class="nav-item active" onclick="navigateTo('/settings')">⚙️ Einstellungen</a>
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
            
            <!-- Home Assistant MQTT Konfiguration -->
            <div class="section">
                <h2>🏠 Home Assistant MQTT Broker</h2>
                <form id="haSettingsForm">
                    <div class="form-group">
                        <label for="ha_mqtt_broker">HA MQTT Broker:</label>
                        <input type="text" id="ha_mqtt_broker" name="ha_mqtt_broker" placeholder="core-mosquitto" required>
                        <div class="help-text">Home Assistant MQTT Broker (Standard: core-mosquitto)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="ha_mqtt_port">HA MQTT Port:</label>
                        <input type="number" id="ha_mqtt_port" name="ha_mqtt_port" placeholder="1883" min="1" max="65535" required>
                        <div class="help-text">Home Assistant MQTT Port (Standard: 1883)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="ha_mqtt_username">HA MQTT Benutzername:</label>
                        <input type="text" id="ha_mqtt_username" name="ha_mqtt_username" placeholder="Optional">
                        <div class="help-text">Home Assistant MQTT Benutzername (Optional)</div>
                    </div>
                    
                    <div class="form-group">
                        <label for="ha_mqtt_password">HA MQTT Passwort:</label>
                        <input type="password" id="ha_mqtt_password" name="ha_mqtt_password" placeholder="Passwort">
                        <div class="help-text">Home Assistant MQTT Passwort (Leer lassen um nicht zu ändern)</div>
                    </div>
                    
                    <button type="submit" class="btn">💾 HA MQTT speichern</button>
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
        // Use server-provided ingress path from X-Ingress-Path header
        const INGRESS_PATH = '{{ ingress_path }}' || '';
        const BASE_URL = INGRESS_PATH || window.location.origin;
        console.log('Ingress path from server:', INGRESS_PATH);
        console.log('BASE_URL resolved:', BASE_URL);
        console.log('Current pathname:', window.location.pathname);
        console.log('Is embedded (iframe):', window.parent !== window);
        
        // HOME ASSISTANT INGRESS CACHE-BUSTING LÖSUNG
        function addCacheBuster(url) {
            const separator = url.includes('?') ? '&' : '?';
            return url + separator + 'cb=' + Date.now() + '&t=' + Math.random();
        }
        
        // Erkenne Home Assistant Ingress Environment  
        const isHomeAssistantIngress = window.location.pathname.includes('/api/hassio_ingress/') || 
                                      document.referrer.includes('homeassistant') || 
                                      window.parent !== window;
        
        if (isHomeAssistantIngress) {
            console.log('🏠 HOME ASSISTANT INGRESS ERKANNT - Cache-Busting aktiviert!');
            
            // Überschreibe fetch mit automatischem Cache-Busting
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (typeof url === 'string' && (url.startsWith('/api/') || url.startsWith(BASE_URL + '/api/'))) {
                    url = addCacheBuster(url);
                    console.log('⚙️ Cache-Buster URL:', url);
                }
                // Aggressive no-cache headers für Home Assistant
                options.cache = 'no-store';
                options.headers = {
                    ...options.headers,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Requested-With': 'XMLHttpRequest'
                };
                return originalFetch(url, options);
            };
        }
        
        // Simplified navigation for embedded mode
        const navigateTo = (path) => {
            const fullUrl = BASE_URL + path;
            console.log('Navigating to:', fullUrl);
            console.log('Path requested:', path);
            
            // Simple approach - just use window.location.href
            // This should work in both embedded and direct access
            window.location.href = fullUrl;
        };
        
        // DOM Elemente
        const settingsForm = document.getElementById('settingsForm');
        const haSettingsForm = document.getElementById('haSettingsForm');
        const alerts = document.getElementById('alerts');
        const connectionStatus = document.getElementById('connectionStatus');
        
        // Einstellungen laden
        async function loadSettings() {
            try {
                const response = await fetch(BASE_URL + '/api/settings');
                const settings = await response.json();
                
                // Formular mit aktuellen Werten füllen
                document.getElementById('mqtt_broker').value = settings.mqtt_broker || '';
                document.getElementById('mqtt_port').value = settings.mqtt_port || 1883;
                document.getElementById('mqtt_username').value = settings.mqtt_username || '';
                document.getElementById('mqtt_password').value = settings.mqtt_password || '';
                document.getElementById('base_topic').value = settings.base_topic || 'bssci';
                document.getElementById('auto_discovery').checked = settings.auto_discovery || false;
                
                // Home Assistant MQTT Felder füllen
                document.getElementById('ha_mqtt_broker').value = settings.ha_mqtt_broker || 'core-mosquitto';
                document.getElementById('ha_mqtt_port').value = settings.ha_mqtt_port || 1883;
                document.getElementById('ha_mqtt_username').value = settings.ha_mqtt_username || '';
                document.getElementById('ha_mqtt_password').value = settings.ha_mqtt_password || '';
                
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
                const response = await fetch(BASE_URL + '/api/settings', {
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
        
        // Home Assistant MQTT Einstellungen speichern
        haSettingsForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(haSettingsForm);
            const data = {
                ha_mqtt_broker: formData.get('ha_mqtt_broker'),
                ha_mqtt_port: formData.get('ha_mqtt_port'),
                ha_mqtt_username: formData.get('ha_mqtt_username'),
                ha_mqtt_password: formData.get('ha_mqtt_password')
            };
            
            try {
                const response = await fetch(BASE_URL + '/api/ha-settings', {
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
                showAlert('Fehler beim Speichern der HA MQTT Einstellungen', 'error');
                console.error('Fehler:', error);
            }
        });
        
        // Verbindungsstatus laden
        async function loadConnectionStatus() {
            try {
                const response = await fetch(BASE_URL + '/api/status');
                const status = await response.json();
                
                const mqttColor = status.mqtt_connected ? '#28a745' : '#dc3545';
                const mqttText = status.mqtt_connected ? 
                    `mioty MQTT: Verbunden (${status.mqtt_broker})` : 
                    'mioty MQTT: Getrennt';
                
                const haMqttColor = status.ha_mqtt_connected ? '#28a745' : '#dc3545';
                const haMqttText = status.ha_mqtt_connected ? 
                    `HA MQTT: Verbunden (${status.ha_mqtt_broker})` : 
                    `HA MQTT: Getrennt (${status.ha_mqtt_broker})`;
                
                connectionStatus.innerHTML = `
                    <div style="padding: 20px; background: #f8f9fa; border-radius: 8px;">
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 12px; height: 12px; background: #28a745; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>Web-GUI: Online</strong>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 12px; height: 12px; background: ${mqttColor}; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>${mqttText}</strong>
                        </div>
                        <div style="display: flex; align-items: center; margin-bottom: 10px;">
                            <div style="width: 12px; height: 12px; background: ${haMqttColor}; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>${haMqttText}</strong>
                        </div>
                        <div style="display: flex; align-items: center;">
                            <div style="width: 12px; height: 12px; background: #ffc107; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>Sensoren aktiv: ${status.sensor_count || 0}</strong>
                        </div>
                        <div style="display: flex; align-items: center; margin-top: 10px;">
                            <div style="width: 12px; height: 12px; background: #17a2b8; border-radius: 50%; margin-right: 10px;"></div>
                            <strong>Base Stations: ${status.basestation_count || 0}</strong>
                        </div>
                    </div>
                `;
                
            } catch (error) {
                connectionStatus.innerHTML = '<p>Fehler beim Laden des Verbindungsstatus.</p>';
                console.error('Fehler:', error);
            }
        }
        
        // Auto-refresh für Verbindungsstatus
        setInterval(loadConnectionStatus, 5000); // Alle 5 Sekunden
        
        // Initialisierung
        document.addEventListener('DOMContentLoaded', () => {
            loadSettings();
            loadConnectionStatus();
        });
    </script>
</body>
</html>
        '''
    
    def get_decoders_template(self) -> str:
        """Decoder-Verwaltungsseiten-Template."""
        return '''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mioty Application Center Decoder</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); min-height: 100vh; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; padding: 30px; text-align: center; }
        .nav { background: #6c757d; padding: 0; display: flex; justify-content: center; }
        .nav-item { color: white; text-decoration: none; padding: 15px 30px; display: block; transition: background-color 0.3s ease; }
        .nav-item:hover, .nav-item.active { background: #ff6b35; color: white; text-decoration: none; }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.2em; opacity: 0.9; }
        .content { padding: 30px; }
        .section { margin-bottom: 40px; }
        .section h2 { color: #333; border-bottom: 3px solid #ff6b35; padding-bottom: 10px; margin-bottom: 20px; }
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; font-weight: 600; margin-bottom: 5px; color: #555; }
        .form-group input[type="text"], .form-group textarea, .form-group select { width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 8px; font-size: 16px; transition: border-color 0.3s ease; }
        .form-group input:focus, .form-group textarea:focus, .form-group select:focus { outline: none; border-color: #ff6b35; }
        .form-group input[type="file"] { padding: 8px; border: 2px dashed #ddd; border-radius: 8px; background: #f8f9fa; }
        .btn { background: linear-gradient(135deg, #ff6b35 0%, #f7931e 100%); color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: transform 0.2s ease; margin-right: 10px; }
        .btn:hover { transform: translateY(-2px); }
        .btn-secondary { background: #6c757d; }
        .btn-danger { background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); }
        .btn-small { padding: 8px 16px; font-size: 14px; }
        .decoder-list { display: grid; gap: 20px; }
        .decoder-card { border: 2px solid #eee; border-radius: 12px; padding: 20px; transition: border-color 0.3s ease; background: #f8f9fa; }
        .decoder-card:hover { border-color: #ff6b35; }
        .decoder-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .decoder-name { font-size: 1.3em; font-weight: 600; color: #333; }
        .decoder-type { background: #ff6b35; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; text-transform: uppercase; }
        .decoder-info { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .info-item { display: flex; flex-direction: column; }
        .info-label { font-weight: 600; color: #666; font-size: 0.9em; margin-bottom: 5px; }
        .info-value { color: #333; }
        .assignment-section { background: white; border-radius: 8px; padding: 15px; margin-top: 15px; border-left: 4px solid #ff6b35; }
        .assignment-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #eee; }
        .assignment-item:last-child { border-bottom: none; }
        .test-result { margin-top: 15px; padding: 15px; border-radius: 8px; background: #f8f9fa; border-left: 4px solid #28a745; }
        .test-result.error { border-left-color: #dc3545; background: #f8d7da; }
        .alert { padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .alert-success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .alert-error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .loading { text-align: center; padding: 40px; color: #666; }
        .help-text { font-size: 0.9em; color: #666; margin-top: 5px; }
        .code { font-family: monospace; background: #f8f9fa; padding: 2px 4px; border-radius: 4px; color: #e83e8c; }
        .json-display { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 15px; font-family: monospace; font-size: 14px; overflow-x: auto; white-space: pre-wrap; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📝 mioty Application Center</h1>
            <p>Payload Decoder Verwaltung <span style="opacity: 0.6; font-size: 0.8em;">• powered by Sentinum</span></p>
        </div>
        <div class="nav">
            <a id="nav-sensors" href="#" class="nav-item" onclick="navigateTo('/')">📊 Sensoren</a>
            <a id="nav-decoders" href="#" class="nav-item active" onclick="navigateTo('/decoders')">📝 Decoder</a>
            <a id="nav-settings" href="#" class="nav-item" onclick="navigateTo('/settings')">⚙️ Einstellungen</a>
        </div>
        <div class="content">
            <div id="alerts"></div>
            <div class="section">
                <h2>📤 Decoder hochladen</h2>
                <form id="uploadForm" enctype="multipart/form-data">
                    <div class="form-group">
                        <label for="decoderFile">Decoder-Datei:</label>
                        <input type="file" id="decoderFile" name="file" accept=".js,.json" required>
                        <div class="help-text">Unterstützte Formate: <span class="code">.json</span> (mioty Blueprint) und <span class="code">.js</span> (Sentinum JavaScript)</div>
                    </div>
                    <button type="submit" class="btn">📤 Decoder hochladen</button>
                </form>
            </div>
            <div class="section">
                <h2>🧪 Decoder testen</h2>
                <form id="testForm">
                    <div class="form-group">
                        <label for="testDecoder">Decoder auswählen:</label>
                        <select id="testDecoder" name="decoder" required>
                            <option value="">-- Decoder auswählen --</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="testPayload">Test-Payload (Hex):</label>
                        <input type="text" id="testPayload" name="payload" placeholder="01A2B3C4 oder 01 A2 B3 C4" required>
                        <div class="help-text">Hex-Bytes getrennt durch Leerzeichen oder zusammen</div>
                    </div>
                    <button type="submit" class="btn">🧪 Test ausführen</button>
                </form>
                <div id="testResult"></div>
            </div>
            <div class="section">
                <h2>🔗 Sensor-Decoder Zuordnung</h2>
                <form id="assignForm">
                    <div class="form-group">
                        <label for="assignSensor">Sensor EUI:</label>
                        <input type="text" id="assignSensor" name="sensor_eui" placeholder="fca84a0300001234" pattern="[0-9a-fA-F]{16}" required>
                    </div>
                    <div class="form-group">
                        <label for="assignDecoder">Decoder auswählen:</label>
                        <select id="assignDecoder" name="decoder" required>
                            <option value="">-- Decoder auswählen --</option>
                        </select>
                    </div>
                    <button type="submit" class="btn">🔗 Decoder zuweisen</button>
                </form>
            </div>
            <div class="section">
                <h2>📚 Verfügbare Decoder</h2>
                <div id="decoderList" class="loading">Lade Decoder...</div>
            </div>
            <div class="section">
                <h2>📋 Aktuelle Zuweisungen</h2>
                <div id="assignmentList" class="loading">Lade Zuweisungen...</div>
            </div>
        </div>
    </div>
    <script>
        // Use server-provided ingress path from X-Ingress-Path header
        const INGRESS_PATH = '{{ ingress_path }}' || '';
        const BASE_URL = INGRESS_PATH || window.location.origin;
        console.log('Ingress path from server:', INGRESS_PATH);
        console.log('BASE_URL resolved:', BASE_URL);
        console.log('Current pathname:', window.location.pathname);
        console.log('Is embedded (iframe):', window.parent !== window);
        
        // HOME ASSISTANT INGRESS CACHE-BUSTING LÖSUNG
        function addCacheBuster(url) {
            const separator = url.includes('?') ? '&' : '?';
            return url + separator + 'cb=' + Date.now() + '&t=' + Math.random();
        }
        
        // Erkenne Home Assistant Ingress Environment  
        const isHomeAssistantIngress = window.location.pathname.includes('/api/hassio_ingress/') || 
                                      document.referrer.includes('homeassistant') || 
                                      window.parent !== window;
        
        if (isHomeAssistantIngress) {
            console.log('🏠 HOME ASSISTANT INGRESS ERKANNT - Cache-Busting aktiviert!');
            
            // Überschreibe fetch mit automatischem Cache-Busting
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (typeof url === 'string' && (url.startsWith('/api/') || url.startsWith(BASE_URL + '/api/'))) {
                    url = addCacheBuster(url);
                    console.log('⚙️ Cache-Buster URL:', url);
                }
                // Aggressive no-cache headers für Home Assistant
                options.cache = 'no-store';
                options.headers = {
                    ...options.headers,
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0',
                    'X-Requested-With': 'XMLHttpRequest'
                };
                return originalFetch(url, options);
            };
        }
        
        // Simplified navigation for embedded mode
        const navigateTo = (path) => {
            const fullUrl = BASE_URL + path;
            console.log('Navigating to:', fullUrl);
            console.log('Path requested:', path);
            
            // Simple approach - just use window.location.href
            // This should work in both embedded and direct access
            window.location.href = fullUrl;
        };
        
        const uploadForm = document.getElementById('uploadForm');
        const testForm = document.getElementById('testForm');
        const assignForm = document.getElementById('assignForm');
        const decoderList = document.getElementById('decoderList');
        const assignmentList = document.getElementById('assignmentList');
        const testResult = document.getElementById('testResult');
        const alerts = document.getElementById('alerts');
        let currentDecoders = [];
        let currentAssignments = {};
        
        async function loadDecoders() {
            try {
                const response = await fetch(BASE_URL + '/api/decoders');
                const data = await response.json();
                currentDecoders = data.decoders || [];
                currentAssignments = data.assignments || {};
                updateDecoderList();
                updateAssignmentList();
                updateDecoderSelects();
            } catch (error) {
                showAlert('Fehler beim Laden der Decoder', 'error');
            }
        }
        
        function updateDecoderList() {
            if (currentDecoders.length === 0) {
                decoderList.innerHTML = '<p>Noch keine Decoder hochgeladen.</p>';
                return;
            }
            let html = '<div class="decoder-list">';
            for (const decoder of currentDecoders) {
                html += createDecoderCard(decoder);
            }
            html += '</div>';
            decoderList.innerHTML = html;
        }
        
        function createDecoderCard(decoder) {
            const createdDate = new Date(decoder.created_at * 1000).toLocaleString();
            const assignedSensors = Object.entries(currentAssignments).filter(([eui, assignment]) => assignment.decoder_name === decoder.name).map(([eui, assignment]) => eui);
            return `<div class="decoder-card"><div class="decoder-header"><div class="decoder-name">${decoder.display_name}</div><div class="decoder-type">${decoder.type}</div></div><div class="decoder-info"><div class="info-item"><div class="info-label">Version</div><div class="info-value">${decoder.version}</div></div><div class="info-item"><div class="info-label">Beschreibung</div><div class="info-value">${decoder.description}</div></div><div class="info-item"><div class="info-label">Erstellt am</div><div class="info-value">${createdDate}</div></div><div class="info-item"><div class="info-label">Zugewiesene Sensoren</div><div class="info-value">${assignedSensors.length}</div></div></div>${assignedSensors.length > 0 ? `<div class="assignment-section"><strong>Zugewiesene Sensoren:</strong>${assignedSensors.map(eui => `<div class="assignment-item"><span class="code">${eui}</span><button class="btn btn-small btn-secondary" onclick="unassignDecoder('${eui}')">Entfernen</button></div>`).join('')}</div>` : ''}<div style="margin-top: 15px;"><button class="btn btn-small" onclick="testDecoderQuick('${decoder.name}')">🧪 Schnelltest</button><button class="btn btn-small btn-danger" onclick="deleteDecoder('${decoder.name}')">🗑️ Löschen</button></div></div>`;
        }
        
        function updateAssignmentList() {
            const assignments = Object.entries(currentAssignments);
            if (assignments.length === 0) {
                assignmentList.innerHTML = '<p>Keine Decoder-Zuweisungen vorhanden.</p>';
                return;
            }
            let html = '<div style="background: white; border-radius: 8px; padding: 20px;">';
            for (const [sensorEui, assignment] of assignments) {
                const assignedDate = new Date(assignment.assigned_at * 1000).toLocaleString();
                html += `<div class="assignment-item"><div><strong class="code">${sensorEui}</strong><br><small>Decoder: ${assignment.decoder_name}</small><br><small>Zugewiesen: ${assignedDate}</small></div><button class="btn btn-small btn-secondary" onclick="unassignDecoder('${sensorEui}')">Entfernen</button></div>`;
            }
            html += '</div>';
            assignmentList.innerHTML = html;
        }
        
        function updateDecoderSelects() {
            const selects = [document.getElementById('testDecoder'), document.getElementById('assignDecoder')];
            selects.forEach(select => {
                const currentValue = select.value;
                while (select.options.length > 1) { select.remove(1); }
                for (const decoder of currentDecoders) {
                    const option = new Option(decoder.display_name, decoder.name);
                    select.add(option);
                }
                select.value = currentValue;
            });
        }
        
        function showAlert(message, type = 'success') {
            const alert = document.createElement('div');
            alert.className = `alert alert-${type}`;
            alert.textContent = message;
            alerts.appendChild(alert);
            setTimeout(() => { alert.remove(); }, 5000);
        }
        
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(uploadForm);
            try {
                const response = await fetch(BASE_URL + '/api/decoder/upload', { method: 'POST', body: formData });
                const result = await response.json();
                if (response.ok) {
                    showAlert(result.message, 'success');
                    uploadForm.reset();
                    loadDecoders();
                } else {
                    showAlert(result.error, 'error');
                }
            } catch (error) {
                showAlert('Fehler beim Hochladen des Decoders', 'error');
            }
        });
        
        testForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(testForm);
            const data = { decoder_name: formData.get('decoder'), test_payload: formData.get('payload') };
            try {
                const response = await fetch(BASE_URL + '/api/decoder/test', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                const result = await response.json();
                displayTestResult(result);
            } catch (error) {
                displayTestResult({ decoded: false, reason: 'Netzwerk-Fehler', raw_data: [] });
            }
        });
        
        function displayTestResult(result) {
            const isSuccess = result.decoded;
            let html = `<div class="test-result ${isSuccess ? '' : 'error'}"><h4>${isSuccess ? '✅ Dekodierung erfolgreich' : '❌ Dekodierung fehlgeschlagen'}</h4>`;
            if (isSuccess) {
                html += `<p><strong>Decoder:</strong> ${result.decoder_name || 'Unbekannt'}</p><p><strong>Typ:</strong> ${result.decoder_type || 'Unbekannt'}</p><h5>Dekodierte Daten:</h5><div class="json-display">${JSON.stringify(result.data, null, 2)}</div>`;
                if (result.warning) { html += `<p><small><em>⚠️ ${result.warning}</em></small></p>`; }
            } else {
                html += `<p><strong>Grund:</strong> ${result.reason || 'Unbekannt'}</p>`;
            }
            html += `<p><strong>Raw Data:</strong> <span class="code">[${result.raw_data?.join(', ') || 'Keine Daten'}]</span></p></div>`;
            testResult.innerHTML = html;
        }
        
        assignForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(assignForm);
            const data = { sensor_eui: formData.get('sensor_eui'), decoder_name: formData.get('decoder') };
            try {
                const response = await fetch(BASE_URL + '/api/decoder/assign', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data) });
                const result = await response.json();
                if (response.ok) {
                    showAlert(result.message, 'success');
                    assignForm.reset();
                    loadDecoders();
                } else {
                    showAlert(result.error, 'error');
                }
            } catch (error) {
                showAlert('Fehler beim Zuweisen des Decoders', 'error');
            }
        });
        
        async function unassignDecoder(sensorEui) {
            if (!confirm(`Decoder-Zuweisung für Sensor ${sensorEui} wirklich entfernen?`)) { return; }
            try {
                const response = await fetch(BASE_URL + '/api/decoder/unassign', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sensor_eui: sensorEui}) });
                const result = await response.json();
                if (response.ok) {
                    showAlert(result.message, 'success');
                    loadDecoders();
                } else {
                    showAlert(result.error, 'error');
                }
            } catch (error) {
                showAlert('Fehler beim Entfernen der Decoder-Zuweisung', 'error');
            }
        }
        
        async function deleteDecoder(decoderName) {
            if (!confirm(`Decoder "${decoderName}" wirklich löschen? Alle Zuweisungen werden entfernt.`)) { return; }
            try {
                const response = await fetch(BASE_URL + '/api/decoder/delete', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({decoder_name: decoderName}) });
                const result = await response.json();
                if (response.ok) {
                    showAlert(result.message, 'success');
                    loadDecoders();
                } else {
                    showAlert(result.error, 'error');
                }
            } catch (error) {
                showAlert('Fehler beim Löschen des Decoders', 'error');
            }
        }
        
        function testDecoderQuick(decoderName) {
            document.getElementById('testDecoder').value = decoderName;
            document.getElementById('testPayload').value = '01 A2 03 B4';
            document.querySelector('#testForm').scrollIntoView({behavior: 'smooth'});
        }
        
        document.addEventListener('DOMContentLoaded', () => {
            loadDecoders();
            setInterval(loadDecoders, 30000);
        });
    </script>
    
</body>
</html>'''