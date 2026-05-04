from .detectors.base import EntitySpan
from .crypto import DocShieldCrypto

class Masker:
    def __init__(self, crypto: DocShieldCrypto):
        self.crypto = crypto

    def mask(self, text: str, spans: list[EntitySpan]) -> str:
        """
        Replaces detected spans with encrypted tokens.
        The token format is: <<TYPE:ENCRYPTED_BLOB>>
        Iterates backwards so indices don't shift.
        """
        if not spans:
            return text
            
        # Ensure spans are sorted backwards so replacement indices remain valid
        spans.sort(key=lambda s: s.start, reverse=True)
        
        masked_text = text
        for span in spans:
            # Encrypt the original text
            encrypted_blob = self.crypto.encrypt(span.text)
            token = f"<<{span.entity_type}:{encrypted_blob}>>"
            
            # Replace in text
            masked_text = masked_text[:span.start] + token + masked_text[span.end:]
            
        return masked_text
