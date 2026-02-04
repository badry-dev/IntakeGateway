"""
Encryption service for sensitive data (API keys, passwords, tokens)

Uses Fernet symmetric encryption from cryptography library.
Encryption key is stored in environment variable for security.
"""
import os
import base64
from cryptography.fernet import Fernet
from loguru import logger


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""
    
    def __init__(self, encryption_key: str | None = None):
        """
        Initialize encryption service with key from environment or parameter
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, reads from ENCRYPTION_KEY env var.
        
        Raises:
            ValueError: If no encryption key provided
        """
        key = encryption_key or os.getenv("ENCRYPTION_KEY")
        
        if not key:
            # For development, generate a temporary key (NOT for production!)
            app_env = os.getenv("APP_ENV", "dev").lower()
            if app_env in ("development", "dev"):
                logger.warning("No ENCRYPTION_KEY found, generating temporary key for development")
                key = Fernet.generate_key().decode()
                logger.warning(f"Generated temporary encryption key: {key}")
                logger.warning("Set ENCRYPTION_KEY in .env for production!")
            else:
                raise ValueError(
                    "ENCRYPTION_KEY environment variable not set. "
                    "Generate key with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
                )
        
        # Ensure key is bytes
        if isinstance(key, str):
            key = key.encode()
        
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string
        
        Args:
            plaintext: String to encrypt
        
        Returns:
            Base64-encoded encrypted string
        
        Example:
            >>> enc = EncryptionService()
            >>> encrypted = enc.encrypt("my-secret-api-key")
            >>> print(encrypted)
            'gAAAAABh...'
        """
        if not plaintext:
            return ""
        
        try:
            encrypted_bytes = self.cipher.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError("Failed to encrypt value") from e
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext string
        
        Args:
            ciphertext: Base64-encoded encrypted string
        
        Returns:
            Decrypted plaintext string
        
        Raises:
            ValueError: If decryption fails (invalid key or corrupted data)
        
        Example:
            >>> enc = EncryptionService()
            >>> decrypted = enc.decrypt('gAAAAABh...')
            >>> print(decrypted)
            'my-secret-api-key'
        """
        if not ciphertext:
            return ""
        
        try:
            decrypted_bytes = self.cipher.decrypt(ciphertext.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Failed to decrypt value (invalid key or corrupted data)") from e
    
    def rotate_key(self, old_key: str, new_key: str, ciphertext: str) -> str:
        """
        Rotate encryption key by decrypting with old key and re-encrypting with new key
        
        Args:
            old_key: Old encryption key (base64-encoded)
            new_key: New encryption key (base64-encoded)
            ciphertext: Encrypted value to rotate
        
        Returns:
            Re-encrypted value with new key
        
        Example:
            >>> enc = EncryptionService()
            >>> old_encrypted = enc.encrypt("secret")
            >>> new_encrypted = enc.rotate_key(old_key, new_key, old_encrypted)
        """
        # Decrypt with old key
        old_cipher = Fernet(old_key.encode() if isinstance(old_key, str) else old_key)
        plaintext = old_cipher.decrypt(ciphertext.encode()).decode()
        
        # Encrypt with new key
        new_cipher = Fernet(new_key.encode() if isinstance(new_key, str) else new_key)
        return new_cipher.encrypt(plaintext.encode()).decode()


# Global encryption service instance
_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """
    Get singleton encryption service instance
    
    Returns:
        Global EncryptionService instance
    
    Example:
        >>> from app.core.encryption import get_encryption_service
        >>> enc = get_encryption_service()
        >>> encrypted = enc.encrypt("api-key-123")
    """
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service


def encrypt_value(plaintext: str) -> str:
    """
    Convenience function to encrypt a value using global service
    
    Args:
        plaintext: String to encrypt
    
    Returns:
        Encrypted string
    """
    return get_encryption_service().encrypt(plaintext)


def decrypt_value(ciphertext: str) -> str:
    """
    Convenience function to decrypt a value using global service
    
    Args:
        ciphertext: Encrypted string
    
    Returns:
        Decrypted plaintext
    """
    return get_encryption_service().decrypt(ciphertext)
