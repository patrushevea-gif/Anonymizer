"""Acceptance test № 1 — the QA document that failed on the previous build.

``fixtures/acceptance_test_1.docx`` is the synthetic test document supplied
by QA (all values are fictional). Every defect from the QA report is
asserted here so it can never come back:

* P0 — data left in headers, footers, comments and document properties;
* P0 — 11 of 12 ordinary Russian full names left unmasked;
* P1 — false positives (DOCX, Microsoft), misclassification (IP as formula,
  contract date as birth date, BIK as KPP), dangling quote after ОРГ;
* P1 — formulas masked partially (H₂ФОРМУЛА3₄);
* P1 — run formatting collapsed into the first run, hidden text revealed.
"""
import re
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("lxml")

FIXTURE = Path(__file__).parent / "fixtures" / "acceptance_test_1.docx"

SECRETS = [
    # body
    "Иванов Иван Иванович", "Иванов И.И.", "Ивановой Марине Петровне",
    "Ивановой Марии Петровне", "Лаборатория Тестовых Решений",
    "+7 (999) 000-11-22", "8 (999) 120-45-67", "ivanov-qa@example.invalid",
    "office-qa@example.invalid", "https://qa.test.example", "192.0.2.47",
    "Примерск", "Тестовая", "9900123450", "990012345668", "987-654-321 83",
    "4111 1111 1111 1111", "Романову", "Петру", "Сергеевичу",
    "Сидорова Наталья Аркадьевна", "sk-test-NOT-REAL-93A1E8C50F12",
    "049999999", "40702810900000000001",
    # hidden text
    "Антонова Полина Георгиевна", "secret-hidden@example.invalid", "+7 999 888-77-66",
    # the twelve names
    "Павлов Алексей Сергеевич", "Соколова Анна Викторовна", "Смирнов Кирилл Андреевич",
    "Орлова Екатерина Дмитриевна", "Фёдоров Артём Ильич", "Кузнецова Ольга Николаевна",
    "Морозов Павел Романович", "Зайцева Елена Борисовна", "Медведев Игорь Львович",
    "Никитина Алина Валерьевна", "Егоров Дмитрий Александрович", "Волкова Инна Михайловна",
    # header / footer / comment / metadata
    "Иванова Марина Петровна", "header-qa@example.invalid", "+7 (999) 120-45-67",
    "Степанов Денис Львович", "comment-qa@example.invalid", "+7 999 543-21-00",
    "Полина Викторовна Лабораторная", "metapii@example.invalid", "+7 999 301-20-10",
    "QA Тестировщик", "Fictional Author", "Synthetic Only",
]

MUST_SURVIVE = [
    "DOCX", "Microsoft Word", "Сайт и IP", "09.10.2026", "9 октября 2026 года",
    "БИК ", "pH 7,0", "LAB-2026-0047", "QA-017",
]


def _all_xml_text(data: bytes) -> str:
    """Every text node and attribute of every XML part, tags stripped."""
    chunks = []
    with zipfile.ZipFile(__import__("io").BytesIO(data)) as zf:
        for name in zf.namelist():
            if name.endswith((".xml", ".rels")):
                xml = zf.read(name).decode("utf-8", errors="replace")
                chunks.append(re.sub(r"<[^>]+>", "", xml))
                chunks.extend(re.findall(r'="([^"]*)"', xml))
    return "\n".join(chunks)


def _paragraph_runs(data: bytes, needle: str) -> list[tuple[str, str]]:
    import io

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml = zf.read("word/document.xml").decode("utf-8")
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S):
        if needle in re.sub(r"<[^>]+>", "", p):
            out = []
            for r in re.findall(r"<w:r[ >].*?</w:r>", p, flags=re.S):
                props = "".join(sorted(re.findall(r"<w:(b|i|u|color|vanish)\b", r)))
                text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", r, flags=re.S))
                out.append((props, text))
            return out
    raise AssertionError(f"paragraph with {needle!r} not found")


def _run(use_ner: bool):
    from anonymizer.core.mapping import MappingStore
    from anonymizer.core.pipeline import Pipeline
    from anonymizer.io.ooxml import DocxDocument

    doc = DocxDocument.open(FIXTURE)
    store = MappingStore()
    result = Pipeline.default(use_ner=use_ner).run(doc.text, store)
    data, report = doc.anonymize(result.spans, store)
    return doc, store, result, data, report


@pytest.fixture(scope="module", params=[False, pytest.param(True, marks=pytest.mark.ner)])
def processed(request):
    pytest.importorskip("natasha")
    return _run(use_ner=request.param)


def test_no_secret_left_anywhere_in_package(processed) -> None:
    _, _, _, data, report = processed
    text = _all_xml_text(data)
    leaked = [s for s in SECRETS if s in text]
    assert leaked == []
    assert report.ok, report.leaks


