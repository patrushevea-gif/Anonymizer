from anonymizer.core.entities import EntityKind, EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import apply_mask
from anonymizer.core.pipeline import anonymize
from anonymizer.core.reverse import restore


def test_mapping_is_consistent():
    store = MappingStore()
    a1 = store.alias_for(EntityKind.PHONE, "+7 999 111 22 33")
    a2 = store.alias_for(EntityKind.PHONE, "+7 999 111 22 33")
    a3 = store.alias_for(EntityKind.PHONE, "+7 999 222 33 44")
    assert a1 == a2
    assert a1 != a3
    assert a1 == "ТЕЛ1"
    assert a3 == "ТЕЛ2"


def test_mapping_reverse_lookup():
    store = MappingStore()
    alias = store.alias_for(EntityKind.PERSON, "Иванов Иван Иванович")
    assert store.original_for(alias) == "Иванов Иван Иванович"
    assert store.original_for("nonexistent") is None


def test_apply_mask_replaces_spans_correctly():
    store = MappingStore()
    text = "Позвоните +7 999 111 22 33 или напишите ivan@example.com"
    spans = [
        EntitySpan(EntityKind.PHONE, 10, 26, "+7 999 111 22 33"),
        EntitySpan(EntityKind.EMAIL, 40, 57, "ivan@example.com"),
    ]
    out = apply_mask(text, spans, store)
    assert "+7 999 111 22 33" not in out
    assert "ivan@example.com" not in out
    assert "ТЕЛ1" in out
    assert "EMAIL1" in out


def test_restore_round_trip():
    store = MappingStore()
    original = "+7 999 111 22 33"
    alias = store.alias_for(EntityKind.PHONE, original)
    ai_response = f"Позвоните по номеру {alias}, пожалуйста."
    restored = restore(ai_response, store)
    assert original in restored
    assert alias not in restored


def test_anonymize_passthrough_without_detectors():
    store = MappingStore()
    text = "Тестовый текст без настоящих детекторов."
    result = anonymize(text, store)
    assert result.masked_text == text
    assert result.spans == []


def test_main_window_constructs():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    from anonymizer.gui.main_window import MainWindow

    window = MainWindow()
    assert window.windowTitle().startswith("Anonymizer")
    window.ner_checkbox.setChecked(False)
    window.input_edit.setPlainText("Просто текст без персональных данных.")
    window.run_anonymize(async_=False)
    assert "Просто текст" in window.output_edit.toPlainText()
    del window
    app.processEvents()
