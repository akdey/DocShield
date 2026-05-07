# DocShield - Business Document Anonymizer
from pathlib import Path
from .pipeline import DetectionPipeline
from .masker import Masker
from .deanonymizer import Deanonymizer
from .crypto import DocShieldCrypto
from .detectors.base import EntitySpan
from .parsers import get_parser

class DocShield:
    """
    High-level facade for DocShield library usage.
    """
    def __init__(self, key: str):
        """
        Initialize DocShield with an encryption key.
        
        Args:
            key (str): The passphrase used for AES-SIV deterministic encryption.
        """
        self.crypto = DocShieldCrypto(key)
        self.pipeline = DetectionPipeline()
        self.masker = Masker(self.crypto)
        self.deanonymizer = Deanonymizer(self.crypto)

    @staticmethod
    def download_models():
        """
        Downloads the required NLP models (SpaCy, etc.) needed for DocShield.
        """
        import spacy
        from .config import config
        
        model_name = config.spacy_model
        if not spacy.util.is_package(model_name):
            print(f"Downloading SpaCy model: {model_name}...")
            spacy.cli.download(model_name)
            print("Download complete.")
        else:
            print(f"SpaCy model {model_name} is already installed.")
        
        print("\nNote: GLiNER models will be downloaded automatically upon first use.")

    def scan(self, text: str) -> list[EntitySpan]:
        """
        Scan text for sensitive entities.
        
        Args:
            text (str): The text to scan.
            
        Returns:
            list[EntitySpan]: A list of detected entity spans.
        """
        return self.pipeline.run(text)

    def anonymize(self, text: str) -> str:
        """
        Detect and mask sensitive entities in text using stateless tokens.
        
        Args:
            text (str): The text to anonymize.
            
        Returns:
            str: The masked text with embedded encrypted tokens.
        """
        spans = self.scan(text)
        return self.masker.mask(text, spans)

    def deanonymize(self, text: str) -> str:
        """
        Recover original text from a masked string containing DocShield tokens.
        
        Args:
            text (str): The masked text.
            
        Returns:
            str: The recovered original text.
        """
        return self.deanonymizer.deanonymize(text)

    def anonymize_file(self, input_path: str | Path, output_path: str | Path) -> int:
        """
        Read a file, anonymize its contents, and save to a new file.
        
        Args:
            input_path (str | Path): Path to the original document.
            output_path (str | Path): Path to save the masked document.
            
        Returns:
            int: The number of entities masked.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        parser = get_parser(input_path)
        
        doc = parser.read(input_path)
        spans = self.scan(doc.text)
        masked_text, replacements = self.masker.mask_with_replacements(doc.text, spans)
        parser.write_masked(input_path, output_path, masked_text, replacements)
        
        from .config import config
        if config.enable_image_masking:
            from .image_masker import ImageMasker
            im = ImageMasker()
            # If input was PDF, output is actually .docx
            final_output = output_path.with_suffix(".docx") if input_path.suffix.lower() == ".pdf" else output_path
            if final_output.suffix.lower() == ".docx":
                im.anonymize_docx_images(final_output, self, final_output.parent)
                
        return len(spans)

    def deanonymize_file(self, input_path: str | Path, output_path: str | Path) -> None:
        """
        Read a masked file, recover its original contents, and save to a new file.
        
        Args:
            input_path (str | Path): Path to the masked document.
            output_path (str | Path): Path to save the recovered document.
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        parser = get_parser(input_path)
        
        doc = parser.read(input_path)
        recovered_text, replacements = self.deanonymizer.deanonymize_with_replacements(doc.text)
        parser.write_masked(input_path, output_path, recovered_text, replacements)
        
        from .config import config
        if config.enable_image_masking:
            from .image_masker import ImageMasker
            im = ImageMasker()
            if output_path.suffix.lower() == ".docx":
                im.deanonymize_docx_images(output_path, input_path.parent)

__all__ = [
    "DocShield",
    "DetectionPipeline",
    "Masker",
    "Deanonymizer",
    "DocShieldCrypto",
    "EntitySpan",
]
