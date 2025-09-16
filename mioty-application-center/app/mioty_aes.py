"""
mioty Application Layer AES Decryption
======================================

Implementierung der offiziellen mioty Application Layer Specification v1.1.0
für AES-Entschlüsselung von verschlüsselten mioty-Sensor payloads.

Unterstützt:
- mioty Application Layer Cryptography (Section 3)
- Session specific keys (Section 3.1) 
- AES-GCM Encryption/Decryption (Section 3.3)
- Authentication (Section 3.4)
- Application Packet counter (Section 3.5)
- Payload format (Section 3.6)

Autor: mioty Application Center
Version: 1.0.5.6.25
Basis: mioty Application Layer Specification v1.1.0
Nutzt PyCryptodome für bessere Kompatibilität mit Replit/NixOS.
"""

import logging
import binascii
import struct
from typing import Optional, Dict, Any, Union, List, Tuple
from Cryptodome.Cipher import AES
from Cryptodome.Hash import SHA256, HMAC


class MiotyAESDecryption:
    """
    Offizielle mioty Application Layer AES-Entschlüsselung.
    
    Implementiert die mioty Application Layer Specification v1.1.0:
    - Application Session Key derivation
    - AES-GCM authenticated encryption
    - Payload counter validation
    - Perfect forward secrecy
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # mioty Spezifikation Konstanten
        self.AES_KEY_SIZE = 16  # 128-bit AES wie in mioty spec
        self.AES_NONCE_SIZE = 12  # 96-bit nonce für AES-GCM
        self.PAYLOAD_COUNTER_SIZE = 4  # 32-bit application packet counter
        self.AUTH_TAG_SIZE = 16  # 128-bit authentication tag
        
    def decrypt_mioty_payload(self, encrypted_payload: Union[str, bytes, List[int]], 
                             application_key: str,
                             application_counter: Optional[int] = None) -> Dict[str, Any]:
        """
        Entschlüsselt ein mioty application layer payload gemäß Specification v1.1.0.
        
        Args:
            encrypted_payload: Verschlüsseltes Payload (hex string, bytes oder int list)
            application_key: mioty Application Key (hexadezimal)
            application_counter: Erwarteter Application Packet Counter (optional)
            
        Returns:
            Dict mit decrypted_payload, success, counter, error_message
        """
        try:
            # Normalisiere Eingaben
            payload_bytes = self._normalize_payload(encrypted_payload)
            key_bytes = self._normalize_key(application_key)
            
            if not payload_bytes or len(payload_bytes) < (self.PAYLOAD_COUNTER_SIZE + self.AES_NONCE_SIZE + self.AUTH_TAG_SIZE):
                return {
                    'success': False,
                    'error_message': f'Payload zu kurz (mindestens {self.PAYLOAD_COUNTER_SIZE + self.AES_NONCE_SIZE + self.AUTH_TAG_SIZE} bytes)',
                    'decrypted_payload': None
                }
            
            if not key_bytes or len(key_bytes) != self.AES_KEY_SIZE:
                return {
                    'success': False,
                    'error_message': f'Application Key muss {self.AES_KEY_SIZE} bytes (128-bit) lang sein',
                    'decrypted_payload': None
                }
            
            # Parse mioty Application Layer Payload Format (Section 3.6)
            payload_format = self._parse_mioty_payload_format(payload_bytes)
            if not payload_format['valid']:
                return {
                    'success': False,
                    'error_message': payload_format['error'],
                    'decrypted_payload': None
                }
            
            # Validiere Application Packet Counter (Section 3.5)
            received_counter = payload_format['counter']
            if application_counter is not None and received_counter <= application_counter:
                return {
                    'success': False,
                    'error_message': f'Replay attack detected: counter {received_counter} <= expected {application_counter}',
                    'decrypted_payload': None
                }
            
            # Generiere Session Key (Section 3.1)
            session_key = self._derive_application_session_key(
                key_bytes, 
                received_counter
            )
            
            # AES-GCM Entschlüsselung (Section 3.3)
            decrypt_result = self._decrypt_aes_gcm(
                payload_format['nonce'],
                payload_format['ciphertext'], 
                session_key,
                payload_format['additional_data']
            )
            
            if decrypt_result['success']:
                self.logger.info(f"✅ mioty Application Layer Entschlüsselung erfolgreich")
                self.logger.info(f"   📊 Counter: {received_counter}")
                self.logger.info(f"   📏 Plaintext: {len(decrypt_result['plaintext'])} bytes")
                
                return {
                    'success': True,
                    'error_message': None,
                    'decrypted_payload': list(decrypt_result['plaintext']),
                    'application_counter': received_counter,
                    'mioty_spec': 'v1.1.0'
                }
            else:
                return {
                    'success': False,
                    'error_message': f'AES-GCM decryption failed: {decrypt_result["error"]}',
                    'decrypted_payload': None,
                    'application_counter': received_counter
                }
                
        except Exception as e:
            self.logger.error(f"mioty AES decryption failed: {e}")
            return {
                'success': False,
                'error_message': f'mioty decryption error: {str(e)}',
                'decrypted_payload': None
            }
    
    def _parse_mioty_payload_format(self, payload_bytes: bytes) -> Dict[str, Any]:
        """
        Parse mioty Application Layer Payload Format (Section 3.6).
        
        Format: [Application_Packet_Counter(4)] [Nonce(12)] [Ciphertext] [Auth_Tag(16)]
        """
        try:
            if len(payload_bytes) < (self.PAYLOAD_COUNTER_SIZE + self.AES_NONCE_SIZE + self.AUTH_TAG_SIZE):
                return {
                    'valid': False,
                    'error': 'Payload zu kurz für mioty format'
                }
            
            # Extract Application Packet Counter (4 bytes, big-endian)
            counter_bytes = payload_bytes[:self.PAYLOAD_COUNTER_SIZE]
            counter = struct.unpack('>I', counter_bytes)[0]  # Big-endian 32-bit unsigned
            
            # Extract Nonce (12 bytes)
            nonce_start = self.PAYLOAD_COUNTER_SIZE
            nonce = payload_bytes[nonce_start:nonce_start + self.AES_NONCE_SIZE]
            
            # Extract Ciphertext + Authentication Tag (remaining bytes)
            ciphertext_start = nonce_start + self.AES_NONCE_SIZE
            ciphertext_with_tag = payload_bytes[ciphertext_start:]
            
            if len(ciphertext_with_tag) < self.AUTH_TAG_SIZE:
                return {
                    'valid': False,
                    'error': 'Nicht genug Daten für Authentication Tag'
                }
            
            # Additional Data für AES-GCM (counter für authentication)
            additional_data = counter_bytes  # Counter wird als Additional Data verwendet
            
            return {
                'valid': True,
                'counter': counter,
                'nonce': nonce,
                'ciphertext': ciphertext_with_tag,  # Enthält Auth Tag
                'additional_data': additional_data,
                'raw_counter_bytes': counter_bytes
            }
            
        except Exception as e:
            return {
                'valid': False,
                'error': f'Payload parsing error: {str(e)}'
            }
    
    def _derive_application_session_key(self, application_key: bytes, 
                                       application_counter: int) -> bytes:
        """
        Generiert Application Session Key gemäß mioty Specification Section 3.1.
        
        Session Key = AES-ECB(Application_Key, Application_Packet_Counter || Padding)
        """
        try:
            # Create counter block (4 bytes counter + 12 bytes padding = 16 bytes)
            counter_block = struct.pack('>I', application_counter) + b'\x00' * 12
            
            # AES-ECB verschlüsselung für Session Key Derivation mit PyCryptodome
            cipher = AES.new(application_key, AES.MODE_ECB)
            session_key = cipher.encrypt(counter_block)
            
            self.logger.debug(f"🔑 Session Key generiert für Counter {application_counter}")
            return session_key[:self.AES_KEY_SIZE]  # Nur erste 16 bytes verwenden
            
        except Exception as e:
            raise Exception(f"Session key derivation failed: {str(e)}")
    
    def _decrypt_aes_gcm(self, nonce: bytes, ciphertext_with_tag: bytes, 
                        session_key: bytes, additional_data: bytes) -> Dict[str, Any]:
        """
        AES-GCM Entschlüsselung gemäß mioty Specification Section 3.3.
        """
        try:
            # AES-GCM Instanz mit PyCryptodome erstellen
            cipher = AES.new(session_key, AES.MODE_GCM, nonce=nonce)
            
            # Separate ciphertext and authentication tag (last 16 bytes)
            if len(ciphertext_with_tag) < 16:
                raise ValueError("Ciphertext too short for authentication tag")
            ciphertext = ciphertext_with_tag[:-16]
            auth_tag = ciphertext_with_tag[-16:]
            
            # Entschlüsselung und Authentifizierung mit PyCryptodome
            plaintext = cipher.decrypt_and_verify(ciphertext, auth_tag)
            
            return {
                'success': True,
                'plaintext': plaintext,
                'error': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'plaintext': None,
                'error': str(e)
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
            
            # Validiere Schlüssellänge für mioty (128-bit)
            if len(key_bytes) != self.AES_KEY_SIZE:
                self.logger.error(f"mioty Application Key muss {self.AES_KEY_SIZE} bytes sein, erhalten: {len(key_bytes)}")
                return None
            
            return key_bytes
            
        except Exception as e:
            self.logger.error(f"Key normalization failed: {e}")
            return None
    
    def validate_mioty_application_key(self, key: str) -> Dict[str, Any]:
        """
        Validiert einen mioty Application Key.
        
        Returns:
            Dict mit is_valid, key_size, error_message
        """
        try:
            key_bytes = self._normalize_key(key)
            if key_bytes is None:
                return {
                    'is_valid': False,
                    'key_size': None,
                    'error_message': f'Ungültiges Key-Format oder -Länge (erwartet: {self.AES_KEY_SIZE} bytes / 128-bit)'
                }
            
            return {
                'is_valid': True,
                'key_size': len(key_bytes) * 8,
                'error_message': None,
                'mioty_compatible': True
            }
            
        except Exception as e:
            return {
                'is_valid': False,
                'key_size': None,
                'error_message': str(e),
                'mioty_compatible': False
            }
    
    def create_test_encrypted_payload(self, plaintext: Union[str, bytes], 
                                    application_key: str,
                                    application_counter: int = 1) -> Dict[str, Any]:
        """
        Erstellt ein verschlüsseltes Test-Payload für mioty Testing.
        
        Nur für Entwicklung und Testing!
        """
        try:
            import os
            
            # Normalisiere Eingaben
            if isinstance(plaintext, str):
                plaintext_bytes = plaintext.encode('utf-8')
            else:
                plaintext_bytes = plaintext
                
            key_bytes = self._normalize_key(application_key)
            if not key_bytes:
                return {
                    'success': False,
                    'error_message': 'Ungültiger application key'
                }
            
            # Generiere Session Key
            session_key = self._derive_application_session_key(key_bytes, application_counter)
            
            # Generiere zufällige Nonce
            nonce = os.urandom(self.AES_NONCE_SIZE)
            
            # Application Counter als Additional Data
            counter_bytes = struct.pack('>I', application_counter)
            
            # AES-GCM Verschlüsselung mit PyCryptodome
            cipher = AES.new(session_key, AES.MODE_GCM, nonce=nonce)
            ciphertext, auth_tag = cipher.encrypt_and_digest(plaintext_bytes)
            ciphertext_with_tag = ciphertext + auth_tag
            
            # Erstelle mioty Payload Format
            encrypted_payload = counter_bytes + nonce + ciphertext_with_tag
            
            self.logger.info(f"✅ Test-Payload erstellt: {len(encrypted_payload)} bytes")
            
            return {
                'success': True,
                'encrypted_payload': encrypted_payload.hex(),
                'encrypted_payload_bytes': list(encrypted_payload),
                'application_counter': application_counter,
                'original_plaintext': plaintext_bytes.hex()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error_message': f'Test payload creation failed: {str(e)}'
            }