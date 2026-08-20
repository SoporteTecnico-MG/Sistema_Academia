"""Capa de acceso a datos del Sistema de Gestion Academica.

Este modulo concentra la conexion SQLite, la creacion/actualizacion del
esquema y todas las consultas usadas por la interfaz y los reportes. Las
funciones devuelven datos simples o tuplas `(exito, mensaje)` para que la UI
pueda mostrar respuestas claras al usuario.
"""

import re
import sqlite3
import sys
import shutil
from datetime import date
from pathlib import Path


def obtener_directorio_app():
    """Devuelve la carpeta donde debe vivir la base de datos editable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def obtener_directorio_recursos():
    """Devuelve la carpeta donde PyInstaller deja la base inicial incluida."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


ARCHIVO_DB = obtener_directorio_app() / "datos_academia.db"
ARCHIVO_DB_INICIAL = obtener_directorio_recursos() / "datos_academia.db"
CURSOS_OFICIALES = [
    ("LEX", "LEXICON"),
    ("CG", "CULTURA GENERAL"),
    ("CPP", "CONSTITUCION POLITICA DEL PERU"),
    ("MAT", "MATEMATICA"),
]
USUARIOS_INICIALES = [
    ("ADMIN", "admin123", "Administrador Maestro", "Admin"),
    ("GESTION", "gestion123", "Usuario de Gestion", "Gestion"),
]


def preparar_base_datos_portable():
    """Copia la base incluida al lado del ejecutable cuando aun no existe."""
    if ARCHIVO_DB.exists() or ARCHIVO_DB == ARCHIVO_DB_INICIAL or not ARCHIVO_DB_INICIAL.exists():
        return

    try:
        shutil.copy2(ARCHIVO_DB_INICIAL, ARCHIVO_DB)
    except Exception as e:
        print(f"No se pudo preparar la base de datos portable: {e}")


def conectar():
    """Abre una conexion SQLite hacia `datos_academia.db`."""
    try:
        preparar_base_datos_portable()
        conexion = sqlite3.connect(ARCHIVO_DB)
        return conexion
    except Exception as e:
        print(f"Error: {e}")
        return None


