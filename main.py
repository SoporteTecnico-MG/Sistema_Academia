"""Interfaz grafica del Sistema de Gestion Academica.

La aplicacion usa CustomTkinter para manejar inicio de sesion, matricula,
edicion de alumnos, carga diaria de notas, gestion de aulas y generacion de
constancias PDF. La logica de persistencia vive en `database.py` y los reportes
en `reportes.py`.
"""

import calendar
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox
import os
import sys

if getattr(sys, "frozen", False):
    base_tk = Path(sys._MEIPASS) / "tcl"
    os.environ.setdefault("TCL_LIBRARY", str(base_tk / "tcl8.6"))
    os.environ.setdefault("TK_LIBRARY", str(base_tk / "tk8.6"))

import customtkinter as ctk
import database
import excel_io
import reportes

try:
    from PIL import Image
except ImportError:
    Image = None


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

NOMBRE_SISTEMA = "SISTEMA DE GESTION ACADEMICA CRNL LEONCIO PRADO"
LOGO_RUTAS = (
    "logo_leoncio_prado.png.png",
    "logo_leoncio_prado.png",
    "logo_leoncio_prado.jpg",
    "logo.png",
    "logo.jpg",
    "logo.jpeg",
    "imagenes/logo_leoncio_prado.png",
    "imagenes/logo_leoncio_prado.jpg",
    "imagenes/logo.png",
    "imagenes/logo.jpg",
    "imagenes/logo.jpeg",
)
LOGIN_ESCUDO_RUTA = "assets/login_escudo.png"
LOGIN_LETRAS_RUTA = "assets/logo_apmipol_recortado.png"
LOGIN_PERSONAJE_RUTA = "assets/login_personaje.png"
APP_ICONO_RUTA = "assets/app_personaje.ico"
LOGO_MAX_ANCHO = 620
LOGO_MAX_ALTO = 140
LOGO_PANEL_MAX_ANCHO = 760
LOGO_PANEL_MAX_ALTO = 115
NOTAS_ANCHO_CODIGO = 92
NOTAS_ANCHO_DNI = 92
NOTAS_ANCHO_ESTUDIANTE = 190
NOTAS_ANCHO_NOTA = 64
NOTAS_ANCHO_NSP = 60
NOTAS_ALTO_FILA = 42
NOTAS_FONT_FILA = ("Roboto", 11)
NOTAS_COLOR_TEXTO = "#dce4ee"
NOTAS_COLOR_TEXTO_DESHABILITADO = "#9a9a9a"
NOTAS_COLOR_ENTRADA_BG = "#343638"
NOTAS_COLOR_BORDE = "#565b5e"
NOTAS_COLOR_ACENTO = "#1f6aa5"
MAX_RESULTADOS_EDICION = 50
NOTA_MINIMA_DEFAULT = "0"
NOTA_MAXIMA_DEFAULT = "20"
NOTA_APROBATORIA_DEFAULT = "11"
MESES_ES = [
    "",
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


def obtener_directorio_app():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def obtener_directorio_recursos():
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


class App(ctk.CTk):
    """Ventana principal y controladores de la interfaz del sistema."""

    def __init__(self):
        super().__init__()
        self.title(NOMBRE_SISTEMA)
        self.geometry("1200x760")
        self.configurar_icono_ventana()
        self.after(0, self.maximizar_ventana)
        self.usuario_actual = ""
        self.rol_actual = ""
        self.logo_login = None
        self.logo_login_escudo = None
        self.logo_login_letras = None
        self.logo_login_personaje = None
        self.logo_panel = None
        self.logo_panel_escudo = None
        self.logo_panel_letras = None
        self.logo_panel_personaje = None
        self._banner_cache = {}

        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=90, padx=160, fill="both", expand=True)

        self.mostrar_logo_login()
        ctk.CTkLabel(
            self.frame_login,
            text="SISTEMA DE GESTION ACADEMICA",
            font=("Roboto", 20, "bold"),
            wraplength=430
        ).pack(pady=(8, 4))
        ctk.CTkLabel(self.frame_login, text="INICIO DE SESION", font=("Roboto", 18, "bold")).pack(pady=(0, 18))

        self.entry_usr = ctk.CTkEntry(self.frame_login, placeholder_text="Usuario", justify="center")
        self.entry_usr.pack(pady=10)
        self.entry_pwd = ctk.CTkEntry(self.frame_login, placeholder_text="Contrasena", show="*", justify="center")
        self.entry_pwd.pack(pady=10)
        self.entry_usr.bind("<Return>", self.iniciar_sesion)
        self.entry_pwd.bind("<Return>", self.iniciar_sesion)
        self.lbl_login_msg = ctk.CTkLabel(self.frame_login, text="", text_color="red")
        self.lbl_login_msg.pack(pady=5)
        ctk.CTkButton(self.frame_login, text="Ingresar", command=self.iniciar_sesion).pack(pady=20)

    def configurar_icono_ventana(self):
        icono = obtener_directorio_recursos() / APP_ICONO_RUTA
        if icono.exists():
            try:
                self.iconbitmap(str(icono))
            except Exception:
                pass

    def maximizar_ventana(self):
        try:
            self.state("zoomed")
        except Exception:
            self.attributes("-zoomed", True)

    def mostrar_logo_login(self):
        if self.mostrar_banner_login():
            return

        ctk.CTkLabel(
            self.frame_login,
            text="CRNL.\nLEONCIO PRADO",
            width=420,
            height=110,
            corner_radius=8,
            fg_color="#1f6aa5",
            font=("Roboto", 30, "bold")
        ).pack(pady=(22, 8))

    def mostrar_banner_login(self):
        return self.mostrar_banner_institucional(self.frame_login, (150, 145), (430, 135), pady=(20, 8))

    def obtener_imagenes_banner(self, tamano_lateral, tamano_letras):
        """Carga y escala el escudo/letras/personaje una sola vez por tamano solicitado.

        Antes se releian y reescalaban las 3 imagenes desde disco cada vez que se
        cambiaba de panel (Matricula, Notas, Reportes, Aulas); con el cache solo
        se hace una vez por combinacion de tamanos (login y panel).
        """
        clave = (tamano_lateral, tamano_letras)
        if clave in self._banner_cache:
            return self._banner_cache[clave]

        rutas = [
            obtener_directorio_recursos() / LOGIN_ESCUDO_RUTA,
            obtener_directorio_recursos() / LOGIN_LETRAS_RUTA,
            obtener_directorio_recursos() / LOGIN_PERSONAJE_RUTA,
        ]
        if not all(ruta.exists() for ruta in rutas):
            return None

        escudo = Image.open(rutas[0])
        letras = Image.open(rutas[1])
        personaje = Image.open(rutas[2])

        imagenes = (
            ctk.CTkImage(escudo, size=self.calcular_tamano_logo(escudo.size, *tamano_lateral)),
            ctk.CTkImage(letras, size=self.calcular_tamano_logo(letras.size, *tamano_letras)),
            ctk.CTkImage(personaje, size=self.calcular_tamano_logo(personaje.size, *tamano_lateral)),
        )
        self._banner_cache[clave] = imagenes
        return imagenes

    def mostrar_banner_institucional(self, padre, tamano_lateral, tamano_letras, pady=(20, 8)):
        if not Image:
            return False

        imagenes = self.obtener_imagenes_banner(tamano_lateral, tamano_letras)
        if imagenes is None:
            return False
        imagen_escudo, imagen_letras, imagen_personaje = imagenes

        banner = ctk.CTkFrame(padre, fg_color="transparent")
        banner.pack(pady=pady)

        if padre == self.frame_login:
            self.logo_login_escudo = imagen_escudo
            self.logo_login_letras = imagen_letras
            self.logo_login_personaje = imagen_personaje
        else:
            self.logo_panel_escudo = imagen_escudo
            self.logo_panel_letras = imagen_letras
            self.logo_panel_personaje = imagen_personaje

        ctk.CTkLabel(banner, text="", image=imagen_personaje).grid(row=0, column=0, padx=(0, 18))
        ctk.CTkLabel(banner, text="", image=imagen_letras).grid(row=0, column=1, padx=8)
        ctk.CTkLabel(banner, text="", image=imagen_escudo).grid(row=0, column=2, padx=(18, 0))
        return True

    def obtener_ruta_logo(self):
        directorio_recursos = obtener_directorio_recursos()
        return next((directorio_recursos / ruta for ruta in LOGO_RUTAS if (directorio_recursos / ruta).exists()), None)

    def calcular_tamano_logo(self, tamano_original, max_ancho=LOGO_MAX_ANCHO, max_alto=LOGO_MAX_ALTO):
        ancho_original, alto_original = tamano_original
        escala = min(max_ancho / ancho_original, max_alto / alto_original)
        return int(ancho_original * escala), int(alto_original * escala)

    def mostrar_logo_panel(self):
        if self.mostrar_banner_institucional(self.panel_central, (105, 100), (360, 105), pady=(2, 12)):
            return

        ctk.CTkLabel(
            self.panel_central,
            text=NOMBRE_SISTEMA,
            font=("Roboto", 22, "bold"),
            wraplength=760
        ).pack(pady=(5, 16))

    def iniciar_sesion(self, event=None):
        usr, pwd = self.entry_usr.get().strip(), self.entry_pwd.get().strip()
        exito, nombre, rol = database.validar_login(usr, pwd)
        if exito:
            self.usuario_actual, self.rol_actual = usr, rol
            self.frame_login.pack_forget()
            self.construir_interfaz_principal(nombre)
        else:
            self.lbl_login_msg.configure(text="Credenciales incorrectas.")

    def construir_interfaz_principal(self, nombre_usuario):
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar,
            text="SISTEMA DE GESTION\nACADEMICA APMIPOL",
            font=("Roboto", 16, "bold"),
            justify="center",
            wraplength=210
        ).pack(pady=(20, 8), padx=16)
        ctk.CTkLabel(
            self.sidebar,
            text=f"{nombre_usuario}\n[{self.rol_actual}]",
            font=("Roboto", 12),
            text_color="gray"
        ).pack(pady=5)

        ctk.CTkButton(self.sidebar, text="1. Matricula", command=self.mostrar_registro).pack(
            pady=10, padx=20, fill="x"
        )
        if self.rol_actual == "Admin":
            ctk.CTkButton(self.sidebar, text="2. Editar Estudiantes", command=self.mostrar_edicion_estudiantes).pack(
                pady=10, padx=20, fill="x"
            )

        ctk.CTkButton(self.sidebar, text="3. Notas", command=self.mostrar_notas).pack(
            pady=10, padx=20, fill="x"
        )
        ctk.CTkButton(self.sidebar, text="4. Reportes PDF", command=self.mostrar_reportes).pack(
            pady=10, padx=20, fill="x"
        )

        if self.rol_actual == "Admin":
            ctk.CTkButton(
                self.sidebar, text="5. Importar/Exportar Excel", command=self.mostrar_excel
            ).pack(pady=10, padx=20, fill="x")

        if self.rol_actual == "Admin":
            ctk.CTkButton(
                self.sidebar,
                text="Gestion de Aulas",
                fg_color="darkred",
                command=self.mostrar_aulas
            ).pack(pady=30, padx=20, fill="x")

        ctk.CTkButton(
            self.sidebar,
            text="Cerrar Sesion",
            fg_color="#555555",
            hover_color="#333333",
            command=self.cerrar_sesion
        ).pack(side="bottom", pady=25, padx=20, fill="x")

        self.panel_central = ctk.CTkFrame(self)
        self.panel_central.pack(side="right", fill="both", expand=True, padx=20, pady=20)
        self.mostrar_registro()

    def cerrar_sesion(self):
        self.usuario_actual = ""
        self.rol_actual = ""
        self.sidebar.destroy()
        self.panel_central.destroy()
        self.entry_usr.delete(0, "end")
        self.entry_pwd.delete(0, "end")
        self.lbl_login_msg.configure(text="")
        self.frame_login.pack(pady=90, padx=160, fill="both", expand=True)
        self.entry_usr.focus()

    def limpiar_panel(self):
        for widget in self.panel_central.winfo_children():
            widget.destroy()

    def crear_fila_formulario(self, padre, texto, fila, ancho=350):
        etiqueta = ctk.CTkLabel(padre, text=texto, width=150, anchor="e")
        etiqueta.grid(row=fila, column=0, padx=(0, 10), pady=5, sticky="e")
        entrada = ctk.CTkEntry(padre, width=ancho)
        entrada.grid(row=fila, column=1, padx=(0, 0), pady=5, sticky="w")
        return entrada

    def mostrar_mensaje(self, etiqueta, mensaje, color="gray", limpiar=False):
        etiqueta.configure(text=mensaje, text_color=color)
        if limpiar:
            self.after(3000, lambda: self.limpiar_mensaje_si_igual(etiqueta, mensaje))

    def limpiar_mensaje_si_igual(self, etiqueta, mensaje):
        if etiqueta.winfo_exists() and etiqueta.cget("text") == mensaje:
            etiqueta.configure(text="")

    def configurar_limite_numerico(self, entrada, max_digitos):
        validacion = (self.register(lambda valor: valor.isdigit() and len(valor) <= max_digitos or valor == ""), "%P")
        entrada.configure(validate="key", validatecommand=validacion)

    def validar_datos_estudiante(self, codigo, dni, nombres, apellidos, telefono, etiqueta):
        if not codigo or not dni or not nombres or not apellidos or not telefono:
            etiqueta.configure(text="Complete codigo, DNI, nombres, apellidos y celular.", text_color="red")
            return False
        if not codigo.isdigit() or len(codigo) != 6:
            etiqueta.configure(text="El codigo del estudiante debe tener exactamente 6 digitos.", text_color="red")
            return False
        if not dni.isdigit() or len(dni) != 8:
            etiqueta.configure(text="El DNI debe tener exactamente 8 digitos.", text_color="red")
            return False
        if not telefono.isdigit() or len(telefono) != 9:
            etiqueta.configure(text="El celular debe tener exactamente 9 digitos.", text_color="red")
            return False
        return True

    def crear_fila_fecha(self, padre, texto, fila):
        etiqueta = ctk.CTkLabel(padre, text=texto, width=150, anchor="e")
        etiqueta.grid(row=fila, column=0, padx=(0, 10), pady=5, sticky="e")

        contenedor = ctk.CTkFrame(padre, fg_color="transparent")
        contenedor.grid(row=fila, column=1, pady=5, sticky="w")
        entrada = ctk.CTkEntry(contenedor, width=260, justify="center")
        entrada.pack(side="left")
        ctk.CTkButton(
            contenedor,
            text="Calendario",
            width=86,
            command=lambda e=entrada: self.abrir_calendario(e)
        ).pack(side="left", padx=(6, 0))
        return entrada

    def abrir_calendario(self, entrada):
        fecha_base = self.obtener_fecha_desde_entry(entrada) or date.today()
        self.calendario_entry_destino = entrada
        self.calendario_anio = fecha_base.year
        self.calendario_mes = fecha_base.month

        self.calendario_popup = ctk.CTkToplevel(self)
        self.calendario_popup.title("Seleccionar fecha")
        self.calendario_popup.geometry("310x300")
        self.calendario_popup.transient(self)
        self.calendario_popup.grab_set()

        self.calendario_contenido = ctk.CTkFrame(self.calendario_popup, fg_color="transparent")
        self.calendario_contenido.pack(fill="both", expand=True, padx=12, pady=12)
        self.dibujar_calendario()

    def dibujar_calendario(self):
        for widget in self.calendario_contenido.winfo_children():
            widget.destroy()

        cabecera = ctk.CTkFrame(self.calendario_contenido, fg_color="transparent")
        cabecera.grid(row=0, column=0, columnspan=7, sticky="ew", pady=(0, 8))
        ctk.CTkButton(cabecera, text="<", width=34, command=lambda: self.cambiar_mes_calendario(-1)).pack(side="left")
        ctk.CTkLabel(
            cabecera,
            text=f"{MESES_ES[self.calendario_mes]} {self.calendario_anio}",
            width=190,
            font=("Roboto", 14, "bold")
        ).pack(side="left", padx=8)
        ctk.CTkButton(cabecera, text=">", width=34, command=lambda: self.cambiar_mes_calendario(1)).pack(side="left")

        dias = ["L", "M", "M", "J", "V", "S", "D"]
        for col, dia in enumerate(dias):
            ctk.CTkLabel(self.calendario_contenido, text=dia, width=38, font=("Roboto", 12, "bold")).grid(
                row=1, column=col, padx=1, pady=2
            )

        primer_dia, cantidad_dias = calendar.monthrange(self.calendario_anio, self.calendario_mes)
        fila = 2
        columna = primer_dia
        for dia in range(1, cantidad_dias + 1):
            ctk.CTkButton(
                self.calendario_contenido,
                text=str(dia),
                width=38,
                height=28,
                command=lambda d=dia: self.seleccionar_dia_calendario(d)
            ).grid(row=fila, column=columna, padx=1, pady=2)
            columna += 1
            if columna == 7:
                columna = 0
                fila += 1

    def cambiar_mes_calendario(self, delta):
        mes = self.calendario_mes + delta
        if mes < 1:
            self.calendario_mes = 12
            self.calendario_anio -= 1
        elif mes > 12:
            self.calendario_mes = 1
            self.calendario_anio += 1
        else:
            self.calendario_mes = mes
        self.dibujar_calendario()

    def seleccionar_dia_calendario(self, dia):
        fecha = date(self.calendario_anio, self.calendario_mes, dia)
        self.calendario_entry_destino.delete(0, "end")
        self.calendario_entry_destino.insert(0, fecha.strftime("%d/%m/%Y"))
        self.calendario_popup.destroy()

    def obtener_fecha_desde_entry(self, entrada):
        texto = entrada.get().strip()
        if not texto:
            return None
        try:
            return datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            return None

    def convertir_fecha_aula_db(self, entrada, nombre_campo):
        fecha = self.obtener_fecha_desde_entry(entrada)
        if not fecha:
            self.lbl_msg_aula.configure(text=f"Seleccione una fecha valida para {nombre_campo}.", text_color="red")
            return None
        return fecha.strftime("%Y-%m-%d")

    def mostrar_aulas(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(
            self.panel_central,
            text="Programacion de Nuevas Aulas",
            font=("Roboto", 22, "bold")
        ).pack(pady=20)

        formulario = ctk.CTkFrame(self.panel_central, fg_color="transparent")
        formulario.pack(pady=8)

        self.ent_aula_nom = self.crear_fila_formulario(formulario, "Nombre del Aula", 0, ancho=350)
        self.ent_aula_ini = self.crear_fila_fecha(formulario, "Fecha Inicio", 1)
        self.ent_aula_fin = self.crear_fila_fecha(formulario, "Fecha Fin", 2)

        ctk.CTkButton(
            self.panel_central,
            text="Programar Aula",
            command=self.guardar_aula_ui,
            width=350,
            fg_color="green"
        ).pack(pady=20)
        self.lbl_msg_aula = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_msg_aula.pack()

    def guardar_aula_ui(self):
        nom = self.ent_aula_nom.get().strip()
        if not nom or not self.ent_aula_ini.get().strip() or not self.ent_aula_fin.get().strip():
            self.lbl_msg_aula.configure(text="Complete todos los campos.", text_color="red")
            return

        ini = self.convertir_fecha_aula_db(self.ent_aula_ini, "Fecha Inicio")
        fin = self.convertir_fecha_aula_db(self.ent_aula_fin, "Fecha Fin")
        if not ini or not fin:
            return

        if datetime.strptime(fin, "%Y-%m-%d") < datetime.strptime(ini, "%Y-%m-%d"):
            self.lbl_msg_aula.configure(text="La fecha fin no puede ser anterior a la fecha inicio.", text_color="red")
            return

        exito, msj = database.crear_aula(nom, ini, fin)
        self.mostrar_mensaje(self.lbl_msg_aula, msj, "green" if exito else "red", limpiar=exito)

    def mostrar_registro(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(self.panel_central, text="Registro de Estudiantes", font=("Roboto", 22, "bold")).pack(pady=20)
        aulas = database.obtener_aulas_activas()
        self.dict_au = {a[1]: a[0] for a in aulas}

        formulario = ctk.CTkFrame(self.panel_central, fg_color="transparent")
        formulario.pack(pady=4)
        self.e_codigo = self.crear_fila_formulario(formulario, "Codigo de matricula", 0)
        self.cargar_siguiente_codigo_matricula()
        self.e_dni = self.crear_fila_formulario(formulario, "DNI", 1)
        self.e_nom = self.crear_fila_formulario(formulario, "Nombres", 2)
        self.e_ape = self.crear_fila_formulario(formulario, "Apellidos", 3)
        self.e_tel = self.crear_fila_formulario(formulario, "Celular", 4)
        self.configurar_limite_numerico(self.e_codigo, 6)
        self.configurar_limite_numerico(self.e_dni, 8)
        self.configurar_limite_numerico(self.e_tel, 9)

        ctk.CTkLabel(formulario, text="Seleccione Aula", width=150, anchor="e").grid(
            row=5, column=0, padx=(0, 10), pady=5, sticky="e"
        )
        self.cb_au = ctk.CTkComboBox(
            formulario,
            values=list(self.dict_au.keys()) if aulas else ["No hay aulas"],
            width=350
        )
        self.cb_au.grid(row=5, column=1, pady=5, sticky="w")

        ctk.CTkButton(self.panel_central, text="Guardar Estudiante", command=self.guardar_estudiante_ui).pack(pady=20)
        self.lbl_m = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_m.pack()

    def cargar_siguiente_codigo_matricula(self):
        self.e_codigo.delete(0, "end")
        self.e_codigo.insert(0, database.obtener_siguiente_codigo_matricula())

    def guardar_estudiante_ui(self):
        c = self.e_codigo.get().strip().upper()
        d = self.e_dni.get().strip()
        n = self.e_nom.get().strip().upper()
        a = self.e_ape.get().strip().upper()
        t = self.e_tel.get().strip()
        au = self.cb_au.get()

        if au == "No hay aulas":
            self.lbl_m.configure(text="Seleccione un aula valida.", text_color="red")
            return

        if not self.validar_datos_estudiante(c, d, n, a, t, self.lbl_m):
            return

        exito, msj = database.insertar_alumno(c, d, n, a, t, self.dict_au[au], self.usuario_actual)
        if exito:
            self.mostrar_mensaje(self.lbl_m, msj, "green", limpiar=True)
            self.e_dni.delete(0, "end")
            self.e_nom.delete(0, "end")
            self.e_ape.delete(0, "end")
            self.e_tel.delete(0, "end")
            self.cargar_siguiente_codigo_matricula()
            self.e_dni.focus()
        else:
            self.lbl_m.configure(text=msj, text_color="red")

    def mostrar_edicion_estudiantes(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        area_edicion = ctk.CTkScrollableFrame(self.panel_central)
        area_edicion.pack(fill="both", expand=True)
        ctk.CTkLabel(area_edicion, text="Modificar Datos de Estudiantes", font=("Roboto", 22, "bold")).pack(pady=12)

        alumnos = database.obtener_alumnos()
        self.alumnos_edicion = alumnos
        aulas = database.obtener_aulas_activas()
        self.dict_au_edicion = {a[1]: a[0] for a in aulas}
        self.dict_estudiantes_edicion = {}

        buscador = ctk.CTkFrame(area_edicion, fg_color="transparent")
        buscador.pack(fill="x", padx=34, pady=(0, 8))

        campo_ap_pat = ctk.CTkFrame(buscador, fg_color="transparent")
        campo_ap_pat.pack(side="left", padx=4)
        ctk.CTkLabel(campo_ap_pat, text="Apellido paterno").pack(anchor="w")
        self.e_bus_ap_pat = ctk.CTkEntry(campo_ap_pat, width=150)
        self.e_bus_ap_pat.pack()

        campo_ap_mat = ctk.CTkFrame(buscador, fg_color="transparent")
        campo_ap_mat.pack(side="left", padx=4)
        ctk.CTkLabel(campo_ap_mat, text="Apellido materno").pack(anchor="w")
        self.e_bus_ap_mat = ctk.CTkEntry(campo_ap_mat, width=150)
        self.e_bus_ap_mat.pack()

        campo_nombre = ctk.CTkFrame(buscador, fg_color="transparent")
        campo_nombre.pack(side="left", padx=4)
        ctk.CTkLabel(campo_nombre, text="Nombre").pack(anchor="w")
        self.e_bus_nombre = ctk.CTkEntry(campo_nombre, width=150)
        self.e_bus_nombre.pack()

        ctk.CTkButton(buscador, text="Buscar", width=86, command=self.filtrar_estudiantes_edicion).pack(
            side="left", padx=4, pady=(24, 0)
        )
        ctk.CTkButton(buscador, text="Limpiar", width=86, command=self.limpiar_busqueda_estudiantes).pack(
            side="left", padx=4, pady=(24, 0)
        )

        for entrada in (self.e_bus_ap_pat, self.e_bus_ap_mat, self.e_bus_nombre):
            entrada.bind("<KeyRelease>", lambda _event: self.filtrar_estudiantes_edicion())
            entrada.bind("<Return>", lambda _event: self.filtrar_estudiantes_edicion())

        ctk.CTkLabel(area_edicion, text="Resultados de busqueda:").pack(anchor="w", padx=40)
        self.resultados_estudiantes_frame = ctk.CTkScrollableFrame(area_edicion, height=82)
        self.resultados_estudiantes_frame.pack(fill="x", padx=40, pady=6)
        self.actualizar_lista_estudiantes_edicion(alumnos)

        formulario = ctk.CTkFrame(area_edicion, fg_color="transparent")
        formulario.pack(pady=8)

        self.edit_codigo_original = ""
        self.e_edit_codigo = self.crear_fila_formulario(formulario, "Codigo de matricula", 0, ancho=360)
        self.e_edit_dni = self.crear_fila_formulario(formulario, "DNI", 1, ancho=360)
        self.e_edit_nom = self.crear_fila_formulario(formulario, "Nombres", 2, ancho=360)
        self.e_edit_ape = self.crear_fila_formulario(formulario, "Apellidos", 3, ancho=360)
        self.e_edit_tel = self.crear_fila_formulario(formulario, "Celular", 4, ancho=360)
        self.configurar_limite_numerico(self.e_edit_codigo, 6)
        self.configurar_limite_numerico(self.e_edit_dni, 8)
        self.configurar_limite_numerico(self.e_edit_tel, 9)

        ctk.CTkLabel(formulario, text="Aula", width=150, anchor="e").grid(
            row=5, column=0, padx=(0, 10), pady=5, sticky="e"
        )
        self.cb_edit_aula = ctk.CTkComboBox(
            formulario,
            values=list(self.dict_au_edicion.keys()) if aulas else ["No hay aulas"],
            width=360
        )
        self.cb_edit_aula.grid(row=5, column=1, pady=5, sticky="w")

        acciones = ctk.CTkFrame(area_edicion, fg_color="transparent")
        acciones.pack(pady=10)
        ctk.CTkButton(acciones, text="Cargar Datos", command=self.seleccionar_estudiante_edicion).pack(
            side="left", padx=6
        )
        ctk.CTkButton(
            acciones,
            text="Guardar Cambios",
            command=self.guardar_edicion_estudiante_ui,
            fg_color="green"
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            acciones,
            text="Eliminar Estudiante",
            command=self.eliminar_estudiante_ui,
            fg_color="darkred"
        ).pack(side="left", padx=6)

        self.lbl_edit_estudiante = ctk.CTkLabel(area_edicion, text="")
        self.lbl_edit_estudiante.pack(pady=4)

        if alumnos:
            self.seleccionar_estudiante_edicion(alumnos[0][0])

    def actualizar_lista_estudiantes_edicion(self, alumnos):
        # Con miles de estudiantes acumulados (varios ciclos x varias aulas x anio),
        # crear un boton por cada resultado sin filtrar volveria a ser tan lento
        # como la grilla de notas. Se limita cuantos botones se crean de una vez y
        # se pide afinar la busqueda cuando hay mas resultados que el limite.
        self.dict_estudiantes_edicion = {
            f"{alumno[3]}, {alumno[2]} | {alumno[1]} | {alumno[0]}": alumno[0]
            for alumno in alumnos
        }
        for widget in self.resultados_estudiantes_frame.winfo_children():
            widget.destroy()

        if not alumnos:
            ctk.CTkLabel(self.resultados_estudiantes_frame, text="No hay estudiantes").pack(
                anchor="w", padx=8, pady=6
            )
            return

        for alumno in alumnos[:MAX_RESULTADOS_EDICION]:
            texto = f"{alumno[3]}, {alumno[2]} | DNI {alumno[1]} | Cod. {alumno[0]}"
            ctk.CTkButton(
                self.resultados_estudiantes_frame,
                text=texto,
                anchor="w",
                fg_color="#3a3a3a",
                command=lambda codigo=alumno[0]: self.seleccionar_estudiante_edicion(codigo)
            ).pack(fill="x", padx=4, pady=2)

        restantes = len(alumnos) - MAX_RESULTADOS_EDICION
        if restantes > 0:
            ctk.CTkLabel(
                self.resultados_estudiantes_frame,
                text=f"... y {restantes} estudiante(s) mas. Afine la busqueda para verlos.",
                text_color="gray"
            ).pack(anchor="w", padx=8, pady=4)

    def filtrar_estudiantes_edicion(self):
        apellido_paterno = self.e_bus_ap_pat.get().strip().upper()
        apellido_materno = self.e_bus_ap_mat.get().strip().upper()
        nombre = self.e_bus_nombre.get().strip().upper()

        filtrados = []
        for alumno in self.alumnos_edicion:
            nombres = (alumno[2] or "").upper()
            apellidos = (alumno[3] or "").upper()
            if apellido_paterno and apellido_paterno not in apellidos:
                continue
            if apellido_materno and apellido_materno not in apellidos:
                continue
            if nombre and nombre not in nombres:
                continue
            filtrados.append(alumno)

        self.actualizar_lista_estudiantes_edicion(filtrados)
        if filtrados:
            self.seleccionar_estudiante_edicion(filtrados[0][0])
            self.lbl_edit_estudiante.configure(text=f"{len(filtrados)} estudiante(s) encontrado(s).", text_color="gray")
        else:
            self.edit_codigo_original = ""
            self.lbl_edit_estudiante.configure(text="No se encontraron estudiantes con esos datos.", text_color="red")

    def limpiar_busqueda_estudiantes(self):
        for entrada in (self.e_bus_ap_pat, self.e_bus_ap_mat, self.e_bus_nombre):
            entrada.delete(0, "end")
        self.actualizar_lista_estudiantes_edicion(self.alumnos_edicion)
        if self.alumnos_edicion:
            self.seleccionar_estudiante_edicion(self.alumnos_edicion[0][0])

    def seleccionar_estudiante_edicion(self, codigo_matricula=None):
        codigo_matricula = codigo_matricula or self.edit_codigo_original
        if not codigo_matricula:
            self.lbl_edit_estudiante.configure(text="Seleccione un estudiante valido.", text_color="red")
            return

        alumno = database.obtener_alumno_por_codigo(codigo_matricula)
        if not alumno:
            self.lbl_edit_estudiante.configure(text="No se encontraron datos para el estudiante.", text_color="red")
            return

        codigo, dni_actual, nombres, apellidos, telefono, id_aula = alumno
        self.edit_codigo_original = codigo
        for entry, valor in (
            (self.e_edit_codigo, codigo),
            (self.e_edit_dni, dni_actual),
            (self.e_edit_nom, nombres),
            (self.e_edit_ape, apellidos),
            (self.e_edit_tel, telefono or ""),
        ):
            entry.delete(0, "end")
            entry.insert(0, valor)

        aula_nombre = next((nombre for nombre, aula_id in self.dict_au_edicion.items() if aula_id == id_aula), "")
        if aula_nombre:
            self.cb_edit_aula.set(aula_nombre)
        self.lbl_edit_estudiante.configure(text="Datos cargados para edicion.", text_color="gray")

    def guardar_edicion_estudiante_ui(self):
        if not self.edit_codigo_original:
            self.lbl_edit_estudiante.configure(text="Primero seleccione un estudiante.", text_color="red")
            return

        codigo = self.e_edit_codigo.get().strip().upper()
        dni = self.e_edit_dni.get().strip()
        nombres = self.e_edit_nom.get().strip().upper()
        apellidos = self.e_edit_ape.get().strip().upper()
        telefono = self.e_edit_tel.get().strip()
        aula = self.cb_edit_aula.get()

        if aula == "No hay aulas":
            self.lbl_edit_estudiante.configure(text="Seleccione un aula valida.", text_color="red")
            return

        if not self.validar_datos_estudiante(codigo, dni, nombres, apellidos, telefono, self.lbl_edit_estudiante):
            return

        exito, msj = database.actualizar_alumno(
            self.edit_codigo_original,
            codigo,
            dni,
            nombres,
            apellidos,
            telefono,
            self.dict_au_edicion[aula]
        )
        self.mostrar_mensaje(self.lbl_edit_estudiante, msj, "green" if exito else "red", limpiar=exito)
        if exito:
            self.mostrar_edicion_estudiantes()
            self.mostrar_mensaje(self.lbl_edit_estudiante, msj, "green", limpiar=True)

    def eliminar_estudiante_ui(self):
        codigo_matricula = self.edit_codigo_original
        if not codigo_matricula:
            self.lbl_edit_estudiante.configure(text="Seleccione un estudiante valido.", text_color="red")
            return

        seleccion = f"{self.e_edit_ape.get().strip()}, {self.e_edit_nom.get().strip()} | {codigo_matricula}"

        confirmar = messagebox.askyesno(
            "Eliminar estudiante",
            f"Esta accion eliminara al estudiante seleccionado y sus notas.\n\n{seleccion}\n\nDesea continuar?"
        )
        if not confirmar:
            return

        exito, msj = database.eliminar_alumno(codigo_matricula)
        self.mostrar_mensaje(self.lbl_edit_estudiante, msj, "green" if exito else "red", limpiar=exito)
        if exito:
            self.mostrar_edicion_estudiantes()
            self.mostrar_mensaje(self.lbl_edit_estudiante, msj, "green", limpiar=True)

    def mostrar_notas(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(self.panel_central, text="Carga de Notas por Aula", font=("Roboto", 22, "bold")).pack(pady=10)

        aulas = database.obtener_aulas_activas()
        self.dict_aulas_notas = {a[1]: a[0] for a in aulas}
        self.cursos_notas = database.obtener_cursos()
        self.filas_notas = []
        self.evaluaciones_fecha = {}

        controles = ctk.CTkFrame(self.panel_central, fg_color="transparent")
        controles.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(controles, text="Aula:").pack(side="left", padx=(0, 6))
        self.cb_aula_notas = ctk.CTkComboBox(
            controles,
            values=list(self.dict_aulas_notas.keys()) if aulas else ["No hay aulas"],
            width=260
        )
        self.cb_aula_notas.pack(side="left", padx=(0, 10))

        ctk.CTkLabel(controles, text="Fecha:").pack(side="left", padx=(8, 6))
        self.ent_fecha_notas = ctk.CTkEntry(controles, width=112, justify="center")
        self.ent_fecha_notas.insert(0, date.today().strftime("%Y-%m-%d"))
        self.ent_fecha_notas.pack(side="left", padx=(0, 4))
        ctk.CTkButton(controles, text="<", width=32, command=lambda: self.cambiar_fecha_notas(-1)).pack(
            side="left", padx=2
        )
        ctk.CTkButton(controles, text="Hoy", width=48, command=self.usar_fecha_actual_notas).pack(side="left", padx=2)
        ctk.CTkButton(controles, text=">", width=32, command=lambda: self.cambiar_fecha_notas(1)).pack(
            side="left", padx=(2, 10)
        )
        ctk.CTkButton(controles, text="Cargar Aula", command=self.cargar_alumnos_aula).pack(side="left")

        self.contenedor_notas = ctk.CTkScrollableFrame(self.panel_central, height=310)
        self.contenedor_notas.pack(fill="both", expand=True, pady=8)
        self._widgets_filas_notas = []
        self.crear_encabezado_notas()

        self.btn_guardar_notas_aula = ctk.CTkButton(
            self.panel_central,
            text="Guardar Notas del Aula",
            fg_color="green",
            command=self.guardar_notas_aula
        )
        self.btn_guardar_notas_aula.pack(pady=10)
        self.lbl_res = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_res.pack()

    def cargar_alumnos_aula(self):
        for widget in self._widgets_filas_notas:
            widget.destroy()
        self._widgets_filas_notas = []
        self.filas_notas = []

        if not self.cursos_notas:
            self.lbl_res.configure(text="No hay cursos registrados para cargar notas.", text_color="red")
            return

        aula = self.cb_aula_notas.get()
        if aula == "No hay aulas":
            self.lbl_res.configure(text="Primero debe crear un aula.", text_color="red")
            return

        fecha_eval = self.obtener_fecha_notas()
        if not fecha_eval:
            return

        id_aula = self.dict_aulas_notas[aula]
        alumnos = database.obtener_alumnos_por_aula(id_aula)
        if not alumnos:
            self.lbl_res.configure(text="No hay estudiantes registrados en esta aula.", text_color="red")
            return

        self.evaluaciones_fecha = database.obtener_evaluaciones_por_aula_fecha(id_aula, fecha_eval)
        self.lbl_res.configure(text=f"{len(alumnos)} estudiantes cargados para {fecha_eval}.", text_color="gray")

        # Se oculta el contenedor mientras se insertan todas las filas para que el
        # scroll no recalcule su area en cada widget agregado; con aulas de varias
        # decenas de alumnos eso era lo que hacia notoriamente lenta la carga.
        color_fondo = self.obtener_color_fondo_notas()
        self.contenedor_notas.pack_forget()
        try:
            for fila, alumno in enumerate(alumnos, start=1):
                self.crear_fila_notas(fila, alumno, color_fondo)
        finally:
            self.contenedor_notas.pack(fill="both", expand=True, pady=8, before=self.btn_guardar_notas_aula)

    def obtener_color_fondo_notas(self):
        try:
            return self.contenedor_notas._parent_canvas.cget("bg")
        except Exception:
            return "#2b2b2b"

    def obtener_fecha_notas(self):
        fecha_texto = self.ent_fecha_notas.get().strip()
        try:
            datetime.strptime(fecha_texto, "%Y-%m-%d")
            return fecha_texto
        except ValueError:
            self.lbl_res.configure(text="Use una fecha valida con formato AAAA-MM-DD.", text_color="red")
            return None

    def usar_fecha_actual_notas(self):
        self.ent_fecha_notas.delete(0, "end")
        self.ent_fecha_notas.insert(0, date.today().strftime("%Y-%m-%d"))
        self.recargar_notas_si_hay_aula()

    def cambiar_fecha_notas(self, dias):
        fecha_eval = self.obtener_fecha_notas()
        if not fecha_eval:
            return

        nueva_fecha = datetime.strptime(fecha_eval, "%Y-%m-%d").date() + timedelta(days=dias)
        self.ent_fecha_notas.delete(0, "end")
        self.ent_fecha_notas.insert(0, nueva_fecha.strftime("%Y-%m-%d"))
        self.recargar_notas_si_hay_aula()

    def recargar_notas_si_hay_aula(self):
        if self.filas_notas:
            self.cargar_alumnos_aula()

    def crear_encabezado_notas(self):
        self.contenedor_notas.grid_columnconfigure(0, minsize=NOTAS_ANCHO_CODIGO)
        self.contenedor_notas.grid_columnconfigure(1, minsize=NOTAS_ANCHO_DNI)
        self.contenedor_notas.grid_columnconfigure(2, minsize=NOTAS_ANCHO_ESTUDIANTE)

        ctk.CTkLabel(
            self.contenedor_notas,
            text="Codigo",
            width=NOTAS_ANCHO_CODIGO,
            font=("Roboto", 12, "bold"),
            anchor="w"
        ).grid(
            row=0, column=0, padx=3, pady=(4, 8), sticky="ew"
        )
        ctk.CTkLabel(
            self.contenedor_notas,
            text="DNI",
            width=NOTAS_ANCHO_DNI,
            font=("Roboto", 12, "bold"),
            anchor="w"
        ).grid(
            row=0, column=1, padx=3, pady=(4, 8), sticky="ew"
        )
        ctk.CTkLabel(
            self.contenedor_notas,
            text="Estudiante",
            width=NOTAS_ANCHO_ESTUDIANTE,
            font=("Roboto", 12, "bold"),
            anchor="w"
        ).grid(
            row=0, column=2, padx=3, pady=(4, 8), sticky="ew"
        )

        for indice, (_, nombre_curso) in enumerate(self.cursos_notas):
            col_nota = 3 + indice * 2
            col_nsp = col_nota + 1
            self.contenedor_notas.grid_columnconfigure(col_nota, minsize=NOTAS_ANCHO_NOTA)
            self.contenedor_notas.grid_columnconfigure(col_nsp, minsize=NOTAS_ANCHO_NSP)
            ctk.CTkLabel(
                self.contenedor_notas,
                text=nombre_curso,
                height=42,
                font=("Roboto", 12, "bold"),
                wraplength=NOTAS_ANCHO_NOTA + NOTAS_ANCHO_NSP - 8,
                justify="center"
            ).grid(row=0, column=col_nota, columnspan=2, padx=3, pady=(4, 8), sticky="ew")

    def crear_fila_notas(self, fila, alumno, color_fondo):
        # Las celdas de datos usan widgets Tkinter simples (no CustomTkinter): cada
        # CTkEntry/CTkCheckBox registra seguimiento de escalado/tema al crearse, y con
        # decenas de alumnos x 4 cursos esa sobrecarga por widget era la causa real de
        # la lentitud al cargar un aula (no el contenedor ni las consultas a la base).
        codigo_matricula, dni, nombres, apellidos = alumno
        estudiante = f"{apellidos}, {nombres}"
        widgets_fila = []

        kwargs_label = dict(bg=color_fondo, fg=NOTAS_COLOR_TEXTO, font=NOTAS_FONT_FILA, anchor="w")
        lbl_codigo = tk.Label(self.contenedor_notas, text=codigo_matricula, **kwargs_label)
        lbl_codigo.grid(row=fila, column=0, padx=3, pady=3, sticky="ew")
        lbl_dni = tk.Label(self.contenedor_notas, text=dni, **kwargs_label)
        lbl_dni.grid(row=fila, column=1, padx=3, pady=3, sticky="ew")
        lbl_estudiante = tk.Label(self.contenedor_notas, text=estudiante, **kwargs_label)
        lbl_estudiante.grid(row=fila, column=2, padx=3, pady=3, sticky="ew")
        widgets_fila.extend((lbl_codigo, lbl_dni, lbl_estudiante))

        fila_cursos = []
        for indice, (id_curso, _) in enumerate(self.cursos_notas):
            col_nota = 3 + indice * 2
            col_nsp = col_nota + 1

            entrada = tk.Entry(
                self.contenedor_notas,
                width=6,
                justify="center",
                font=NOTAS_FONT_FILA,
                bg=NOTAS_COLOR_ENTRADA_BG,
                fg=NOTAS_COLOR_TEXTO,
                insertbackground=NOTAS_COLOR_TEXTO,
                disabledbackground=NOTAS_COLOR_ENTRADA_BG,
                disabledforeground=NOTAS_COLOR_TEXTO_DESHABILITADO,
                relief="flat",
                highlightthickness=1,
                highlightbackground=NOTAS_COLOR_BORDE,
                highlightcolor=NOTAS_COLOR_ACENTO
            )
            entrada.grid(row=fila, column=col_nota, padx=(3, 1), pady=3, sticky="w")

            nsp_var = tk.BooleanVar(value=False)
            chk_nsp = tk.Checkbutton(
                self.contenedor_notas,
                text="NSP",
                font=NOTAS_FONT_FILA,
                variable=nsp_var,
                bg=color_fondo,
                fg=NOTAS_COLOR_TEXTO,
                activebackground=color_fondo,
                activeforeground=NOTAS_COLOR_TEXTO,
                selectcolor=NOTAS_COLOR_ENTRADA_BG,
                highlightthickness=0,
                bd=0,
                command=lambda e=entrada, v=nsp_var: self.actualizar_estado_nsp(e, v)
            )
            chk_nsp.grid(row=fila, column=col_nsp, padx=(1, 3), pady=3, sticky="w")
            widgets_fila.extend((entrada, chk_nsp))

            registro_existente = self.evaluaciones_fecha.get((codigo_matricula, id_curso))
            if registro_existente:
                nota, estado = registro_existente
                if estado == "NSP":
                    nsp_var.set(True)
                    self.actualizar_estado_nsp(entrada, nsp_var)
                elif nota is not None:
                    entrada.insert(0, str(nota).rstrip("0").rstrip("."))

            fila_cursos.append((id_curso, entrada, nsp_var))

        self.filas_notas.append((codigo_matricula, fila_cursos))
        self._widgets_filas_notas.extend(widgets_fila)

    def actualizar_estado_nsp(self, entrada, nsp_var):
        entrada.configure(state="normal")
        entrada.delete(0, "end")
        if nsp_var.get():
            entrada.insert(0, "NSP")
            entrada.configure(state="disabled")

    def guardar_notas_aula(self):
        if not self.filas_notas:
            self.lbl_res.configure(text="Cargue un aula antes de guardar.", text_color="red")
            return

        fecha_eval = self.obtener_fecha_notas()
        if not fecha_eval:
            return

        nota_minima, nota_maxima, _ = self.obtener_parametros_notas()

        registros = []
        for codigo_matricula, cursos in self.filas_notas:
            for id_curso, entrada, nsp_var in cursos:
                nota = "" if nsp_var.get() else entrada.get().strip().replace(",", ".")
                estado = "NSP" if nsp_var.get() else ("PENDIENTE" if nota == "" else "OK")

                if estado == "OK":
                    try:
                        nota_numero = float(nota)
                        if nota_numero < nota_minima or nota_numero > nota_maxima:
                            raise ValueError
                    except ValueError:
                        self.lbl_res.configure(
                            text=(
                                f"Revise la nota del codigo {codigo_matricula}. "
                                f"Ingrese {nota_minima:g} a {nota_maxima:g}, o deje vacio para guion."
                            ),
                            text_color="red"
                        )
                        return

                registros.append((codigo_matricula, id_curso, nota, estado))

        self.btn_guardar_notas_aula.configure(state="disabled", text="Guardando...")
        self.update_idletasks()
        try:
            exito, cantidad, msj = database.registrar_evaluaciones_lote(
                registros, self.usuario_actual, fecha_eval=fecha_eval
            )
            if exito:
                self.mostrar_mensaje(
                    self.lbl_res,
                    f"Guardado completo: {len(self.filas_notas)} estudiantes y {cantidad} notas.",
                    "green",
                    limpiar=True
                )
            else:
                self.lbl_res.configure(text=f"Error al guardar las notas: {msj}", text_color="red")
        finally:
            self.btn_guardar_notas_aula.configure(state="normal", text="Guardar Notas del Aula")

    def obtener_parametros_notas(self):
        return (
            float(NOTA_MINIMA_DEFAULT),
            float(NOTA_MAXIMA_DEFAULT),
            float(NOTA_APROBATORIA_DEFAULT)
        )

    def mostrar_reportes(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(self.panel_central, text="Reportes", font=("Roboto", 22, "bold")).pack(pady=20)
        self.e_rep = ctk.CTkEntry(self.panel_central, placeholder_text="DNI o codigo de matricula", width=250)
        self.e_rep.pack(pady=10)
        ctk.CTkButton(self.panel_central, text="Generar PDF", command=self.pdf_ui).pack(pady=10)
        self.lbl_p = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_p.pack()

    def pdf_ui(self):
        exito, msj = reportes.generar_consolidado_pdf(self.e_rep.get())
        self.mostrar_mensaje(self.lbl_p, msj, "green" if exito else "red", limpiar=exito)

    def mostrar_excel(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(
            self.panel_central, text="Importar / Exportar Estudiantes (Excel)", font=("Roboto", 22, "bold")
        ).pack(pady=20)

        bloque_export = ctk.CTkFrame(self.panel_central, fg_color="transparent")
        bloque_export.pack(pady=(0, 20))
        ctk.CTkLabel(bloque_export, text="Exportar todos los estudiantes registrados a un archivo Excel.").pack()
        ctk.CTkButton(
            bloque_export, text="Exportar a Excel", command=self.exportar_excel_ui, fg_color="green"
        ).pack(pady=10)

        bloque_import = ctk.CTkFrame(self.panel_central, fg_color="transparent")
        bloque_import.pack(pady=10)
        ctk.CTkLabel(
            bloque_import,
            text=(
                "Importar estudiantes desde Excel. Columnas requeridas: DNI, Nombres, Apellidos, Telefono.\n"
                "Columnas opcionales: Codigo_Matricula (se genera automaticamente si falta) y Aula\n"
                "(si una fila no trae Aula, se usa la seleccionada abajo)."
            ),
            justify="center",
            wraplength=620
        ).pack(pady=(0, 10))

        aulas = database.obtener_aulas_activas()
        self.dict_au_excel = {a[1]: a[0] for a in aulas}
        ctk.CTkLabel(bloque_import, text="Aula por defecto").pack()
        self.cb_au_excel = ctk.CTkComboBox(
            bloque_import,
            values=list(self.dict_au_excel.keys()) if aulas else ["No hay aulas"],
            width=300
        )
        self.cb_au_excel.pack(pady=(0, 10))

        ctk.CTkButton(
            bloque_import, text="Seleccionar e Importar Archivo", command=self.importar_excel_ui
        ).pack(pady=6)

        self.lbl_excel_resumen = ctk.CTkLabel(self.panel_central, text="", justify="center", wraplength=760)
        self.lbl_excel_resumen.pack(pady=10)

        self.txt_excel_errores = ctk.CTkTextbox(self.panel_central, height=180, width=760)
        self.txt_excel_errores.pack(pady=(0, 10))
        self.txt_excel_errores.configure(state="disabled")

    def exportar_excel_ui(self):
        ruta = filedialog.asksaveasfilename(
            title="Guardar listado de estudiantes",
            defaultextension=".xlsx",
            filetypes=[("Archivo Excel", "*.xlsx")],
            initialfile="estudiantes.xlsx"
        )
        if not ruta:
            return

        try:
            exito, msj = excel_io.exportar_alumnos(ruta)
        except Exception as e:
            exito, msj = False, f"Error al exportar: {e}"
        self.mostrar_mensaje(self.lbl_excel_resumen, msj, "green" if exito else "red", limpiar=exito)

    def importar_excel_ui(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar archivo de estudiantes",
            filetypes=[("Archivo Excel", "*.xlsx")]
        )
        if not ruta:
            return

        aula_defecto = self.cb_au_excel.get()
        id_aula_defecto = self.dict_au_excel.get(aula_defecto)

        try:
            insertados, errores = excel_io.importar_alumnos(ruta, id_aula_defecto, self.usuario_actual)
        except Exception as e:
            self.mostrar_mensaje(self.lbl_excel_resumen, f"No se pudo leer el archivo: {e}", "red")
            return

        resumen = f"{insertados} estudiante(s) importado(s)."
        if errores:
            resumen += f" {len(errores)} fila(s) con errores."
        color = "green" if insertados and not errores else ("orange" if insertados else "red")
        self.mostrar_mensaje(self.lbl_excel_resumen, resumen, color)

        self.txt_excel_errores.configure(state="normal")
        self.txt_excel_errores.delete("1.0", "end")
        self.txt_excel_errores.insert("1.0", "\n".join(errores) if errores else "Sin errores.")
        self.txt_excel_errores.configure(state="disabled")


if __name__ == "__main__":
    database.inicializar_base_datos()
    App().mainloop()
