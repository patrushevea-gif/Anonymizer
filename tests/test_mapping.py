from anonymizer.core.entities import EntityKind
from anonymizer.core.mapping import MappingStore


def test_consistent_alias_by_key() -> None:
    store = MappingStore()
    a = store.alias_for(EntityKind.PERSON, "иванов иван иванович", display_original="Иванов Иван Иванович")
    b = store.alias_for(EntityKind.PERSON, "иванов иван иванович", display_original="Иванов И.И.")
    assert a == b == "ФИО1"
    assert store.original_for("ФИО1") == "Иванов Иван Иванович"


def test_source_alias_collision_avoided() -> None:
    store = MappingStore()
    store.reserve_source_aliases("В тексте уже есть ФИО1 и даже ФИО3 как псевдонимы.")
    alias1 = store.alias_for(EntityKind.PERSON, "Иванов")
    alias2 = store.alias_for(EntityKind.PERSON, "Петров")
    alias3 = store.alias_for(EntityKind.PERSON, "Сидоров")
    assert "ФИО1" not in {alias1, alias2, alias3}
    assert "ФИО3" not in {alias1, alias2, alias3}
    assert alias1 == "ФИО2"
    assert alias2 == "ФИО4"
    assert alias3 == "ФИО5"


def test_different_kinds_independent_counters() -> None:
    store = MappingStore()
    assert store.alias_for(EntityKind.PHONE, "+79991112233") == "ТЕЛ1"
    assert store.alias_for(EntityKind.EMAIL, "a@b.ru") == "EMAIL1"
    assert store.alias_for(EntityKind.PHONE, "+79992223344") == "ТЕЛ2"
