from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
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
from anonymizer.core.pipeline import anonymize
from anonymizer.core.reverse import restore


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Anonymizer — локальное обезличивание")
        self.resize(1200, 800)
        self._store = MappingStore()
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        anon_row = QHBoxLayout()
        anon_row.addLayout(self._build_input_column())
        anon_row.addLayout(self._build_output_column())
        root.addLayout(anon_row, stretch=1)

        reverse_row = QHBoxLayout()
        reverse_row.addLayout(self._build_ai_response_column())
        reverse_row.addLayout(self._build_restored_column())
        root.addLayout(reverse_row, stretch=1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов к работе. Сеть не используется.")

    def _build_input_column(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.addWidget(QLabel("Исходный текст"))
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "Вставьте текст документа или перетащите файл (в следующих итерациях)."
        )
        col.addWidget(self.input_edit)
        self.anon_btn = QPushButton("Обезличить")
        self.anon_btn.clicked.connect(self._on_anonymize)
        col.addWidget(self.anon_btn)
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
        text = self.input_edit.toPlainText()
        result = anonymize(text, self._store)
        self.output_edit.setPlainText(result.masked_text)
        self.statusBar().showMessage(
            f"Найдено сущностей: {len(result.spans)} (заглушка детекторов — iter 1)"
        )

    def _on_copy_output(self) -> None:
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self.output_edit.toPlainText())
        self.statusBar().showMessage("Обезличенный текст скопирован в буфер.")

    def _on_restore(self) -> None:
        text = self.ai_response_edit.toPlainText()
        self.restored_edit.setPlainText(restore(text, self._store))
        self.statusBar().showMessage("Восстановление выполнено.")
