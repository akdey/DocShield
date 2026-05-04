from abc import ABC, abstractmethod
from pathlib import Path
from dataclasses import dataclass

@dataclass
class ParsedDocument:
    original_path: Path
    text: str
    
class BaseParser(ABC):
    @abstractmethod
    def read(self, path: Path) -> ParsedDocument:
        """Reads a document and returns the extracted text."""
        pass
        
    @abstractmethod
    def write_masked(self, original_path: Path, output_path: Path, text: str, replacements: list[tuple[int, int, str]]) -> None:
        """
        Writes the masked version.
        For simple text, we just replace.
        For structured docs, replacements might need to be applied in place.
        `replacements` is a list of (start_idx, end_idx, masked_string).
        Alternatively, if `text` is already fully masked, just use `text`.
        """
        pass
