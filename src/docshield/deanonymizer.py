import re
from .crypto import DocShieldCrypto

class Deanonymizer:
    def __init__(self, crypto: DocShieldCrypto):
        self.crypto = crypto
        # Regex to find our tokens: <<TYPE:BLOB>>
        # Captured group 1 is the type, group 2 is the encrypted blob.
        self.token_pattern = re.compile(r"<<([A-Z0-9_]+):([A-Za-z0-9_\-]+)>>")

    def deanonymize(self, text: str) -> str:
        """
        Finds all tokens in the text, extracts the encrypted blob,
        and decrypts it using the crypto engine.
        """
        def replace_match(match):
            token_type = match.group(1)
            encrypted_blob = match.group(2)
            
            original = self.crypto.decrypt(encrypted_blob)
            if original is not None:
                return original
            
            # If decryption fails (wrong key or corrupted token), leave as is
            return match.group(0)

        return self.token_pattern.sub(replace_match, text)
