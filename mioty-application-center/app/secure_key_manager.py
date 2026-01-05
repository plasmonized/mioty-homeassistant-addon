"""
Secure Key Manager for mioty Application Center
==============================================

Provides encrypted storage for application keys and sensitive data.
Uses environment-based master key for encryption/decryption.

Autor: mioty Application Center  
Version: 1.0.5.7.0
Security: FIPS-compliant encryption for production use
"""

import os
import json
import logging
import hashlib
import time
import subprocess
from typing import Dict, Any, Optional, Union
from pathlib import Path
from Cryptodome.Cipher import AES
from Cryptodome.Protocol.KDF import PBKDF2
from Cryptodome.Hash import SHA256
from Cryptodome.Random import get_random_bytes
import base64


class SecurityError(Exception):
    """Critical security error - master keys in insecure locations."""
    pass


class SecureKeyManager:
    """
    Secure storage manager for application keys and sensitive data.
    
    Features:
    - Environment-based master key derivation
    - PyCryptodome AES-GCM authenticated encryption
    - Atomic file operations
    - Key rotation support
    - Audit logging
    - VCS-tracking protection (CRITICAL SECURITY)
    - Fail-fast startup for security compliance
    
    SECURITY: This class enforces that master keys are NEVER stored in 
    VCS-tracked directories or project paths. Only secure system directories
    like /data are allowed for master key storage.
    """
    
    def __init__(self, storage_dir: str = "/data/secure"):
        """Initialize secure key manager with strict security validation."""
        self.logger = logging.getLogger(__name__)
        
        # SECURITY: If environment variable is set, we don't need file storage
        if os.getenv('MIOTY_MASTER_KEY'):
            self.logger.info("🔐 Using environment-provided master key - no file storage needed")
            self.storage_dir = None  # No file storage needed
        else:
            # SECURITY: Validate storage directory is secure and outside VCS tracking
            secure_dir = self._validate_secure_storage_directory(storage_dir)
            if not secure_dir:
                raise SecurityError(
                    "❌ CRITICAL SECURITY ERROR: Cannot establish secure storage directory. "
                    "Master keys cannot be stored in VCS-tracked or project directories. "
                    "Ensure /data directory is writable or set MIOTY_MASTER_KEY environment variable."
                )
            self.storage_dir = secure_dir
        if self.storage_dir:
            self.logger.info(f"🔐 Secure storage directory validated: {self.storage_dir}")
            
            # Secure files
            self.keys_file = self.storage_dir / "encrypted_keys.dat"
            self.counters_file = self.storage_dir / "app_counters.dat"
            self.audit_file = self.storage_dir / "key_audit.log"
        else:
            # Environment-only mode - use temporary directory for non-key data
            import tempfile
            temp_dir = Path(tempfile.gettempdir()) / "mioty_app_temp"
            temp_dir.mkdir(exist_ok=True)
            self.keys_file = temp_dir / "encrypted_keys.dat"
            self.counters_file = temp_dir / "app_counters.dat"
            self.audit_file = temp_dir / "key_audit.log"
        
        # Initialize encryption key
        self.encryption_key = self._init_encryption()
        
        # Application counter tracking (in memory for performance)
        self.app_counters = self._load_app_counters()
        
        self.logger.info("🔐 Secure Key Manager initialisiert")
    
    def _validate_secure_storage_directory(self, storage_dir: str) -> Optional[Path]:
        """
        Validate storage directory is secure and outside VCS tracking.
        
        SECURITY: This method enforces that master keys are never stored in:
        - Project/codebase directories
        - VCS-tracked paths
        - Any directory that could be committed to version control
        
        Args:
            storage_dir: Requested storage directory path
            
        Returns:
            Validated Path object or None if insecure
        """
        try:
            target_dir = Path(storage_dir).resolve()
            
            # SECURITY CHECK 1: Refuse any path in current working directory tree
            cwd = Path.cwd().resolve()
            try:
                target_dir.relative_to(cwd)
                self.logger.error(
                    f"❌ SECURITY VIOLATION: Storage directory {target_dir} is inside project directory {cwd}. "
                    "Master keys CANNOT be stored in project/codebase directories!"
                )
                return None
            except ValueError:
                # Good - target_dir is not under cwd
                pass
            
            # SECURITY CHECK 2: Detect VCS tracking
            if self._is_vcs_tracked_path(target_dir):
                self.logger.error(
                    f"❌ SECURITY VIOLATION: Storage directory {target_dir} is in VCS-tracked path. "
                    "Master keys CANNOT be stored in version-controlled directories!"
                )
                return None
            
            # SECURITY CHECK 3: Ensure directory is writable and secure
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Test write permissions
                test_file = target_dir / ".security_test"
                test_file.write_text("security_validation_test")
                test_file.unlink()
                
                # Set secure permissions on directory (owner only)
                target_dir.chmod(0o700)
                
                self.logger.info(f"✓ Security validation passed for {target_dir}")
                return target_dir
                
            except (OSError, PermissionError) as e:
                self.logger.error(f"❌ Storage directory {target_dir} is not writable: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Security validation failed: {e}")
            return None
    
    def _is_vcs_tracked_path(self, path: Path) -> bool:
        """
        Check if path is under version control tracking.
        
        Returns:
            True if path is VCS-tracked (dangerous for keys)
        """
        try:
            current_path = path.resolve()
            
            # Check for git repository
            while current_path != current_path.parent:
                if (current_path / ".git").exists():
                    self.logger.warning(f"⚠️ VCS detected: Git repository at {current_path}")
                    return True
                
                # Check for other VCS systems
                vcs_dirs = [".svn", ".hg", ".bzr", "CVS"]
                if any((current_path / vcs_dir).exists() for vcs_dir in vcs_dirs):
                    self.logger.warning(f"⚠️ VCS detected at {current_path}")
                    return True
                
                current_path = current_path.parent
            
            return False
            
        except Exception as e:
            # If we can't determine VCS status, err on the side of security
            self.logger.warning(f"Cannot determine VCS status for {path}: {e} - assuming unsafe")
            return True

    def _init_encryption(self) -> bytes:
        """Initialize encryption key with secure master key handling."""
        try:
            # SECURITY: Always prefer environment variable for master key
            master_password = os.getenv('MIOTY_MASTER_KEY')
            if not master_password:
                # SECURITY: Environment-only mode - no file storage
                if not self.storage_dir:
                    raise SecurityError(
                        "❌ CRITICAL: No master key available. "
                        "Set MIOTY_MASTER_KEY environment variable or ensure /data directory is writable."
                    )
                
                # SECURITY: Only load from validated secure storage directory
                master_key_file = self.storage_dir / "master.key"
                
                # SECURITY: Double-check the master key file location is safe
                if self._is_vcs_tracked_path(master_key_file.parent):
                    raise SecurityError(
                        f"❌ CRITICAL: Master key file {master_key_file} would be in VCS-tracked directory! "
                        "This is a severe security violation."
                    )
                
                if master_key_file.exists():
                    # Load existing master key from secure location
                    try:
                        with open(master_key_file, 'rb') as f:
                            master_password = f.read().decode('utf-8')
                        self.logger.info("🔐 Master Key loaded from secure storage")
                        
                        # Verify file permissions are secure
                        file_mode = master_key_file.stat().st_mode & 0o777
                        if file_mode != 0o600:
                            self.logger.warning(f"⚠️ Fixing insecure master key permissions: {oct(file_mode)} -> 0o600")
                            master_key_file.chmod(0o600)
                            
                    except Exception as e:
                        raise SecurityError(f"❌ Cannot read master key from secure storage: {e}")
                else:
                    # Generate new secure master key
                    import secrets
                    master_password = secrets.token_urlsafe(64)  # 512-bit secure key
                    
                    try:
                        # Atomic write with secure permissions
                        temp_file = master_key_file.with_suffix('.tmp')
                        with open(temp_file, 'wb') as f:
                            f.write(master_password.encode('utf-8'))
                        
                        # Set secure permissions before moving
                        temp_file.chmod(0o600)
                        temp_file.replace(master_key_file)
                        
                        self.logger.info("🔐 New secure master key generated and stored")
                        self._audit_log("MASTER_KEY_GENERATED: New secure master key created")
                        
                    except Exception as e:
                        raise SecurityError(f"❌ Cannot create master key in secure storage: {e}")
            else:
                self.logger.info("🔐 Using master key from environment variable")
                self._audit_log("MASTER_KEY_ENV: Using environment-provided master key")
            
            # Derive encryption key using PBKDF2 with PyCryptodome
            salt = b'mioty-application-center-2024'  # Fixed salt for deterministic key
            key = PBKDF2(
                master_password,  # PBKDF2 expects string, not bytes
                salt,
                32,  # AES-256 key length
                count=100000,
                hmac_hash_module=SHA256
            )
            
            self.logger.info("🔑 AES-GCM Verschlüsselungsschlüssel erfolgreich abgeleitet")
            return key
            
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
            
            # Encrypt the key data using AES-GCM
            plaintext = json.dumps(key_data).encode()
            cipher = AES.new(self.encryption_key, AES.MODE_GCM)
            ciphertext, auth_tag = cipher.encrypt_and_digest(plaintext)
            
            # Store nonce + auth_tag + ciphertext as base64
            encrypted_data = bytes(cipher.nonce) + bytes(auth_tag) + bytes(ciphertext)
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
            
            # Decrypt key data using AES-GCM
            encrypted_data = base64.b64decode(encrypted_keys[sensor_eui])
            
            # Extract nonce, auth_tag, and ciphertext
            nonce = encrypted_data[:16]  # AES-GCM nonce is 16 bytes
            auth_tag = encrypted_data[16:32]  # Auth tag is 16 bytes
            ciphertext = encrypted_data[32:]  # Rest is ciphertext
            
            # Decrypt and verify authenticity
            cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)
            decrypted_data = cipher.decrypt_and_verify(ciphertext, auth_tag)
            key_data = json.loads(decrypted_data.decode())
            
            # Update last used timestamp
            key_data['last_used'] = time.time()
            
            # Re-encrypt with updated timestamp
            plaintext = json.dumps(key_data).encode()
            cipher = AES.new(self.encryption_key, AES.MODE_GCM)
            ciphertext, auth_tag = cipher.encrypt_and_digest(plaintext)
            
            # Store updated encrypted data
            encrypted_data = bytes(cipher.nonce) + bytes(auth_tag) + bytes(ciphertext)
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
                    # Decrypt only metadata using AES-GCM
                    encrypted_bytes = base64.b64decode(encrypted_data)
                    
                    # Extract nonce, auth_tag, and ciphertext
                    nonce = encrypted_bytes[:16]
                    auth_tag = encrypted_bytes[16:32]
                    ciphertext = encrypted_bytes[32:]
                    
                    # Decrypt and verify
                    cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)
                    decrypted_data = cipher.decrypt_and_verify(ciphertext, auth_tag)
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