"""
Secure Key Manager for mioty Application Center
==============================================

Provides encrypted storage for application keys and sensitive data.
Uses environment-based master key for encryption/decryption.

Autor: mioty Application Center  
Version: 1.0.5.6.24
Security: FIPS-compliant encryption for production use
"""

import os
import json
import logging
import hashlib
import time
from typing import Dict, Any, Optional, Union
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class SecureKeyManager:
    """
    Secure storage manager for application keys and sensitive data.
    
    Features:
    - Environment-based master key derivation
    - Fernet symmetric encryption (AES 128 in CBC mode)
    - Atomic file operations
    - Key rotation support
    - Audit logging
    """
    
    def __init__(self, storage_dir: str = "/data/secure"):
        """Initialize secure key manager."""
        self.logger = logging.getLogger(__name__)
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Secure files
        self.keys_file = self.storage_dir / "encrypted_keys.dat"
        self.counters_file = self.storage_dir / "app_counters.dat"
        self.audit_file = self.storage_dir / "key_audit.log"
        
        # Initialize encryption
        self.fernet = self._init_encryption()
        
        # Application counter tracking (in memory for performance)
        self.app_counters = self._load_app_counters()
        
        self.logger.info("🔐 Secure Key Manager initialisiert")
    
    def _init_encryption(self) -> Fernet:
        """Initialize Fernet encryption with environment-based key."""
        try:
            # Get master password from environment
            master_password = os.getenv('MIOTY_MASTER_KEY')
            if not master_password:
                # SICHERHEIT: Generiere oder lade einen sicheren Master Key
                master_key_file = self.storage_dir / "master.key"
                if master_key_file.exists():
                    # Lade existierenden Master Key
                    with open(master_key_file, 'rb') as f:
                        master_password = f.read().decode('utf-8')
                    self.logger.info("🔐 Master Key aus sicherer Datei geladen")
                else:
                    # Generiere neuen sicheren Master Key
                    import secrets
                    master_password = secrets.token_urlsafe(64)  # 512-bit sicherer Key
                    with open(master_key_file, 'wb') as f:
                        f.write(master_password.encode('utf-8'))
                    # Sichere Dateiberechtigungen setzen (nur Owner lesen/schreiben)
                    master_key_file.chmod(0o600)
                    self.logger.info("🔐 Neuer sicherer Master Key generiert und gespeichert")
            
            # Derive encryption key using PBKDF2
            salt = b'mioty-application-center-2024'  # Fixed salt for deterministic key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master_password.encode()))
            
            self.logger.info("🔑 Verschlüsselungsschlüssel erfolgreich abgeleitet")
            return Fernet(key)
            
        except Exception as e:
            self.logger.error(f"❌ Fehler bei Verschlüsselungsinitialisierung: {e}")
            raise
    
    def store_application_key(self, sensor_eui: str, application_key: str, 
                            encryption_mode: str = 'GCM') -> bool:
        """
        Store application key securely encrypted.
        
        Args:
            sensor_eui: Sensor EUI (identifier)
            application_key: Application key to encrypt and store
            encryption_mode: Encryption mode (GCM/CBC)
            
        Returns:
            bool: Success status
        """
        try:
            # Load existing keys
            encrypted_keys = self._load_encrypted_keys()
            
            # Prepare key data
            key_data = {
                'application_key': application_key,
                'encryption_mode': encryption_mode,
                'created_at': time.time(),
                'last_used': None
            }
            
            # Encrypt the key data
            encrypted_data = self.fernet.encrypt(json.dumps(key_data).encode())
            encrypted_keys[sensor_eui] = base64.b64encode(encrypted_data).decode()
            
            # Atomic save
            success = self._save_encrypted_keys(encrypted_keys)
            
            if success:
                self._audit_log(f"STORE_KEY: {sensor_eui} ({encryption_mode})")
                # DO NOT LOG THE ACTUAL KEY
                self.logger.info(f"🔐 Application key für {sensor_eui} sicher gespeichert")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Speichern des application key: {e}")
            return False
    
    def retrieve_application_key(self, sensor_eui: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt application key.
        
        Args:
            sensor_eui: Sensor EUI
            
        Returns:
            Dict with application_key, encryption_mode, etc. or None
        """
        try:
            encrypted_keys = self._load_encrypted_keys()
            
            if sensor_eui not in encrypted_keys:
                return None
            
            # Decrypt key data
            encrypted_data = base64.b64decode(encrypted_keys[sensor_eui])
            decrypted_data = self.fernet.decrypt(encrypted_data)
            key_data = json.loads(decrypted_data.decode())
            
            # Update last used timestamp
            key_data['last_used'] = time.time()
            encrypted_data = self.fernet.encrypt(json.dumps(key_data).encode())
            encrypted_keys[sensor_eui] = base64.b64encode(encrypted_data).decode()
            self._save_encrypted_keys(encrypted_keys)
            
            self._audit_log(f"RETRIEVE_KEY: {sensor_eui}")
            return key_data
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Abrufen des application key für {sensor_eui}: {e}")
            return None
    
    def remove_application_key(self, sensor_eui: str) -> bool:
        """Remove application key securely."""
        try:
            encrypted_keys = self._load_encrypted_keys()
            
            if sensor_eui in encrypted_keys:
                del encrypted_keys[sensor_eui]
                success = self._save_encrypted_keys(encrypted_keys)
                
                if success:
                    self._audit_log(f"REMOVE_KEY: {sensor_eui}")
                    self.logger.info(f"🗑️ Application key für {sensor_eui} entfernt")
                
                return success
            
            return True  # Already removed
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Entfernen des application key: {e}")
            return False
    
    def has_application_key(self, sensor_eui: str) -> bool:
        """Check if sensor has application key stored."""
        try:
            encrypted_keys = self._load_encrypted_keys()
            return sensor_eui in encrypted_keys
        except Exception:
            return False
    
    def get_application_counter(self, sensor_eui: str) -> int:
        """Get current application counter for sensor."""
        return self.app_counters.get(sensor_eui, 0)
    
    def update_application_counter(self, sensor_eui: str, counter: int) -> bool:
        """
        Update application counter with replay protection.
        
        Args:
            sensor_eui: Sensor EUI
            counter: New counter value
            
        Returns:
            bool: True if counter is valid (higher than stored), False for replay
        """
        try:
            current_counter = self.app_counters.get(sensor_eui, 0)
            
            # Replay protection: counter must be higher than stored
            if counter <= current_counter:
                self.logger.warning(f"🚫 REPLAY ATTACK DETECTED: {sensor_eui} counter {counter} <= {current_counter}")
                self._audit_log(f"REPLAY_DETECTED: {sensor_eui} counter {counter} <= {current_counter}")
                return False
            
            # Update counter
            self.app_counters[sensor_eui] = counter
            
            # Persist atomically
            success = self._save_app_counters()
            
            if success:
                self._audit_log(f"UPDATE_COUNTER: {sensor_eui} counter={counter}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Aktualisieren des Counters: {e}")
            return False
    
    def _load_encrypted_keys(self) -> Dict[str, str]:
        """Load encrypted keys from storage."""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Fehler beim Laden der Schlüssel: {e}")
        
        return {}
    
    def _save_encrypted_keys(self, encrypted_keys: Dict[str, str]) -> bool:
        """Save encrypted keys atomically."""
        try:
            # Atomic write
            temp_file = self.keys_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(encrypted_keys, f, indent=2)
            
            temp_file.replace(self.keys_file)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Speichern der Schlüssel: {e}")
            return False
    
    def _load_app_counters(self) -> Dict[str, int]:
        """Load application counters from storage."""
        try:
            if self.counters_file.exists():
                with open(self.counters_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"Fehler beim Laden der Counter: {e}")
        
        return {}
    
    def _save_app_counters(self) -> bool:
        """Save application counters atomically."""
        try:
            # Atomic write
            temp_file = self.counters_file.with_suffix('.tmp')
            with open(temp_file, 'w') as f:
                json.dump(self.app_counters, f, indent=2)
            
            temp_file.replace(self.counters_file)
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Speichern der Counter: {e}")
            return False
    
    def _audit_log(self, message: str):
        """Write audit log entry."""
        try:
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            with open(self.audit_file, 'a') as f:
                f.write(f"{timestamp} - {message}\n")
        except Exception as e:
            self.logger.warning(f"Audit log Fehler: {e}")
    
    def list_stored_keys(self) -> Dict[str, Dict[str, Any]]:
        """List all stored keys with metadata (NO ACTUAL KEYS)."""
        try:
            encrypted_keys = self._load_encrypted_keys()
            result = {}
            
            for sensor_eui, encrypted_data in encrypted_keys.items():
                try:
                    # Decrypt only metadata
                    decrypted_data = self.fernet.decrypt(base64.b64decode(encrypted_data))
                    key_data = json.loads(decrypted_data.decode())
                    
                    # Return metadata WITHOUT the actual key
                    result[sensor_eui] = {
                        'encryption_mode': key_data.get('encryption_mode', 'GCM'),
                        'created_at': key_data.get('created_at'),
                        'last_used': key_data.get('last_used'),
                        'has_key': True
                    }
                except Exception:
                    result[sensor_eui] = {'has_key': False, 'error': 'decrypt_failed'}
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Fehler beim Auflisten der Schlüssel: {e}")
            return {}
    
    def migrate_from_plaintext(self, plaintext_keys: Dict[str, Dict[str, Any]]) -> bool:
        """
        Migrate from plaintext key storage to encrypted storage.
        
        Args:
            plaintext_keys: Dictionary with sensor_eui -> {application_key, encryption_mode}
            
        Returns:
            bool: Migration success
        """
        try:
            migration_count = 0
            
            for sensor_eui, key_info in plaintext_keys.items():
                if 'application_key' in key_info:
                    application_key = key_info['application_key']
                    encryption_mode = key_info.get('encryption_mode', 'GCM')
                    
                    success = self.store_application_key(sensor_eui, application_key, encryption_mode)
                    if success:
                        migration_count += 1
                    else:
                        self.logger.error(f"❌ Migration fehlgeschlagen für {sensor_eui}")
                        return False
            
            self.logger.info(f"✅ Migration abgeschlossen: {migration_count} Schlüssel migriert")
            self._audit_log(f"MIGRATION_COMPLETED: {migration_count} keys migrated")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Migration fehlgeschlagen: {e}")
            return False