def inicializar_base_datos():
    """Crea las tablas base, usuarios iniciales, cursos y migraciones minimas."""
    conexion = conectar()
    if not conexion:
        return

    cursor = conexion.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS Usuarios_Sistema (
            ID_Usuario TEXT PRIMARY KEY, Password TEXT, Nombre_Completo TEXT, Rol TEXT
        );
        CREATE TABLE IF NOT EXISTS Cursos (
            ID_Curso TEXT PRIMARY KEY, Nombre_Curso TEXT
        );
        CREATE TABLE IF NOT EXISTS Aulas (
            ID_Aula INTEGER PRIMARY KEY AUTOINCREMENT,
            Nombre_Aula TEXT, Fecha_Inicio TEXT, Fecha_Fin TEXT, Estado_Aula TEXT
        );
        CREATE TABLE IF NOT EXISTS Alumnos (
            Codigo_Matricula TEXT PRIMARY KEY, DNI TEXT, Nombres TEXT, Apellidos TEXT, Telefono TEXT,
            ID_Aula INTEGER, Usuario_Registro TEXT,
            FOREIGN KEY(ID_Aula) REFERENCES Aulas(ID_Aula)
        );
        CREATE TABLE IF NOT EXISTS Evaluaciones (
            ID_Evaluacion INTEGER PRIMARY KEY AUTOINCREMENT,
            Codigo_Matricula TEXT, ID_Curso TEXT, Fecha_Evaluacion TEXT, Nota REAL,
            Estado TEXT, Usuario_Registro TEXT,
            UNIQUE (Codigo_Matricula, ID_Curso, Fecha_Evaluacion)
        );
    """)

    cursor.executemany("INSERT OR IGNORE INTO Usuarios_Sistema VALUES (?, ?, ?, ?)", USUARIOS_INICIALES)
    sincronizar_cursos(cursor)
    asegurar_codigo_matricula(cursor)
    normalizar_codigos_matricula(cursor)
    migrar_llave_alumnos(cursor)
    normalizar_nombres_alumnos(cursor)

    conexion.commit()
    conexion.close()


def normalizar_texto_nombre(valor):
    """Limpia comas y espacios sobrantes de un nombre o apellido.

    Una version anterior guardaba el apellido con una coma pegada al final
    (por ejemplo "CAMALA MONTERROSO,"); al mostrarlo junto al nombre con el
    formato "Apellidos, Nombres" quedaba una coma doble ("CAMALA MONTERROSO,,
    ALEMBERT SIXTO."). Tambien colapsa espacios dobles y recorta los bordes.
    """
    if valor is None:
        return valor
    limpio = re.sub(r"\s+", " ", valor.strip())
    return limpio.rstrip(",").rstrip()


def normalizar_nombres_alumnos(cursor):
    """Corrige de una vez las comas y espacios sobrantes ya guardados en Alumnos."""
    for codigo, nombres, apellidos in cursor.execute(
        "SELECT Codigo_Matricula, Nombres, Apellidos FROM Alumnos"
    ).fetchall():
        nombres_limpio = normalizar_texto_nombre(nombres)
        apellidos_limpio = normalizar_texto_nombre(apellidos)
        if nombres_limpio != nombres or apellidos_limpio != apellidos:
            cursor.execute(
                "UPDATE Alumnos SET Nombres = ?, Apellidos = ? WHERE Codigo_Matricula = ?",
                (nombres_limpio, apellidos_limpio, codigo)
            )


def sincronizar_cursos(cursor):
    """Mantiene la tabla Cursos alineada con los cursos oficiales del sistema."""
    cursor.execute("DELETE FROM Cursos")
    cursor.executemany("INSERT INTO Cursos VALUES (?, ?)", CURSOS_OFICIALES)


def asegurar_codigo_matricula(cursor):
    """Agrega y completa el codigo de matricula si la base viene de una version anterior."""
    columnas = [columna[1] for columna in cursor.execute("PRAGMA table_info(Alumnos)").fetchall()]
    if "Codigo_Matricula" not in columnas:
        cursor.execute("ALTER TABLE Alumnos ADD COLUMN Codigo_Matricula TEXT")

    for rowid, in cursor.execute(
        """
        SELECT rowid
        FROM Alumnos
        WHERE Codigo_Matricula IS NULL OR trim(Codigo_Matricula) = ''
        ORDER BY rowid
        """
    ).fetchall():
        cursor.execute(
            "UPDATE Alumnos SET Codigo_Matricula = ? WHERE rowid = ?",
            (obtener_siguiente_codigo_matricula(cursor), rowid)
        )
    cursor.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_alumnos_codigo_matricula
        ON Alumnos(Codigo_Matricula)
        """
    )


def normalizar_codigos_matricula(cursor):
    """Convierte codigos antiguos o invalidos al formato numerico de seis digitos."""
    registros = cursor.execute(
        """
        SELECT rowid
        FROM Alumnos
        WHERE Codigo_Matricula LIKE 'MAT-%'
           OR Codigo_Matricula IS NULL
           OR trim(Codigo_Matricula) = ''
           OR Codigo_Matricula NOT GLOB '[0-9][0-9][0-9][0-9][0-9][0-9]'
        ORDER BY rowid
        """
    ).fetchall()
    for rowid, in registros:
        cursor.execute(
            "UPDATE Alumnos SET Codigo_Matricula = ? WHERE rowid = ?",
            (obtener_siguiente_codigo_matricula(cursor), rowid)
        )


