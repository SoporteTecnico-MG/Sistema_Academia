from PyInstaller.utils.hooks import collect_data_files

datas = (
    collect_data_files("tkinter")
    + [
        (
            r"C:\Users\Legen\AppData\Local\Programs\Python\Python313\tcl\tcl8.6",
            "_tcl_data",
        ),
        (
            r"C:\Users\Legen\AppData\Local\Programs\Python\Python313\tcl\tk8.6",
            "_tk_data",
        ),
    ]
)
