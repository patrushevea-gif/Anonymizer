from anonymizer.core.entities import EntityKind
from anonymizer.core.mapping import MappingStore


def test_load_restores_items() -> None:
    store = MappingStore()
    store.load([
        ("ТЕЛ1", EntityKind.PHONE, "+7 999 111 22 33"),
        ("EMAIL1", EntityKind.EMAIL, "ivan@example.com"),
    ])
    assert store.original_for("ТЕЛ1") == "+7 999 111 22 33"
    assert store.original_for("EMAIL1") == "ivan@example.com"
    assert len(store) == 2


def test_load_keeps_counter_consistent() -> None:
    """After restoring ТЕЛ1, a fresh alias_for() must not re-emit ТЕЛ1."""
    store = MappingStore()
    store.load([("ТЕЛ1", EntityKind.PHONE, "+7 111")])
    new_alias = store.alias_for(EntityKind.PHONE, "+7 222")
    assert new_alias != "ТЕЛ1"
    assert new_alias == "ТЕЛ2"


def test_drop_alias_removes_both_directions() -> None:
    store = MappingStore()
    alias = store.alias_for(EntityKind.PHONE, "+7 999 111 22 33")
    assert store.original_for(alias) == "+7 999 111 22 33"

    store.drop_alias(alias)
    assert store.original_for(alias) is None
    # Re-adding the same original should produce a fresh alias, not reuse the dropped one
    new_alias = store.alias_for(EntityKind.PHONE, "+7 999 111 22 33")
    assert store.original_for(new_alias) == "+7 999 111 22 33"
