from pathlib import Path
from .txt_parser import TxtParser
from .word_parser import WordParser
from .pdf_parser import PdfParser

def get_parser(file_path: Path):
    """
    Factory function to get the appropriate parser based on file extension.
    """
    suffix = file_path.suffix.lower()
    if suffix == ".txt":
        return TxtParser()
    elif suffix == ".docx":
        return WordParser()
    elif suffix == ".pdf":
        return PdfParser()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

__all__ = ["get_parser", "TxtParser", "WordParser", "PdfParser"]
