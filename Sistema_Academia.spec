# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('C:\\Users\\Legen\\AppData\\Local\\Programs\\Python\\Python313\\DLLs\\_tkinter.pyd', '.'), ('C:\\Users\\Legen\\AppData\\Local\\Programs\\Python\\Python313\\DLLs\\tcl86t.dll', '.'), ('C:\\Users\\Legen\\AppData\\Local\\Programs\\Python\\Python313\\DLLs\\tk86t.dll', '.')],
    datas=[
        ('datos_academia.db', '.'),
        ('logo_leoncio_prado.png.png', '.'),
        ('assets/login_escudo.png', 'assets'),
        ('assets/login_letras.png', 'assets'),
        ('assets/login_personaje.png', 'assets'),
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
