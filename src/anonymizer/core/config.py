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
    theme: str = "dark"  # "dark" | "light"
    # Terms that must never be anonymised (company's own brand, product
    # names, public authorities…). Compared case-insensitively.
    allowlist: list[str] = field(default_factory=list)

    def is_enabled(self, kind: EntityKind) -> bool:
        return kind in self.enabled_kinds

    def set_enabled(self, kind: EntityKind, enabled: bool) -> None:
        if enabled:
            self.enabled_kinds.add(kind)
        else:
            self.enabled_kinds.discard(kind)


_VALID_KIND_VALUES = {k.value for k in EntityKind}


def load_config() -> Config:
    path = _config_path()
    if not path.exists():
        return Config()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        _log.exception("Failed to parse config, using defaults")
        return Config()

    cfg = Config()  # defaults: all kinds enabled
    if "disabled_kinds" in data:
        # New format — storing what the user TURNED OFF. Anything not listed
        # (including kinds added in a future version) stays enabled.
        for v in data["disabled_kinds"]:
            if v in _VALID_KIND_VALUES:
                cfg.set_enabled(EntityKind(v), False)
    elif "enabled_kinds" in data:
        # Legacy format — explicit set of enabled kinds. We keep the user's
        # choices for known kinds but enable any kind introduced later.
        legacy_enabled = {
            EntityKind(v) for v in data["enabled_kinds"] if v in _VALID_KIND_VALUES
        }
        legacy_known = set(data["enabled_kinds"])  # values the file knew about
        cfg.enabled_kinds = legacy_enabled | {
            k for k in EntityKind if k.value not in legacy_known
        }
    if "use_ner" in data:
        cfg.use_ner = bool(data["use_ner"])
    if "theme" in data and data["theme"] in ("dark", "light"):
        cfg.theme = data["theme"]
    if isinstance(data.get("allowlist"), list):
        cfg.allowlist = [str(t).strip() for t in data["allowlist"] if str(t).strip()]
    return cfg


def save_config(cfg: Config) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    disabled = set(EntityKind) - cfg.enabled_kinds
    payload = {
        "disabled_kinds": sorted(k.value for k in disabled),
        "use_ner": cfg.use_ner,
        "theme": cfg.theme,
        "allowlist": cfg.allowlist,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
