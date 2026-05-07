from .detectors.base import EntitySpan
from .crypto import DocShieldCrypto

class Masker:
    def __init__(self, crypto: DocShieldCrypto):
        self.crypto = crypto

    def mask_with_replacements(self, text: str, spans: list[EntitySpan]) -> tuple[str, list[tuple[int, int, str, str]]]:
        """
        NEW COMPACT MODE: Replaces detected spans with FPE-scrambled text.
        Returns the masked text AND a list of (start, end, original_text, masked_token) replacements.
        """
        if not spans:
            return text, []
            
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
            "SERVICE_ACCOUNT": "K",
            "API_KEY": "X",
            "INTERNAL_ID": "D",
            "CONTRACT": "C",
            "PROJECT_NAME": "J",
        }

        # Sort backwards so replacement indices remain valid for string manipulation
        spans.sort(key=lambda s: s.start, reverse=True)
        
        masked_text = text
        replacements = []
        
        for span in spans:
            # FPE encrypt (same length, safe for LLMs)
            scrambled = self.crypto.fpe_encrypt(span.text)
            
            # Use alias if available
            t = type_aliases.get(span.entity_type, span.entity_type)
            token = f"[{t}:{scrambled}]"
            
            # We store the replacement info
            replacements.append((span.start, span.end, span.text, token))
            
            masked_text = masked_text[:span.start] + token + masked_text[span.end:]
            
        return masked_text, replacements

    def mask(self, text: str, spans: list[EntitySpan]) -> str:
        """Backward compatible wrapper."""
        masked_text, _ = self.mask_with_replacements(text, spans)
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
