"""
Payload Decoder Engine für mioty Application Center
Unterstützt mioty Blueprint Decoder und Sentinum .js Files
"""

import os
import json
import logging
import re
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Union
from pathlib import Path


class PayloadDecoder:
    """Payload Decoder Engine für verschiedene Decoder-Formate."""
    
    def __init__(self, decoder_dir: str = "/data/decoders"):
        """Initialisiere Payload Decoder."""
        self.decoder_dir = Path(decoder_dir)
        self.decoder_dir.mkdir(parents=True, exist_ok=True)
        
        # Decoder Registry
        self.decoders = {}  # sensor_eui -> decoder_info
        self.decoder_files = {}  # decoder_name -> file_info
        
        self.load_decoders()
        logging.info("Payload Decoder Engine initialisiert")
    
    def load_decoders(self):
        """Lade alle verfügbaren Decoder."""
        try:
            # Lade Decoder-Registry
            registry_file = self.decoder_dir / "decoder_registry.json"
            if registry_file.exists():
                with open(registry_file, 'r') as f:
                    data = json.load(f)
                    self.decoders = data.get('sensor_decoders', {})
                    self.decoder_files = data.get('decoder_files', {})
            
            # Scanne Decoder-Verzeichnis
            self._scan_decoder_directory()
            
        except Exception as e:
            logging.error(f"Fehler beim Laden der Decoder: {e}")
    
    def save_decoders(self):
        """Speichere Decoder-Registry."""
        try:
            registry_file = self.decoder_dir / "decoder_registry.json"
            with open(registry_file, 'w') as f:
                json.dump({
                    'sensor_decoders': self.decoders,
                    'decoder_files': self.decoder_files
                }, f, indent=2)
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Decoder-Registry: {e}")
            return False
    
    def _scan_decoder_directory(self):
        """Scanne Decoder-Verzeichnis nach neuen Dateien."""
        for file_path in self.decoder_dir.glob("*"):
            if file_path.is_file() and file_path.suffix in ['.js', '.json']:
                decoder_name = file_path.stem
                if decoder_name not in self.decoder_files:
                    # Neuer Decoder gefunden, analysiere ihn
                    decoder_info = self._analyze_decoder_file(file_path)
                    if decoder_info:
                        self.decoder_files[decoder_name] = decoder_info
    
    def _analyze_decoder_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Analysiere Decoder-Datei und extrahiere Metadaten."""
        try:
            if file_path.suffix == '.json':
                # mioty Blueprint Decoder
                return self._analyze_blueprint_decoder(file_path)
            elif file_path.suffix == '.js':
                # Sentinum JavaScript Decoder
                return self._analyze_js_decoder(file_path)
        except Exception as e:
            logging.error(f"Fehler beim Analysieren der Decoder-Datei {file_path}: {e}")
        return None
    
    def _analyze_blueprint_decoder(self, file_path: Path) -> Dict[str, Any]:
        """Analysiere mioty Blueprint Decoder."""
        with open(file_path, 'r') as f:
            blueprint = json.load(f)
        
        return {
            'type': 'blueprint',
            'file_path': str(file_path),
            'name': blueprint.get('name', file_path.stem),
            'version': blueprint.get('version', '1.0'),
            'description': blueprint.get('description', 'mioty Blueprint Decoder'),
            'supported_devices': blueprint.get('devices', []),
            'payload_format': blueprint.get('payload', {}),
            'created_at': file_path.stat().st_mtime
        }
    
    def _analyze_js_decoder(self, file_path: Path) -> Dict[str, Any]:
        """Analysiere Sentinum JavaScript Decoder."""
        with open(file_path, 'r') as f:
            js_content = f.read()
        
        # Extrahiere Metadaten aus Kommentaren
        name_match = re.search(r'//\s*@name\s+(.+)', js_content)
        version_match = re.search(r'//\s*@version\s+(.+)', js_content)
        desc_match = re.search(r'//\s*@description\s+(.+)', js_content)
        
        return {
            'type': 'javascript',
            'file_path': str(file_path),
            'name': name_match.group(1) if name_match else file_path.stem,
            'version': version_match.group(1) if version_match else '1.0',
            'description': desc_match.group(1) if desc_match else 'Sentinum JavaScript Decoder',
            'supported_devices': [],  # Kann aus JS Code extrahiert werden
            'created_at': file_path.stat().st_mtime
        }
    
    def upload_decoder(self, filename: str, content: Union[str, bytes]) -> bool:
        """Lade neue Decoder-Datei hoch."""
        try:
            file_path = self.decoder_dir / filename
            
            # Schreibe Datei
            if isinstance(content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(file_path, 'w') as f:
                    f.write(content)
            
            # Analysiere neue Datei
            decoder_info = self._analyze_decoder_file(file_path)
            if decoder_info:
                self.decoder_files[file_path.stem] = decoder_info
                self.save_decoders()
                logging.info(f"Decoder {filename} erfolgreich hochgeladen")
                return True
            
        except Exception as e:
            logging.error(f"Fehler beim Hochladen des Decoders {filename}: {e}")
        return False
    
    def assign_decoder(self, sensor_eui: str, decoder_name: str) -> bool:
        """Weise Decoder einem Sensor zu."""
        if decoder_name not in self.decoder_files:
            logging.error(f"Decoder {decoder_name} nicht gefunden")
            return False
        
        self.decoders[sensor_eui] = {
            'decoder_name': decoder_name,
            'assigned_at': time.time()
        }
        
        return self.save_decoders()
    
    def remove_decoder_assignment(self, sensor_eui: str) -> bool:
        """Entferne Decoder-Zuweisung für Sensor."""
        if sensor_eui in self.decoders:
            del self.decoders[sensor_eui]
            return self.save_decoders()
        return True
    
    def decode_payload(self, sensor_eui: str, payload_bytes: List[int], 
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Dekodiere Payload für spezifischen Sensor."""
        if sensor_eui not in self.decoders:
            return {
                'decoded': False,
                'reason': 'No decoder assigned',
                'raw_data': payload_bytes
            }
        
        decoder_assignment = self.decoders[sensor_eui]
        decoder_name = decoder_assignment['decoder_name']
        
        if decoder_name not in self.decoder_files:
            return {
                'decoded': False,
                'reason': 'Decoder file not found',
                'raw_data': payload_bytes
            }
        
        decoder_info = self.decoder_files[decoder_name]
        
        try:
            if decoder_info['type'] == 'blueprint':
                return self._decode_with_blueprint(decoder_info, payload_bytes, metadata)
            elif decoder_info['type'] == 'javascript':
                return self._decode_with_javascript(decoder_info, payload_bytes, metadata)
        except Exception as e:
            logging.error(f"Fehler beim Dekodieren für Sensor {sensor_eui}: {e}")
            return {
                'decoded': False,
                'reason': f'Decoding error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _decode_with_blueprint(self, decoder_info: Dict[str, Any], 
                              payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Dekodiere mit mioty Blueprint."""
        try:
            # Lade Blueprint
            with open(decoder_info['file_path'], 'r') as f:
                blueprint = json.load(f)
            
            payload_config = blueprint.get('payload', {})
            decoded_data = {}
            
            # Einfache Blueprint-Interpretation
            byte_index = 0
            for field_name, field_config in payload_config.items():
                if byte_index >= len(payload_bytes):
                    break
                
                field_type = field_config.get('type', 'uint8')
                field_length = field_config.get('length', 1)
                
                # Extrahiere Bytes für dieses Feld
                field_bytes = payload_bytes[byte_index:byte_index + field_length]
                
                # Konvertiere basierend auf Typ
                if field_type == 'uint8' and field_length == 1:
                    value = field_bytes[0] if field_bytes else 0
                elif field_type == 'uint16' and field_length == 2:
                    value = (field_bytes[0] << 8 | field_bytes[1]) if len(field_bytes) == 2 else 0
                elif field_type == 'float' and field_length == 4:
                    # Vereinfachte Float-Interpretation
                    import struct
                    if len(field_bytes) == 4:
                        value = struct.unpack('>f', bytes(field_bytes))[0]
                    else:
                        value = 0.0
                else:
                    value = field_bytes
                
                # Skalierung anwenden
                scale = field_config.get('scale', 1.0)
                offset = field_config.get('offset', 0.0)
                if isinstance(value, (int, float)):
                    value = value * scale + offset
                
                decoded_data[field_name] = {
                    'value': value,
                    'unit': field_config.get('unit', ''),
                    'description': field_config.get('description', field_name)
                }
                
                byte_index += field_length
            
            return {
                'decoded': True,
                'decoder_type': 'blueprint',
                'decoder_name': decoder_info['name'],
                'data': decoded_data,
                'raw_data': payload_bytes
            }
            
        except Exception as e:
            raise Exception(f"Blueprint decoding error: {str(e)}")
    
    def _decode_with_javascript(self, decoder_info: Dict[str, Any], 
                               payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Dekodiere mit Sentinum JavaScript."""
        try:
            # Erstelle temporäre Node.js Umgebung
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Kopiere Decoder-Datei
                decoder_file = temp_path / "decoder.js"
                with open(decoder_info['file_path'], 'r') as src:
                    decoder_content = src.read()
                
                # Erstelle Wrapper für Node.js Ausführung
                wrapper_content = f"""
const decoder = require('./decoder.js');

// Input-Daten
const payload = {json.dumps(payload_bytes)};
const metadata = {json.dumps(metadata or {})};

try {{
    // Führe Dekodierung aus
    let result;
    if (typeof decoder.decode === 'function') {{
        result = decoder.decode(payload, metadata);
    }} else if (typeof decoder === 'function') {{
        result = decoder(payload, metadata);
    }} else {{
        throw new Error('No decode function found');
    }}
    
    console.log(JSON.stringify({{
        decoded: true,
        decoder_type: 'javascript',
        decoder_name: '{decoder_info["name"]}',
        data: result,
        raw_data: payload
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{
        decoded: false,
        reason: 'JavaScript execution error: ' + error.message,
        raw_data: payload
    }}));
}}
"""
                
                # Schreibe Dateien
                with open(decoder_file, 'w') as f:
                    f.write(decoder_content)
                
                wrapper_file = temp_path / "wrapper.js"
                with open(wrapper_file, 'w') as f:
                    f.write(wrapper_content)
                
                # Führe Node.js aus
                try:
                    result = subprocess.run(
                        ['node', str(wrapper_file)],
                        capture_output=True,
                        text=True,
                        timeout=5,  # 5 Sekunden Timeout
                        cwd=temp_dir
                    )
                    
                    if result.returncode == 0:
                        return json.loads(result.stdout)
                    else:
                        raise Exception(f"Node.js execution failed: {result.stderr}")
                        
                except FileNotFoundError:
                    # Node.js nicht verfügbar, verwende vereinfachte JS Interpretation
                    return self._simple_js_decode(decoder_content, payload_bytes, metadata)
                
        except Exception as e:
            raise Exception(f"JavaScript decoding error: {str(e)}")
    
    def _simple_js_decode(self, js_content: str, payload_bytes: List[int], 
                         metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Vereinfachte JavaScript Dekodierung ohne Node.js."""
        # Fallback: Einfache Pattern-Matching für häufige Sentinum-Muster
        logging.warning("Node.js nicht verfügbar, verwende vereinfachte JS Dekodierung")
        
        # Prüfe auf Febris-Decoder basierend auf JS-Content
        if 'febris' in js_content.lower() or 'base_id' in js_content:
            return self._decode_febris_python(payload_bytes, metadata)
        
        # Suche nach Temperatur/Humidity Pattern
        temp_pattern = r'temperature.*?(\d+(?:\.\d+)?)'
        humidity_pattern = r'humidity.*?(\d+(?:\.\d+)?)'
        
        decoded_data = {}
        
        # Einfache Heuristiken für common sensor data
        if len(payload_bytes) >= 2:
            # Typisches Temp/Humidity Format
            temp_raw = (payload_bytes[0] << 8 | payload_bytes[1]) if len(payload_bytes) >= 2 else 0
            temp = (temp_raw - 400) / 10.0  # Häufiges Sentinum-Format
            
            decoded_data['temperature'] = {
                'value': round(temp, 1),
                'unit': '°C',
                'description': 'Temperature'
            }
        
        if len(payload_bytes) >= 4:
            humidity_raw = (payload_bytes[2] << 8 | payload_bytes[3]) if len(payload_bytes) >= 4 else 0
            humidity = humidity_raw / 100.0
            
            decoded_data['humidity'] = {
                'value': round(humidity, 1),
                'unit': '%',
                'description': 'Relative Humidity'
            }
        
        return {
            'decoded': True,
            'decoder_type': 'javascript_simplified',
            'decoder_name': 'Simple JS Decoder',
            'data': decoded_data,
            'raw_data': payload_bytes,
            'warning': 'Simplified decoding used (Node.js not available)'
        }
    
    def _decode_febris_python(self, payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Python-Implementierung des Febris TH Decoders."""
        try:
            bytes_data = payload_bytes
            decoded = {}
            
            # Decode header
            decoded['base_id'] = bytes_data[0] >> 4
            decoded['major_version'] = bytes_data[0] & 0x0F
            decoded['minor_version'] = bytes_data[1] >> 4
            decoded['product_version'] = bytes_data[1] & 0x0F
            decoded['up_cnt'] = bytes_data[2]
            decoded['battery_voltage'] = ((bytes_data[3] << 8) | bytes_data[4]) / 1000.0
            decoded['internal_temperature'] = ((bytes_data[5] << 8) | bytes_data[6]) / 10.0 - 100.0
            
            it = 7
            
            if decoded['minor_version'] >= 3:
                # Luftfeuchte ist bei allen Varianten enthalten  
                decoded['humidity'] = bytes_data[it]
                it += 1
                
                if decoded['product_version'] & 0x01:  # Co2 und Druck enthalten
                    decoded['pressure'] = (bytes_data[it] << 8) | bytes_data[it + 1]
                    it += 2
                    decoded['co2_ppm'] = (bytes_data[it] << 8) | bytes_data[it + 1]
                    it += 2
                else:
                    it += 4  # Werte überspringen
                
                decoded['alarm'] = bytes_data[it]
                it += 1
                
                # FIFO Werte wegwerfen
                fifo_size = bytes_data[it] if it < len(bytes_data) else 0
                it += 2 + fifo_size * 7
                
                # Taupunkt
                if it + 1 < len(bytes_data):
                    decoded['dew_point'] = ((bytes_data[it] << 8) | bytes_data[it + 1]) / 10.0 - 100.0
                    it += 2
                
                # Wandtemperatur und Feuchte
                if decoded['product_version'] & 0x04:
                    if it + 4 < len(bytes_data):
                        decoded['wall_temperature'] = ((bytes_data[it] << 8) | bytes_data[it + 1]) / 10.0 - 100.0
                        it += 2
                        decoded['therm_temperature'] = ((bytes_data[it] << 8) | bytes_data[it + 1]) / 10.0 - 100.0
                        it += 2
                        decoded['wall_humidity'] = bytes_data[it]
                        it += 1
                        
            # Konvertiere zu erwartetes Format
            formatted_data = {}
            
            if 'battery_voltage' in decoded:
                formatted_data['battery_voltage'] = {
                    'value': round(decoded['battery_voltage'], 2),
                    'unit': 'V',
                    'description': 'Battery Voltage'
                }
                
            if 'humidity' in decoded:
                formatted_data['humidity'] = {
                    'value': round(decoded['humidity'], 1),
                    'unit': '%RH',
                    'description': 'Relative Humidity'
                }
                
            if 'base_id' in decoded:
                formatted_data['base_id'] = {
                    'value': decoded['base_id'],
                    'unit': '',
                    'description': 'Base ID'
                }
                
            if 'major_version' in decoded:
                formatted_data['major_version'] = {
                    'value': decoded['major_version'],
                    'unit': '',
                    'description': 'Major Version'
                }
                
            if 'minor_version' in decoded:
                formatted_data['minor_version'] = {
                    'value': decoded['minor_version'],
                    'unit': '',
                    'description': 'Minor Version'
                }
                
            if 'product_version' in decoded:
                formatted_data['product_version'] = {
                    'value': decoded['product_version'],
                    'unit': '',
                    'description': 'Product Version'
                }
                
            if 'up_cnt' in decoded:
                formatted_data['up_cnt'] = {
                    'value': decoded['up_cnt'],
                    'unit': '',
                    'description': 'Up Count'
                }
                
            if 'internal_temperature' in decoded:
                formatted_data['internal_temperature'] = {
                    'value': round(decoded['internal_temperature'], 1),
                    'unit': '°C',
                    'description': 'Internal Temperature'
                }
                
            if 'alarm' in decoded:
                formatted_data['alarm'] = {
                    'value': decoded['alarm'],
                    'unit': '',
                    'description': 'Alarm'
                }
                
            if 'dew_point' in decoded:
                formatted_data['dew_point'] = {
                    'value': round(decoded['dew_point'], 1),
                    'unit': '°C',
                    'description': 'Dew Point'
                }
            
            return {
                'decoded': True,
                'decoder_type': 'febris_python',
                'decoder_name': 'Febris TH (Python)',
                'data': formatted_data,
                'raw_data': payload_bytes
            }
            
        except Exception as e:
            logging.error(f"Fehler beim Febris Python Decoding: {e}")
            return {
                'decoded': False,
                'reason': f'Febris Python decoding error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def get_available_decoders(self) -> Dict[str, Any]:
        """Gib alle verfügbaren Decoder zurück."""
        return self.decoder_files.copy()
    
    def get_sensor_decoder_assignments(self) -> Dict[str, Any]:
        """Gib alle Sensor-Decoder Zuweisungen zurück."""
        return self.decoders.copy()
    
    def delete_decoder(self, decoder_name: str) -> bool:
        """Lösche Decoder-Datei und Zuweisungen."""
        if decoder_name not in self.decoder_files:
            return False
        
        try:
            # Lösche Datei
            file_path = Path(self.decoder_files[decoder_name]['file_path'])
            if file_path.exists():
                file_path.unlink()
            
            # Entferne aus Registry
            del self.decoder_files[decoder_name]
            
            # Entferne alle Sensor-Zuweisungen zu diesem Decoder
            to_remove = [eui for eui, assignment in self.decoders.items() 
                        if assignment['decoder_name'] == decoder_name]
            for eui in to_remove:
                del self.decoders[eui]
            
            return self.save_decoders()
            
        except Exception as e:
            logging.error(f"Fehler beim Löschen des Decoders {decoder_name}: {e}")
            return False


# Für Module Import
import time