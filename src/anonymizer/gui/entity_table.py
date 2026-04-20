"""Entity preview table.

After anonymization completes, shows what was replaced and lets the user
uncheck individual entities — unchecking puts the original value back into
the output text and drops the mapping. Useful for removing false positives
from the NER detector.
"""
from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
)

from anonymizer.core.entities import EntitySpan


@dataclass
class TableRow:
    span: EntitySpan
    alias: str
    enabled: bool = True


class EntityTable(QTableWidget):
    COLUMNS = ("Тип", "Исходный текст", "Псевдоним", "Активно")

    def __init__(self, on_toggle: Callable[[], None]) -> None:
        super().__init__(0, len(self.COLUMNS))
        self._rows: list[TableRow] = []
        self._on_toggle = on_toggle
        self._suppress_events = False
        self.setHorizontalHeaderLabels(self.COLUMNS)
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.itemChanged.connect(self._on_item_changed)

    def set_rows(self, rows: list[TableRow]) -> None:
        self._suppress_events = True
        try:
            self._rows = rows
            self.setRowCount(len(rows))
            for i, row in enumerate(rows):
                kind_item = QTableWidgetItem(row.span.kind.value)
                kind_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                text_item = QTableWidgetItem(row.span.text)
                text_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                text_item.setToolTip(row.span.text)

                alias_item = QTableWidgetItem(row.alias)
                alias_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                check_item = QTableWidgetItem()
                check_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsUserCheckable
                    | Qt.ItemFlag.ItemIsSelectable
                )
                check_item.setCheckState(
                    Qt.CheckState.Checked if row.enabled else Qt.CheckState.Unchecked
                )
                check_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                self.setItem(i, 0, kind_item)
                self.setItem(i, 1, text_item)
                self.setItem(i, 2, alias_item)
                self.setItem(i, 3, check_item)
        finally:
            self._suppress_events = False

    def clear_rows(self) -> None:
        self._rows = []
        self.setRowCount(0)

    def rows(self) -> list[TableRow]:
        return list(self._rows)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._suppress_events or item.column() != 3:
            return
        row_idx = item.row()
        if 0 <= row_idx < len(self._rows):
            self._rows[row_idx].enabled = item.checkState() == Qt.CheckState.Checked
            self._on_toggle()
