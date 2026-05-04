from abc import ABC, abstractmethod
from pydantic import BaseModel

class EntitySpan(BaseModel):
    start: int
    end: int
    entity_type: str
    text: str
    source: str

class BaseDetector(ABC):
    @abstractmethod
    def detect(self, text: str) -> list[EntitySpan]:
        """Detect entities in the text and return a list of EntitySpans."""
        pass