def migrar_llave_alumnos(cursor):
    """Cambia la llave principal de Alumnos de DNI a Codigo_Matricula.

    Antes el DNI identificaba al alumno, pero el mismo estudiante puede
    matricularse en varios ciclos y repetir DNI; el Codigo_Matricula si es
    unico por matricula, asi que pasa a ser la llave de Alumnos y de
    Evaluaciones (las notas quedan asociadas a la matricula del ciclo, no
    al DNI). Esta migracion solo actua sobre bases creadas con el esquema
    anterior; en instalaciones nuevas la tabla ya nace con esta llave.
    """
    columnas_alumnos = cursor.execute("PRAGMA table_info(Alumnos)").fetchall()
    pk_actual = next((columna[1] for columna in columnas_alumnos if columna[5] == 1), None)
    if pk_actual == "Codigo_Matricula":
        return

    columnas_base_alumnos = ["Codigo_Matricula", "DNI", "Nombres", "Apellidos", "Telefono", "ID_Aula", "Usuario_Registro"]
    columnas_existentes_alumnos = [columna[1] for columna in columnas_alumnos]
    columnas_extra_alumnos = [c for c in columnas_existentes_alumnos if c not in columnas_base_alumnos]

    cursor.execute("ALTER TABLE Alumnos RENAME TO Alumnos_Antiguo")
    cursor.execute(
        """
        CREATE TABLE Alumnos (
            Codigo_Matricula TEXT PRIMARY KEY, DNI TEXT, Nombres TEXT, Apellidos TEXT, Telefono TEXT,
            ID_Aula INTEGER, Usuario_Registro TEXT,
            FOREIGN KEY(ID_Aula) REFERENCES Aulas(ID_Aula)
        )
        """
    )
    for columna_extra in columnas_extra_alumnos:
        cursor.execute(f'ALTER TABLE Alumnos ADD COLUMN "{columna_extra}" TEXT')

    columnas_copia_alumnos = ", ".join(f'"{c}"' for c in columnas_base_alumnos + columnas_extra_alumnos)
    cursor.execute(
        f"INSERT INTO Alumnos ({columnas_copia_alumnos}) SELECT {columnas_copia_alumnos} FROM Alumnos_Antiguo"
    )
    cursor.execute("DROP TABLE Alumnos_Antiguo")
    cursor.execute("DROP INDEX IF EXISTS idx_alumnos_codigo_matricula")

    columnas_evaluaciones = [columna[1] for columna in cursor.execute("PRAGMA table_info(Evaluaciones)").fetchall()]
    if "DNI" in columnas_evaluaciones:
        columnas_base_eval = ["ID_Curso", "Fecha_Evaluacion", "Nota", "Estado", "Usuario_Registro"]
        columnas_extra_eval = [
            c for c in columnas_evaluaciones
            if c not in ("ID_Evaluacion", "DNI") + tuple(columnas_base_eval)
        ]

        cursor.execute("ALTER TABLE Evaluaciones RENAME TO Evaluaciones_Antiguo")
        cursor.execute(
            """
            CREATE TABLE Evaluaciones (
                ID_Evaluacion INTEGER PRIMARY KEY AUTOINCREMENT,
                Codigo_Matricula TEXT, ID_Curso TEXT, Fecha_Evaluacion TEXT, Nota REAL,
                Estado TEXT, Usuario_Registro TEXT,
                UNIQUE (Codigo_Matricula, ID_Curso, Fecha_Evaluacion)
            )
            """
        )
        for columna_extra in columnas_extra_eval:
            cursor.execute(f'ALTER TABLE Evaluaciones ADD COLUMN "{columna_extra}" TEXT')

        columnas_select_eval = ", ".join(f'E."{c}"' for c in columnas_base_eval + columnas_extra_eval)
        columnas_destino_eval = ", ".join(f'"{c}"' for c in columnas_base_eval + columnas_extra_eval)
        cursor.execute(
            f"""
            INSERT INTO Evaluaciones (Codigo_Matricula, {columnas_destino_eval})
            SELECT A.Codigo_Matricula, {columnas_select_eval}
            FROM Evaluaciones_Antiguo E
            INNER JOIN Alumnos A ON A.DNI = E.DNI
            """
        )
        cursor.execute("DROP TABLE Evaluaciones_Antiguo")


def obtener_codigos_matricula_disponibles(cantidad, cursor=None):
    """Reserva varios codigos de matricula consecutivos y no usados.

    Se usa en altas masivas (por ejemplo, importar un Excel de varios cientos
    de filas) para no tener que consultar toda la tabla Alumnos una vez por
    cada fila nueva, como pasaria llamando a `obtener_siguiente_codigo_matricula`
    en un bucle.
    """
    cerrar_conexion = False
    if cursor is None:
        conexion = conectar()
        cursor = conexion.cursor()
        cerrar_conexion = True

    codigos_existentes = {
        fila[0]
        for fila in cursor.execute(
            """
            SELECT Codigo_Matricula
            FROM Alumnos
            WHERE Codigo_Matricula IS NOT NULL AND trim(Codigo_Matricula) != ''
            """
        ).fetchall()
    }
    codigos_validos = [
        int(codigo)
        for codigo in codigos_existentes
        if codigo.isdigit() and len(codigo) == 6
    ]
    siguiente = max(codigos_validos) + 1 if codigos_validos else 1

    reservados = []
    while len(reservados) < cantidad:
        candidato = f"{siguiente:06d}"
        if candidato not in codigos_existentes:
            reservados.append(candidato)
        siguiente += 1

    if cerrar_conexion:
        conexion.close()

    return reservados


