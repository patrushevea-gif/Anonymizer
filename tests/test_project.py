from pathlib import Path

import pytest


def _crypto_available() -> bool:
    try:
        import argon2.low_level  # noqa: F401
        import cryptography.hazmat.primitives.ciphers.aead  # noqa: F401
    except ImportError:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _crypto_available(),
    reason="cryptography and argon2-cffi required for project tests",
)


def test_project_round_trip(tmp_path: Path) -> None:
    from anonymizer.core.entities import EntityKind
    from anonymizer.core.mapping import MappingStore
    from anonymizer.core.project import ProjectData, load_project, save_project

    store = MappingStore()
    store.alias_for(EntityKind.PHONE, "+7 999 111 22 33")
    store.alias_for(EntityKind.EMAIL, "ivan@example.com")

    data = ProjectData.from_store(
        original_text="Иван, +7 999 111 22 33, ivan@example.com",
        masked_text="Иван, ТЕЛ1, EMAIL1",
        store=store,
    )
    path = tmp_path / "project.anon"
    save_project(path, data, "secret-pass-123")

    loaded = load_project(path, "secret-pass-123")
    assert loaded.original_text == data.original_text
    assert loaded.masked_text == data.masked_text
    assert sorted(loaded.mapping) == sorted(data.mapping)

    restored_store = loaded.to_store()
    assert restored_store.original_for("ТЕЛ1") == "+7 999 111 22 33"
    assert restored_store.original_for("EMAIL1") == "ivan@example.com"


def test_project_wrong_passphrase_raises(tmp_path: Path) -> None:
    from anonymizer.core.mapping import MappingStore
    from anonymizer.core.project import (
        ProjectData,
        ProjectDecryptionError,
        load_project,
        save_project,
    )

    path = tmp_path / "project.anon"
    save_project(
        path,
        ProjectData.from_store("original", "masked", MappingStore()),
        "correct-password",
    )
    with pytest.raises(ProjectDecryptionError):
        load_project(path, "wrong-password")


def test_project_rejects_non_anon_file(tmp_path: Path) -> None:
    from anonymizer.core.project import ProjectFormatError, load_project

    path = tmp_path / "not_a_project.anon"
    path.write_bytes(b"this is not an Anonymizer project file")
    with pytest.raises(ProjectFormatError):
        load_project(path, "any-password")


def test_project_masked_text_not_in_ciphertext(tmp_path: Path) -> None:
    """Basic sanity: the encrypted file should not leak plaintext secrets."""
    from anonymizer.core.mapping import MappingStore
    from anonymizer.core.project import ProjectData, save_project

    path = tmp_path / "project.anon"
    secret = "VERY_SECRET_PHONE_88005553535"
    save_project(
        path,
        ProjectData.from_store(secret, "MASKED", MappingStore()),
        "password",
    )
    assert secret.encode("utf-8") not in path.read_bytes()
