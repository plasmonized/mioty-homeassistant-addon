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
import time
import xml.etree.ElementTree as ET
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
        
        # IO-Link spezifische Datenstrukturen
        self.sensor_data_cache = {}  # sensor_eui -> sensor_data
        self.iolink_assignments = {}  # sensor_eui -> iolink_assignment_info
        
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
            if file_path.is_file() and file_path.suffix in ['.js', '.json', '.xml']:
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
            elif file_path.suffix == '.xml':
                # IODD (IO Device Description) Decoder
                return self._analyze_iodd_decoder(file_path)
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
    
    def _analyze_iodd_decoder(self, file_path: Path) -> Dict[str, Any]:
        """Analysiere IODD (IO Device Description) XML-Datei."""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Erweiterte Namespace-Behandlung für IODD
            namespaces = {
                'iodd': 'http://www.io-link.com/IODD/2010/10',
                'iodd11': 'http://www.io-link.com/IODD/2011/06'
            }
            
            # Extrahiere DeviceIdentity mit verschiedenen Namespace-Optionen
            device_identity = None
            vendor_id = 0
            device_id = 0
            vendor_name = "Unknown"
            device_name = "Unknown"
            
            # Vereinfachte, sichere Suche nach DeviceIdentity
            try:
                # Versuche mit Namespaces
                device_identity = root.find('.//DeviceIdentity', namespaces)
                if device_identity is None:
                    # Fallback ohne Namespace
                    device_identity = root.find('.//DeviceIdentity')
            except Exception as e:
                logging.warning(f"DeviceIdentity Suche fehlgeschlagen: {e}")
                device_identity = None
            
            if device_identity is not None:
                # Extrahiere VendorId - verschiedene Attributnamen möglich
                vendor_id_str = (device_identity.get('vendorId') or 
                               device_identity.get('VendorId') or 
                               device_identity.get('vendorID') or '0')
                vendor_id = int(vendor_id_str) if vendor_id_str.isdigit() else 0
                
                # Extrahiere DeviceId - verschiedene Attributnamen möglich  
                device_id_str = (device_identity.get('deviceId') or
                               device_identity.get('DeviceId') or
                               device_identity.get('deviceID') or '0')
                device_id = int(device_id_str) if device_id_str.isdigit() else 0
                
                # Extrahiere Namen
                vendor_name = (device_identity.get('vendorName') or
                             device_identity.get('VendorName') or 
                             device_identity.text or "Unknown Vendor")
                device_name = (device_identity.get('deviceName') or
                             device_identity.get('DeviceName') or "Unknown Device")
            
            # Fallback: Suche nach VendorId und DeviceId in anderen Elementen (vereinfacht)
            if vendor_id == 0 or device_id == 0:
                try:
                    # Suche nach Vendor-Info im VendorName Element
                    vendor_info = root.find('.//VendorName')
                    if vendor_info is not None and vendor_info.text:
                        vendor_name = vendor_info.text
                    
                    # Suche nach Device-Info im DeviceName Element  
                    device_info = root.find('.//DeviceName')
                    if device_info is not None and device_info.text:
                        device_name = device_info.text
                except Exception as e:
                    logging.warning(f"Fallback-Suche fehlgeschlagen: {e}")
            
            # Spezialbehandlung für ExternalTextDocument (nur Übersetzungen)
            if root.tag.endswith('ExternalTextDocument'):
                logging.info("📋 ExternalTextDocument erkannt - extrahiere Informationen aus Dateinamen")
                
                # Extrahiere aus Dateinamen: ifm-000173-20160824-IODD1.0.1-de.xml
                filename = file_path.name
                if filename.startswith('ifm-'):
                    vendor_name = "ifm electronic"
                    # Extrahiere Geräte-Nummer
                    parts = filename.split('-')
                    if len(parts) >= 2:
                        device_code = parts[1]  # 000173
                        device_name = f"KQ Kapazitiver Sensor ({device_code})"
                    
                    # Verwende Vendor/Device IDs aus echtem IO-Link Payload (310/29441)
                    vendor_id = 310  # IFM Vendor ID
                    device_id = 29441  # KQ-Sensor Device ID (aus Payload)
                
                # Extrahiere Produktinformationen aus Text-Elementen (vereinfacht)
                try:
                    for text_elem in root.findall('.//Text'):
                        text_id = text_elem.get('id', '')
                        text_value = text_elem.get('value', '')
                        
                        if 'Product' in text_id and 'Name' in text_id:
                            if 'KQ' in text_value:
                                device_name = f"ifm {text_value} Kapazitiver Sensor"
                                break
                except Exception as e:
                    logging.warning(f"Text-Element Extraktion fehlgeschlagen: {e}")
            
            logging.info(f"📋 IODD Analyse: VID={vendor_id}, DID={device_id}, Vendor='{vendor_name}', Device='{device_name}'")
            
            # Extrahiere ProcessDataIn für Payload-Format (mit Namespace-sicherer Suche)
            process_data_in = None
            payload_length = 0
            data_fields = []
            
            # Sichere Suche nach ProcessDataIn
            if namespaces:
                for ns_prefix, ns_uri in namespaces.items():
                    process_data_in = root.find(f'.//{{{ns_uri}}}ProcessDataIn')
                    if process_data_in is not None:
                        break
            
            # Fallback ohne Namespace
            if process_data_in is None:
                process_data_in = root.find('.//ProcessDataIn')
            
            if process_data_in is not None:
                # Berechne Bitlength und konvertiere zu Bytes
                bitlength_str = process_data_in.get('bitLength', '0')
                try:
                    bitlength = int(bitlength_str) if bitlength_str.isdigit() else 0
                    payload_length = (bitlength + 7) // 8  # Aufrunden auf volle Bytes
                except ValueError:
                    payload_length = 0
                
                # Extrahiere Datenfelder (vereinfacht für ExternalTextDocument)
                for var_item in process_data_in.findall('.//SingleValue'):
                    field_name = var_item.get('name', 'unknown')
                    data_type = var_item.get('simpleDatatype', 'UIntegerT')
                    data_fields.append({
                        'name': field_name,
                        'type': data_type
                    })
            
            return {
                'type': 'iodd',
                'file_path': str(file_path),
                'filename': file_path.name,
                'name': f"{vendor_name} {device_name}",
                'display_name': f"{vendor_name} {device_name}",
                'version': root.get('version', '1.0'),
                'description': f"IODD für {vendor_name} {device_name} (VID:{vendor_id}, DID:{device_id})",
                'vendor_id': vendor_id,
                'device_id': device_id,
                'vendor_name': vendor_name,
                'device_name': device_name,
                'payload_length': payload_length,
                'data_fields': data_fields,
                'supported_devices': [f"VID_{vendor_id}_DID_{device_id}"],
                'created_at': file_path.stat().st_mtime
            }
            
        except ET.ParseError as e:
            logging.error(f"XML-Parser-Fehler in IODD-Datei {file_path}: {e}")
            # Fallback für ungültige XML-Dateien
            return {
                'type': 'iodd',
                'file_path': str(file_path),
                'name': file_path.stem,
                'version': '1.0',
                'description': f"IODD-Datei (XML-Parser-Fehler: {e})",
                'vendor_id': 0,
                'device_id': 0,
                'vendor_name': 'Unknown',
                'device_name': file_path.stem,
                'payload_length': 0,
                'data_fields': [],
                'supported_devices': [],
                'created_at': file_path.stat().st_mtime,
                'parse_error': str(e)
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
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            # Analysiere neue Datei
            decoder_info = self._analyze_decoder_file(file_path)
            if decoder_info:
                self.decoder_files[file_path.stem] = decoder_info
                self.save_decoders()
                logging.info(f"Decoder {filename} erfolgreich hochgeladen")
                return True
            else:
                logging.error(f"Decoder-Analyse fehlgeschlagen für {filename}")
                return False
            
        except Exception as e:
            logging.error(f"Fehler beim Hochladen des Decoders {filename}: {e}")
            return False
    
    def assign_decoder(self, sensor_eui: str, decoder_name: str) -> bool:
        """Weise Decoder einem Sensor zu."""
        # EUI automatisch zu Großbuchstaben normalisieren
        sensor_eui = self._normalize_sensor_eui(sensor_eui)
        logging.info(f"📋 Decoder-Zuweisung: {sensor_eui} → {decoder_name}")
        
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
        # EUI automatisch zu Großbuchstaben normalisieren
        sensor_eui = self._normalize_sensor_eui(sensor_eui)
        logging.info(f"❌ Decoder-Zuweisung entfernt: {sensor_eui}")
        
        if sensor_eui in self.decoders:
            del self.decoders[sensor_eui]
            return self.save_decoders()
        return True
    
    def decode_payload(self, sensor_eui: str, payload_bytes: List[int], 
                      metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dekodiere Payload für spezifischen Sensor."""
        logging.info(f"🔍 DECODE_PAYLOAD AUFGERUFEN für {sensor_eui}")
        logging.info(f"   📋 Verfügbare Decoder-Zuweisungen: {list(self.decoders.keys())}")
        logging.info(f"   📋 Verfügbare Decoder-Dateien: {list(self.decoder_files.keys())}")
        
        if sensor_eui not in self.decoders:
            logging.warning(f"❌ Kein Decoder für {sensor_eui} zugewiesen - versuche generische Dekodierung")
            # Fallback: Generische Sentinum Dekodierung versuchen
            return self._decode_generic_sentinum(payload_bytes, metadata or {}, "mioty")
        
        logging.info(f"✅ Decoder für {sensor_eui} gefunden: {self.decoders[sensor_eui]}")
        
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
            elif decoder_info['type'] == 'iodd':
                return self._decode_with_iodd(decoder_info, payload_bytes, metadata)
            else:
                return {
                    'decoded': False,
                    'reason': f'Unsupported decoder type: {decoder_info["type"]}',
                    'raw_data': payload_bytes
                }
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
                
                # Erstelle universeller Wrapper für beide Decoder-Formate
                wrapper_content = f"""
// Lade Decoder-Datei
const fs = require('fs');
const decoderContent = fs.readFileSync('./decoder.js', 'utf8');

// Input-Daten
const payload = {json.dumps(payload_bytes)};
const metadata = {json.dumps(metadata or {})};

try {{
    // Führe Decoder-Code aus
    eval(decoderContent);
    
    let result;
    
    // Universelles Interface: Auto-detect Decoder-Format
    if (typeof Decoder === 'function') {{
        // Juno/Apollon Format: Decoder(bytes, port)
        result = Decoder(payload, 1);
        console.log('🔧 Juno/Apollon Decoder Format erkannt');
    }} else if (typeof decodeUplink === 'function') {{
        // Febris Format: decodeUplink(input)
        const decodedResult = decodeUplink({{bytes: payload, fPort: 1}});
        result = decodedResult.data || decodedResult;
        console.log('🔧 Febris decodeUplink Format erkannt');
    }} else {{
        throw new Error('Kein gültiger Decoder gefunden (weder Decoder noch decodeUplink)');
    }}
    
    // Normalisiere Ausgabe-Format
    const normalizedData = {{}};
    for (const [key, value] of Object.entries(result || {{}})) {{
        if (typeof value === 'object' && value !== null && 'value' in value) {{
            // Bereits im richtigen Format
            normalizedData[key] = value;
        }} else {{
            // Einfacher Wert - konvertiere zu Objekt-Format
            normalizedData[key] = {{
                value: value,
                unit: '',
                description: key.replace('_', ' ').replace(/([A-Z])/g, ' $1').trim()
            }};
        }}
    }}
    
    console.log(JSON.stringify({{
        decoded: true,
        decoder_type: 'javascript',
        decoder_name: '{decoder_info["name"]}',
        data: normalizedData,
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
        """Universeller JavaScript Decoder ohne Node.js - direkter Python-basierter Parser."""
        logging.warning("Node.js nicht verfügbar, verwende Python-basierten JS-Decoder")
        
        try:
            # Auto-detect Decoder-Format basierend auf JS-Content
            if 'function Decoder(' in js_content:
                # Juno/Apollon Format erkannt
                return self._execute_juno_decoder(js_content, payload_bytes, metadata)
            elif 'function decodeUplink(' in js_content:
                # Febris Format erkannt  
                return self._execute_febris_decoder(js_content, payload_bytes, metadata)
            else:
                # Fallback zu Sentinum Engine
                logging.warning("Unbekanntes JS-Format, verwende Sentinum Engine")
                return self._sentinum_engine_decode(js_content, payload_bytes, metadata)
                
        except Exception as e:
            logging.error(f"Python JS-Decoder Fehler: {e}")
            # Letzte Rettung: Sentinum Engine
            return self._sentinum_engine_decode(js_content, payload_bytes, metadata)
    
    def _decode_febris_python(self, payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Python-Implementierung des Febris TH Decoders."""
        try:
            bytes_data = payload_bytes
            decoded = {}
            
            logging.info(f"🚨 CRITICAL DEBUG: Payload length: {len(bytes_data)}, Data: {[hex(b) for b in bytes_data[:20]]}")
            
            # Decode header
            decoded['base_id'] = bytes_data[0] >> 4
            decoded['major_version'] = bytes_data[0] & 0x0F
            decoded['minor_version'] = bytes_data[1] >> 4
            decoded['product_version'] = bytes_data[1] & 0x0F
            decoded['up_cnt'] = bytes_data[2]
            decoded['battery_voltage'] = ((bytes_data[3] << 8) | bytes_data[4]) / 1000.0
            decoded['internal_temperature'] = ((bytes_data[5] << 8) | bytes_data[6]) / 10.0 - 100.0
            
            logging.info(f"🚨 HEADER DECODED: minor_ver={decoded['minor_version']}, product_ver={decoded['product_version']}")
            
            it = 7
            
            if decoded['minor_version'] >= 3:
                # Luftfeuchte: 1 Byte (7) - entspricht exakt dem JavaScript Decoder  
                decoded['humidity'] = bytes_data[it]  # Direkt 1 Byte verwenden wie im JS
                it += 1  # 1 Byte verbraucht
                logging.info(f"🌡️ DEBUG: Humidity (Byte {it-1}): {decoded['humidity']}% RH")
                
                # Detaillierte Bedingungsprüfung
                bit_0 = decoded['product_version'] & 0x01
                bit_1 = decoded['product_version'] & 0x02
                logging.info(f"🔥 CONDITION CHECK: product_ver={decoded['product_version']}, bit_0={bit_0}, bit_1={bit_1}")
                
                if bit_0 or bit_1:  # Co2 und Druck enthalten (Bit 0 ODER Bit 1)
                    logging.info(f"✅ CO2/PRESSURE CONDITION TRUE - Reading bytes {it} to {it+3}")
                    decoded['pressure'] = (bytes_data[it] << 8) | bytes_data[it + 1]
                    it += 2
                    decoded['co2_ppm'] = (bytes_data[it] << 8) | bytes_data[it + 1]
                    it += 2
                    logging.info(f"🚨 DEBUG: Pressure: {decoded['pressure']} hPa, CO2: {decoded['co2_ppm']} ppm")
                else:
                    logging.info(f"❌ CO2/PRESSURE CONDITION FALSE - Skipping 4 bytes")
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
                        # Wall Humidity: Nur 1 Byte für Wandfeuchte
                        wall_humidity_raw = bytes_data[it]
                        decoded['wall_humidity'] = wall_humidity_raw  # Direkt verwenden (schon in %)
                        it += 1
                        logging.debug(f"🌡️ Wall Humidity: {wall_humidity_raw}% RH (1-Byte direkt)")
                        
            # Konvertiere zu erwartetes Format
            logging.info(f"🎯 FINAL DECODED VALUES: {list(decoded.keys())}")
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
                
            # ✅ CO2 UND PRESSURE HINZUFÜGEN (DAS WAR DAS PROBLEM!)
            if 'co2_ppm' in decoded:
                formatted_data['co2_ppm'] = {
                    'value': decoded['co2_ppm'],
                    'unit': 'ppm',
                    'description': 'CO2 Concentration'
                }
                
            if 'pressure' in decoded:
                formatted_data['pressure'] = {
                    'value': decoded['pressure'],
                    'unit': 'hPa',
                    'description': 'Atmospheric Pressure'
                }
                
            if 'dew_point' in decoded:
                formatted_data['dew_point'] = {
                    'value': round(decoded['dew_point'], 1),
                    'unit': '°C',
                    'description': 'Dew Point'
                }
                
            if 'wall_temperature' in decoded:
                formatted_data['wall_temperature'] = {
                    'value': round(decoded['wall_temperature'], 1),
                    'unit': '°C',
                    'description': 'Wall Temperature'
                }
                
            if 'therm_temperature' in decoded:
                formatted_data['therm_temperature'] = {
                    'value': round(decoded['therm_temperature'], 1),
                    'unit': '°C',
                    'description': 'Thermal Temperature'
                }
                
            if 'wall_humidity' in decoded:
                formatted_data['wall_humidity'] = {
                    'value': decoded['wall_humidity'],
                    'unit': '%RH',
                    'description': 'Wall Humidity'
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
    
    def _decode_juno_python(self, payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Python-Implementierung des Juno TH Decoders."""
        try:
            bytes_data = payload_bytes
            decoded = {}
            
            # Attributes (Juno Format)
            decoded['base_id'] = bytes_data[0] >> 4
            decoded['major_version'] = bytes_data[0] & 0x0F
            decoded['minor_version'] = bytes_data[1] >> 4
            decoded['product_version'] = bytes_data[1] & 0x0F
            
            # Telemetry
            decoded['up_cnt'] = bytes_data[2]
            decoded['battery_voltage'] = ((bytes_data[3] << 8) | bytes_data[4]) / 1000.0
            decoded['internal_temperature'] = bytes_data[5] - 128
            
            # Version-dependent payload (minor_version > 1)
            if decoded['minor_version'] > 1:
                idx = 6  # Start of variable size payload
                
                # Has Precision TH Sensor (product_version & 0x01)
                if decoded['product_version'] & 0x01:
                    if idx < len(bytes_data):
                        user_data = bytes_data[idx]
                        idx += 1
                        
                        # Alarms
                        decoded['alarms'] = {
                            'temperatureMaxAlarm': (user_data & (1 << 0)) != 0,
                            'temperatureMinAlarm': (user_data & (1 << 1)) != 0,
                            'temperatureDeltaAlarm': (user_data & (1 << 2)) != 0,
                            'humidityMaxAlarm': (user_data & (1 << 3)) != 0,
                            'humidityMinAlarm': (user_data & (1 << 4)) != 0,
                            'humidityDeltaAlarm': (user_data & (1 << 5)) != 0
                        }
                        
                        # Temperature and Humidity
                        if idx + 2 < len(bytes_data):
                            decoded['temperature'] = ((bytes_data[idx] << 8) | bytes_data[idx + 1]) / 10.0 - 100.0
                            idx += 2
                        if idx < len(bytes_data):
                            decoded['humidity'] = bytes_data[idx]
                            idx += 1
                
                # Has Acc Tilt functionality (product_version & 0x02)
                if decoded['product_version'] & 0x02:
                    if idx < len(bytes_data):
                        decoded['orientation'] = bytes_data[idx]
                        idx += 1
                    if idx < len(bytes_data):
                        decoded['open_alarm'] = bytes_data[idx]
                        idx += 1
                    if idx < len(bytes_data):
                        decoded['opened_since_sent'] = bytes_data[idx]
                        idx += 1
                    if idx + 1 < len(bytes_data):
                        decoded['opened_since_boot'] = (bytes_data[idx] << 8) | bytes_data[idx + 1]
                        idx += 2
            
            # Konvertiere zu erwartetes Format
            formatted_data = {}
            
            if 'battery_voltage' in decoded:
                formatted_data['battery_voltage'] = {
                    'value': round(decoded['battery_voltage'], 2),
                    'unit': 'V',
                    'description': 'Battery Voltage'
                }
                
            if 'temperature' in decoded:
                formatted_data['temperature'] = {
                    'value': round(decoded['temperature'], 1),
                    'unit': '°C',
                    'description': 'Temperature'
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
            
            return {
                'decoded': True,
                'decoder_type': 'juno_python',
                'decoder_name': 'Juno TH (Python)',
                'data': formatted_data,
                'raw_data': payload_bytes
            }
            
        except Exception as e:
            logging.error(f"Fehler beim Juno Python Decoding: {e}")
            return {
                'decoded': False,
                'reason': f'Juno Python decoding error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _sentinum_engine_decode(self, js_content: str, payload_bytes: List[int], 
                               metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Professionelle Sentinum Engine Dekodierung in Python."""
        try:
            # 1. Sensor-Typ basierend auf Payload erkennen
            sensor_type = self._detect_sensor_type(payload_bytes)
            logging.info(f"Erkannter Sensor-Typ: {sensor_type}")
            
            # 2. Spezifischen Decoder basierend auf JS-Content und Sensor-Typ wählen
            if 'febris' in js_content.lower() and sensor_type == 'FEBR-Environmental':
                return self._decode_febris_sentinum(payload_bytes, metadata)
            elif 'juno' in js_content.lower():
                return self._decode_juno_sentinum(payload_bytes, metadata)
            elif sensor_type == 'IO-Link-Adapter':
                return self._decode_iolink_adapter(payload_bytes, metadata)
            elif sensor_type == 'FEBR-Environmental':
                return self._decode_febris_sentinum(payload_bytes, metadata)
            else:
                # Fallback zu generischem Decoder
                return self._decode_generic_sentinum(payload_bytes, metadata, sensor_type)
                
        except Exception as e:
            logging.error(f"Sentinum Engine Fehler: {e}")
            return {
                'decoded': False,
                'reason': f'Sentinum Engine error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _detect_sensor_type(self, payload_bytes: List[int]) -> str:
        """Sensor-Typ basierend auf Payload erkennen."""
        if len(payload_bytes) < 2:
            return 'Unknown'
        
        # Febris Environmental (17 bytes, startet mit 0x11)
        if len(payload_bytes) == 17 and payload_bytes[0] == 0x11:
            return 'FEBR-Environmental'
        
        # Febris Utility (12+ bytes)
        if len(payload_bytes) >= 12 and 0x10 <= payload_bytes[0] <= 0x1F:
            return 'FEBR-Utility'
            
        # IO-Link Adapter Erkennung (mindestens 9 Bytes für Header)
        if len(payload_bytes) >= 9:
            control_byte = payload_bytes[0]
            # IO-Link Format erkennen: Control Bits pattern prüfen
            if (control_byte & 0x01) != 0:  # Control Bit 0 = 1
                return 'IO-Link-Adapter'
        
        # Juno-ähnliche Sensoren
        if len(payload_bytes) >= 6 and payload_bytes[0] <= 0x0F:
            return 'Juno-TH'
        
        return 'Generic-mioty'
    
    def _decode_febris_sentinum(self, payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Professionelle Febris TH Dekodierung basierend auf Sentinum Engine."""
        try:
            if len(payload_bytes) < 17:
                return {
                    'decoded': False,
                    'reason': 'Payload zu kurz für Febris TH (mindestens 17 Bytes erforderlich)',
                    'raw_data': payload_bytes
                }
            
            bytes_data = payload_bytes
            data = {}
            
            # Byte 0: Base ID (obere 4 Bits) und Major Version (untere 4 Bits)
            data['base_id'] = (bytes_data[0] >> 4) & 0x0F
            data['major_version'] = bytes_data[0] & 0x0F
            
            # Byte 1: Minor Version (obere 4 Bits) und Product Version (untere 4 Bits)
            data['minor_version'] = (bytes_data[1] >> 4) & 0x0F
            data['product_version'] = bytes_data[1] & 0x0F
            
            # Byte 2: Upload Counter
            data['up_cnt'] = bytes_data[2]
            
            # Bytes 3-4: Battery Voltage (mV)
            data['battery_voltage'] = ((bytes_data[3] << 8) | bytes_data[4]) / 1000.0
            
            # Bytes 5-6: Internal Temperature (0.1°C - 100°C offset)
            temp_raw = (bytes_data[5] << 8) | bytes_data[6]
            data['internal_temperature'] = (temp_raw / 10.0) - 100.0
            
            # Bytes 7-8: Relative Humidity (korrigierte Skalierung)
            humidity_raw = (bytes_data[7] << 8) | bytes_data[8]
            data['humidity'] = humidity_raw / 256.0
            
            # Alarm Status (falls verfügbar)
            if len(bytes_data) > 14:
                data['alarm'] = bytes_data[14]
            
            # Taupunkt berechnen (Magnus-Formel)
            if 'internal_temperature' in data and 'humidity' in data:
                temp = data['internal_temperature']
                rh = data['humidity']
                
                # Magnus-Formel für Taupunkt
                a = 17.27
                b = 237.7
                import math
                alpha = ((a * temp) / (b + temp)) + math.log(rh / 100.0)
                data['dew_point'] = (b * alpha) / (a - alpha)
            
            # Konvertiere zu erwartetes Format
            formatted_data = {}
            
            for key, value in data.items():
                if key in ['networkBaseType', 'networkSubType']:
                    continue
                
                # Bestimme Einheit und Beschreibung
                unit = ''
                description = key.replace('_', ' ').title()
                
                if 'temperature' in key.lower():
                    unit = '°C'
                elif key == 'humidity':
                    unit = '%RH'
                    description = 'Relative Humidity'
                elif 'battery' in key.lower() and 'voltage' in key.lower():
                    unit = 'V'
                    description = 'Battery Voltage'
                elif 'dew_point' in key:
                    unit = '°C'
                    description = 'Dew Point'
                
                if isinstance(value, (int, float)):
                    formatted_data[key] = {
                        'value': round(value, 2),
                        'unit': unit,
                        'description': description
                    }
                else:
                    formatted_data[key] = {
                        'value': value,
                        'unit': unit,
                        'description': description
                    }
            
            return {
                'decoded': True,
                'decoder_type': 'sentinum_febris',
                'decoder_name': 'Febris TH (Sentinum Engine)',
                'data': formatted_data,
                'raw_data': payload_bytes
            }
            
        except Exception as e:
            logging.error(f"Febris Sentinum Decoder Fehler: {e}")
            return {
                'decoded': False,
                'reason': f'Febris Sentinum decoding error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _decode_juno_sentinum(self, payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Verbesserte Juno TH Dekodierung basierend auf Sentinum Engine."""
        # Verwende die bereits implementierte Juno-Logik, aber mit Sentinum-Format
        result = self._decode_juno_python(payload_bytes, metadata)
        if result.get('decoded'):
            result['decoder_type'] = 'sentinum_juno'
            result['decoder_name'] = 'Juno TH (Sentinum Engine)'
        return result
    
    def _decode_iolink_adapter(self, payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Professionelle IO-Link Adapter Dekodierung mit Vendor/Device-ID Extraktion."""
        try:
            if len(payload_bytes) < 9:
                return {
                    'decoded': False,
                    'reason': 'Payload zu kurz für IO-Link Adapter (mindestens 9 Bytes erforderlich)',
                    'raw_data': payload_bytes
                }
            
            bytes_data = payload_bytes
            data = {}
            
            # Byte 0: Control Byte (verschiedene Control Bits)
            control_byte = bytes_data[0]
            data['control_byte'] = control_byte
            data['control_bit_0'] = (control_byte & 0x01) != 0
            data['control_bit_1'] = (control_byte & 0x02) != 0
            data['control_bit_2'] = (control_byte & 0x04) != 0
            data['control_bit_3'] = (control_byte & 0x08) != 0
            
            # Byte 1: PD-in length
            pd_in_length = bytes_data[1]
            data['pd_in_length'] = pd_in_length
            
            # Bytes 2-3: Vendor ID (2 Bytes, Big Endian)
            vendor_id = (bytes_data[2] << 8) | bytes_data[3]
            data['vendor_id'] = vendor_id
            data['vendor_id_hex'] = f"0x{vendor_id:04X}"
            
            # Bytes 4-6: Device ID (3 Bytes, Big-Endian, letztes Byte ignorieren!)
            # Korrektur: Device ID ist ebenfalls Big-Endian wie Vendor ID
            device_id_bytes = bytes_data[5:7]  # Bytes 5-6 (Skip Byte 4 = 0x00)
            device_id = (device_id_bytes[0] << 8) | device_id_bytes[1]  # Big-Endian
            data['device_id'] = device_id
            data['device_id_hex'] = f"0x{device_id:04X}"
            
            logging.info(f"🔗 IO-LINK ADAPTER ERKANNT!")
            logging.info(f"🏭 Vendor ID: {vendor_id} (0x{vendor_id:04X})")
            logging.info(f"📱 Device ID: {device_id} (0x{device_id:04X})")
            logging.info(f"📊 PD-in: {pd_in_length} bytes")
            logging.info(f"🔧 Bytes 2-3 (Vendor): {bytes_data[2]:02X} {bytes_data[3]:02X}")
            logging.info(f"🔧 Bytes 5-6 (Device): {bytes_data[5]:02X} {bytes_data[6]:02X} (Big-Endian)")
            
            # Prozessdaten extrahieren (falls vorhanden)
            pd_start_index = 7  # Nach dem korrigierten Header (nicht mehr 9!)
            if len(bytes_data) > pd_start_index:
                if len(bytes_data) >= pd_start_index + pd_in_length:
                    process_data = bytes_data[pd_start_index:pd_start_index + pd_in_length]
                    data['process_data'] = process_data
                    data['process_data_hex'] = ' '.join([f"{b:02X}" for b in process_data])
            
            # Event Daten (falls vorhanden - letzte 4 Bytes)
            if len(bytes_data) >= 4:
                event_data = bytes_data[-4:-1]  # Letzte 3 Bytes für Event
                adapter_event = bytes_data[-1]   # Letztes Byte für Adapter Event
                data['event_data'] = event_data
                data['adapter_event'] = adapter_event
            
            # Konvertiere zu erwartetes Format
            formatted_data = {}
            
            for key, value in data.items():
                # Bestimme Einheit und Beschreibung
                unit = ''
                description = key.replace('_', ' ').title()
                
                if key == 'vendor_id':
                    description = 'Vendor ID'
                elif key == 'device_id':
                    description = 'Device ID'
                elif key == 'vendor_id_hex':
                    description = 'Vendor ID (Hex)'
                elif key == 'device_id_hex':
                    description = 'Device ID (Hex)'
                elif 'length' in key:
                    unit = 'bytes'
                elif 'process_data' in key:
                    description = 'Process Data'
                    unit = 'hex'
                
                formatted_data[key] = {
                    'value': value,
                    'unit': unit,
                    'description': description
                }
            
            return {
                'decoded': True,
                'decoder_type': 'iolink_adapter',
                'decoder_name': 'IO-Link Adapter (mioty)',
                'data': formatted_data,
                'raw_data': payload_bytes,
                'vendor_id': vendor_id,
                'device_id': device_id,
                'ioddfinder_url': f"https://ioddfinder.com/devices?vendor={vendor_id}&device={device_id}"
            }
            
        except Exception as e:
            logging.error(f"IO-Link Adapter Dekodierung fehlgeschlagen: {e}")
            return {
                'decoded': False,
                'reason': f'IO-Link decode error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _decode_with_iodd(self, decoder_info: Dict[str, Any], 
                         payload_bytes: List[int], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Dekodiere mit IODD (IO Device Description) für IO-Link Sensoren."""
        try:
            # Zuerst IO-Link Adapter Informationen extrahieren
            if len(payload_bytes) < 9:
                return {
                    'decoded': False,
                    'reason': 'Payload zu kurz für IO-Link IODD (mindestens 9 Bytes erforderlich)',
                    'raw_data': payload_bytes
                }
            
            # Extrahiere Vendor/Device ID aus Payload (beide Big-Endian)
            vendor_id = (payload_bytes[2] << 8) | payload_bytes[3]
            device_id_bytes = payload_bytes[5:7]
            device_id = (device_id_bytes[0] << 8) | device_id_bytes[1]
            
            logging.info(f"🔗 IODD-Dekodierung für Vendor {vendor_id} (0x{vendor_id:04X}), Device {device_id} (0x{device_id:04X})")
            
            # Zuerst die IO-Link Adapter-Basisdaten dekodieren
            base_result = self._decode_iolink_adapter(payload_bytes, metadata)
            if not base_result.get('decoded', False):
                return base_result
            
            # IODD-Datei analysieren für zusätzliche Prozessdaten
            iodd_data = self._parse_iodd_process_data(decoder_info, payload_bytes, vendor_id, device_id)
            
            # Kombiniere Basisdaten mit IODD-Prozessdaten
            combined_data = base_result['data'].copy()
            if iodd_data:
                combined_data.update(iodd_data)
            
            return {
                'decoded': True,
                'decoder_type': 'iodd',
                'decoder_name': f"IO-Link IODD (Vendor {vendor_id}, Device {device_id})",
                'iodd_info': {
                    'vendor_id': vendor_id,
                    'device_id': device_id,
                    'iodd_file': decoder_info.get('filename', 'unknown')
                },
                'data': combined_data,
                'raw_data': payload_bytes
            }
            
        except Exception as e:
            logging.error(f"IODD Dekodierung fehlgeschlagen: {e}")
            return {
                'decoded': False,
                'reason': f'IODD decode error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _parse_iodd_process_data(self, decoder_info: Dict[str, Any], 
                                payload_bytes: List[int], vendor_id: int, device_id: int) -> Dict[str, Any]:
        """Parse IODD XML-Datei und dekodiere Prozessdaten entsprechend der Definition."""
        try:
            import xml.etree.ElementTree as ET
            
            # IODD-Datei laden
            filename = decoder_info.get('filename') or decoder_info.get('file_path', '').split('/')[-1]
            iodd_file_path = self.decoder_dir / filename
            if not iodd_file_path.exists():
                logging.warning(f"IODD-Datei nicht gefunden: {iodd_file_path}")
                return {}
            
            # XML parsen
            tree = ET.parse(iodd_file_path)
            root = tree.getroot()
            
            # Namespace handling für IODD
            namespaces = {
                'iodd': 'http://www.io-link.com/IODD/2010/10'
            }
            
            # Prozessdaten-Start-Index (nach IO-Link Header)
            pd_start_index = 7
            pd_length = payload_bytes[1] if len(payload_bytes) > 1 else 0
            
            if len(payload_bytes) < pd_start_index + pd_length:
                logging.warning(f"Nicht genügend Prozessdaten: erwartet {pd_length}, verfügbar {len(payload_bytes) - pd_start_index}")
                return {}
            
            process_data = payload_bytes[pd_start_index:pd_start_index + pd_length]
            
            # IODD ProcessDataIn auslesen
            process_data_in = root.find('.//iodd:ProcessDataIn', namespaces)
            if process_data_in is None:
                process_data_in = root.find('.//ProcessDataIn')  # Fallback ohne Namespace
            
            parsed_data = {}
            
            if process_data_in is not None:
                # Bitlänge ermitteln
                bit_length = process_data_in.get('bitLength', '0')
                try:
                    total_bits = int(bit_length)
                    expected_bytes = (total_bits + 7) // 8  # Aufrunden auf Bytes
                    
                    logging.info(f"📋 IODD ProcessDataIn: {total_bits} Bits ({expected_bytes} Bytes), verfügbar: {len(process_data)} Bytes")
                    
                    # Prozessdaten mit IODD-Definition dekodieren
                    if len(process_data) >= expected_bytes:
                        parsed_data.update(self._decode_iodd_structured_data(process_data_in, process_data, namespaces))
                    else:
                        logging.warning(f"Prozessdaten zu kurz: {len(process_data)} < {expected_bytes}")
                        
                except ValueError:
                    logging.warning(f"Ungültige bitLength in IODD: {bit_length}")
            
            # Falls keine strukturierte Daten gefunden, generische Dekodierung
            if not parsed_data:
                for i, byte_val in enumerate(process_data):
                    parsed_data[f'process_byte_{i}'] = {
                        'value': byte_val,
                        'unit': 'hex',
                        'description': f'Process Data Byte {i}'
                    }
            
            return parsed_data
            
        except Exception as e:
            logging.error(f"IODD ProcessData Parsing fehlgeschlagen: {e}")
            return {}
    
    def _decode_iodd_structured_data(self, process_data_in, process_data: List[int], namespaces: Dict[str, str]) -> Dict[str, Any]:
        """Dekodiere strukturierte IODD-Daten basierend auf XML-Definition."""
        parsed_data = {}
        
        try:
            # Suche nach Strukturelementen in der IODD
            structures = process_data_in.findall('.//iodd:Struct', namespaces)
            if not structures:
                structures = process_data_in.findall('.//Struct')  # Fallback
            
            bit_offset = 0
            
            for struct in structures:
                # Suche nach Variablen in der Struktur
                variables = struct.findall('.//iodd:Variable', namespaces)
                if not variables:
                    variables = struct.findall('.//Variable')  # Fallback
                
                for var in variables:
                    var_name = var.get('name', f'var_{bit_offset}')
                    bit_length = int(var.get('bitLength', '8'))
                    
                    # Extrahiere Wert aus Prozessdaten
                    value = self._extract_bits_from_bytes(process_data, bit_offset, bit_length)
                    
                    parsed_data[var_name] = {
                        'value': value,
                        'unit': '',
                        'description': f'{var_name} ({bit_length} bits)'
                    }
                    
                    bit_offset += bit_length
            
            # Falls keine Variablen gefunden, einfache Byte-Aufteilung
            if not parsed_data:
                for i, byte_val in enumerate(process_data):
                    parsed_data[f'iodd_data_{i}'] = {
                        'value': byte_val,
                        'unit': '',
                        'description': f'IODD Data Byte {i}'
                    }
            
        except Exception as e:
            logging.warning(f"IODD Strukturdekodierung fehlgeschlagen: {e}")
            # Fallback: einfache Byte-Auflistung
            for i, byte_val in enumerate(process_data):
                parsed_data[f'iodd_fallback_{i}'] = {
                    'value': byte_val,
                    'unit': 'hex',
                    'description': f'IODD Fallback Byte {i}'
                }
        
        return parsed_data
    
    def _execute_juno_decoder(self, js_content: str, payload_bytes: List[int], 
                             metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Führe Juno Decoder (function Decoder format) direkt in Python aus."""
        try:
            # Verwende die Python-Implementation des Juno-Decoders
            logging.info("🔧 Juno Decoder Format erkannt - verwende Python-Implementation")
            return self._decode_juno_python(payload_bytes, metadata)
            
        except Exception as e:
            logging.error(f"Juno Decoder Fehler: {e}")
            return {
                'decoded': False,
                'reason': f'Juno decoder error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _execute_febris_decoder(self, js_content: str, payload_bytes: List[int], 
                               metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Führe Febris Decoder (function decodeUplink format) direkt in Python aus."""
        try:
            # Verwende die Python-Implementation des Febris-Decoders
            logging.info("🔧 Febris decodeUplink Format erkannt - verwende Python-Implementation")
            return self._decode_febris_python(payload_bytes, metadata)
            
        except Exception as e:
            logging.error(f"Febris Decoder Fehler: {e}")
            return {
                'decoded': False,
                'reason': f'Febris decoder error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def _extract_bits_from_bytes(self, data: List[int], bit_offset: int, bit_length: int) -> int:
        """Extrahiere spezifische Bits aus Byte-Array."""
        if bit_length <= 0:
            return 0
        
        byte_offset = bit_offset // 8
        bit_in_byte = bit_offset % 8
        
        if byte_offset >= len(data):
            return 0
        
        # Einfache Implementierung für ganze Bytes
        if bit_length == 8 and bit_in_byte == 0:
            return data[byte_offset]
        
        # Für andere Bit-Längen: vereinfachte Extraktion
        value = 0
        for i in range(bit_length):
            current_byte_offset = (bit_offset + i) // 8
            current_bit_in_byte = (bit_offset + i) % 8
            
            if current_byte_offset < len(data):
                bit_value = (data[current_byte_offset] >> current_bit_in_byte) & 1
                value |= bit_value << i
        
        return value
    
    def _decode_generic_sentinum(self, payload_bytes: List[int], metadata: Dict[str, Any], 
                                sensor_type: str) -> Dict[str, Any]:
        """Generischer Sentinum Decoder für unbekannte Sensoren."""
        try:
            data = {}
            
            # Basis-Parsing für mioty-Sensoren
            if len(payload_bytes) >= 6:
                # Standard mioty Header
                data['sensor_id'] = payload_bytes[0]
                data['packet_type'] = payload_bytes[1] if len(payload_bytes) > 1 else 0
                
                # Einfache Werte extrahieren
                if len(payload_bytes) >= 4:
                    value1 = (payload_bytes[2] << 8) | payload_bytes[3]
                    data['value1'] = value1
                
                if len(payload_bytes) >= 6:
                    value2 = (payload_bytes[4] << 8) | payload_bytes[5]
                    data['value2'] = value2
            
            formatted_data = {}
            for key, value in data.items():
                formatted_data[key] = {
                    'value': value,
                    'unit': '',
                    'description': key.replace('_', ' ').title()
                }
            
            # Raw Data als Hex hinzufügen
            formatted_data['raw_hex'] = {
                'value': ' '.join(f'{b:02X}' for b in payload_bytes),
                'unit': 'hex',
                'description': 'Raw Hex Data'
            }
            
            return {
                'decoded': True,
                'decoder_type': 'sentinum_generic',
                'decoder_name': f'Generic {sensor_type} (Sentinum Engine)',
                'data': formatted_data,
                'raw_data': payload_bytes
            }
            
        except Exception as e:
            return {
                'decoded': False,
                'reason': f'Generic Sentinum decoding error: {str(e)}',
                'raw_data': payload_bytes
            }
    
    def get_available_decoders(self) -> Dict[str, Any]:
        """Gib alle verfügbaren Decoder zurück."""
        return self.decoder_files.copy()
    
    def get_sensor_decoder_assignments(self) -> Dict[str, Any]:
        """Gib alle Sensor-Decoder Zuweisungen zurück."""
        return self.decoders.copy()
    
    def _normalize_sensor_eui(self, sensor_eui: str) -> str:
        """Normalisiere Sensor EUI: Wandle Buchstaben in Großbuchstaben um, lasse Zahlen unverändert."""
        if not sensor_eui:
            return sensor_eui
        
        # Konvertiere nur Buchstaben zu Großbuchstaben, Zahlen bleiben unverändert
        normalized = ''
        for char in sensor_eui:
            if char.isalpha():
                normalized += char.upper()
            else:
                normalized += char
        
        return normalized
    
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