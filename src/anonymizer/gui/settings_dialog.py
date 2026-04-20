"""Settings dialog — categorized entity toggles, themed to match the app."""
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from anonymizer.core.config import Config
from anonymizer.core.entities import EntityKind

# Human-readable label per kind.
KIND_LABELS: dict[EntityKind, str] = {
    EntityKind.PERSON:         "ФИО",
    EntityKind.POSITION:       "Должность",
    EntityKind.DOB:            "Дата рождения",
    EntityKind.ORG:            "Организации",
    EntityKind.LOCATION:       "Адреса / локации",
    EntityKind.PHONE:          "Телефоны",
    EntityKind.EMAIL:          "Email",
    EntityKind.URL:            "URL (http / https)",
    EntityKind.IP:             "IP-адреса",
    EntityKind.INN:            "ИНН",
    EntityKind.SNILS:          "СНИЛС",
    EntityKind.PASSPORT:       "Паспорт РФ",
    EntityKind.OGRN:           "ОГРН / ОГРНИП",
    EntityKind.KPP:            "КПП",
    EntityKind.OMS:            "Полисы ОМС",
    EntityKind.DRIVER_LICENSE: "Водительские удостоверения",
    EntityKind.CARD:           "Номера карт",
    EntityKind.ACCOUNT:        "Расчётные счета",
    EntityKind.IBAN:           "IBAN",
    EntityKind.BIC:            "БИК банков",
    EntityKind.CAR_PLATE:      "Автомобильные номера",
    EntityKind.API_KEY:        "API-ключи / токены",
    EntityKind.FORMULA:        "Химические формулы",
    EntityKind.CHEMICAL:       "Химические вещества и реактивы",
}

# Logical groupings shown in the settings dialog.
GROUPS: list[tuple[str, tuple[EntityKind, ...]]] = [
    ("Персональные данные", (
        EntityKind.PERSON,
        EntityKind.POSITION,
        EntityKind.DOB,
    )),
    ("Организации и адреса", (
        EntityKind.ORG,
        EntityKind.LOCATION,
    )),
    ("Контакты и сеть", (
        EntityKind.PHONE,
        EntityKind.EMAIL,
        EntityKind.URL,
        EntityKind.IP,
    )),
    ("Документы", (
        EntityKind.INN,
        EntityKind.SNILS,
        EntityKind.PASSPORT,
        EntityKind.OGRN,
        EntityKind.KPP,
        EntityKind.OMS,
        EntityKind.DRIVER_LICENSE,
    )),
    ("Финансы", (
        EntityKind.CARD,
        EntityKind.ACCOUNT,
        EntityKind.IBAN,
        EntityKind.BIC,
    )),
    ("Транспорт", (
        EntityKind.CAR_PLATE,
    )),
    ("Технические / исследовательские данные", (
        EntityKind.API_KEY,
        EntityKind.FORMULA,
        EntityKind.CHEMICAL,
    )),
]


class _Card(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("card")


class SettingsDialog(QDialog):
    def __init__(self, config: Config, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("settings")
        self.setWindowTitle("Настройки — ANONYMIZER ROSSILBER")
        self.resize(620, 720)
        self._config = config
        self._checkboxes: dict[EntityKind, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 16)
        root.setSpacing(14)

        root.addWidget(self._header())

        # Scroll area for groups so the dialog scales on small screens.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        scroll_layout = QVBoxLayout(container)
        scroll_layout.setContentsMargins(0, 0, 8, 0)
        scroll_layout.setSpacing(14)
        for title, kinds in GROUPS:
            scroll_layout.addWidget(self._build_group(title, kinds, config))
        scroll_layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, stretch=1)

        root.addWidget(self._appearance_panel())
        root.addWidget(self._buttons())

    # --------------------------------------------------------------- sections
    def _header(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        title = QLabel("НАСТРОЙКИ")
        title.setObjectName("section")
        subtitle = QLabel(
            "Выберите типы данных для поиска и маскирования. "
            "Снятые галочки означают, что данные этого типа не будут обезличиваться."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        return w

    def _build_group(self, title: str, kinds: tuple[EntityKind, ...], cfg: Config) -> QWidget:
        card = _Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 10, 16, 14)
        layout.setSpacing(6)
        header = QLabel(title.upper())
        header.setObjectName("group_header")
        layout.addWidget(header)

        # All-on / all-off row.
        bulk = QHBoxLayout()
        bulk.setSpacing(8)
        all_on = QPushButton("Все")
        all_on.setObjectName("ghost")
        all_off = QPushButton("Ничего")
        all_off.setObjectName("ghost")
        all_on.clicked.connect(lambda: self._set_group(kinds, True))
        all_off.clicked.connect(lambda: self._set_group(kinds, False))
        bulk.addStretch()
        bulk.addWidget(all_on)
        bulk.addWidget(all_off)
        layout.addLayout(bulk)

        for kind in kinds:
            cb = QCheckBox(f"{KIND_LABELS[kind]}    ({kind.value})")
            cb.setChecked(kind in cfg.enabled_kinds)
            self._checkboxes[kind] = cb
            layout.addWidget(cb)
        return card

    def _appearance_panel(self) -> QWidget:
        card = _Card()
        layout = QHBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        header = QLabel("ВНЕШНИЙ ВИД")
        header.setObjectName("group_header")
        layout.addWidget(header)
        layout.addStretch()
        layout.addWidget(QLabel("Тема:"))
        self._theme_combo = QComboBox()
        self._theme_combo.addItem("Тёмная", "dark")
        self._theme_combo.addItem("Светлая", "light")
        idx = 0 if self._config.theme == "dark" else 1
        self._theme_combo.setCurrentIndex(idx)
        layout.addWidget(self._theme_combo)
        return card

    def _buttons(self) -> QWidget:
        bar = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bar.button(QDialogButtonBox.StandardButton.Ok).setText("Сохранить")
        bar.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        bar.accepted.connect(self.accept)
        bar.rejected.connect(self.reject)
        return bar

    # ---------------------------------------------------------------- helpers
    def _set_group(self, kinds: tuple[EntityKind, ...], enabled: bool) -> None:
        for kind in kinds:
            cb = self._checkboxes.get(kind)
            if cb is not None:
                cb.setChecked(enabled)

    def result_config(self) -> Config:
        self._config.enabled_kinds = {
            kind for kind, cb in self._checkboxes.items() if cb.isChecked()
        }
        self._config.theme = self._theme_combo.currentData()
        return self._config

    def showEvent(self, event) -> None:
        super().showEvent(event)
        from anonymizer.gui.theme import apply_native_titlebar
        apply_native_titlebar(self, dark=self._config.theme == "dark")
