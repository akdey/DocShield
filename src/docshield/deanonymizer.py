import re
from .crypto import DocShieldCrypto

class Deanonymizer:
    def __init__(self, crypto: DocShieldCrypto):
        self.crypto = crypto
        # 1. Regex for old format: <<TYPE:BLOB>>
        self.old_pattern = re.compile(r"<<([A-Z0-9_]+):([A-Za-z0-9_\-]+)>>")
        # 2. Regex for new format: [T:DATA]
        self.compact_pattern = re.compile(r"\[([A-Z0-9_]+):([^\]]+)\]")

    def deanonymize_with_replacements(self, text: str) -> tuple[str, list[tuple[int, int, str]]]:
        """
        Restores text from masked formats and returns the recovered text
        along with a list of (start, end, recovered_text) replacements.
        """
        matches = list(self.old_pattern.finditer(text)) + list(self.compact_pattern.finditer(text))
        matches.sort(key=lambda m: m.start(), reverse=True)
        
        recovered_text = text
        replacements = []
        
        for match in matches:
            if match.re == self.old_pattern:
                original = self._replace_old(match)
            else:
                original = self._replace_compact(match)
                
            if original != match.group(0):
                replacements.append((match.start(), match.end(), original))
                recovered_text = recovered_text[:match.start()] + original + recovered_text[match.end():]
                
        return recovered_text, replacements

    def deanonymize(self, text: str) -> str:
        recovered_text, _ = self.deanonymize_with_replacements(text)
        return recovered_text

    def _replace_old(self, match):
        encrypted_blob = match.group(2)
        original = self.crypto.decrypt(encrypted_blob)
        return original if original is not None else match.group(0)

    def _replace_compact(self, match):
        scrambled_text = match.group(2)
        # FPE is always successful if we have the key
        original = self.crypto.fpe_decrypt(scrambled_text)
        return original
