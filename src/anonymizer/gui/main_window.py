import logging
import os
import platform
import subprocess
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
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
from anonymizer.core.entities import EntitySpan
from anonymizer.core.mapping import MappingStore
from anonymizer.core.masking import apply_mask
from anonymizer.core.pipeline import AnonymizationResult, Pipeline
from anonymizer.core.project import (
    ProjectData,
    ProjectDecryptionError,
    ProjectFormatError,
    load_project,
    save_project,
)
from anonymizer.core.resolve import resolve_overlaps
from anonymizer.core.reverse import restore
from anonymizer.gui.entity_table import EntityTable, TableRow

_log = logging.getLogger(__name__)


def _divider(orientation: str = "h") -> QFrame:
    frame = QFrame()
    frame.setObjectName("divider" if orientation == "h" else "vdivider")
    frame.setFrameShape(QFrame.Shape.HLine if orientation == "h" else QFrame.Shape.VLine)
    return frame


class MainWindow(QMainWindow):
    def __init__(self, log_file: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("ANONYMIZER")
        self.resize(1400, 900)
        self.setAcceptDrops(True)

        self._store = MappingStore()
        self._ner_detector = NatashaDetector()
        self._pipeline: Pipeline | None = None
        self._preload_started = False
        self._log_file = log_file
        self._last_result: AnonymizationResult | None = None
        self._last_input_text: str = ""

        self._build_ui()
        self._wire_shortcuts()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 8)
        root.setSpacing(12)

        root.addLayout(self._build_header())
        root.addWidget(_divider("h"))

        anon_row = QHBoxLayout()
        anon_row.setSpacing(16)
        anon_row.addLayout(self._build_input_column(), stretch=1)
        anon_row.addLayout(self._build_output_column(), stretch=1)
        root.addLayout(anon_row, stretch=3)

        root.addWidget(self._build_section_label("Маппинги сущностей"))
        self.entity_table = EntityTable(on_toggle=self._on_entity_toggled)
        self.entity_table.setMinimumHeight(160)
        self.entity_table.setMaximumHeight(240)
        root.addWidget(self.entity_table, stretch=1)

        root.addWidget(self._build_section_label("Восстановление"))
        reverse_row = QHBoxLayout()
        reverse_row.setSpacing(16)
        reverse_row.addLayout(self._build_ai_response_column(), stretch=1)
        reverse_row.addLayout(self._build_restored_column(), stretch=1)
        root.addLayout(reverse_row, stretch=2)

        self._build_status_bar()

    def _build_header(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(18)

        brand = QLabel("ANONYMIZER")
        brand.setObjectName("brand")
        bar.addWidget(brand)

        tag = QLabel("LOCAL • ZERO-NETWORK • AES-256")
        tag.setObjectName("tagline")
        bar.addWidget(tag)

        bar.addStretch()

        self.open_btn = QPushButton("Открыть файл")
        self.open_btn.clicked.connect(self._on_open_file)
        bar.addWidget(self.open_btn)

        self.save_btn = QPushButton("Сохранить результат")
        self.save_btn.clicked.connect(self._on_save_result)
        bar.addWidget(self.save_btn)

        self.save_proj_btn = QPushButton("Сохранить проект")
        self.save_proj_btn.clicked.connect(self._on_save_project)
        bar.addWidget(self.save_proj_btn)

        self.load_proj_btn = QPushButton("Загрузить проект")
        self.load_proj_btn.clicked.connect(self._on_load_project)
        bar.addWidget(self.load_proj_btn)

        return bar

    def _build_section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("section")
        return label

    def _build_input_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._build_section_label("Исходный текст"))
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Перетащите файл (.txt, .docx, .xlsx) или вставьте текст.\n\n"
            "Поддерживаются: телефоны, email, ИНН, СНИЛС, ОГРН, паспорт, "
            "номера карт и счетов, даты рождения, ФИО, названия организаций и локации."
        )
        col.addWidget(self.input_edit)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        self.anon_btn = QPushButton("ОБЕЗЛИЧИТЬ")
        self.anon_btn.setObjectName("primary")
        self.anon_btn.clicked.connect(self._on_anonymize)
        self.anon_btn.setToolTip("Ctrl+Enter")
        controls.addWidget(self.anon_btn)

        self.ner_checkbox = QCheckBox("Natasha NER (ФИО / организации / адреса)")
        self.ner_checkbox.setChecked(True)
        self.ner_checkbox.toggled.connect(self._on_ner_toggled)
        controls.addWidget(self.ner_checkbox)
        controls.addStretch()
        col.addLayout(controls)
        return col

    def _build_output_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._build_section_label("Обезличенный текст"))
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        col.addWidget(self.output_edit)
        self.copy_btn = QPushButton("Скопировать в буфер")
        self.copy_btn.clicked.connect(self._on_copy_output)
        self.copy_btn.setToolTip("Ctrl+Shift+C")
        col.addWidget(self.copy_btn)
        return col

    def _build_ai_response_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(8)
        col.addWidget(self._build_section_label("Ответ ИИ"))
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
        col.setSpacing(8)
        col.addWidget(self._build_section_label("Восстановленный текст"))
        self.restored_edit = QTextEdit()
        self.restored_edit.setReadOnly(True)
        col.addWidget(self.restored_edit)
        return col

    def _build_status_bar(self) -> None:
        self.setStatusBar(QStatusBar())
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setMaximumWidth(160)
        self._progress.setTextVisible(False)
        self._progress.hide()
        self.statusBar().addPermanentWidget(self._progress)

        net_label = QLabel("● Оффлайн-режим")
        net_label.setObjectName("net_on")
        net_label.setToolTip("Приложение не отправляет данные в сеть.")
        self.statusBar().addPermanentWidget(net_label)

        if self._log_file:
            log_btn = QPushButton("Открыть лог")
            log_btn.setObjectName("ghost")
            log_btn.clicked.connect(self._on_open_log)
            self.statusBar().addPermanentWidget(log_btn)

        self.statusBar().showMessage("Готов к работе")

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._on_open_file)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._on_save_result)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self._on_save_project)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self._on_load_project)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._on_anonymize)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self._on_anonymize)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self, activated=self._on_copy_output)

    # --------------------------------------------------------------- events
    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._preload_started and self.ner_checkbox.isChecked():
            QTimer.singleShot(100, self._preload_sync)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if not urls:
            return
        path = Path(urls[0].toLocalFile())
        self._load_file(path)

    # -------------------------------------------------------------- preload
    def _on_ner_toggled(self, checked: bool) -> None:
        if checked and not self._preload_started:
            QTimer.singleShot(0, self._preload_sync)

    def _preload_sync(self) -> None:
        if self._preload_started:
            return
        self._preload_started = True
        self._progress.show()
        self.anon_btn.setEnabled(False)
        self.ner_checkbox.setEnabled(False)
        self.statusBar().showMessage("Загрузка моделей Natasha…")
        QApplication.processEvents()
        try:
            self._ner_detector.preload(progress_cb=self._on_preload_progress)
        except Exception as exc:
            _log.exception("Natasha preload failed")
            self._progress.hide()
            self.anon_btn.setEnabled(True)
            self.ner_checkbox.setEnabled(True)
            self.statusBar().showMessage(f"Ошибка загрузки: {exc}")
            suffix = f"\n\nЛог: {self._log_file}" if self._log_file else ""
            QMessageBox.critical(
                self,
                "Ошибка загрузки Natasha",
                f"Не удалось загрузить NLP-модели:\n{exc}{suffix}\n\n"
                "Снимите галочку «Natasha NER» и повторите обезличивание.",
            )
            return
        self._progress.hide()
        self.anon_btn.setEnabled(True)
        self.ner_checkbox.setEnabled(True)
        self.statusBar().showMessage("Модели Natasha загружены — готов к работе")

    def _on_preload_progress(self, message: str) -> None:
        self.statusBar().showMessage(message)
        QApplication.processEvents()

    # ----------------------------------------------------------- anonymize
    def _on_anonymize(self) -> None:
        self.run_anonymize()

    def run_anonymize(self, *, async_: bool = False) -> None:
        del async_
        text = self.input_edit.toPlainText()
        if not text.strip():
            self.statusBar().showMessage("Нет текста для обезличивания")
            return

        use_ner = self.ner_checkbox.isChecked()
        if self._pipeline is None or use_ner != self._pipeline_uses_ner():
            self._pipeline = Pipeline.default(
                use_ner=use_ner,
                ner_detector=self._ner_detector if use_ner else None,
            )

        self._set_busy(True)
        self._progress.show()
        self.statusBar().showMessage("Анализ текста…")
        QApplication.processEvents()

        # Start with a fresh store each run so entity numbering is deterministic.
        self._store = MappingStore()
        try:
            result = self._pipeline.run(text, self._store)
        except Exception as exc:
            _log.exception("Pipeline.run failed")
            self._on_anonymize_failed(str(exc))
            return
        self._last_input_text = text
        self._on_anonymize_done(result)

    def _pipeline_uses_ner(self) -> bool:
        if self._pipeline is None:
            return False
        return any(isinstance(d, NatashaDetector) for d in self._pipeline.detectors)

    def _on_anonymize_done(self, result: AnonymizationResult) -> None:
        self._set_busy(False)
        self._progress.hide()
        self._last_result = result
        self.output_edit.setPlainText(result.masked_text)
        self._refresh_entity_table(result.spans)
        self.statusBar().showMessage(self._format_summary(result))

    def _on_anonymize_failed(self, message: str) -> None:
        self._set_busy(False)
        self._progress.hide()
        self.statusBar().showMessage(f"Ошибка: {message}")
        QMessageBox.critical(self, "Ошибка анализа", message)

    def _refresh_entity_table(self, spans: list[EntitySpan]) -> None:
        rows: list[TableRow] = []
        for span in spans:
            alias = self._store._key_to_alias.get((span.kind, span.key))  # noqa: SLF001
            if alias is not None:
                rows.append(TableRow(span=span, alias=alias, enabled=True))
        # De-duplicate rows that have the same (kind, text, alias) triplet.
        seen = set()
        unique: list[TableRow] = []
        for row in rows:
            sig = (row.span.kind, row.span.text, row.alias)
            if sig in seen:
                continue
            seen.add(sig)
            unique.append(row)
        self.entity_table.set_rows(unique)

    def _on_entity_toggled(self) -> None:
        """User toggled one of the entity checkboxes — re-render output."""
        if self._last_result is None:
            return
        disabled_aliases = {row.alias for row in self.entity_table.rows() if not row.enabled}
        # Drop disabled aliases from the store so the restore path no longer
        # knows them either (user explicitly said "this was a false positive").
        for alias in disabled_aliases:
            self._store.drop_alias(alias)

        active_spans = [
            row.span for row in self.entity_table.rows() if row.enabled
        ]
        active_spans = resolve_overlaps(active_spans)
        masked = apply_mask(self._last_input_text, active_spans, self._store)
        self.output_edit.setPlainText(masked)
        remaining = len(self.entity_table.rows()) - len(disabled_aliases)
        self.statusBar().showMessage(
            f"Активно: {remaining} из {len(self.entity_table.rows())}"
        )

    def _format_summary(self, result: AnonymizationResult) -> str:
        if not result.counts:
            return "Сущностей не найдено"
        parts = [f"{kind.value}: {n}" for kind, n in sorted(result.counts.items())]
        return "Найдено — " + "  ·  ".join(parts)

    def _set_busy(self, busy: bool) -> None:
        self.anon_btn.setEnabled(not busy)
        self.ner_checkbox.setEnabled(not busy)
        self.open_btn.setEnabled(not busy)

    # ------------------------------------------------------------- clipboard
    def _on_copy_output(self) -> None:
        QGuiApplication.clipboard().setText(self.output_edit.toPlainText())
        self.statusBar().showMessage("Обезличенный текст скопирован в буфер")

    def _on_restore(self) -> None:
        text = self.ai_response_edit.toPlainText()
        self.restored_edit.setPlainText(restore(text, self._store))
        self.statusBar().showMessage("Восстановление выполнено")

    # -------------------------------------------------------------- file I/O
    def _on_open_file(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть файл",
            "",
            "Документы (*.txt *.docx *.xlsx);;Все файлы (*.*)",
        )
        if path_str:
            self._load_file(Path(path_str))

    def _load_file(self, path: Path) -> None:
        try:
            from anonymizer.io import read_text
            text = read_text(path)
        except Exception as exc:
            _log.exception("Failed to read file: %s", path)
            QMessageBox.critical(self, "Ошибка чтения", f"{exc}")
            return
        self.input_edit.setPlainText(text)
        self.statusBar().showMessage(f"Файл загружен: {path.name}")

    def _on_save_result(self) -> None:
        text = self.output_edit.toPlainText()
        if not text:
            self.statusBar().showMessage("Нечего сохранять")
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить обезличенный текст",
            "anonymized.txt",
            "Текст (*.txt);;Word (*.docx)",
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            from anonymizer.io import write_text
            write_text(path, text)
        except Exception as exc:
            _log.exception("Failed to save file: %s", path)
            QMessageBox.critical(self, "Ошибка сохранения", f"{exc}")
            return
        self.statusBar().showMessage(f"Сохранено: {path.name}")

    # -------------------------------------------------------------- projects
    def _on_save_project(self) -> None:
        if not self._last_result or not self._last_input_text:
            self.statusBar().showMessage("Сначала выполните обезличивание")
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self, "Сохранить проект", "project.anon", "Anonymizer (*.anon)"
        )
        if not path_str:
            return
        passphrase = self._ask_passphrase("Задайте пароль для шифрования проекта", confirm=True)
        if passphrase is None:
            return
        path = Path(path_str)
        if path.suffix.lower() != ".anon":
            path = path.with_suffix(".anon")
        data = ProjectData.from_store(
            original_text=self._last_input_text,
            masked_text=self._last_result.masked_text,
            store=self._store,
        )
        try:
            save_project(path, data, passphrase)
        except Exception as exc:
            _log.exception("Failed to save project")
            QMessageBox.critical(self, "Ошибка сохранения проекта", f"{exc}")
            return
        self.statusBar().showMessage(f"Проект сохранён: {path.name}")

    def _on_load_project(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self, "Загрузить проект", "", "Anonymizer (*.anon)"
        )
        if not path_str:
            return
        passphrase = self._ask_passphrase("Введите пароль от проекта", confirm=False)
        if passphrase is None:
            return
        try:
            data = load_project(Path(path_str), passphrase)
        except ProjectDecryptionError as exc:
            QMessageBox.warning(self, "Не удалось расшифровать", str(exc))
            return
        except ProjectFormatError as exc:
            QMessageBox.warning(self, "Неправильный формат", str(exc))
            return
        except Exception as exc:
            _log.exception("Failed to load project")
            QMessageBox.critical(self, "Ошибка загрузки", f"{exc}")
            return
        self._store = data.to_store()
        self.input_edit.setPlainText(data.original_text)
        self.output_edit.setPlainText(data.masked_text)
        self._last_input_text = data.original_text
        self._last_result = AnonymizationResult(masked_text=data.masked_text)
        self.entity_table.clear_rows()
        self.statusBar().showMessage(
            f"Проект загружен — маппингов: {len(self._store)}"
        )

    def _ask_passphrase(self, prompt: str, *, confirm: bool) -> str | None:
        text, ok = QInputDialog.getText(
            self, "Пароль", prompt, echo=QLineEdit.EchoMode.Password
        )
        if not ok:
            return None
        text = text.strip()
        if not text:
            QMessageBox.warning(self, "Пароль", "Пароль не может быть пустым.")
            return None
        if confirm:
            confirm_text, ok = QInputDialog.getText(
                self, "Пароль", "Повторите пароль", echo=QLineEdit.EchoMode.Password
            )
            if not ok:
                return None
            if confirm_text.strip() != text:
                QMessageBox.warning(self, "Пароль", "Пароли не совпадают.")
                return None
        return text

    # ------------------------------------------------------------------ log
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
            QMessageBox.information(
                self,
                "Лог",
                f"Путь к файлу лога:\n{self._log_file}\n\nОшибка: {exc}",
            )
