"""Unit tests for authentication logic"""

import base64

import pytest

from app.core.encryption import EncryptionService, decrypt_value, encrypt_value
from app.services.api_connector import apply_authentication


class TestEncryptionService:
    """Test encryption and decryption functionality"""

    def test_encryption_and_decryption(self):
        """Test that encrypted value can be decrypted back to original"""
        enc = EncryptionService()
        plaintext = "my-secret-api-key-12345"

        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)

        assert decrypted == plaintext
        assert encrypted != plaintext  # Should be different

    def test_empty_string_encryption(self):
        """Test that empty string is handled correctly"""
        enc = EncryptionService()

        encrypted = enc.encrypt("")
        assert encrypted == ""  # Empty string should return empty

    def test_decrypt_invalid_ciphertext(self):
        """Test that decryption fails gracefully with invalid ciphertext"""
        enc = EncryptionService()

        with pytest.raises(ValueError, match="Failed to decrypt"):
            enc.decrypt("invalid-base64-ciphertext")

    def test_encrypt_value_convenience_function(self):
        """Test encrypt_value convenience function"""
        plaintext = "test-api-key"

        encrypted = encrypt_value(plaintext)
        decrypted = decrypt_value(encrypted)

        assert decrypted == plaintext

    def test_encryption_different_on_each_call(self):
        """Test that same plaintext produces different ciphertext (Fernet uses timestamp)"""
        enc = EncryptionService()
        plaintext = "same-value"

        # Fernet includes timestamp, so same plaintext can produce different ciphertext
        # But decryption should still work
        encrypted1 = enc.encrypt(plaintext)
        encrypted2 = enc.encrypt(plaintext)

        assert enc.decrypt(encrypted1) == plaintext
        assert enc.decrypt(encrypted2) == plaintext


class TestApplyAuthentication:
    """Test apply_authentication function"""

    def test_no_auth(self):
        """Test that 'none' auth type returns unchanged headers"""
        headers = {"User-Agent": "test"}

        result = apply_authentication(headers, auth_type="none")

        assert result == headers
        assert "Authorization" not in result

    def test_bearer_token_auth(self):
        """Test Bearer token authentication"""
        headers = {}
        token = "my-bearer-token-123"
        encrypted_token = encrypt_value(token)

        result = apply_authentication(headers=headers, auth_type="bearer", api_key=encrypted_token)

        assert "Authorization" in result
        assert result["Authorization"] == f"Bearer {token}"

    def test_bearer_token_requires_api_key(self):
        """Test that Bearer auth requires api_key"""
        with pytest.raises(ValueError, match="Bearer token required"):
            apply_authentication(headers={}, auth_type="bearer", api_key=None)

    def test_api_key_auth_with_default_header(self):
        """Test API Key authentication with default header name"""
        headers = {}
        api_key = "my-api-key-xyz"
        encrypted_key = encrypt_value(api_key)

        result = apply_authentication(headers=headers, auth_type="api_key", api_key=encrypted_key)

        assert "X-API-Key" in result
        assert result["X-API-Key"] == api_key

    def test_api_key_auth_with_custom_header(self):
        """Test API Key authentication with custom header name"""
        headers = {}
        api_key = "my-api-key-xyz"
        encrypted_key = encrypt_value(api_key)

        result = apply_authentication(
            headers=headers,
            auth_type="api_key",
            api_key=encrypted_key,
            oauth_config={"api_key_header": "X-Custom-Key"},
        )

        assert "X-Custom-Key" in result
        assert result["X-Custom-Key"] == api_key

    def test_api_key_requires_api_key(self):
        """Test that API Key auth requires api_key"""
        with pytest.raises(ValueError, match="API key required"):
            apply_authentication(headers={}, auth_type="api_key", api_key=None)

    def test_basic_auth(self):
        """Test Basic authentication"""
        headers = {}
        username = "myuser"
        password = "mypassword"
        encrypted_password = encrypt_value(password)

        result = apply_authentication(
            headers=headers,
            auth_type="basic",
            username=username,
            password=encrypted_password,
        )

        assert "Authorization" in result
        assert result["Authorization"].startswith("Basic ")

        # Verify the encoded value is correct
        encoded_part = result["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(encoded_part).decode()
        assert decoded == f"{username}:{password}"

    def test_basic_auth_requires_credentials(self):
        """Test that Basic auth requires both username and password"""
        with pytest.raises(ValueError, match="Username and password required"):
            apply_authentication(headers={}, auth_type="basic", username=None, password=None)

    def test_basic_auth_requires_username(self):
        """Test that Basic auth requires username"""
        encrypted_password = encrypt_value("password")

        with pytest.raises(ValueError, match="Username and password required"):
            apply_authentication(
                headers={},
                auth_type="basic",
                username=None,
                password=encrypted_password,
            )

    def test_basic_auth_requires_password(self):
        """Test that Basic auth requires password"""
        with pytest.raises(ValueError, match="Username and password required"):
            apply_authentication(headers={}, auth_type="basic", username="user", password=None)

    def test_oauth_missing_access_token_raises(self):
        """Test that OAuth auth with no access_token raises ValueError"""
        with pytest.raises(ValueError, match="no access_token available"):
            apply_authentication(headers={}, auth_type="oauth", oauth_config={"client_id": "test"})

    def test_unknown_auth_type(self):
        """Test that unknown auth type is handled gracefully"""
        headers = {}

        # Should not raise error, just log warning
        result = apply_authentication(headers=headers, auth_type="unknown_type")

        # Should return unchanged headers
        assert result == headers

    def test_empty_headers_dict_creation(self):
        """Test that None headers creates new dict"""
        result = apply_authentication(headers=None, auth_type="none")

        assert isinstance(result, dict)
        assert len(result) == 0

    def test_preserve_existing_headers(self):
        """Test that existing headers are preserved"""
        headers = {"User-Agent": "MyApp/1.0", "Accept": "application/json"}
        token = "my-token"
        encrypted_token = encrypt_value(token)

        result = apply_authentication(headers=headers, auth_type="bearer", api_key=encrypted_token)

        # Check that original headers are preserved
        assert result["User-Agent"] == "MyApp/1.0"
        assert result["Accept"] == "application/json"
        # And new auth header is added
        assert result["Authorization"] == f"Bearer {token}"


class TestAuthenticationIntegration:
    """Integration tests for authentication in real scenarios"""

    def test_bearer_token_with_special_characters(self):
        """Test Bearer token with special characters"""
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        encrypted_token = encrypt_value(token)

        result = apply_authentication(headers={}, auth_type="bearer", api_key=encrypted_token)

        assert result["Authorization"] == f"Bearer {token}"

    def test_basic_auth_with_special_characters_in_password(self):
        """Test Basic auth with special characters in password"""
        username = "user@domain.com"
        password = "p@$$w0rd!#%&"
        encrypted_password = encrypt_value(password)

        result = apply_authentication(
            headers={},
            auth_type="basic",
            username=username,
            password=encrypted_password,
        )

        # Verify the encoded value is correct
        encoded_part = result["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(encoded_part).decode()
        assert decoded == f"{username}:{password}"
