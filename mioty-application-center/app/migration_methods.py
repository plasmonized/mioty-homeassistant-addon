"""
Migration and Security Helper Methods für PayloadDecoder
=======================================================

Diese Datei enthält die Migration und Sicherheits-Helper Methoden
die in die PayloadDecoder Klasse integriert werden sollen.

Autor: mioty Application Center
Version: 1.0.5.7.0
"""

def _migrate_plaintext_keys(self):
    """Migriere bestehende plaintext application keys zu sicherer Speicherung."""
    try:
        if not self.secure_key_manager:
            return
        
        migration_needed = False
        plaintext_keys = {}
        
        # Prüfe alle Decoder-Zuweisungen auf plaintext application keys
        for sensor_eui, assignment in self.decoders.items():
            if 'application_key' in assignment:
                migration_needed = True
                plaintext_keys[sensor_eui] = {
                    'application_key': assignment['application_key'],
                    'encryption_mode': assignment.get('encryption_mode', 'GCM')
                }
        
        if migration_needed:
            logging.info(f"🔄 Starte Migration von {len(plaintext_keys)} plaintext application keys...")
            
            # Migriere zu sicherer Speicherung
            success = self.secure_key_manager.migrate_from_plaintext(plaintext_keys)
            
            if success:
                # Aktualisiere Decoder-Zuweisungen
                for sensor_eui in plaintext_keys.keys():
                    if sensor_eui in self.decoders:
                        assignment = self.decoders[sensor_eui]
                        # Entferne plaintext key aus assignment
                        assignment.pop('application_key', None)
                        # Markiere als sicher gespeichert
                        assignment['has_application_key'] = True
                
                # Speichere aktualisierte Registry (ohne plaintext keys)
                self.save_decoders()
                logging.info("✅ Migration zu sicherer Key-Speicherung abgeschlossen")
            else:
                logging.error("❌ Migration fehlgeschlagen - plaintext keys beibehalten")
        else:
            logging.info("ℹ️ Keine plaintext keys gefunden - keine Migration erforderlich")
            
    except Exception as e:
        logging.error(f"❌ Fehler bei Key-Migration: {e}")

def assign_application_key(self, sensor_eui: str, application_key: str, 
                         encryption_mode: str = 'GCM') -> bool:
    """Weise application key sicher einem Sensor zu (ohne Decoder-Zuweisung)."""
    sensor_eui = self._normalize_sensor_eui(sensor_eui)
    
    if not self.secure_key_manager:
        logging.error("❌ Secure Key Manager nicht verfügbar")
        return False
    
    # Validiere application key
    if self.mioty_aes_decoder:
        validation = self.mioty_aes_decoder.validate_mioty_application_key(application_key)
    elif self.aes_decoder:
        validation = self.aes_decoder.validate_application_key(application_key)
    else:
        logging.error("❌ Kein AES Decoder verfügbar")
        return False
    
    if not validation['is_valid']:
        logging.error(f"❌ Ungültiger application key: {validation['error_message']}")
        return False
    
    # Speichere key sicher
    success = self.secure_key_manager.store_application_key(
        sensor_eui, application_key, encryption_mode
    )
    
    if success:
        # Aktualisiere assignment falls vorhanden
        if sensor_eui in self.decoders:
            self.decoders[sensor_eui]['has_application_key'] = True
            self.decoders[sensor_eui]['encryption_mode'] = encryption_mode
            self.save_decoders()
        
        logging.info(f"🔐 Application Key für {sensor_eui} sicher zugewiesen")
    
    return success

def remove_application_key(self, sensor_eui: str) -> bool:
    """Entferne application key sicher von Sensor."""
    sensor_eui = self._normalize_sensor_eui(sensor_eui)
    
    if not self.secure_key_manager:
        return True  # Nichts zu tun
    
    success = self.secure_key_manager.remove_application_key(sensor_eui)
    
    if success:
        # Aktualisiere assignment falls vorhanden
        if sensor_eui in self.decoders:
            self.decoders[sensor_eui]['has_application_key'] = False
            self.decoders[sensor_eui].pop('encryption_mode', None)
            self.save_decoders()
        
        logging.info(f"🗑️ Application Key für {sensor_eui} entfernt")
    
    return success

def test_application_key(self, sensor_eui: str, test_payload: str) -> Dict[str, Any]:
    """Teste application key mit Testdaten (sichere Version)."""
    sensor_eui = self._normalize_sensor_eui(sensor_eui)
    
    if not self.secure_key_manager:
        return {
            'success': False,
            'error_message': 'Secure Key Manager nicht verfügbar'
        }
    
    # Rufe key sicher ab
    key_data = self.secure_key_manager.retrieve_application_key(sensor_eui)
    if not key_data:
        return {
            'success': False,
            'error_message': 'Kein application key für Sensor gefunden'
        }
    
    try:
        # Konvertiere test payload
        if isinstance(test_payload, str):
            payload_bytes = bytes.fromhex(test_payload.replace(' ', ''))
        else:
            payload_bytes = test_payload
        
        application_key = key_data['application_key']
        encryption_mode = key_data.get('encryption_mode', 'GCM')
        
        # Teste mit mioty-spezifischem Decoder falls verfügbar
        if self.mioty_aes_decoder:
            result = self.mioty_aes_decoder.decrypt_mioty_payload(
                payload_bytes, application_key
            )
        elif self.aes_decoder:
            result = self.aes_decoder.decrypt_payload(
                payload_bytes, application_key, encryption_mode
            )
        else:
            return {
                'success': False,
                'error_message': 'Kein AES Decoder verfügbar'
            }
        
        # Entferne sensitive Daten aus Test-Ergebnis
        if result.get('success'):
            # Nur Erfolg und Payload-Länge zurückgeben
            return {
                'success': True,
                'decrypted_length': len(result.get('decrypted_payload', [])),
                'mode': result.get('mode', 'Unknown'),
                'test_passed': True
            }
        else:
            return {
                'success': False,
                'error_message': result.get('error_message', 'Entschlüsselung fehlgeschlagen'),
                'test_passed': False
            }
            
    except Exception as e:
        return {
            'success': False,
            'error_message': f'Test error: {str(e)}',
            'test_passed': False
        }

def get_sensor_decoder_assignments(self) -> Dict[str, Any]:
    """Gib alle Sensor-Decoder Zuweisungen zurück (OHNE sensitive Daten)."""
    safe_assignments = {}
    for sensor_eui, assignment in self.decoders.items():
        safe_assignment = assignment.copy()
        # Entferne sensitive Daten aus der Antwort
        safe_assignment.pop('application_key', None)  # Falls noch alte Daten vorhanden
        # Füge key metadata hinzu falls verfügbar
        if self.secure_key_manager:
            has_key = self.secure_key_manager.has_application_key(sensor_eui)
            safe_assignment['has_application_key'] = has_key
        safe_assignments[sensor_eui] = safe_assignment
    return safe_assignments