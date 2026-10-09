"""Detection quality: names, addresses, labelled requisites, false positives."""
import pytest

from anonymizer.core.entities import EntityKind
from anonymizer.core.mapping import MappingStore
from anonymizer.core.pipeline import Pipeline
from anonymizer.core.reverse import restore


def _spans(text: str, use_ner: bool = False):
    store = MappingStore()
    result = Pipeline.default(use_ner=use_ner).run(text, store)
    return result, store


def _found(text: str, kind: EntityKind) -> list[str]:
    result, _ = _spans(text)
    return [s.text for s in result.spans if s.kind is kind]


# ------------------------------------------------------------------ persons
@pytest.fixture(autouse=True, scope="module")
def _dictionary():
    pytest.importorskip("natasha")


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Павлов Алексей Сергеевич; Соколова Анна Викторовна.",
         ["Павлов Алексей Сергеевич", "Соколова Анна Викторовна"]),
        ("передали Ивановой Марине Петровне документы", ["Ивановой Марине Петровне"]),
        ("автор Полина Викторовна Лабораторная", ["Полина Викторовна Лабораторная"]),
        ("Подписал Иванов И.И. и согласовал А. В. Сидоров.", ["Иванов И.И.", "А. В. Сидоров"]),
        ("ИВАНОВ ИВАН ИВАНОВИЧ", ["ИВАНОВ ИВАН ИВАНОВИЧ"]),
        ("Уважаемая Анна Петровна, добрый день.", ["Анна Петровна"]),
        ("Фёдоров Артём Ильич", ["Фёдоров Артём Ильич"]),
    ],
)
def test_person_rule_detector(text: str, expected: list[str]) -> None:
    assert _found(text, EntityKind.PERSON) == expected


def test_person_detector_ignores_ordinary_capitalised_words() -> None:
    text = "Приказ утверждён. Москва и Санкт-Петербург. Важная информация: Отправитель."
    assert _found(text, EntityKind.PERSON) == []


def test_linker_variants_and_genders() -> None:
    text = (
        "Иванов Иван Иванович подписал. Иванову Ивану Ивановичу направлено. "
        "Иванов И.И. согласовал. Ивановой Марине Петровне и Ивановой Марии Петровне."
    )
    _, store = _spans(text)
    persons = [a for a, k, _ in store.items() if k is EntityKind.PERSON]
    assert len(persons) == 3


def test_display_form_is_nominative() -> None:
    text = "Передать Ивановой Марине Петровне. Подпись: Иванова Марина Петровна."
    result, store = _spans(text)
    alias = next(a for a, k, _ in store.items() if k is EntityKind.PERSON)
    assert store.original_for(alias) == "Иванова Марина Петровна"
    assert result.masked_text.count(alias) == 2


def test_inflected_surname_propagates() -> None:
    result, store = _spans("Романов Пётр Сергеевич принят. Позже Романову выдали пропуск.")
    assert "Романову" not in result.masked_text
    assert len([a for a, k, _ in store.items() if k is EntityKind.PERSON]) == 1


def test_found_value_masked_everywhere() -> None:
    text = "ИНН 7707083893.\n[Верхний колонтитул]\nКонтрагент 7707083893"
    result, _ = _spans(text)
    assert "7707083893" not in result.masked_text


def test_aliases_numbered_in_reading_order() -> None:
    result, _ = _spans("Тел. +7 999 111-22-33, затем +7 999 444-55-66.")
    assert result.masked_text.index("ТЕЛ1") < result.masked_text.index("ТЕЛ2")


# ---------------------------------------------------------------- requisites
def test_bic_not_kpp_and_kpp_by_label() -> None:
    result, _ = _spans("БИК 049999999, КПП 770701001, просто 044525225")
    kinds = {s.text: s.kind for s in result.spans}
    assert kinds["049999999"] is EntityKind.BIC
    assert kinds["770701001"] is EntityKind.KPP
    assert kinds["044525225"] is EntityKind.BIC


def test_labelled_values_masked_even_with_bad_checksum() -> None:
    result, _ = _spans("ИНН: 1234567890, СНИЛС 123-456-789 00, р/с 40702810000000000000")
    kinds = {s.kind for s in result.spans}
    assert {EntityKind.INN, EntityKind.SNILS, EntityKind.ACCOUNT} <= kinds


def test_passport_with_series_and_number_sign() -> None:
    assert _found("паспорт серия 45 06 № 123456 выдан", EntityKind.PASSPORT) == ["45 06 № 123456"]


