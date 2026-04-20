from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from anonymizer.core.mapping import MappingStore
from anonymizer.core.pipeline import AnonymizationResult, Pipeline
from anonymizer.core.reverse import restore


class _AnonymizeWorker(QObject):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, pipeline: Pipeline, text: str, store: MappingStore) -> None:
        super().__init__()
        self._pipeline = pipeline
        self._text = text
        self._store = store

    def run(self) -> None:
        try:
            result = self._pipeline.run(self._text, self._store)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.done.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anonymizer — локальное обезличивание")
        self.resize(1200, 820)
        self._store = MappingStore()
        self._pipeline: Pipeline | None = None
        self._thread: QThread | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        anon_row = QHBoxLayout()
        anon_row.addLayout(self._build_input_column(), stretch=1)
        anon_row.addLayout(self._build_output_column(), stretch=1)
        root.addLayout(anon_row, stretch=1)

        reverse_row = QHBoxLayout()
        reverse_row.addLayout(self._build_ai_response_column(), stretch=1)
        reverse_row.addLayout(self._build_restored_column(), stretch=1)
        root.addLayout(reverse_row, stretch=1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов к работе. Сеть не используется.")

    def _build_input_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Исходный текст"))
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Вставьте текст документа. Поддерживаются номера телефонов, "
            "email, ИНН, СНИЛС, ОГРН, паспорт, номера карт и счетов, "
            "даты рождения, ФИО, названия организаций и локации."
        )
        col.addWidget(self.input_edit)

        controls = QHBoxLayout()
        self.anon_btn = QPushButton("Обезличить")
        self.anon_btn.clicked.connect(self._on_anonymize)
        controls.addWidget(self.anon_btn)
        self.ner_checkbox = QCheckBox("Использовать Natasha (ФИО/ОРГ/АДРЕС)")
        self.ner_checkbox.setChecked(True)
        controls.addWidget(self.ner_checkbox)
        controls.addStretch()
        col.addLayout(controls)
        return col

    def _build_output_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Обезличенный текст"))
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        col.addWidget(self.output_edit)
        self.copy_btn = QPushButton("Скопировать в буфер")
        self.copy_btn.clicked.connect(self._on_copy_output)
        col.addWidget(self.copy_btn)
        return col

    def _build_ai_response_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Ответ ИИ (вставьте сюда)"))
        self.ai_response_edit = QTextEdit()
        self.ai_response_edit.setPlaceholderText(
            "Вставьте ответ ИИ-сервиса, содержащий псевдонимы."
        )
        col.addWidget(self.ai_response_edit)
        self.restore_btn = QPushButton("Восстановить оригинальные данные")
        self.restore_btn.clicked.connect(self._on_restore)
        col.addWidget(self.restore_btn)
        return col

    def _build_restored_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Восстановленный текст"))
        self.restored_edit = QTextEdit()
        self.restored_edit.setReadOnly(True)
        col.addWidget(self.restored_edit)
        return col

    def _on_anonymize(self) -> None:
        self.run_anonymize(async_=True)

    def run_anonymize(self, *, async_: bool = True) -> None:
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("Нет текста для обезличивания.")
            return

        use_ner = self.ner_checkbox.isChecked()
        if self._pipeline is None or use_ner != self._pipeline_uses_ner():
            self.statusBar().showMessage(
                "Загрузка моделей Natasha (только при первом запуске)…"
                if use_ner
                else "Подготовка детекторов…"
            )
            QGuiApplication.processEvents()
            self._pipeline = Pipeline.default(use_ner=use_ner)

        if not async_:
            result = self._pipeline.run(text, self._store)
            self._on_anonymize_done(result)
            return

        self._set_busy(True)
        self.statusBar().showMessage("Анализ текста…")
        self._thread = QThread(self)
        worker = _AnonymizeWorker(self._pipeline, text, self._store)
        worker.moveToThread(self._thread)
        self._thread.started.connect(worker.run)
        worker.done.connect(self._on_anonymize_done)
        worker.failed.connect(self._on_anonymize_failed)
        worker.done.connect(self._thread.quit)
        worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _pipeline_uses_ner(self) -> bool:
        if self._pipeline is None:
            return False
        from anonymizer.core.detectors.ner_detector import NatashaDetector
        return any(isinstance(d, NatashaDetector) for d in self._pipeline.detectors)

    def _on_anonymize_done(self, result: AnonymizationResult) -> None:
        self._set_busy(False)
        self.output_edit.setPlainText(result.masked_text)
        summary = self._format_summary(result)
        self.statusBar().showMessage(summary)

    def _on_anonymize_failed(self, message: str) -> None:
        self._set_busy(False)
        self.statusBar().showMessage(f"Ошибка: {message}")

    def _format_summary(self, result: AnonymizationResult) -> str:
        if not result.counts:
            return "Сущностей не найдено."
        parts = [f"{kind.value}: {n}" for kind, n in sorted(result.counts.items())]
        return "Найдено — " + ", ".join(parts)

    def _set_busy(self, busy: bool) -> None:
        self.anon_btn.setEnabled(not busy)
        self.ner_checkbox.setEnabled(not busy)

    def _on_copy_output(self) -> None:
        QGuiApplication.clipboard().setText(self.output_edit.toPlainText())
        self.statusBar().showMessage("Обезличенный текст скопирован в буфер.")

    def _on_restore(self) -> None:
        text = self.ai_response_edit.toPlainText()
        self.restored_edit.setPlainText(restore(text, self._store))
        self.statusBar().showMessage("Восстановление выполнено.")
