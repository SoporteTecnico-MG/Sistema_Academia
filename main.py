from datetime import date, datetime, timedelta
from pathlib import Path

import customtkinter as ctk
import database
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
LOGO_MAX_ANCHO = 620
LOGO_MAX_ALTO = 140
LOGO_PANEL_MAX_ANCHO = 760
LOGO_PANEL_MAX_ALTO = 115


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(NOMBRE_SISTEMA)
        self.geometry("1000x650")
        self.usuario_actual = ""
        self.rol_actual = ""
        self.logo_login = None
        self.logo_panel = None

        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=90, padx=160, fill="both", expand=True)

        self.mostrar_logo_login()
        ctk.CTkLabel(
            self.frame_login,
            text=NOMBRE_SISTEMA,
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

    def mostrar_logo_login(self):
        logo_path = self.obtener_ruta_logo()

        if logo_path and Image:
            imagen = Image.open(logo_path)
            ancho, alto = self.calcular_tamano_logo(imagen.size)
            self.logo_login = ctk.CTkImage(imagen, size=(ancho, alto))
            ctk.CTkLabel(self.frame_login, text="", image=self.logo_login).pack(pady=(22, 8))
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

    def obtener_ruta_logo(self):
        return next((Path(ruta) for ruta in LOGO_RUTAS if Path(ruta).exists()), None)

    def calcular_tamano_logo(self, tamano_original, max_ancho=LOGO_MAX_ANCHO, max_alto=LOGO_MAX_ALTO):
        ancho_original, alto_original = tamano_original
        escala = min(max_ancho / ancho_original, max_alto / alto_original)
        return int(ancho_original * escala), int(alto_original * escala)

    def mostrar_logo_panel(self):
        logo_path = self.obtener_ruta_logo()

        if logo_path and Image:
            imagen = Image.open(logo_path)
            ancho, alto = self.calcular_tamano_logo(
                imagen.size,
                max_ancho=LOGO_PANEL_MAX_ANCHO,
                max_alto=LOGO_PANEL_MAX_ALTO
            )
            self.logo_panel = ctk.CTkImage(imagen, size=(ancho, alto))
            ctk.CTkLabel(self.panel_central, text="", image=self.logo_panel).pack(pady=(5, 16))
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
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.pack(side="left", fill="y")

        ctk.CTkLabel(self.sidebar, text="ACADEMIA", font=("Roboto", 20, "bold")).pack(pady=20)
        ctk.CTkLabel(
            self.sidebar,
            text=f"{nombre_usuario}\n[{self.rol_actual}]",
            font=("Roboto", 12),
            text_color="gray"
        ).pack(pady=5)

        ctk.CTkButton(self.sidebar, text="1. Matricula", command=self.mostrar_registro).pack(
            pady=10, padx=20, fill="x"
        )
        ctk.CTkButton(self.sidebar, text="2. Notas", command=self.mostrar_notas).pack(
            pady=10, padx=20, fill="x"
        )
        ctk.CTkButton(self.sidebar, text="3. Reportes PDF", command=self.mostrar_reportes).pack(
            pady=10, padx=20, fill="x"
        )

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

    def mostrar_aulas(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(
            self.panel_central,
            text="Programacion de Nuevas Aulas",
            font=("Roboto", 22, "bold")
        ).pack(pady=20)

        self.ent_aula_nom = ctk.CTkEntry(
            self.panel_central,
            placeholder_text="Nombre del Aula (Ej: Alfa 2026)",
            width=350
        )
        self.ent_aula_nom.pack(pady=10)

        self.ent_aula_ini = ctk.CTkEntry(self.panel_central, placeholder_text="Fecha Inicio (AAAA-MM-DD)", width=350)
        self.ent_aula_ini.pack(pady=10)

        self.ent_aula_fin = ctk.CTkEntry(self.panel_central, placeholder_text="Fecha Fin (AAAA-MM-DD)", width=350)
        self.ent_aula_fin.pack(pady=10)

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
        nom, ini, fin = self.ent_aula_nom.get(), self.ent_aula_ini.get(), self.ent_aula_fin.get()
        if not nom or not ini or not fin:
            self.lbl_msg_aula.configure(text="Complete todos los campos.", text_color="red")
            return

        exito, msj = database.crear_aula(nom, ini, fin)
        self.lbl_msg_aula.configure(text=msj, text_color="green" if exito else "red")

    def mostrar_registro(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(self.panel_central, text="Registro de Postulantes", font=("Roboto", 22, "bold")).pack(pady=20)
        aulas = database.obtener_aulas_activas()
        self.dict_au = {a[1]: a[0] for a in aulas}

        self.e_dni = ctk.CTkEntry(self.panel_central, placeholder_text="DNI", width=350)
        self.e_dni.pack(pady=5)
        self.e_nom = ctk.CTkEntry(self.panel_central, placeholder_text="Nombres", width=350)
        self.e_nom.pack(pady=5)
        self.e_ape = ctk.CTkEntry(self.panel_central, placeholder_text="Apellidos", width=350)
        self.e_ape.pack(pady=5)
        self.e_tel = ctk.CTkEntry(self.panel_central, placeholder_text="Celular", width=350)
        self.e_tel.pack(pady=5)

        ctk.CTkLabel(self.panel_central, text="Seleccione Aula:").pack()
        self.cb_au = ctk.CTkComboBox(
            self.panel_central,
            values=list(self.dict_au.keys()) if aulas else ["No hay aulas"],
            width=350
        )
        self.cb_au.pack(pady=5)

        ctk.CTkButton(self.panel_central, text="Guardar Estudiante", command=self.guardar_estudiante_ui).pack(pady=20)
        self.lbl_m = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_m.pack()

    def guardar_estudiante_ui(self):
        d = self.e_dni.get()
        n = self.e_nom.get().upper()
        a = self.e_ape.get().upper()
        t = self.e_tel.get()
        au = self.cb_au.get()

        if not d or not n or not a or au == "No hay aulas":
            return

        exito, msj = database.insertar_alumno(d, n, a, t, self.dict_au[au], self.usuario_actual)
        self.lbl_m.configure(text=msj, text_color="green" if exito else "red")

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

        ctk.CTkButton(
            self.panel_central,
            text="Guardar Notas del Aula",
            fg_color="green",
            command=self.guardar_notas_aula
        ).pack(pady=10)
        self.lbl_res = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_res.pack()

    def cargar_alumnos_aula(self):
        for widget in self.contenedor_notas.winfo_children():
            widget.destroy()
        self.filas_notas = []

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
        self.crear_encabezado_notas()

        for fila, alumno in enumerate(alumnos, start=1):
            self.crear_fila_notas(fila, alumno)

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
        ctk.CTkLabel(self.contenedor_notas, text="DNI", width=85, font=("Roboto", 12, "bold")).grid(
            row=0, column=0, padx=4, pady=5, sticky="w"
        )
        ctk.CTkLabel(self.contenedor_notas, text="Estudiante", width=190, font=("Roboto", 12, "bold")).grid(
            row=0, column=1, padx=4, pady=5, sticky="w"
        )

        for col, (_, nombre_curso) in enumerate(self.cursos_notas, start=2):
            ctk.CTkLabel(
                self.contenedor_notas,
                text=nombre_curso,
                width=120,
                font=("Roboto", 12, "bold"),
                wraplength=110
            ).grid(row=0, column=col, padx=4, pady=5)
        ctk.CTkLabel(self.contenedor_notas, text="Accion", width=85, font=("Roboto", 12, "bold")).grid(
            row=0, column=len(self.cursos_notas) + 2, padx=4, pady=5
        )

    def crear_fila_notas(self, fila, alumno):
        dni, nombres, apellidos = alumno
        estudiante = f"{apellidos}, {nombres}"
        ctk.CTkLabel(self.contenedor_notas, text=dni, width=85).grid(row=fila, column=0, padx=4, pady=4, sticky="w")
        ctk.CTkLabel(
            self.contenedor_notas,
            text=estudiante,
            width=190,
            anchor="w",
            wraplength=185
        ).grid(row=fila, column=1, padx=4, pady=4, sticky="w")

        fila_cursos = []
        for col, (id_curso, _) in enumerate(self.cursos_notas, start=2):
            celda = ctk.CTkFrame(self.contenedor_notas, fg_color="transparent")
            celda.grid(row=fila, column=col, padx=4, pady=4)

            entrada = ctk.CTkEntry(celda, placeholder_text="0-20", width=58, justify="center")
            entrada.pack(side="left", padx=(0, 4))

            nsp_var = ctk.BooleanVar(value=False)
            chk_nsp = ctk.CTkCheckBox(
                celda,
                text="NSP",
                width=54,
                variable=nsp_var,
                command=lambda e=entrada, v=nsp_var: self.actualizar_estado_nsp(e, v)
            )
            chk_nsp.pack(side="left")

            registro_existente = self.evaluaciones_fecha.get((dni, id_curso))
            if registro_existente:
                nota, estado = registro_existente
                if estado == "NSP":
                    nsp_var.set(True)
                    self.actualizar_estado_nsp(entrada, nsp_var)
                elif nota is not None:
                    entrada.insert(0, str(nota).rstrip("0").rstrip("."))

            fila_cursos.append((id_curso, entrada, nsp_var))

        self.filas_notas.append((dni, fila_cursos))
        ctk.CTkButton(
            self.contenedor_notas,
            text="Guardar",
            width=82,
            command=lambda d=dni, c=fila_cursos: self.guardar_fila_notas(d, c)
        ).grid(row=fila, column=len(self.cursos_notas) + 2, padx=4, pady=4)

    def actualizar_estado_nsp(self, entrada, nsp_var):
        if nsp_var.get():
            entrada.delete(0, "end")
            entrada.configure(state="disabled", placeholder_text="NSP")
        else:
            entrada.configure(state="normal", placeholder_text="0-20")

    def guardar_notas_aula(self):
        if not self.filas_notas:
            self.lbl_res.configure(text="Cargue un aula antes de guardar.", text_color="red")
            return

        registros_guardados = 0
        for dni, cursos in self.filas_notas:
            guardados = self.guardar_cursos_estudiante(dni, cursos, mostrar_mensaje=False)
            if guardados is None:
                return
            registros_guardados += guardados

        self.lbl_res.configure(text=f"Se guardaron {registros_guardados} registros de evaluacion.", text_color="green")

    def guardar_fila_notas(self, dni, cursos):
        guardados = self.guardar_cursos_estudiante(dni, cursos, mostrar_mensaje=False)
        if guardados is not None:
            self.lbl_res.configure(text=f"DNI {dni}: {guardados} notas guardadas.", text_color="green")

    def guardar_cursos_estudiante(self, dni, cursos, mostrar_mensaje=True):
        fecha_eval = self.obtener_fecha_notas()
        if not fecha_eval:
            return None

        registros_guardados = 0
        for id_curso, entrada, nsp_var in cursos:
            estado = "NSP" if nsp_var.get() else "OK"
            nota = "" if nsp_var.get() else entrada.get().strip()

            if estado == "OK":
                try:
                    nota_numero = float(nota)
                    if nota_numero < 0 or nota_numero > 20:
                        raise ValueError
                except ValueError:
                    self.lbl_res.configure(
                        text=f"Revise la nota de DNI {dni}. Debe estar entre 0 y 20, o marque NSP.",
                        text_color="red"
                    )
                    return None

            exito, msj = database.registrar_evaluacion(
                dni,
                id_curso,
                nota,
                estado,
                self.usuario_actual,
                fecha_eval=fecha_eval
            )
            if not exito:
                self.lbl_res.configure(text=f"DNI {dni}: {msj}", text_color="red")
                return None
            registros_guardados += 1

        if mostrar_mensaje:
            self.lbl_res.configure(text=f"DNI {dni}: {registros_guardados} notas guardadas.", text_color="green")
        return registros_guardados

    def mostrar_reportes(self):
        self.limpiar_panel()
        self.mostrar_logo_panel()
        ctk.CTkLabel(self.panel_central, text="Reportes", font=("Roboto", 22, "bold")).pack(pady=20)
        self.e_rep = ctk.CTkEntry(self.panel_central, placeholder_text="DNI", width=250)
        self.e_rep.pack(pady=10)
        ctk.CTkButton(self.panel_central, text="Generar PDF", command=self.pdf_ui).pack(pady=10)
        self.lbl_p = ctk.CTkLabel(self.panel_central, text="")
        self.lbl_p.pack()

    def pdf_ui(self):
        exito, msj = reportes.generar_consolidado_pdf(self.e_rep.get())
        self.lbl_p.configure(text=msj, text_color="green" if exito else "red")


if __name__ == "__main__":
    database.inicializar_base_datos()
    App().mainloop()
