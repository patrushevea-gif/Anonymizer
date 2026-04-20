from dataclasses import dataclass, field
from enum import StrEnum


class EntityKind(StrEnum):
    PERSON = "ФИО"
    ORG = "ОРГ"
    PHONE = "ТЕЛ"
    EMAIL = "EMAIL"
    INN = "ИНН"
    SNILS = "СНИЛС"
    PASSPORT = "ПАСПОРТ"
    CARD = "КАРТА"
    OGRN = "ОГРН"
    ACCOUNT = "СЧЕТ"
    KPP = "КПП"
    LOCATION = "АДРЕС"
    DOB = "ДАТАРОЖД"


@dataclass(frozen=True)
class EntitySpan:
    kind: EntityKind
    start: int
    end: int
    text: str
    normalized_key: str | None = field(default=None)
    priority: int = field(default=0)

    @property
    def key(self) -> str:
        return self.normalized_key if self.normalized_key is not None else self.text
