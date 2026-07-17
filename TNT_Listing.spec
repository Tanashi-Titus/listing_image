# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec cho TNT Listing Image (PySide6 + Playwright)."""
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []
hiddenimports = ["core", "ui_listing", "tnt_license", "cryptography"]

# Playwright cần kèm driver (node) — collect_all lấy hết data package.
for pkg in ("playwright",):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

# gom submodule local để chắc chắn không sót
hiddenimports += collect_submodules("core")
hiddenimports += collect_submodules("ui_listing")

a = Analysis(
    ["app_listing.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "scipy"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="TNT_Listing",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # app cửa sổ, không console
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="TNT_Listing",
)
