from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

class DocShieldConfig(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCSHIELD_")
    
    # Vault key for AES Fernet encryption
    vault_key: str | None = Field(default=None, description="Vault key for AES Fernet")
    
    # Detector Toggles
    enable_keyword_detector: bool = Field(default=True, description="Enable flashtext keyword detection")
    enable_regex_detector: bool = Field(default=True, description="Enable cloud/generic regex detection")
    enable_presidio_detector: bool = Field(default=True, description="Enable Microsoft Presidio PII detection")
    enable_gliner_detector: bool = Field(default=True, description="Enable GLiNER for zero-shot NER")
    
    # Gliner model path
    # Small model (~160MB): urchade/gliner_small-v2.1
    # Medium model (~1.5GB): urchade/gliner_medium-v2.1
    gliner_model: str = Field(default="urchade/gliner_small-v2.1")
    
    # Spacy model
    spacy_model: str = Field(default="en_core_web_lg")

    # Cloud regex patterns file path
    cloud_patterns_path: Path = Field(
        default=Path(__file__).parent.parent.parent / "rules" / "cloud_patterns.yaml"
    )

    # Custom sensitive terms (CSV: term, category)
    sensitive_terms_path: Path = Field(
        default=Path(__file__).parent.parent.parent / "rules" / "sensitive_terms.csv"
    )

config = DocShieldConfig()

