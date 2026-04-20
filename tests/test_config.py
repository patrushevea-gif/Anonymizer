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


def test_theme_persists(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "_config_path", lambda: tmp_path / "cfg.json")
    cfg = Config()
    cfg.theme = "light"
    save_config(cfg)
    loaded = load_config()
    assert loaded.theme == "light"


def test_theme_default_is_dark() -> None:
    assert Config().theme == "dark"


def test_legacy_config_enables_new_kinds(tmp_path: Path, monkeypatch) -> None:
    """Old configs that listed enabled_kinds before API_KEY/FORMULA existed
    should still enable those new kinds after upgrade."""
    import json
    monkeypatch.setattr(config_module, "_config_path", lambda: tmp_path / "cfg.json")
    (tmp_path / "cfg.json").write_text(
        json.dumps({
            "enabled_kinds": ["ФИО", "ТЕЛ", "EMAIL"],
            "use_ner": True,
        }),
        encoding="utf-8",
    )
    cfg = load_config()
    # User-listed kinds are enabled.
    assert cfg.is_enabled(EntityKind.PERSON)
    assert cfg.is_enabled(EntityKind.PHONE)
    assert cfg.is_enabled(EntityKind.EMAIL)
    # Unknown-at-save-time kinds default to enabled.
    assert cfg.is_enabled(EntityKind.API_KEY)
    assert cfg.is_enabled(EntityKind.FORMULA)
    assert cfg.is_enabled(EntityKind.CHEMICAL)


def test_new_format_disabled_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(config_module, "_config_path", lambda: tmp_path / "cfg.json")
    cfg = Config()
    cfg.set_enabled(EntityKind.URL, False)
    save_config(cfg)
    import json
    payload = json.loads((tmp_path / "cfg.json").read_text(encoding="utf-8"))
    assert payload["disabled_kinds"] == ["URL"]
    loaded = load_config()
    assert not loaded.is_enabled(EntityKind.URL)
    assert loaded.is_enabled(EntityKind.PHONE)