def obtener_siguiente_codigo_matricula(cursor=None):
    """Calcula el siguiente codigo de matricula disponible con seis digitos."""
    return obtener_codigos_matricula_disponibles(1, cursor=cursor)[0]


def crear_aula(nombre, f_inicio, f_fin):
    """Guarda una nueva aula programada en la base de datos."""
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("""
            INSERT INTO Aulas (Nombre_Aula, Fecha_Inicio, Fecha_Fin, Estado_Aula)
            VALUES (?, ?, ?, 'Activa')
        """, (nombre, f_inicio, f_fin))
        conexion.commit()
        return True, "Aula programada y activada correctamente."
    except Exception as e:
        return False, str(e)
    finally:
        conexion.close()


def obtener_aulas_activas():
    """Lista las aulas disponibles para matricula, notas y reportes."""
    conexion = conectar()
    if not conexion:
        return []

    try:
        cursor = conexion.cursor()
        cursor.execute("SELECT ID_Aula, Nombre_Aula FROM Aulas WHERE Estado_Aula = 'Activa'")
        return cursor.fetchall()
    finally:
        conexion.close()


def validar_login(usuario, password):
    """Valida credenciales y devuelve nombre completo y rol del usuario."""
    conexion = conectar()
    if not conexion:
        return False, "", ""

    cursor = conexion.cursor()
    cursor.execute(
        "SELECT Nombre_Completo, Rol FROM Usuarios_Sistema WHERE ID_Usuario = ? AND Password = ?",
        (usuario, password)
    )
    res = cursor.fetchone()
    conexion.close()

    if res:
        return True, res[0], res[1]
    return False, "", ""


def insertar_alumno(codigo_matricula, dni, nom, ape, tel, id_aula, user):
    """Registra un nuevo alumno en un aula activa."""
    codigo_matricula = codigo_matricula.strip().upper()
    dni = dni.strip()
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            INSERT INTO Alumnos (
                Codigo_Matricula, DNI, Nombres, Apellidos, Telefono, ID_Aula, Usuario_Registro
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (codigo_matricula, dni, normalizar_texto_nombre(nom), normalizar_texto_nombre(ape), tel, id_aula, user)
        )
        conexion.commit()
        return True, "Estudiante registrado correctamente."
    except sqlite3.IntegrityError as e:
        mensaje = str(e)
        if "Codigo_Matricula" in mensaje:
            return False, "El codigo de matricula ya existe."
        return False, mensaje
    except Exception as e:
        return False, str(e)
    finally:
        conexion.close()


def insertar_alumnos_lote(alumnos, user):
    """Inserta varios alumnos en una sola conexion/transaccion.

    Se usa en la importacion desde Excel para no abrir una conexion SQLite por
    cada fila del archivo (una importacion de varios cientos de filas llegaba
    a abrir igual numero de conexiones). `alumnos` es una lista de tuplas
    (codigo_matricula, dni, nombres, apellidos, telefono, id_aula); devuelve
    una lista de (exito, mensaje) en el mismo orden que `alumnos`.
    """
    conexion = conectar()
    if not conexion:
        return [(False, "No se pudo conectar a la base de datos.") for _ in alumnos]

    resultados = []
    try:
        cursor = conexion.cursor()
        for codigo_matricula, dni, nom, ape, tel, id_aula in alumnos:
            try:
                cursor.execute(
                    """
                    INSERT INTO Alumnos (
                        Codigo_Matricula, DNI, Nombres, Apellidos, Telefono, ID_Aula, Usuario_Registro
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        codigo_matricula.strip().upper(), dni.strip(),
                        normalizar_texto_nombre(nom), normalizar_texto_nombre(ape),
                        tel, id_aula, user
                    )
                )
                resultados.append((True, "Estudiante registrado correctamente."))
            except sqlite3.IntegrityError as e:
                mensaje = str(e)
                if "Codigo_Matricula" in mensaje:
                    resultados.append((False, "El codigo de matricula ya existe."))
                else:
                    resultados.append((False, mensaje))
            except Exception as e:
                resultados.append((False, str(e)))
        conexion.commit()
        return resultados
    finally:
        conexion.close()


def obtener_alumnos():
    """Devuelve alumnos con su aula para seleccion y mantenimiento."""
    conexion = conectar()
    if not conexion:
        return []

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT
            A.Codigo_Matricula,
            A.DNI,
            A.Nombres,
            A.Apellidos,
            A.Telefono,
            A.ID_Aula,
            AU.Nombre_Aula
        FROM Alumnos A
        LEFT JOIN Aulas AU ON A.ID_Aula = AU.ID_Aula
        ORDER BY A.Apellidos, A.Nombres
        """
    )
    res = cursor.fetchall()
    conexion.close()
    return res


