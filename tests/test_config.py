from pathlib import Path

from anonymizer.core import config as config_module
from anonymizer.core.config import Config, load_config, save_config
from anonymizer.core.entities import EntityKind


def test_config_defaults_all_kinds() -> None:
    cfg = Config()
    assert len(cfg.enabled_kinds) == len(list(EntityKind))
    for kind in EntityKind:
        assert cfg.is_enabled(kind)


def test_config_round_trip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "_config_path", lambda: tmp_path / "cfg.json")
    cfg = Config()
    cfg.set_enabled(EntityKind.IP, False)
    cfg.set_enabled(EntityKind.URL, False)
    cfg.use_ner = False
    save_config(cfg)

    loaded = load_config()
    assert not loaded.is_enabled(EntityKind.IP)
    assert not loaded.is_enabled(EntityKind.URL)
    assert loaded.is_enabled(EntityKind.PHONE)
    assert loaded.use_ner is False


def test_missing_config_returns_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "_config_path", lambda: tmp_path / "nonexistent.json")
    cfg = load_config()
    assert cfg.is_enabled(EntityKind.PHONE)
