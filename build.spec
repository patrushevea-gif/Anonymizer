# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = Path(SPECPATH)

natasha_datas = collect_data_files("natasha", include_py_files=False)
pymorphy_datas = collect_data_files("pymorphy3_dicts_ru", include_py_files=False)
pymorphy_datas += collect_data_files("pymorphy3", include_py_files=False)

hidden = (
    collect_submodules("natasha")
    + collect_submodules("slovnet")
    + collect_submodules("navec")
    + collect_submodules("razdel")
    + collect_submodules("pymorphy3")
    + collect_submodules("pymorphy3_dicts_ru")
    + collect_submodules("ipymarkup")
)

a = Analysis(
    [str(ROOT / "src" / "anonymizer" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=natasha_datas + pymorphy_datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "test",
        "unittest",
        "pytest",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Anonymizer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Anonymizer",
)
