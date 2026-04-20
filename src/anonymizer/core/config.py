"""User-facing configuration: which entity types to detect.

Persisted as JSON in %LOCALAPPDATA%/Anonymizer/config.json (Windows) or
~/.config/anonymizer/config.json (Linux/macOS).
"""
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from anonymizer.core.entities import EntityKind

_log = logging.getLogger(__name__)


def _config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "Anonymizer"
    return Path.home() / ".config" / "anonymizer"


def _config_path() -> Path:
    return _config_dir() / "config.json"


@dataclass
class Config:
    enabled_kinds: set[EntityKind] = field(default_factory=lambda: set(EntityKind))
    use_ner: bool = True

    def is_enabled(self, kind: EntityKind) -> bool:
        return kind in self.enabled_kinds

    def set_enabled(self, kind: EntityKind, enabled: bool) -> None:
        if enabled:
            self.enabled_kinds.add(kind)
        else:
            self.enabled_kinds.discard(kind)


def load_config() -> Config:
    path = _config_path()
    if not path.exists():
        return Config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _log.exception("Failed to parse config, using defaults")
        return Config()

    cfg = Config()
    if "enabled_kinds" in data:
        cfg.enabled_kinds = {
            EntityKind(v) for v in data["enabled_kinds"] if v in EntityKind.__members__.values()
        }
    if "use_ner" in data:
        cfg.use_ner = bool(data["use_ner"])
    return cfg


def save_config(cfg: Config) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "enabled_kinds": sorted(k.value for k in cfg.enabled_kinds),
        "use_ner": cfg.use_ner,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
