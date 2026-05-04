from .detectors.base import EntitySpan
from .crypto import DocShieldCrypto

class Masker:
    def __init__(self, crypto: DocShieldCrypto):
        self.crypto = crypto

    def mask(self, text: str, spans: list[EntitySpan]) -> str:
        """
        NEW COMPACT MODE: Replaces detected spans with FPE-scrambled text.
        Format: [T:scrambled] where T is a 1-letter type code.
        This is much shorter and LLM-friendly.
        """
        if not spans:
            return text
            
        # 1-letter aliases for common types to keep it extremely short
        type_aliases = {
            "PERSON": "P",
            "GENERIC_EMAIL": "E",
            "LOCATION": "L",
            "AWS_ACCOUNT_ID": "A",
            "AWS_REGION": "R",
            "AWS_ARN": "N",
            "AWS_S3_BUCKET_URI": "S",
            "AWS_SUBNET_ID": "U",
            "GENERIC_IPV4": "I",
        }

        # Sort backwards
        spans.sort(key=lambda s: s.start, reverse=True)
        
        masked_text = text
        for span in spans:
            # FPE encrypt (same length, safe for LLMs)
            scrambled = self.crypto.fpe_encrypt(span.text)
            
            # Use alias if available
            t = type_aliases.get(span.entity_type, span.entity_type)
            token = f"[{t}:{scrambled}]"
            
            masked_text = masked_text[:span.start] + token + masked_text[span.end:]
            
        return masked_text

    def mask_old(self, text: str, spans: list[EntitySpan]) -> str:
        """
        OLD MODE: Replaces detected spans with encrypted tokens.
        The token format is: <<TYPE:ENCRYPTED_BLOB>>
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
