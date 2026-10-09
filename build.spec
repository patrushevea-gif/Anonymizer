# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH)

_PACKAGES = (
    "natasha",
    "slovnet",
    "navec",
    "razdel",
    "pymorphy2",
    "pymorphy2_dicts_ru",
    "yargy",
    "ipymarkup",
    "intervaltree",
    "sortedcontainers",
    "dawg_python",
    "docx",
    "lxml",
    "openpyxl",
    "pdfplumber",
    "pdfminer",
    "cryptography",
    "argon2",
)

datas = [
    (str(ROOT / "assets" / "icon.ico"), "assets"),
]
binaries = []
hiddenimports = []
for pkg in _PACKAGES:
    try:
        d, b, h = collect_all(pkg)
    except Exception:
        continue
    datas += d
    binaries += b
    hiddenimports += h

_ICON_PATH = str(ROOT / "assets" / "icon.ico")

a = Analysis(
    [str(ROOT / "src" / "anonymizer" / "__main__.py")],
    pathex=[str(ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    icon=_ICON_PATH,
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
