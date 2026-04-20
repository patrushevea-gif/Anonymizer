from dataclasses import dataclass
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