def obtener_alumno_por_codigo(codigo_matricula):
    """Busca los datos editables de un alumno por Codigo_Matricula."""
    conexion = conectar()
    if not conexion:
        return None

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT Codigo_Matricula, DNI, Nombres, Apellidos, Telefono, ID_Aula
        FROM Alumnos
        WHERE Codigo_Matricula = ?
        """,
        (codigo_matricula.strip().upper(),)
    )
    res = cursor.fetchone()
    conexion.close()
    return res


def actualizar_alumno(codigo_original, codigo_matricula, dni, nom, ape, tel, id_aula):
    """Actualiza datos del alumno y conserva sus evaluaciones si cambia el codigo de matricula."""
    codigo_matricula = codigo_matricula.strip().upper()
    codigo_original = codigo_original.strip().upper()
    dni = dni.strip()
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE Alumnos
            SET Codigo_Matricula = ?, DNI = ?, Nombres = ?, Apellidos = ?,
                Telefono = ?, ID_Aula = ?
            WHERE Codigo_Matricula = ?
            """,
            (
                codigo_matricula, dni,
                normalizar_texto_nombre(nom), normalizar_texto_nombre(ape),
                tel, id_aula, codigo_original
            )
        )
        if cursor.rowcount == 0:
            return False, "No se encontro el estudiante seleccionado."

        if codigo_original != codigo_matricula:
            cursor.execute(
                "UPDATE Evaluaciones SET Codigo_Matricula = ? WHERE Codigo_Matricula = ?",
                (codigo_matricula, codigo_original)
            )

        conexion.commit()
        return True, "Datos del estudiante actualizados correctamente."
    except sqlite3.IntegrityError as e:
        mensaje = str(e)
        if "Codigo_Matricula" in mensaje:
            return False, "El codigo de matricula ya existe."
        return False, mensaje
    except Exception as e:
        return False, str(e)
    finally:
        conexion.close()


def eliminar_alumno(codigo_matricula):
    """Elimina un alumno y sus evaluaciones asociadas."""
    conexion = conectar()
    if not conexion:
        return False, "No se pudo conectar a la base de datos."

    try:
        cursor = conexion.cursor()
        codigo_matricula = codigo_matricula.strip().upper()
        cursor.execute("DELETE FROM Evaluaciones WHERE Codigo_Matricula = ?", (codigo_matricula,))
        cursor.execute("DELETE FROM Alumnos WHERE Codigo_Matricula = ?", (codigo_matricula,))
        if cursor.rowcount == 0:
            conexion.rollback()
            return False, "No se encontro el estudiante seleccionado."

        conexion.commit()
        return True, "Estudiante eliminado correctamente."
    except Exception as e:
        conexion.rollback()
        return False, str(e)
    finally:
        conexion.close()


def buscar_alumno_con_aula(codigo_matricula):
    """Devuelve un texto corto con alumno y aula a partir del codigo de matricula."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT A.Nombres, A.Apellidos, AU.Nombre_Aula
        FROM Alumnos A
        INNER JOIN Aulas AU ON A.ID_Aula = AU.ID_Aula
        WHERE A.Codigo_Matricula = ?
        """,
        (codigo_matricula,)
    )
    res = cursor.fetchone()
    conexion.close()
    return f"{res[0]} {res[1]} [{res[2]}]" if res else None


