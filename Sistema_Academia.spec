# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

# Rutas de los DLL de Tcl/Tk resueltas contra el interprete que ejecuta este
# build (antes estaban fijas a la carpeta de usuario de otra maquina y el
# build fallaba en cualquier equipo distinto de ese).
_dlls_dir = Path(sys.base_prefix) / "DLLs"

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        (str(_dlls_dir / '_tkinter.pyd'), '.'),
        (str(_dlls_dir / 'tcl86t.dll'), '.'),
        (str(_dlls_dir / 'tk86t.dll'), '.'),
    ],
    datas=[
        ('assets/login_escudo.png', 'assets'),
        ('assets/login_letras.png', 'assets'),
        ('assets/login_personaje.png', 'assets'),
        ('assets/logo_apmipol.png', 'assets'),
        ('assets/logo_apmipol_recortado.png', 'assets'),
        ('assets/firma_reporte.png', 'assets'),
        ('assets/app_personaje.ico', 'assets'),
    ],
    hiddenimports=['tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.filedialog', 'tkinter.constants'],
    hookspath=['pyinstaller_hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Sistema_Academia',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/app_personaje.ico',
    version='version_info.txt',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Sistema_Academia',
)
