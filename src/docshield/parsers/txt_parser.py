from pathlib import Path
from .base import BaseParser, ParsedDocument

class TxtParser(BaseParser):
    def read(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        return ParsedDocument(original_path=path, text=text)
        
    def write_masked(self, original_path: Path, output_path: Path, text: str, replacements: list[tuple[int, int, str]]) -> None:
        """For text files, we simply write the pre-masked text out."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
