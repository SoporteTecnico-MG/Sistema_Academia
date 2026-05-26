import sqlite3
import sys
from datetime import date
from pathlib import Path


def obtener_directorio_app():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


ARCHIVO_DB = obtener_directorio_app() / "datos_academia.db"
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


def conectar():
    try:
        conexion = sqlite3.connect(ARCHIVO_DB)
        return conexion
    except Exception as e:
        print(f"Error: {e}")
        return None


def inicializar_base_datos():
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
            DNI TEXT PRIMARY KEY, Nombres TEXT, Apellidos TEXT, Telefono TEXT,
            ID_Aula INTEGER, Usuario_Registro TEXT,
            FOREIGN KEY(ID_Aula) REFERENCES Aulas(ID_Aula)
        );
        CREATE TABLE IF NOT EXISTS Evaluaciones (
            ID_Evaluacion INTEGER PRIMARY KEY AUTOINCREMENT,
            DNI TEXT, ID_Curso TEXT, Fecha_Evaluacion TEXT, Nota REAL,
            Estado TEXT, Usuario_Registro TEXT,
            UNIQUE (DNI, ID_Curso, Fecha_Evaluacion)
        );
    """)

    cursor.executemany("INSERT OR IGNORE INTO Usuarios_Sistema VALUES (?, ?, ?, ?)", USUARIOS_INICIALES)
    sincronizar_cursos(cursor)
    asegurar_codigo_matricula(cursor)
    normalizar_codigos_matricula(cursor)

    conexion.commit()
    conexion.close()


def sincronizar_cursos(cursor):
    cursor.execute("DELETE FROM Cursos")
    cursor.executemany("INSERT INTO Cursos VALUES (?, ?)", CURSOS_OFICIALES)


def asegurar_codigo_matricula(cursor):
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


def obtener_siguiente_codigo_matricula(cursor=None):
    cerrar_conexion = False
    if cursor is None:
        conexion = conectar()
        cursor = conexion.cursor()
        cerrar_conexion = True

    codigos = [
        fila[0]
        for fila in cursor.execute(
            """
            SELECT Codigo_Matricula
            FROM Alumnos
            WHERE Codigo_Matricula IS NOT NULL AND trim(Codigo_Matricula) != ''
            """
        ).fetchall()
    ]
    codigos_validos = [
        int(codigo)
        for codigo in codigos
        if codigo.isdigit() and len(codigo) == 6
    ]
    siguiente = max(codigos_validos) + 1 if codigos_validos else 1
    codigos_existentes = set(codigos)

    while f"{siguiente:06d}" in codigos_existentes:
        siguiente += 1

    if cerrar_conexion:
        conexion.close()

    return f"{siguiente:06d}"


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
            (codigo_matricula, dni, nom, ape, tel, id_aula, user)
        )
        conexion.commit()
        return True, "Estudiante registrado correctamente."
    except sqlite3.IntegrityError as e:
        mensaje = str(e)
        if "Codigo_Matricula" in mensaje:
            return False, "El codigo de matricula ya existe."
        if "Alumnos.DNI" in mensaje or "UNIQUE constraint failed: Alumnos.DNI" in mensaje:
            return False, "El DNI ya existe."
        return False, mensaje
    except Exception as e:
        return False, str(e)
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


def obtener_alumno_por_dni(dni):
    """Busca los datos editables de un alumno por DNI."""
    conexion = conectar()
    if not conexion:
        return None

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT Codigo_Matricula, DNI, Nombres, Apellidos, Telefono, ID_Aula
        FROM Alumnos
        WHERE DNI = ?
        """,
        (dni.strip(),)
    )
    res = cursor.fetchone()
    conexion.close()
    return res


