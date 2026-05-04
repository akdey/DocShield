import base64
from cryptography.hazmat.primitives.ciphers.aead import AESSIV
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class DocShieldCrypto:
    def __init__(self, password: str):
        # We use a fixed salt for stateless mode so that the same password 
        # always generates the same key (enabling deterministic tokens).
        self.salt = b'docshield_stateless_salt_v1'
        self.key = self._derive_key(password)
        self.aead = AESSIV(self.key)

    def _derive_key(self, password: str) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.salt,
            iterations=100000,
        )
        # AES-SIV requires 32, 48, or 64 bytes.
        return kdf.derive(password.encode())

    def encrypt(self, plaintext: str) -> str:
        data = plaintext.encode()
        ciphertext = self.aead.encrypt(data, [])
        # Use URL-safe base64 and remove padding to save space
        return base64.urlsafe_b64encode(ciphertext).decode().rstrip("=")

    def decrypt(self, token_data: str) -> str | None:
        try:
            # Restore padding if missing
            padding = len(token_data) % 4
            if padding:
                token_data += "=" * (4 - padding)
            
            ciphertext = base64.urlsafe_b64decode(token_data)
            decrypted = self.aead.decrypt(ciphertext, [])
            return decrypted.decode()
        except Exception:
            return None
