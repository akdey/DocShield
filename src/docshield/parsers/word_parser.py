from pathlib import Path
import docx
from .base import BaseParser, ParsedDocument
import re

class WordParser(BaseParser):
    def read(self, path: Path) -> ParsedDocument:
        doc = docx.Document(path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        # We can also extract tables if needed later.
        text = "\n".join(full_text)
        return ParsedDocument(original_path=path, text=text)

    def write_masked(self, original_path: Path, output_path: Path, text: str, replacements: list[tuple[int, int, str]]) -> None:
        """
        Replacing text in DOCX while preserving formatting is complex because of 'runs'.
        For a simple implementation, we'll iterate through paragraphs and runs, 
        and replace any tokens we find.
        """
        doc = docx.Document(original_path)
        
        # We don't have the original text to search for, we just have `replacements` 
        # which are (start, end, masked_token). But wait, we need to map the original text 
        # to the masked token.
        # Actually, if we just replace the exact text in the paragraphs, it's easier.
        # But for now, we will simply rely on the vault to give us original -> token mappings, 
        # or we just re-run the masking on each paragraph directly.
        
        # Since we have `text` which is the FULL masked text, 
        # a naive approach for DOCX is to replace paragraph text.
        # This destroys inline formatting (like bolding part of a word).
        # A more robust approach requires applying regex to runs, but that's complex.
        
        # We will split the fully masked text back into paragraphs.
        masked_paragraphs = text.split("\n")
        
        # Replace the text of each paragraph
        for i, para in enumerate(doc.paragraphs):
            if i < len(masked_paragraphs):
                # We clear runs and add the new masked text to preserve the paragraph style
                if para.text.strip():
                    para.text = masked_paragraphs[i]
                    
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_path)
