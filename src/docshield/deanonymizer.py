import re
from .crypto import DocShieldCrypto

class Deanonymizer:
    def __init__(self, crypto: DocShieldCrypto):
        self.crypto = crypto
        # 1. Regex for old format: <<TYPE:BLOB>>
        self.old_pattern = re.compile(r"<<([A-Z0-9_]+):([A-Za-z0-9_\-]+)>>")
        # 2. Regex for new format: [T:DATA]
        self.compact_pattern = re.compile(r"\[([A-Z0-9]):([^\]]+)\]")

    def deanonymize(self, text: str) -> str:
        # First, restore from old format
        text = self.old_pattern.sub(self._replace_old, text)
        # Then, restore from new compact format
        text = self.compact_pattern.sub(self._replace_compact, text)
        return text

    def _replace_old(self, match):
        encrypted_blob = match.group(2)
        original = self.crypto.decrypt(encrypted_blob)
        return original if original is not None else match.group(0)

    def _replace_compact(self, match):
        scrambled_text = match.group(2)
        # FPE is always successful if we have the key
        original = self.crypto.fpe_decrypt(scrambled_text)
        return original
