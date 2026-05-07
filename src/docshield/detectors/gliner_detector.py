from .base import BaseDetector, EntitySpan

class GLiNERDetector(BaseDetector):
    def __init__(self, model_name: str = "urchade/gliner_medium-v2.1", labels: list[str] = None):
        try:
            from gliner import GLiNER
            self.model = GLiNER.from_pretrained(model_name, local_files_only=True)
        except ImportError:
            self.model = None
            print("GLiNER not installed. pip install gliner")
            
        self.labels = labels or [
            "cloud subscription ID", "AWS resource name", "Azure resource group",
            "GCP project name", "API key", "internal hostname", "customer company name",
            "contract number", "employee name", "service account", "project codename"
        ]

    def detect(self, text: str) -> list[EntitySpan]:
        if not self.model or not text.strip():
            return []
            
        entities = self.model.predict_entities(text, self.labels)
        spans = []
        for ent in entities:
            # GLiNER returns dicts like {'start': 0, 'end': 5, 'text': '...', 'label': '...'}
            # Note: GLiNER labels often contain spaces. We should normalize them.
            normalized_label = ent["label"].upper().replace(" ", "_")
            spans.append(EntitySpan(
                start=ent["start"],
                end=ent["end"],
                entity_type=normalized_label,
                text=ent["text"],
                source="gliner"
            ))
        return spans