def test_secret_after_label() -> None:
    result, _ = _spans("логин admin, пароль: Qwerty123! — не сообщать. Токен доступа выдан.")
    assert [s.text for s in result.spans if s.kind is EntityKind.API_KEY] == ["Qwerty123!"]
    assert "доступа" in result.masked_text


def test_dates_only_with_birth_context() -> None:
    result, _ = _spans("Договор от 09.10.2026. Дата рождения: 12.03.1985. Родился 5 мая 1980 г.")
    dobs = [s.text for s in result.spans if s.kind is EntityKind.DOB]
    assert dobs == ["12.03.1985", "5 мая 1980 г."]
    assert "09.10.2026" in result.masked_text


def test_address_merged_into_one_entity() -> None:
    found = _found("Адрес: 125009, г. Москва, ул. Тверская, д. 7, кв. 15.", EntityKind.LOCATION)
    assert found == ["125009, г. Москва, ул. Тверская, д. 7, кв. 15"]


def test_year_before_g_is_not_a_city() -> None:
    assert _found("В 2026 г. Сидоров уволился.", EntityKind.LOCATION) == []


def test_phones_international_and_local() -> None:
    found = _found("моб. +375 29 123 45 67, раб. (495) 123-45-67", EntityKind.PHONE)
    assert found == ["+375 29 123 45 67", "(495) 123-45-67"]


def test_bare_domain_detected_but_not_filenames() -> None:
    result, _ = _spans("сайт www.rossilber.ru, файл writers.py, почта a@b.ru")
    urls = [s.text for s in result.spans if s.kind is EntityKind.URL]
    assert urls == ["www.rossilber.ru"]


# ------------------------------------------------------------------ formulas
@pytest.mark.parametrize(
    "formula", ["NaOH", "H₂SO₄", "CuSO₄·5H₂O", "(NH4)2SO4", "K[Fe(CN)6]", "C6H12O6", "KOH"]
)
def test_formula_matched_whole(formula: str) -> None:
    assert _found(f"Реактив {formula} получен.", EntityKind.FORMULA) == [formula]


@pytest.mark.parametrize("word", ["IP", "CO", "NO", "II", "SPb", "HDMI", "USB"])
def test_abbreviation_is_not_formula(word: str) -> None:
    assert _found(f"Поле {word} заполнено.", EntityKind.FORMULA) == []


# ------------------------------------------------------- false positives/NER
@pytest.mark.ner
def test_ner_false_positives_filtered() -> None:
    result, _ = _spans(
        "Файл DOCX открыт в Microsoft Word. КОНТРОЛЬНАЯ ФРАЗА ДЛЯ КОММЕНТАРИЯ. CO2 и NO.",
        use_ner=True,
    )
    masked = {s.text for s in result.spans if s.kind is EntityKind.ORG}
    assert masked == set()


@pytest.mark.ner
def test_org_keeps_closing_quote() -> None:
    result, _ = _spans("Отправитель: ООО «Лаборатория Тестовых Решений». Далее.", use_ner=True)
    assert "»" not in result.masked_text.split("Отправитель:")[1].split(".")[0]


def test_allowlist_respected() -> None:
    store = MappingStore()
    result = Pipeline.default(use_ner=False, allowlist=["ООО «Россильбер»"]).run(
        "Поставщик ООО «Россильбер», покупатель ООО «Ромашка».", store
    )
    assert "ООО «Россильбер»" in result.masked_text
    assert "Ромашка" not in result.masked_text


# ------------------------------------------------------------------ restore
def test_restore_exact_round_trip_with_variants() -> None:
    text = "Иванов Иван Иванович и Иванов И.И.; тел. 8 (999) 120-45-67 и +7 (999) 120-45-67."
    result, store = _spans(text)
    assert restore(result.masked_text, store) == text


def test_restore_ai_answer_uses_full_form() -> None:
    text = "Иванов Иван Иванович и Иванов И.И. подписали."
    result, store = _spans(text)
    alias = next(a for a, k, _ in store.items() if k is EntityKind.PERSON)
    assert restore(f"Ответ: {alias} прав.", store) == "Ответ: Иванов Иван Иванович прав."


def test_restore_does_not_confuse_alias_prefixes() -> None:
    store = MappingStore()
    for i in range(1, 13):
        store.alias_for(EntityKind.PHONE, str(i), display_original=f"+7 900 000-00-{i:02d}")
    assert restore("ТЕЛ1 и ТЕЛ12", store) == "+7 900 000-00-01 и +7 900 000-00-12"