def test_every_part_was_processed(processed) -> None:
    _, _, _, _, report = processed
    for part in ("word/document.xml", "word/header1.xml", "word/footer1.xml",
                 "word/comments.xml", "docProps/core.xml"):
        assert part in report.parts_changed
    assert "thumbnail" in report.metadata_removed


def test_twelve_names_each_get_own_alias(processed) -> None:
    _, store, result, _, _ = processed
    names = [
        "Павлов Алексей Сергеевич", "Соколова Анна Викторовна", "Смирнов Кирилл Андреевич",
        "Орлова Екатерина Дмитриевна", "Фёдоров Артём Ильич", "Кузнецова Ольга Николаевна",
        "Морозов Павел Романович", "Зайцева Елена Борисовна", "Медведев Игорь Львович",
        "Никитина Алина Валерьевна", "Егоров Дмитрий Александрович", "Волкова Инна Михайловна",
    ]
    aliases = {store.original_for(a): a for a in store.aliases()}
    assert all(n in aliases for n in names)
    assert len({aliases[n] for n in names}) == 12
    # Aliases already present in the source text are never reused.
    assert "ФИО1" not in store.aliases() and "ФИО10" not in store.aliases()
    assert "ФИО1, ФИО10" in result.masked_text


def test_name_variants_linked_and_distinguished(processed) -> None:
    _, store, _, _, _ = processed
    by_variant = {v: a for v, a in store.all_variants()}
    assert by_variant["Иванов И.И."] == by_variant["Иванов Иван Иванович"]
    # Header (nominative) and body (dative) forms are the same person …
    assert by_variant["Иванова Марина Петровна"] == by_variant["Ивановой Марине Петровне"]
    # … but Марина and Мария are different people.
    assert by_variant["Ивановой Марии Петровне"] != by_variant["Ивановой Марине Петровне"]


def test_no_false_positives_or_misclassification(processed) -> None:
    from anonymizer.core.entities import EntityKind

    _, _, result, data, _ = processed
    text = _all_xml_text(data)
    for keep in MUST_SURVIVE:
        assert keep in text, keep
    kinds = {s.text: s.kind for s in result.spans}
    assert kinds["192.0.2.47"] is EntityKind.IP
    assert kinds["049999999"] is EntityKind.BIC
    assert EntityKind.DOB not in kinds.values()
    assert not any(s.kind is EntityKind.FORMULA and s.text == "IP" for s in result.spans)
    assert kinds["ООО «Лаборатория Тестовых Решений»"] is EntityKind.ORG
    assert "ОРГ1»" not in result.masked_text


def test_formulas_masked_whole(processed) -> None:
    _, _, result, _, _ = processed
    formulas = {s.text for s in result.spans if s.kind.value == "ФОРМУЛА"}
    assert formulas == {"NaOH", "H₂SO₄", "CuSO₄·5H₂O"}
    assert "₄" not in result.masked_text.split("Технологические обозначения:")[1].split("\n")[0]


def test_run_formatting_preserved(processed) -> None:
    _, _, _, data, _ = processed
    sender = _paragraph_runs(data, "Отправитель")
    assert sender[0] == ("b", "Отправитель: ")
    assert sender[1][0] == ""  # the organisation stays in a regular run
    assert sender[2] == ("b", "Ответственный: ")

    quality = _paragraph_runs(data, "Важная информация")
    props = [p for p, _ in quality]
    assert "colori" in props  # italic coloured name run kept
    assert ("u", "неизменность технических параметров") in quality

    split = _paragraph_runs(data, "следующему сотруднику")
    assert split[1][0] == "bcolor" and re.fullmatch(r"ФИО\d+", split[1][1])


def test_hidden_text_stays_hidden(processed) -> None:
    _, _, _, data, _ = processed
    runs = _paragraph_runs(data, "конец проверяемой зоны")
    hidden = [t for p, t in runs if "vanish" in p]
    assert hidden and hidden[0].startswith("СКРЫТО: ФИО")
    visible = "".join(t for p, t in runs if "vanish" not in p)
    assert "СКРЫТО" not in visible


def test_round_trip_restores_document_exactly(processed, tmp_path: Path) -> None:
    from anonymizer.io.ooxml import DocxDocument

    doc, store, _, data, _ = processed
    anon = tmp_path / "anon.docx"
    anon.write_bytes(data)
    restored_bytes, count = DocxDocument.open(anon).restore(store)
    assert count > 40
    restored = DocxDocument(restored_bytes)
    assert restored.text == doc.text


def test_output_opens_with_python_docx(processed, tmp_path: Path) -> None:
    docx = pytest.importorskip("docx")
    _, _, _, data, _ = processed
    out = tmp_path / "out.docx"
    out.write_bytes(data)
    document = docx.Document(str(out))
    assert len(document.tables) == 1
    assert document.sections[0].header.paragraphs[0].text.startswith("ТЕСТ / КОНТРОЛЬНАЯ ОБЛАСТЬ")
