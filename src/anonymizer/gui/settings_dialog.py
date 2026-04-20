"""Settings dialog: toggle which entity kinds are detected."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QVBoxLayout,
)

from anonymizer.core.config import Config
from anonymizer.core.entities import EntityKind

# Human-readable label + a short hint per kind.
KIND_LABELS: dict[EntityKind, str] = {
    EntityKind.PERSON: "ФИО",
    EntityKind.POSITION: "Должность",
    EntityKind.ORG: "Организации",
    EntityKind.PHONE: "Телефоны",
    EntityKind.EMAIL: "Email",
    EntityKind.INN: "ИНН",
    EntityKind.SNILS: "СНИЛС",
    EntityKind.PASSPORT: "Паспорт РФ",
    EntityKind.CARD: "Номера карт",
    EntityKind.OGRN: "ОГРН / ОГРНИП",
    EntityKind.ACCOUNT: "Расчётные счета",
    EntityKind.KPP: "КПП",
    EntityKind.LOCATION: "Адреса / локации",
    EntityKind.DOB: "Даты рождения",
    EntityKind.IP: "IP-адреса",
    EntityKind.URL: "URL (http/https)",
    EntityKind.IBAN: "IBAN",
    EntityKind.BIC: "БИК банков",
    EntityKind.CAR_PLATE: "Автомобильные номера",
    EntityKind.DRIVER_LICENSE: "Водительские удостоверения",
    EntityKind.OMS: "Полисы ОМС",
}


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Настройки детекторов")
        self.resize(520, 600)
        self._config = config
        self._checkboxes: dict[EntityKind, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        title = QLabel("Выберите типы данных для поиска и маскирования")
        title.setObjectName("section")
        root.addWidget(title)

        hint = QLabel(
            "Снятые галочки означают, что данные этого типа не будут "
            "обезличиваться. Полезно для снижения ложных срабатываний."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        grid = QGridLayout()
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(8)
        items = list(KIND_LABELS.items())
        mid = (len(items) + 1) // 2
        for i, (kind, label) in enumerate(items):
            cb = QCheckBox(f"{label}  ({kind.value})")
            cb.setChecked(kind in config.enabled_kinds)
            self._checkboxes[kind] = cb
            col = 0 if i < mid else 1
            row = i if i < mid else i - mid
            grid.addWidget(cb, row, col, alignment=Qt.AlignmentFlag.AlignLeft)
        root.addLayout(grid)

        root.addStretch()

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def result_config(self) -> Config:
        self._config.enabled_kinds = {
            kind for kind, cb in self._checkboxes.items() if cb.isChecked()
        }
        return self._config
