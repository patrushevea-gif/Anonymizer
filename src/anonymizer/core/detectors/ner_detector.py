from anonymizer.core.entities import EntitySpan


class NatashaDetector:
    def __init__(self) -> None:
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True

    def find(self, text: str) -> list[EntitySpan]:
        self._ensure_loaded()
        return []
