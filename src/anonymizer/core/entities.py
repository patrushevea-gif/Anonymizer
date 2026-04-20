from dataclasses import dataclass, field
from enum import StrEnum


class EntityKind(StrEnum):
    PERSON = "ФИО"
    POSITION = "ДОЛЖНОСТЬ"
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
    IP = "IP"
    URL = "URL"
    IBAN = "IBAN"
    BIC = "БИК"
    CAR_PLATE = "АВТО"
    DRIVER_LICENSE = "ВУ"
    OMS = "ОМС"
    API_KEY = "APIKEY"
    FORMULA = "ФОРМУЛА"
    CHEMICAL = "ВЕЩЕСТВО"


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
