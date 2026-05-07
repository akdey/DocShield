from pathlib import Path
import pdfplumber
from pypdf import PdfWriter, PdfReader
from .base import BaseParser, ParsedDocument

class PdfParser(BaseParser):
    def read(self, path: Path) -> ParsedDocument:
        text = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return ParsedDocument(original_path=path, text="\n\n".join(text))

    def write_masked(self, original_path: Path, output_path: Path, text: str, replacements: list[tuple[int, int, str]]) -> None:
        """
        In-place redaction for PDFs is extremely difficult without exact coordinates.
        We generate a clean new PDF containing the masked text to ensure the file type matches
        and no hidden metadata leaks. We preserve the basic paragraph structure.
        """
        from fpdf import FPDF
        
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        
        # Split text into lines to preserve some basic structure
        for line in text.split("\n"):
            # Ensure text is compatible with latin-1 (default fonts in FPDF)
            safe_line = line.encode('latin-1', 'replace').decode('latin-1')
            # Use write for wrapping text which is more robust against long unbroken strings
            pdf.write(5, text=safe_line + '\n')
            
        # Ensure output is a .pdf
        out_pdf_path = output_path.with_suffix(".pdf")
        out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(out_pdf_path))
