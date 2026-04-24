"""
Encryption: encrypt/decrypt sensitive data.

Uses Fernet (symmetric encryption) from cryptography library.
"""

import os
from typing import Optional
import structlog
from cryptography.fernet import Fernet


logger = structlog.get_logger(__name__)


class EncryptionManager:
    """
    Manages encryption/decryption of sensitive data.

    Uses Fernet for symmetric encryption.
    """

    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize encryption manager.

        Args:
            encryption_key: Encryption key (from env if not provided)
        """
        self.encryption_key = encryption_key or os.getenv("ENCRYPTION_KEY", "")

        if not self.encryption_key:
            logger.warning("no_encryption_key_provided")
            self.cipher: Optional[Fernet] = None
        else:
            try:
                self.cipher = Fernet(self.encryption_key.encode())
                logger.info("encryption_manager_initialized")
            except Exception as e:
                logger.error("invalid_encryption_key", error=str(e))
                self.cipher = None

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not self.cipher:
            logger.warning("encryption_disabled")
            return plaintext

        try:
            ciphertext = self.cipher.encrypt(plaintext.encode())
            return ciphertext.decode()
        except Exception as e:
            logger.error("encryption_error", error=str(e), exc_info=True)
            raise

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string.

        Args:
            ciphertext: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext

        Raises:
            Exception if decryption fails (e.g., wrong key)
        """
        if not self.cipher:
            logger.warning("decryption_disabled")
            return ciphertext

        try:
            plaintext = self.cipher.decrypt(ciphertext.encode())
            return plaintext.decode()
        except Exception as e:
            logger.error("decryption_error", error=str(e), exc_info=True)
            raise


# Global instance
encryptor = EncryptionManager()