def actualizar_alumno(dni_original, codigo_matricula, dni, nom, ape, tel, id_aula):
    """Actualiza datos del alumno y conserva sus evaluaciones si cambia el DNI."""
    codigo_matricula = codigo_matricula.strip().upper()
    dni_original = dni_original.strip()
    dni = dni.strip()
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute(
            """
            UPDATE Alumnos
            SET Codigo_Matricula = ?, DNI = ?, Nombres = ?, Apellidos = ?,
                Telefono = ?, ID_Aula = ?
            WHERE DNI = ?
            """,
            (codigo_matricula, dni, nom, ape, tel, id_aula, dni_original)
        )
        if cursor.rowcount == 0:
            return False, "No se encontro el estudiante seleccionado."

        if dni_original != dni:
            cursor.execute("UPDATE Evaluaciones SET DNI = ? WHERE DNI = ?", (dni, dni_original))

        conexion.commit()
        return True, "Datos del estudiante actualizados correctamente."
    except sqlite3.IntegrityError as e:
        mensaje = str(e)
        if "Codigo_Matricula" in mensaje:
            return False, "El codigo de matricula ya existe."
        if "Alumnos.DNI" in mensaje or "UNIQUE constraint failed: Alumnos.DNI" in mensaje:
            return False, "El DNI ya existe."
        return False, mensaje
    except Exception as e:
        return False, str(e)
    finally:
        conexion.close()


def eliminar_alumno(dni):
    """Elimina un alumno y sus evaluaciones asociadas."""
    conexion = conectar()
    if not conexion:
        return False, "No se pudo conectar a la base de datos."

    try:
        cursor = conexion.cursor()
        dni = dni.strip()
        cursor.execute("DELETE FROM Evaluaciones WHERE DNI = ?", (dni,))
        cursor.execute("DELETE FROM Alumnos WHERE DNI = ?", (dni,))
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


def buscar_alumno_con_aula(dni):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT A.Nombres, A.Apellidos, AU.Nombre_Aula
        FROM Alumnos A
        INNER JOIN Aulas AU ON A.ID_Aula = AU.ID_Aula
        WHERE A.DNI = ?
        """,
        (dni,)
    )
    res = cursor.fetchone()
    conexion.close()
    return f"{res[0]} {res[1]} [{res[2]}]" if res else None


def obtener_detalle_alumno(identificador):
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
        WHERE A.DNI = ? OR A.Codigo_Matricula = ?
        """,
        (identificador, identificador)
    )
    res = cursor.fetchone()
    conexion.close()
    return res


def obtener_alumnos_por_aula(id_aula):
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
    conexion = conectar()
    res = conexion.execute("SELECT * FROM Cursos ORDER BY rowid").fetchall()
    conexion.close()
    return res


def obtener_evaluaciones_por_aula_fecha(id_aula, fecha_eval):
    conexion = conectar()
    if not conexion:
        return {}

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT E.DNI, E.ID_Curso, E.Nota, E.Estado
        FROM Evaluaciones E
        INNER JOIN Alumnos A ON E.DNI = A.DNI
        WHERE A.ID_Aula = ? AND E.Fecha_Evaluacion = ?
        """,
        (id_aula, fecha_eval)
    )
    registros = cursor.fetchall()
    conexion.close()
    return {(dni, id_curso): (nota, estado) for dni, id_curso, nota, estado in registros}


def registrar_evaluacion(dni, id_c, nota, est, user, fecha_eval=None):
    conexion = conectar()
    try:
        f = fecha_eval or date.today().strftime("%Y-%m-%d")
        n = float(nota) if nota else None
        conexion.execute(
            """
            INSERT INTO Evaluaciones (DNI, ID_Curso, Fecha_Evaluacion, Nota, Estado, Usuario_Registro)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(DNI, ID_Curso, Fecha_Evaluacion)
            DO UPDATE SET
                Nota = excluded.Nota,
                Estado = excluded.Estado,
                Usuario_Registro = excluded.Usuario_Registro
            """,
            (dni, id_c, f, n, est, user)
        )
        conexion.commit()
        return True, "Nota guardada."
    except Exception as e:
        return False, str(e)
    finally:
        conexion.close()


def obtener_historial_notas(dni):
    conexion = conectar()
    res = conexion.execute(
        """
        SELECT C.Nombre_Curso, E.Fecha_Evaluacion, E.Nota, E.Estado
        FROM Evaluaciones E
        INNER JOIN Cursos C ON E.ID_Curso = C.ID_Curso
        WHERE E.DNI = ?
        ORDER BY E.Fecha_Evaluacion ASC
        """,
        (dni,)
    ).fetchall()
    conexion.close()
    return res
