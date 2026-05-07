from pathlib import Path
from pdf2docx import Converter
import os
import logging

from .base import BaseParser, ParsedDocument
from .word_parser import WordParser

class PdfParser(BaseParser):
    def __init__(self):
        self.word_parser = WordParser()
        self._temp_docx = None

    def read(self, path: Path) -> ParsedDocument:
        # Create a temporary file name for the docx conversion
        self._temp_docx = path.with_suffix(".temp.docx")
        
        # Suppress pdf2docx noisy stdout
        logging.getLogger('pdf2docx').setLevel(logging.ERROR)
        
        # Convert PDF to temp DOCX
        cv = Converter(str(path))
        cv.convert(str(self._temp_docx), start=0, end=None)
        cv.close()
        
        # Delegate the reading to the WordParser which perfectly extracts runs
        return self.word_parser.read(self._temp_docx)

    def write_masked(self, original_path: Path, output_path: Path, text: str, replacements: list[tuple[int, int, str]]) -> None:
        """
        Since we converted the PDF to a Word document to preserve layout,
        the output file must be a .docx file.
        """
        # Ensure output is a .docx
        final_output = output_path.with_suffix(".docx")
        
        # Delegate writing to the WordParser using the temporary docx as the template
        self.word_parser.write_masked(self._temp_docx, final_output, text, replacements)
        
        # Cleanup the temporary docx file
        if self._temp_docx and self._temp_docx.exists():
            os.remove(self._temp_docx)