def obtener_detalle_alumno(identificador):
    """Busca datos completos del alumno por codigo de matricula o DNI.

    Como el DNI puede repetirse entre matriculas de distintos ciclos, una
    coincidencia exacta de Codigo_Matricula tiene prioridad; si se busca por
    DNI y hay mas de una matricula, se devuelve "AMBIGUO" para que quien
    llama pida el codigo de matricula exacto en vez de adivinar el ciclo.
    """
    identificador = identificador.strip().upper()
    conexion = conectar()
    if not conexion:
        return None

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT A.Codigo_Matricula, A.DNI, A.Nombres, A.Apellidos, AU.Nombre_Aula, AU.Fecha_Inicio, AU.Fecha_Fin
        FROM Alumnos A
        INNER JOIN Aulas AU ON A.ID_Aula = AU.ID_Aula
        WHERE A.Codigo_Matricula = ?
        """,
        (identificador,)
    )
    res = cursor.fetchone()
    if res:
        conexion.close()
        return res

    cursor.execute(
        """
        SELECT A.Codigo_Matricula, A.DNI, A.Nombres, A.Apellidos, AU.Nombre_Aula, AU.Fecha_Inicio, AU.Fecha_Fin
        FROM Alumnos A
        INNER JOIN Aulas AU ON A.ID_Aula = AU.ID_Aula
        WHERE A.DNI = ?
        """,
        (identificador,)
    )
    coincidencias = cursor.fetchall()
    conexion.close()

    if len(coincidencias) > 1:
        return "AMBIGUO"
    return coincidencias[0] if coincidencias else None


def obtener_alumnos_por_aula(id_aula):
    """Obtiene los alumnos de un aula ordenados para carga masiva de notas."""
    conexion = conectar()
    if not conexion:
        return []

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT Codigo_Matricula, DNI, Nombres, Apellidos
        FROM Alumnos
        WHERE ID_Aula = ?
        ORDER BY Apellidos, Nombres
        """,
        (id_aula,)
    )
    res = cursor.fetchall()
    conexion.close()
    return res


def obtener_cursos():
    """Devuelve los cursos oficiales en el orden registrado."""
    conexion = conectar()
    res = conexion.execute("SELECT * FROM Cursos ORDER BY rowid").fetchall()
    conexion.close()
    return res


def obtener_evaluaciones_por_aula_fecha(id_aula, fecha_eval):
    """Trae las notas ya guardadas de un aula en una fecha especifica."""
    conexion = conectar()
    if not conexion:
        return {}

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT E.Codigo_Matricula, E.ID_Curso, E.Nota, E.Estado
        FROM Evaluaciones E
        INNER JOIN Alumnos A ON E.Codigo_Matricula = A.Codigo_Matricula
        WHERE A.ID_Aula = ? AND E.Fecha_Evaluacion = ?
        """,
        (id_aula, fecha_eval)
    )
    registros = cursor.fetchall()
    conexion.close()
    return {
        (codigo_matricula, id_curso): (nota, estado)
        for codigo_matricula, id_curso, nota, estado in registros
    }


def registrar_evaluaciones_lote(registros, user, fecha_eval=None):
    """Inserta o actualiza en una sola transaccion todas las notas de una carga por aula.

    `registros` es una lista de tuplas (codigo_matricula, id_curso, nota, estado). Antes cada
    nota se guardaba con su propia conexion/commit; para un aula de 30 alumnos x 4 cursos eso
    eran 120 conexiones SQLite. Agrupar todo en una sola conexion evita ese costo repetido.
    """
    conexion = conectar()
    if not conexion:
        return False, 0, "No se pudo conectar a la base de datos."

    try:
        f = fecha_eval or date.today().strftime("%Y-%m-%d")
        cursor = conexion.cursor()
        for codigo_matricula, id_curso, nota, estado in registros:
            n = float(nota) if nota else None
            cursor.execute(
                """
                INSERT INTO Evaluaciones (Codigo_Matricula, ID_Curso, Fecha_Evaluacion, Nota, Estado, Usuario_Registro)
                VALUES (?,?,?,?,?,?)
                ON CONFLICT(Codigo_Matricula, ID_Curso, Fecha_Evaluacion)
                DO UPDATE SET
                    Nota = excluded.Nota,
                    Estado = excluded.Estado,
                    Usuario_Registro = excluded.Usuario_Registro
                """,
                (codigo_matricula, id_curso, f, n, estado, user)
            )
        conexion.commit()
        return True, len(registros), "Notas guardadas."
    except Exception as e:
        conexion.rollback()
        return False, 0, str(e)
    finally:
        conexion.close()


def obtener_historial_notas(codigo_matricula):
    """Devuelve todo el historial de evaluaciones de una matricula."""
    conexion = conectar()
    res = conexion.execute(
        """
        SELECT C.Nombre_Curso, E.Fecha_Evaluacion, E.Nota, E.Estado
        FROM Evaluaciones E
        INNER JOIN Cursos C ON E.ID_Curso = C.ID_Curso
        WHERE E.Codigo_Matricula = ?
        ORDER BY E.Fecha_Evaluacion ASC
        """,
        (codigo_matricula,)
    ).fetchall()
    conexion.close()
    return res
