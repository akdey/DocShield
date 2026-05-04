from .detectors.base import EntitySpan
from .detectors.regex_detector import RegexDetector
from .detectors.presidio_detector import PresidioDetector
from .detectors.gliner_detector import GlinerDetector
from .detectors.keyword_detector import KeywordDetector
from .config import config

class DetectionPipeline:
    def __init__(self):
        self.detectors = []
        
        # Load denylist from file
        self.denylist = set()
        if config.denylist_path.exists():
            for line in config.denylist_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    self.denylist.add(line.lower())
        
        # 1. Keyword Detector (Highest Priority)
        if config.enable_keyword_detector:
            self.detectors.append(KeywordDetector(config.sensitive_terms_path))
        
        # 2. Regex Detector
        if config.enable_regex_detector:
            self.detectors.append(RegexDetector(config.cloud_patterns_path))
        
        # 3. Presidio
        if config.enable_presidio_detector:
            self.detectors.append(PresidioDetector())
        
        # 4. GLiNER
        if config.enable_gliner_detector:
            self.detectors.append(GlinerDetector(config.gliner_model))
            
    def _deduplicate_spans(self, spans: list[EntitySpan]) -> list[EntitySpan]:
        """
        Merge overlapping spans. Keep the longest span.
        If spans overlap identically, keep the one from the higher priority detector.
        (Priority is implicit by list insertion order if we sort appropriately, but here
         we can simply sort by start index, then descending end index to keep longest).
        """
        if not spans:
            return []
            
        # Sort by start index, then by end index descending (longest first)
        spans.sort(key=lambda s: (s.start, -s.end))
        
        deduped = []
        current = spans[0]
        
        for span in spans[1:]:
            # If the current span completely encompasses the next span, ignore the next span
            if span.start >= current.start and span.end <= current.end:
                continue
            # If they overlap but the new one extends further, we might merge or keep the new one.
            # For simplicity, if they overlap, we'll extend `current` if it makes sense, 
            # but usually it means the token is split differently. Let's just avoid overlaps entirely.
            if span.start < current.end:
                # We have an overlap. We keep `current` because it's longer or started earlier.
                # In a more advanced implementation, we might merge them.
                continue
            else:
                deduped.append(current)
                current = span
                
        deduped.append(current)
        return deduped

    def run(self, text: str) -> list[EntitySpan]:
        all_spans = []
        for detector in self.detectors:
            try:
                all_spans.extend(detector.detect(text))
            except Exception as e:
                print(f"Detector {detector.__class__.__name__} failed: {e}")
                
        # Apply denylist
        filtered_spans = [
            span for span in all_spans 
            if span.text.strip().lower() not in self.denylist
        ]
                
        return self._deduplicate_spans(filtered_spans)
