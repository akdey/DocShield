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

    def write_masked(self, original_path: Path, output_path: Path, text: str, replacements: list[tuple[int, int, str, str]]) -> None:
        """
        True in-place visual redaction for PDFs.
        We use PyMuPDF (fitz) to search for the original text and draw redaction
        annotations. This perfectly preserves the PDF's images, layout, and other text.
        """
        import fitz
        
        doc = fitz.open(original_path)
        
        # Extract unique replacements to avoid redacting the same string twice
        # replacements is [(start, end, text_to_replace, new_text)]
        unique_reps = {}
        for _, _, orig, token in replacements:
            unique_reps[orig] = token
            
        for page in doc:
            for orig, token in unique_reps.items():
                rects = page.search_for(orig)
                for rect in rects:
                    # Draw a white box over the old text and write the token
                    page.add_redact_annot(rect, text=token, fill=(1, 1, 1), text_color=(0, 0, 0), cross_out=False)
                    
            # Apply all redactions for this page
            page.apply_redactions()
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path))
