from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

import sys

def get_base_path() -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent

class DocShieldConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCSHIELD_")
    
    # Vault key for AES Fernet encryption
    vault_key: str | None = Field(default=None, description="Vault key for AES Fernet")
    
    # Detector Toggles
    enable_keyword_detector: bool = Field(default=True, description="Enable flashtext keyword detection")
    enable_regex_detector: bool = Field(default=True, description="Enable cloud/generic regex detection")
    enable_presidio_detector: bool = Field(default=True, description="Enable Microsoft Presidio PII detection")
    enable_gliner_detector: bool = Field(default=True, description="Enable GLiNER for zero-shot NER")
    enable_image_masking: bool = Field(default=False, description="Enable OCR-based image redaction (heavy dependency)")    
    # Gliner model path
    gliner_model: str = Field(
        default_factory=lambda: str(get_base_path() / "models" / "gliner_model") if getattr(sys, 'frozen', False) else "urchade/gliner_small-v2.1"
    )
    
    # Spacy model
    spacy_model: str = Field(
        default_factory=lambda: str(get_base_path() / "models" / "spacy_model") if getattr(sys, 'frozen', False) else "en_core_web_lg"
    )

    # Cloud regex patterns file path
    cloud_patterns_path: Path = Field(
        default_factory=lambda: get_base_path() / "rules" / "cloud_patterns.yaml"
    )

    # Custom sensitive terms (CSV: term, category)
    sensitive_terms_path: Path = Field(
        default_factory=lambda: get_base_path() / "rules" / "sensitive_terms.csv"
    )

    # Terms to explicitly skip (one per line)
    denylist_path: Path = Field(
        default_factory=lambda: get_base_path() / "rules" / "denylist.txt"
    )

config = DocShieldConfig()

