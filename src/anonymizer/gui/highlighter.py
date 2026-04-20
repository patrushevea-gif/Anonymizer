"""Visual highlighting of detected entities in a QTextEdit.

Uses QTextEdit.setExtraSelections() which paints colored backgrounds over
character ranges without modifying the document. The user can still edit
freely; we just clear and reapply on each anonymization.
"""
from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from anonymizer.core.entities import EntityKind, EntitySpan

# A muted, high-contrast palette — every color is readable on the dark theme
# background and clearly distinguishable from its neighbours.
KIND_COLORS: dict[EntityKind, str] = {
    EntityKind.PERSON:         "#ff5577",  # rose
    EntityKind.POSITION:       "#ff99cc",  # soft pink
    EntityKind.ORG:            "#00d4ff",  # electric blue
    EntityKind.PHONE:          "#ffcc33",  # amber
    EntityKind.EMAIL:          "#66ddcc",  # teal
    EntityKind.INN:            "#cc88ff",  # lavender
    EntityKind.SNILS:          "#cc88ff",  # lavender
    EntityKind.PASSPORT:       "#ff8844",  # orange
    EntityKind.CARD:           "#ffd700",  # gold
    EntityKind.OGRN:           "#99bbff",  # cornflower
    EntityKind.ACCOUNT:        "#88aaff",  # muted blue
    EntityKind.KPP:            "#aaccff",  # ice blue
    EntityKind.LOCATION:       "#77ff77",  # green
    EntityKind.DOB:            "#ff9977",  # peach
    EntityKind.IP:             "#88ffaa",  # mint
    EntityKind.URL:            "#55ccee",  # sky
    EntityKind.IBAN:           "#bbaaff",  # periwinkle
    EntityKind.BIC:            "#aabbee",  # slate
    EntityKind.CAR_PLATE:      "#ffaa77",  # tan
    EntityKind.DRIVER_LICENSE: "#ffbb99",  # apricot
    EntityKind.OMS:            "#77ddaa",  # sage
}


def _highlight_format(kind: EntityKind) -> QTextCharFormat:
    fmt = QTextCharFormat()
    color = QColor(KIND_COLORS.get(kind, "#888888"))
    # Semi-transparent background, so the selection doesn't scream.
    color.setAlpha(70)
    fmt.setBackground(color)
    # A solid underline in the full color makes the type legible at a glance.
    underline_color = QColor(KIND_COLORS.get(kind, "#888888"))
    fmt.setUnderlineColor(underline_color)
    fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
    return fmt


def highlight_spans(edit: QTextEdit, spans: list[EntitySpan]) -> None:
    selections: list[QTextEdit.ExtraSelection] = []
    doc = edit.document()
    for span in spans:
        cursor = QTextCursor(doc)
        cursor.setPosition(span.start)
        cursor.setPosition(span.end, QTextCursor.MoveMode.KeepAnchor)
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor
        selection.format = _highlight_format(span.kind)
        selections.append(selection)
    edit.setExtraSelections(selections)


def clear_highlights(edit: QTextEdit) -> None:
    edit.setExtraSelections([])
