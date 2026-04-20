import pytest

from anonymizer.core.entities import EntityKind
from anonymizer.core.mapping import MappingStore
from anonymizer.core.pipeline import Pipeline
from anonymizer.core.reverse import restore


def test_regex_only_pipeline_masks_and_restores() -> None:
    pipeline = Pipeline.default(use_ner=False)
    store = MappingStore()
    text = (
        "Свяжитесь с нами: +7 999 111-22-33, почта ivan@example.com, "
        "ИНН 7707083893, карта 4111 1111 1111 1111."
    )
    result = pipeline.run(text, store)

    assert "+7 999 111-22-33" not in result.masked_text
    assert "ivan@example.com" not in result.masked_text
    assert "7707083893" not in result.masked_text
    assert "4111 1111 1111 1111" not in result.masked_text

    assert result.counts[EntityKind.PHONE] == 1
    assert result.counts[EntityKind.EMAIL] == 1
    assert result.counts[EntityKind.INN] == 1
    assert result.counts[EntityKind.CARD] == 1

    ai_response = result.masked_text + " — спасибо!"
    restored = restore(ai_response, store)
    assert "+7 999 111-22-33" in restored
    assert "ivan@example.com" in restored


def test_same_value_in_multiple_places_gets_same_alias() -> None:
    pipeline = Pipeline.default(use_ner=False)
    store = MappingStore()
    text = "Позвоните +7 999 111 22 33. Повторим: +7 999 111-22-33 или 8 999 111 22 33."
    result = pipeline.run(text, store)
    assert result.counts[EntityKind.PHONE] == 3
    phone_store_aliases = [a for a, k, _ in store.items() if k is EntityKind.PHONE]
    assert len(phone_store_aliases) == 1


def test_source_alias_collision_resolved() -> None:
    pipeline = Pipeline.default(use_ner=False)
    store = MappingStore()
    text = "В договоре упоминается ТЕЛ1 как старый шифр. Новый телефон +7 999 111 22 33."
    result = pipeline.run(text, store)
    assert "ТЕЛ1" in result.masked_text
    phone_aliases = [a for a, k, _ in store.items() if k is EntityKind.PHONE]
    assert phone_aliases and "ТЕЛ1" not in phone_aliases


@pytest.mark.ner
def test_ner_pipeline_finds_person_and_org() -> None:
    try:
        import natasha  # noqa: F401
    except ImportError:
        pytest.skip("natasha not installed")
    pipeline = Pipeline.default(use_ner=True)
    store = MappingStore()
    text = "Иванов Иван Иванович работает в ООО Рога и Копыта в Москве."
    result = pipeline.run(text, store)
    assert result.counts.get(EntityKind.PERSON, 0) >= 1
    assert result.counts.get(EntityKind.ORG, 0) >= 1
    assert "Иванов Иван Иванович" not in result.masked_text
    assert "ООО Рога и Копыта" not in result.masked_text


@pytest.mark.ner
def test_ner_preload_reports_progress() -> None:
    try:
        import natasha  # noqa: F401
    except ImportError:
        pytest.skip("natasha not installed")
    from anonymizer.core.detectors.ner_detector import NatashaDetector

    detector = NatashaDetector()
    messages: list[str] = []
    detector.preload(progress_cb=messages.append)
    assert messages, "preload must emit at least one progress message"
    assert messages[-1].startswith("Модель ROSSILBER Intelligence загружена")
    assert detector.is_loaded


@pytest.mark.ner
def test_ner_consistent_alias_for_name_variants() -> None:
    try:
        import natasha  # noqa: F401
    except ImportError:
        pytest.skip("natasha not installed")
    pipeline = Pipeline.default(use_ner=True)
    store = MappingStore()
    text = (
        "Иванов Иван Иванович подписал договор. "
        "Иванов И.И. также утвердил смету. "
        "Иванову Ивану Ивановичу благодарность."
    )
    pipeline.run(text, store)
    person_aliases = [a for a, k, _ in store.items() if k is EntityKind.PERSON]
    assert len(person_aliases) == 1, (
        f"Expected one alias for three variants of the same name, got {person_aliases}"
    )
