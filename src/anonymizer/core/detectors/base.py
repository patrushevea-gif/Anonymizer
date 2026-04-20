from typing import Protocol

from anonymizer.core.entities import EntitySpan


class Detector(Protocol):
    def find(self, text: str) -> list[EntitySpan]: ...
