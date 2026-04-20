"""Encrypted `.anon` project format.

A project bundles the original text, the masked text, and the full alias
mapping into a single file encrypted with AES-GCM. The symmetric key is
derived from the user's passphrase via Argon2id.

Binary layout:
    magic       4 bytes   b"ANON"
    version     1 byte    currently 1
    salt        16 bytes  Argon2id salt
    nonce       12 bytes  AES-GCM nonce
    ciphertext  rest      AES-GCM(plaintext_json + 16-byte auth tag)
"""
import json
import os
from dataclasses import dataclass
from pathlib import Path

from anonymizer.core.entities import EntityKind
from anonymizer.core.mapping import MappingStore

_MAGIC = b"ANON"
_VERSION = 1
_SALT_LEN = 16
_NONCE_LEN = 12
_KEY_LEN = 32


class ProjectDecryptionError(ValueError):
    """Raised when the passphrase is wrong or the file is corrupted."""


class ProjectFormatError(ValueError):
    """Raised when the file doesn't look like an Anonymizer project."""


@dataclass
class ProjectData:
    original_text: str
    masked_text: str
    mapping: list[tuple[str, str, str]]  # (alias, kind.value, original)

    @classmethod
    def from_store(
        cls, original_text: str, masked_text: str, store: MappingStore
    ) -> "ProjectData":
        mapping = [(alias, kind.value, original) for alias, kind, original in store.items()]
        return cls(original_text=original_text, masked_text=masked_text, mapping=mapping)

    def to_store(self) -> MappingStore:
        store = MappingStore()
        store.load([(alias, EntityKind(kind), original) for alias, kind, original in self.mapping])
        return store

    def to_json_bytes(self) -> bytes:
        payload = {
            "version": _VERSION,
            "original_text": self.original_text,
            "masked_text": self.masked_text,
            "mapping": self.mapping,
        }
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    @classmethod
    def from_json_bytes(cls, data: bytes) -> "ProjectData":
        obj = json.loads(data.decode("utf-8"))
        mapping = [tuple(item) for item in obj["mapping"]]
        return cls(
            original_text=obj["original_text"],
            masked_text=obj["masked_text"],
            mapping=mapping,  # type: ignore[arg-type]
        )


def _derive_key(passphrase: str, salt: bytes) -> bytes:
    from argon2.low_level import Type, hash_secret_raw

    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=1,
        hash_len=_KEY_LEN,
        type=Type.ID,
    )


def save_project(path: Path, data: ProjectData, passphrase: str) -> None:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if not passphrase:
        raise ValueError("Пароль не может быть пустым.")

    salt = os.urandom(_SALT_LEN)
    nonce = os.urandom(_NONCE_LEN)
    key = _derive_key(passphrase, salt)
    ciphertext = AESGCM(key).encrypt(nonce, data.to_json_bytes(), None)

    with open(path, "wb") as f:
        f.write(_MAGIC)
        f.write(bytes([_VERSION]))
        f.write(salt)
        f.write(nonce)
        f.write(ciphertext)


def load_project(path: Path, passphrase: str) -> ProjectData:
    from cryptography.exceptions import InvalidTag
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    with open(path, "rb") as f:
        raw = f.read()

    header_len = len(_MAGIC) + 1 + _SALT_LEN + _NONCE_LEN
    if len(raw) < header_len + 16:
        raise ProjectFormatError("Файл слишком мал, чтобы быть проектом Anonymizer.")
    if raw[:4] != _MAGIC:
        raise ProjectFormatError("Файл не является проектом Anonymizer (magic mismatch).")
    version = raw[4]
    if version != _VERSION:
        raise ProjectFormatError(f"Неподдерживаемая версия проекта: {version}")
    salt = raw[5 : 5 + _SALT_LEN]
    nonce = raw[5 + _SALT_LEN : 5 + _SALT_LEN + _NONCE_LEN]
    ciphertext = raw[5 + _SALT_LEN + _NONCE_LEN :]

    key = _derive_key(passphrase, salt)
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
    except InvalidTag as exc:
        raise ProjectDecryptionError("Неверный пароль или повреждённый файл.") from exc
    return ProjectData.from_json_bytes(plaintext)
