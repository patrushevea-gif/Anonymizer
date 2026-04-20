import logging
import os
import platform
import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from anonymizer.core.detectors.ner_detector import NatashaDetector
from anonymizer.core.mapping import MappingStore
from anonymizer.core.pipeline import AnonymizationResult, Pipeline
from anonymizer.core.reverse import restore

_log = logging.getLogger(__name__)


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


class _PreloadWorker(QObject):
    progress = Signal(str)
    done = Signal()
    failed = Signal(str)

    def __init__(self, detector: NatashaDetector) -> None:
        super().__init__()
        self._detector = detector

    def run(self) -> None:
        try:
            self._detector.preload(progress_cb=self.progress.emit)
        except Exception as exc:
            _log.exception("Natasha preload failed")
            self.failed.emit(str(exc))
            return
        self.done.emit()


class MainWindow(QMainWindow):
    def __init__(self, log_file: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Anonymizer — локальное обезличивание")
        self.resize(1200, 820)
        self._store = MappingStore()
        self._ner_detector = NatashaDetector()
        self._pipeline: Pipeline | None = None
        self._thread: QThread | None = None
        self._preload_thread: QThread | None = None
        self._preload_started = False
        self._log_file = log_file
        self._build_ui()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._preload_started and self.ner_checkbox.isChecked():
            self._start_preload()

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
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setMaximumWidth(200)
        self._progress.setTextVisible(False)
        self._progress.hide()
        self.statusBar().addPermanentWidget(self._progress)

        if self._log_file:
            log_btn = QPushButton("Открыть лог")
            log_btn.setFixedHeight(20)
            log_btn.setStyleSheet("font-size: 11px;")
            log_btn.clicked.connect(self._on_open_log)
            self.statusBar().addPermanentWidget(log_btn)

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
        self.ner_checkbox.toggled.connect(self._on_ner_toggled)
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

    def _on_ner_toggled(self, checked: bool) -> None:
        if checked and not self._preload_started:
            self._start_preload()

    def _start_preload(self) -> None:
        self._preload_started = True
        self._progress.show()
        self.statusBar().showMessage(
            "Загрузка моделей Natasha в фоне — первое обезличивание станет быстрее…"
        )
        self._preload_thread = QThread(self)
        worker = _PreloadWorker(self._ner_detector)
        worker.moveToThread(self._preload_thread)
        self._preload_thread.started.connect(worker.run)
        worker.progress.connect(self._on_preload_progress)
        worker.done.connect(self._on_preload_done)
        worker.failed.connect(self._on_preload_failed)
        worker.done.connect(self._preload_thread.quit)
        worker.failed.connect(self._preload_thread.quit)
        self._preload_thread.finished.connect(worker.deleteLater)
        self._preload_thread.finished.connect(self._preload_thread.deleteLater)
        self._preload_thread.finished.connect(self._clear_preload_thread)
        self._preload_thread.start()

    def _on_preload_progress(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def _clear_preload_thread(self) -> None:
        self._preload_thread = None

    def _on_preload_done(self) -> None:
        if self._thread is None:
            self._progress.hide()
            self.statusBar().showMessage("Модели Natasha загружены, готов к работе.")
        else:
            self.statusBar().showMessage("Модели загружены, идёт анализ текста…")

    def _on_preload_failed(self, message: str) -> None:
        self._progress.hide()
        suffix = f"\n\nЛог: {self._log_file}" if self._log_file else ""
        self.statusBar().showMessage(f"Ошибка загрузки моделей: {message}")
        QMessageBox.critical(
            self,
            "Ошибка загрузки Natasha",
            f"Не удалось загрузить NLP-модели:\n{message}{suffix}\n\n"
            "Попробуйте снять галочку «Использовать Natasha» и повторить обезличивание.",
        )

    def _on_open_log(self) -> None:
        if not self._log_file or not self._log_file.exists():
            QMessageBox.information(self, "Лог", "Файл лога не найден.")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(str(self._log_file))  # type: ignore[attr-defined]
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", str(self._log_file)])
            else:
                subprocess.Popen(["xdg-open", str(self._log_file)])
        except Exception as exc:
            QMessageBox.information(self, "Лог", f"Путь к файлу лога:\n{self._log_file}\n\nОшибка открытия: {exc}")

    def _on_anonymize(self) -> None:
        self.run_anonymize(async_=True)

    def run_anonymize(self, *, async_: bool = True) -> None:
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("Нет текста для обезличивания.")
            return

        use_ner = self.ner_checkbox.isChecked()
        if self._pipeline is None or use_ner != self._pipeline_uses_ner():
            self._pipeline = Pipeline.default(
                use_ner=use_ner,
                ner_detector=self._ner_detector if use_ner else None,
            )

        if not async_:
            result = self._pipeline.run(text, self._store)
            self._on_anonymize_done(result)
            return

        self._set_busy(True)
        self._progress.show()
        if use_ner and not self._ner_detector.is_loaded:
            self.statusBar().showMessage(
                "Дозагрузка моделей Natasha и анализ текста…"
            )
        else:
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
        self._thread.finished.connect(self._clear_thread)
        self._thread.start()

    def _clear_thread(self) -> None:
        self._thread = None

    def _pipeline_uses_ner(self) -> bool:
        if self._pipeline is None:
            return False
        return any(isinstance(d, NatashaDetector) for d in self._pipeline.detectors)

    def _on_anonymize_done(self, result: AnonymizationResult) -> None:
        self._set_busy(False)
        self._progress.hide()
        self.output_edit.setPlainText(result.masked_text)
        self.statusBar().showMessage(self._format_summary(result))

    def _on_anonymize_failed(self, message: str) -> None:
        self._set_busy(False)
        self._progress.hide()
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
