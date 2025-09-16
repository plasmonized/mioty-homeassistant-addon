"""
AES Application Payload Decryption Module for mioty Sensors
===========================================================

Unterstützt AES-GCM und AES-CBC Entschlüsselung für mioty-Sensoren mit application keys.
Kompatibel mit verschiedenen Key-Formaten und Payload-Größen.

Autor: mioty Application Center
Version: 1.0.5.6.24
"""

import logging
import binascii
from typing import Optional, Dict, Any, Union, List
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class AESDecryption:
    """
    Professionelle AES-Entschlüsselung für mioty application payloads.
    
    Unterstützt:
    - AES-GCM (empfohlen, authenticated encryption)
    - AES-CBC (traditionell, benötigt separate Authentifizierung)
    - Verschiedene Key-Größen: 128, 192, 256 Bit
    - Hexadezimale und binäre Key-Formate
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_modes = ['GCM', 'CBC']
        self.supported_key_sizes = [16, 24, 32]  # 128, 192, 256 bit
    
    def decrypt_payload(self, encrypted_payload: Union[str, bytes, List[int]], 
                       application_key: str, 
                       mode: str = 'GCM',
                       iv_nonce: Optional[Union[str, bytes]] = None) -> Dict[str, Any]:
        """
        Entschlüsselt ein verschlüsseltes mioty application payload.
        
        Args:
            encrypted_payload: Verschlüsseltes Payload (hex string, bytes oder int list)
            application_key: AES-Schlüssel (hexadezimal string)
            mode: Verschlüsselungsmodus ('GCM' oder 'CBC')
            iv_nonce: IV/Nonce (optional, wird automatisch extrahiert wenn None)
            
        Returns:
            Dict mit decrypted_payload, success, error_message
        """
        try:
            # Eingabe-Validation und Normalisierung
            payload_bytes = self._normalize_payload(encrypted_payload)
            key_bytes = self._normalize_key(application_key)
            
            if not payload_bytes:
                return {
                    'success': False,
                    'error_message': 'Leeres oder ungültiges Payload',
                    'decrypted_payload': None
                }
            
            if not key_bytes:
                return {
                    'success': False,
                    'error_message': 'Ungültiger application key',
                    'decrypted_payload': None
                }
            
            # Mode-spezifische Entschlüsselung
            if mode.upper() == 'GCM':
                return self._decrypt_gcm(payload_bytes, key_bytes, iv_nonce)
            elif mode.upper() == 'CBC':
                return self._decrypt_cbc(payload_bytes, key_bytes, iv_nonce)
            else:
                return {
                    'success': False,
                    'error_message': f'Unsupported encryption mode: {mode}',
                    'decrypted_payload': None
                }
                
        except Exception as e:
            self.logger.error(f"AES decryption failed: {e}")
            return {
                'success': False,
                'error_message': f'Decryption error: {str(e)}',
                'decrypted_payload': None
            }
    
    def _decrypt_gcm(self, payload_bytes: bytes, key_bytes: bytes, 
                     nonce: Optional[Union[str, bytes]] = None) -> Dict[str, Any]:
        """AES-GCM Entschlüsselung (authenticated encryption)."""
        try:
            # Für GCM: Nonce ist normalerweise in den ersten 12 Bytes
            if nonce is None:
                if len(payload_bytes) < 12:
                    raise ValueError("Payload zu kurz für GCM (mindestens 12 Bytes für Nonce)")
                nonce_bytes = payload_bytes[:12]
                ciphertext = payload_bytes[12:]
            else:
                nonce_bytes = self._normalize_bytes(nonce)
                ciphertext = payload_bytes
            
            if len(nonce_bytes) != 12:
                raise ValueError("GCM Nonce muss 12 Bytes lang sein")
            
            # AES-GCM Instanz erstellen
            aesgcm = AESGCM(key_bytes)
            
            # Entschlüsselung und Authentifizierung
            plaintext = aesgcm.decrypt(nonce_bytes, ciphertext, None)
            
            self.logger.info(f"✅ AES-GCM Entschlüsselung erfolgreich: {len(plaintext)} bytes")
            
            return {
                'success': True,
                'error_message': None,
                'decrypted_payload': list(plaintext),
                'mode': 'AES-GCM',
                'key_size': len(key_bytes) * 8
            }
            
        except Exception as e:
            self.logger.error(f"AES-GCM decryption failed: {e}")
            return {
                'success': False,
                'error_message': f'AES-GCM decryption failed: {str(e)}',
                'decrypted_payload': None
            }
    
    def _decrypt_cbc(self, payload_bytes: bytes, key_bytes: bytes, 
                     iv: Optional[Union[str, bytes]] = None) -> Dict[str, Any]:
        """AES-CBC Entschlüsselung (traditionell)."""
        try:
            # Für CBC: IV ist normalerweise in den ersten 16 Bytes
            if iv is None:
                if len(payload_bytes) < 16:
                    raise ValueError("Payload zu kurz für CBC (mindestens 16 Bytes für IV)")
                iv_bytes = payload_bytes[:16]
                ciphertext = payload_bytes[16:]
            else:
                iv_bytes = self._normalize_bytes(iv)
                ciphertext = payload_bytes
            
            if len(iv_bytes) != 16:
                raise ValueError("CBC IV muss 16 Bytes lang sein")
            
            # CBC muss ein Vielfaches von 16 Bytes sein
            if len(ciphertext) % 16 != 0:
                raise ValueError("CBC ciphertext Länge muss ein Vielfaches von 16 sein")
            
            # AES-CBC Cipher erstellen
            cipher = Cipher(
                algorithms.AES(key_bytes),
                modes.CBC(iv_bytes),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Entschlüsselung
            plaintext = decryptor.update(ciphertext) + decryptor.finalize()
            
            # PKCS7 Padding entfernen
            plaintext = self._remove_pkcs7_padding(plaintext)
            
            self.logger.info(f"✅ AES-CBC Entschlüsselung erfolgreich: {len(plaintext)} bytes")
            
            return {
                'success': True,
                'error_message': None,
                'decrypted_payload': list(plaintext),
                'mode': 'AES-CBC',
                'key_size': len(key_bytes) * 8
            }
            
        except Exception as e:
            self.logger.error(f"AES-CBC decryption failed: {e}")
            return {
                'success': False,
                'error_message': f'AES-CBC decryption failed: {str(e)}',
                'decrypted_payload': None
            }
    
    def _normalize_payload(self, payload: Union[str, bytes, List[int]]) -> Optional[bytes]:
        """Normalisiert Payload zu bytes."""
        try:
            if isinstance(payload, str):
                # Hexadezimaler String
                return bytes.fromhex(payload.replace(' ', '').replace(':', ''))
            elif isinstance(payload, bytes):
                return payload
            elif isinstance(payload, list):
                # Liste von Integers
                return bytes(payload)
            else:
                return None
        except Exception as e:
            self.logger.error(f"Payload normalization failed: {e}")
            return None
    
    def _normalize_key(self, key: str) -> Optional[bytes]:
        """Normalisiert AES-Schlüssel zu bytes."""
        try:
            if not isinstance(key, str):
                return None
            
            # Entferne Leerzeichen und Trennzeichen
            clean_key = key.replace(' ', '').replace(':', '').replace('-', '')
            
            # Konvertiere von hex zu bytes
            key_bytes = bytes.fromhex(clean_key)
            
            # Validiere Schlüssellänge
            if len(key_bytes) not in self.supported_key_sizes:
                self.logger.error(f"Unsupported key size: {len(key_bytes)} bytes. "
                                f"Supported: {self.supported_key_sizes}")
                return None
            
            self.logger.info(f"🔑 AES Key normalized: {len(key_bytes)*8}-bit")
            return key_bytes
            
        except Exception as e:
            self.logger.error(f"Key normalization failed: {e}")
            return None
    
    def _normalize_bytes(self, data: Union[str, bytes]) -> bytes:
        """Normalisiert Daten zu bytes."""
        if isinstance(data, str):
            return bytes.fromhex(data.replace(' ', '').replace(':', ''))
        elif isinstance(data, bytes):
            return data
        else:
            raise ValueError("Data must be string or bytes")
    
    def _remove_pkcs7_padding(self, data: bytes) -> bytes:
        """Entfernt PKCS7 Padding von entschlüsselten Daten."""
        if not data:
            return data
        
        # Letztes Byte gibt die Padding-Länge an
        padding_length = data[-1]
        
        # Validiere Padding
        if padding_length == 0 or padding_length > 16:
            return data  # Kein valides Padding
        
        # Prüfe ob alle Padding-Bytes korrekt sind
        for i in range(padding_length):
            if data[-(i + 1)] != padding_length:
                return data  # Kein valides Padding
        
        # Entferne Padding
        return data[:-padding_length]
    
    def validate_application_key(self, key: str) -> Dict[str, Any]:
        """
        Validiert einen application key.
        
        Returns:
            Dict mit is_valid, key_size, error_message
        """
        try:
            key_bytes = self._normalize_key(key)
            if key_bytes is None:
                return {
                    'is_valid': False,
                    'key_size': None,
                    'error_message': 'Ungültiges Key-Format oder -Länge'
                }
            
            return {
                'is_valid': True,
                'key_size': len(key_bytes) * 8,
                'error_message': None
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'key_size': None,
                'error_message': str(e)
            }
    
    def test_decryption(self, test_payload: str, test_key: str, 
                       expected_result: Optional[str] = None) -> Dict[str, Any]:
        """
        Testet AES-Entschlüsselung mit Testdaten.
        
        Returns:
            Dict mit test_result, success, error_message
        """
        try:
            # Teste beide Modi
            results = {}
            
            for mode in ['GCM', 'CBC']:
                result = self.decrypt_payload(test_payload, test_key, mode)
                results[mode] = result
                
                if result['success']:
                    self.logger.info(f"✅ Test {mode} erfolgreich")
                else:
                    self.logger.warning(f"❌ Test {mode} fehlgeschlagen: {result['error_message']}")
            
            return {
                'test_results': results,
                'success': any(r['success'] for r in results.values()),
                'error_message': None
            }
            
        except Exception as e:
            self.logger.error(f"Test decryption failed: {e}")
            return {
                'test_results': {},
                'success': False,
                'error_message': str(e)
            }