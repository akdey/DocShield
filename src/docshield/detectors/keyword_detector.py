from flashtext import KeywordProcessor
from pathlib import Path
import csv
from .base import BaseDetector, EntitySpan

class KeywordDetector(BaseDetector):
    def __init__(self, terms_path: Path):
        self.processor = KeywordProcessor(case_sensitive=False)
        self.loaded = False
        if terms_path.exists():
            with open(terms_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        term = row[0].strip()
                        category = row[1].strip().upper().replace(" ", "_")
                        # flashtext allows adding keywords with a 'clean_name'
                        # which we can use as the category.
                        self.processor.add_keyword(term, f"{category}|{term}")
            self.loaded = True

    def detect(self, text: str) -> list[EntitySpan]:
        if not self.loaded or not text:
            return []
            
        spans = []
        # span_info=True returns (clean_name, start, end)
        matches = self.processor.extract_keywords(text, span_info=True)
        for match in matches:
            clean_name, start, end = match
            category, term = clean_name.split("|", 1)
            spans.append(EntitySpan(
                start=start,
                end=end,
                entity_type=category,
                text=text[start:end],
                source="keyword"
            ))
        return spans
