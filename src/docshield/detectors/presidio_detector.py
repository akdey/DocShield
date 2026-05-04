from .base import BaseDetector, EntitySpan

class PresidioDetector(BaseDetector):
    def __init__(self, spacy_model: str = "en_core_web_lg"):
        from presidio_analyzer import AnalyzerEngine
        # We can configure the NLP engine to use the requested spacy model if needed.
        # For simplicity, default Presidio uses en_core_web_lg if installed and configured.
        self.analyzer = AnalyzerEngine()

    def detect(self, text: str) -> list[EntitySpan]:
        results = self.analyzer.analyze(text=text, language='en')
        spans = []
        for res in results:
            spans.append(EntitySpan(
                start=res.start,
                end=res.end,
                entity_type=res.entity_type,
                text=text[res.start:res.end],
                source="presidio"
            ))
        return spans
