import re
import yaml
from pathlib import Path
from .base import BaseDetector, EntitySpan

class RegexDetector(BaseDetector):
    def __init__(self, patterns_path: Path):
        self.patterns = []
        if patterns_path.exists():
            with open(patterns_path, "r") as f:
                data = yaml.safe_load(f)
            if data:
                for category, rules in data.items():
                    for name, pattern in rules.items():
                        entity_type = f"{category.upper()}_{name.upper()}"
                        # Compile regex, ignoring case if specified in pattern or globally
                        try:
                            compiled = re.compile(pattern)
                            self.patterns.append((entity_type, compiled))
                        except re.error as e:
                            print(f"Failed to compile regex for {entity_type}: {e}")

    def detect(self, text: str) -> list[EntitySpan]:
        spans = []
        for entity_type, pattern in self.patterns:
            for match in pattern.finditer(text):
                spans.append(EntitySpan(
                    start=match.start(),
                    end=match.end(),
                    entity_type=entity_type,
                    text=match.group(),
                    source="regex"
                ))
        return spans
