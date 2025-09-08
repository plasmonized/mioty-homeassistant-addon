"""
Decoder Manager für mioty Application Center
Verwaltet Decoder-Dateien und deren Zuweisungen
"""

import os
import json
import logging
import shutil
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
from payload_decoder import PayloadDecoder


class DecoderManager:
    """Manager für Payload Decoder."""
    
    def __init__(self, decoder_dir: str = "/data/decoders"):
        """Initialisiere Decoder Manager."""
        self.decoder_dir = Path(decoder_dir)
        self.decoder_dir.mkdir(parents=True, exist_ok=True)
        
        # Payload Decoder Engine
        self.payload_decoder = PayloadDecoder(str(self.decoder_dir))
        
        # Erstelle Beispiel-Decoder
        self._create_sample_decoders()
        
        logging.info("Decoder Manager initialisiert")
    
    def decode_payload(self, sensor_eui: str, payload_bytes: List[int], metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Delegiere Payload-Dekodierung an PayloadDecoder Engine."""
        return self.payload_decoder.decode_payload(sensor_eui, payload_bytes, metadata)
    
    def _create_sample_decoders(self):
        """Erstelle Beispiel-Decoder für Demo."""
        # mioty Blueprint Beispiel
        blueprint_example = {
            "name": "Temperature Humidity Sensor",
            "version": "1.0",
            "description": "Standard Temperature/Humidity Sensor Blueprint",
            "devices": ["TH_SENSOR_V1", "TH_SENSOR_V2"],
            "payload": {
                "temperature": {
                    "type": "uint16",
                    "length": 2,
                    "scale": 0.1,
                    "offset": -40.0,
                    "unit": "°C",
                    "description": "Temperature measurement"
                },
                "humidity": {
                    "type": "uint16", 
                    "length": 2,
                    "scale": 0.01,
                    "offset": 0.0,
                    "unit": "%",
                    "description": "Relative humidity"
                },
                "battery": {
                    "type": "uint8",
                    "length": 1,
                    "scale": 0.1,
                    "offset": 0.0,
                    "unit": "V",
                    "description": "Battery voltage"
                }
            }
        }
        
        # Sentinum JavaScript Beispiel
        sentinum_example = '''
// @name Sentinum Temperature Humidity Decoder
// @version 1.0
// @description Decodes temperature and humidity sensor data

function decode(payload, metadata) {
    if (payload.length < 4) {
        return { error: "Payload too short" };
    }
    
    // Temperature (bytes 0-1)
    const tempRaw = (payload[0] << 8) | payload[1];
    const temperature = (tempRaw - 400) / 10.0;
    
    // Humidity (bytes 2-3) 
    const humRaw = (payload[2] << 8) | payload[3];
    const humidity = humRaw / 100.0;
    
    // Battery (byte 4, optional)
    let battery = null;
    if (payload.length >= 5) {
        battery = payload[4] * 0.1;
    }
    
    const result = {
        temperature: {
            value: Math.round(temperature * 10) / 10,
            unit: "°C"
        },
        humidity: {
            value: Math.round(humidity * 10) / 10, 
            unit: "%"
        }
    };
    
    if (battery !== null) {
        result.battery = {
            value: Math.round(battery * 10) / 10,
            unit: "V"
        };
    }
    
    return result;
}

module.exports = { decode };
'''
        
        # Erstelle Beispiel-Dateien falls sie nicht existieren
        blueprint_file = self.decoder_dir / "temp_humidity_blueprint.json"
        if not blueprint_file.exists():
            try:
                with open(blueprint_file, 'w') as f:
                    json.dump(blueprint_example, f, indent=2)
                logging.info("Blueprint Beispiel-Decoder erstellt")
            except Exception as e:
                logging.error(f"Fehler beim Erstellen des Blueprint-Beispiels: {e}")
        
        sentinum_file = self.decoder_dir / "temp_humidity_sentinum.js"
        if not sentinum_file.exists():
            try:
                with open(sentinum_file, 'w') as f:
                    f.write(sentinum_example)
                logging.info("Sentinum Beispiel-Decoder erstellt")
            except Exception as e:
                logging.error(f"Fehler beim Erstellen des Sentinum-Beispiels: {e}")
        
        # Decoder neu laden um Beispiele zu erkennen
        self.payload_decoder.load_decoders()
    
    def upload_decoder_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Lade Decoder-Datei hoch."""
        try:
            # Validiere Dateiname
            if not filename.endswith(('.js', '.json', '.xml')):
                return {
                    'success': False,
                    'error': 'Nur .js, .json und .xml (IODD) Dateien werden unterstützt'
                }
            
            # Dekodiere Content falls nötig
            if isinstance(content, bytes):
                try:
                    content_str = content.decode('utf-8')
                except UnicodeDecodeError:
                    return {
                        'success': False,
                        'error': 'Datei konnte nicht als UTF-8 dekodiert werden'
                    }
            else:
                content_str = content
            
            # Validiere JSON für .json Dateien
            if filename.endswith('.json'):
                try:
                    json.loads(content_str)
                except json.JSONDecodeError as e:
                    return {
                        'success': False,
                        'error': f'Ungültige JSON-Datei: {str(e)}'
                    }
            
            # Validiere XML für .xml (IODD) Dateien
            elif filename.endswith('.xml'):
                try:
                    import xml.etree.ElementTree as ET
                    ET.fromstring(content_str)
                except ET.ParseError as e:
                    return {
                        'success': False,
                        'error': f'Ungültige XML-Datei: {str(e)}'
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f'XML-Verarbeitungsfehler: {str(e)}'
                    }
            
            # Upload über PayloadDecoder
            success = self.payload_decoder.upload_decoder(filename, content_str)
            
            if success:
                return {
                    'success': True,
                    'message': f'Decoder {filename} erfolgreich hochgeladen'
                }
            else:
                return {
                    'success': False,
                    'error': 'Fehler beim Hochladen der Datei'
                }
                
        except Exception as e:
            logging.error(f"Fehler beim Hochladen der Decoder-Datei: {e}")
            return {
                'success': False,
                'error': f'Unerwarteter Fehler: {str(e)}'
            }
    
    def get_available_decoders(self) -> List[Dict[str, Any]]:
        """Gib verfügbare Decoder zurück."""
        decoders = self.payload_decoder.get_available_decoders()
        
        decoder_list = []
        for name, info in decoders.items():
            decoder_list.append({
                'name': name,
                'display_name': info['name'],
                'type': info['type'],
                'version': info['version'],
                'description': info['description'],
                'supported_devices': info.get('supported_devices', []),
                'created_at': info['created_at']
            })
        
        # Sortiere nach Erstellungsdatum
        decoder_list.sort(key=lambda x: x['created_at'], reverse=True)
        return decoder_list
    
    def get_sensor_assignments(self) -> Dict[str, Any]:
        """Gib Sensor-Decoder Zuweisungen zurück."""
        return self.payload_decoder.get_sensor_decoder_assignments()
    
    def assign_decoder_to_sensor(self, sensor_eui: str, decoder_name: str) -> bool:
        """Weise Decoder einem Sensor zu."""
        return self.payload_decoder.assign_decoder(sensor_eui, decoder_name)
    
    def remove_sensor_assignment(self, sensor_eui: str) -> bool:
        """Entferne Decoder-Zuweisung von Sensor."""
        return self.payload_decoder.remove_decoder_assignment(sensor_eui)
    
    def delete_decoder(self, decoder_name: str) -> bool:
        """Lösche Decoder."""
        return self.payload_decoder.delete_decoder(decoder_name)
    
    def decode_sensor_payload(self, sensor_eui: str, payload_bytes: List[int], 
                             metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Dekodiere Sensor-Payload."""
        return self.payload_decoder.decode_payload(sensor_eui, payload_bytes, metadata)
    
    def test_decoder(self, decoder_name: str, test_payload: List[int]) -> Dict[str, Any]:
        """Teste Decoder mit Test-Payload."""
        try:
            # Erstelle temporäre Zuweisung für Test
            test_eui = "test_sensor_eui"
            
            # Sichere eventuelle bestehende Zuweisung
            original_assignment = self.payload_decoder.decoders.get(test_eui)
            
            # Temporäre Zuweisung
            self.payload_decoder.decoders[test_eui] = {
                'decoder_name': decoder_name,
                'assigned_at': 0
            }
            
            # Teste Dekodierung
            result = self.payload_decoder.decode_payload(test_eui, test_payload)
            
            # Stelle ursprüngliche Zuweisung wieder her
            if original_assignment:
                self.payload_decoder.decoders[test_eui] = original_assignment
            else:
                self.payload_decoder.decoders.pop(test_eui, None)
            
            return result if result else {
                'decoded': False,
                'reason': 'Test fehlgeschlagen',
                'raw_data': test_payload
            }
            
        except Exception as e:
            logging.error(f"Fehler beim Testen des Decoders: {e}")
            return {
                'decoded': False,
                'reason': f'Test error: {str(e)}',
                'raw_data': test_payload
            }
    
    def get_decoder_info(self, decoder_name: str) -> Optional[Dict[str, Any]]:
        """Gib detaillierte Decoder-Informationen zurück."""
        decoders = self.payload_decoder.get_available_decoders()
        return decoders.get(decoder_name)
    
    def export_decoder_config(self) -> Dict[str, Any]:
        """Exportiere Decoder-Konfiguration."""
        return {
            'decoders': self.payload_decoder.get_available_decoders(),
            'assignments': self.payload_decoder.get_sensor_decoder_assignments(),
            'version': '1.0'
        }
    
    def import_decoder_config(self, config: Dict[str, Any]) -> bool:
        """Importiere Decoder-Konfiguration."""
        try:
            # Hier könnte eine vollständige Import-Logik implementiert werden
            # Für jetzt nur eine einfache Bestätigung
            logging.info("Decoder-Konfiguration Import angefordert")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Importieren der Decoder-Konfiguration: {e}")
            return False
    
    def assign_iodd_to_iolink_adapter(self, sensor_eui: str, vendor_id: int, device_id: int, iodd_name: str) -> bool:
        """Weise IODD einem IO-Link Adapter basierend auf Vendor/Device ID zu."""
        try:
            # Verifiziere dass IODD existiert
            decoders = self.payload_decoder.get_available_decoders()
            if iodd_name not in decoders:
                logging.error(f"IODD {iodd_name} nicht gefunden")
                return False
            
            # Verifiziere dass es eine IODD-Datei ist
            decoder_info = decoders[iodd_name]
            if decoder_info.get('type') != 'iodd':
                logging.error(f"Decoder {iodd_name} ist keine IODD-Datei")
                return False
            
            # Verifiziere Vendor/Device ID Übereinstimmung
            iodd_vendor_id = decoder_info.get('vendor_id', 0)
            iodd_device_id = decoder_info.get('device_id', 0)
            
            if iodd_vendor_id != vendor_id or iodd_device_id != device_id:
                logging.warning(f"Vendor/Device ID Mismatch: IODD({iodd_vendor_id},{iodd_device_id}) vs Adapter({vendor_id},{device_id})")
                # Erlaube trotzdem Zuweisung für Flexibilität
            
            # Erstelle spezielle IO-Link Zuweisung
            success = self.payload_decoder.assign_decoder(sensor_eui, iodd_name)
            
            if success:
                # Speichere zusätzliche IO-Link Metadaten
                if not hasattr(self.payload_decoder, 'iolink_assignments'):
                    self.payload_decoder.iolink_assignments = {}
                
                self.payload_decoder.iolink_assignments[sensor_eui] = {
                    'vendor_id': vendor_id,
                    'device_id': device_id,
                    'iodd_name': iodd_name,
                    'assigned_at': time.time()
                }
                
                logging.info(f"IODD {iodd_name} erfolgreich zu IO-Link Adapter {sensor_eui} zugewiesen (VID:{vendor_id}, DID:{device_id})")
            
            return success
            
        except Exception as e:
            logging.error(f"Fehler beim Zuweisen der IODD: {e}")
            return False
    
    def get_iolink_adapters(self) -> List[Dict[str, Any]]:
        """Gib Liste aller erkannten IO-Link Adapter zurück."""
        try:
            # Sammle IO-Link Adapter aus Sensor-Daten
            adapters = []
            
            # Prüfe alle Sensoren im System
            if hasattr(self.payload_decoder, 'sensor_data_cache'):
                for sensor_eui, sensor_data in self.payload_decoder.sensor_data_cache.items():
                    # Prüfe ob der Sensor IO-Link Adapter Daten gesendet hat
                    if 'vendor_id' in sensor_data and 'device_id' in sensor_data:
                        adapter_info = {
                            'sensor_eui': sensor_eui,
                            'vendor_id': sensor_data['vendor_id'],
                            'device_id': sensor_data['device_id'],
                            'vendor_id_hex': f"0x{sensor_data['vendor_id']:04X}",
                            'device_id_hex': f"0x{sensor_data['device_id']:04X}",
                            'last_seen': sensor_data.get('last_seen', 0),
                            'assigned_iodd': None
                        }
                        
                        # Prüfe ob IODD zugewiesen ist
                        if hasattr(self.payload_decoder, 'iolink_assignments'):
                            assignment = self.payload_decoder.iolink_assignments.get(sensor_eui)
                            if assignment:
                                adapter_info['assigned_iodd'] = assignment['iodd_name']
                        
                        adapters.append(adapter_info)
            
            # Sortiere nach letztem Kontakt
            adapters.sort(key=lambda x: x['last_seen'], reverse=True)
            
            return adapters
            
        except Exception as e:
            logging.error(f"Fehler beim Abrufen der IO-Link Adapter: {e}")
            return []