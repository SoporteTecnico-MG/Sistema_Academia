import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

# Resuelto contra el interprete que corre el build (antes apuntaba a la
# carpeta de usuario de otra maquina y el build fallaba en cualquier otra).
_tcl_dir = Path(sys.base_prefix) / "tcl"

datas = (
    collect_data_files("tkinter")
    + [
        (str(_tcl_dir / "tcl8.6"), "_tcl_data"),
        (str(_tcl_dir / "tk8.6"), "_tk_data"),
    ]
)
