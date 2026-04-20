from pathlib import Path


def test_batch_anonymizes_txt_files(tmp_path: Path) -> None:
    from anonymizer.core.pipeline import Pipeline
    from anonymizer.io.batch import collect_files, run_batch

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "a.txt").write_text(
        "Позвоните +7 999 111 22 33 или ivan@example.com", encoding="utf-8"
    )
    (src_dir / "b.txt").write_text(
        "ИНН 7707083893, счёт 40702810900000000001", encoding="utf-8"
    )
    files = collect_files(src_dir)
    assert len(files) == 2

    out_dir = tmp_path / "out"
    pipeline = Pipeline.default(use_ner=False)
    results = run_batch(pipeline, files, out_dir)

    assert all(r.error is None for r in results), [r.error for r in results]
    assert all(r.destination is not None and r.destination.exists() for r in results)

    a_out = (out_dir / "a_anon.txt").read_text(encoding="utf-8")
    assert "+7 999 111 22 33" not in a_out
    assert "ivan@example.com" not in a_out


def test_batch_filters_unsupported_files(tmp_path: Path) -> None:
    from anonymizer.io.batch import collect_files

    (tmp_path / "note.md").write_text("ignored", encoding="utf-8")
    (tmp_path / "data.txt").write_text("+7 999 111 22 33", encoding="utf-8")
    files = collect_files(tmp_path)
    assert len(files) == 1
    assert files[0].name == "data.txt"
