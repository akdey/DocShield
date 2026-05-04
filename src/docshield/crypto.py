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

    def fpe_encrypt(self, plaintext: str) -> str:
        """
        Format Preserving Encryption: Scrambles text while keeping length and type.
        (Letters stay letters, numbers stay numbers).
        """
        import string
        import hmac
        import hashlib
        
        # We create a mapping for each character class
        classes = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
        
        result = []
        for char in plaintext:
            found = False
            for cls in classes:
                if char in cls:
                    # A keyed shuffle is better.
                    shuffled = self._get_keyed_shuffle(cls)
                    result.append(shuffled[cls.index(char)])
                    found = True
                    break
            if not found:
                result.append(char)
        return "".join(result)

    def fpe_decrypt(self, ciphertext: str) -> str:
        import string
        classes = [string.ascii_lowercase, string.ascii_uppercase, string.digits]
        
        result = []
        for char in ciphertext:
            found = False
            for cls in classes:
                shuffled = self._get_keyed_shuffle(cls)
                if char in shuffled:
                    result.append(cls[shuffled.index(char)])
                    found = True
                    break
            if not found:
                result.append(char)
        return "".join(result)

    def _get_keyed_shuffle(self, alphabet: str) -> str:
        """Generates a deterministic shuffle of an alphabet based on the key."""
        import hashlib
        import random
        # Seed random with the hash of (key + alphabet)
        seed = hashlib.sha256(self.key + alphabet.encode()).digest()
        rng = random.Random(seed)
        chars = list(alphabet)
        rng.shuffle(chars)
        return "".join(chars)
