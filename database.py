import sqlite3
from datetime import date


ARCHIVO_DB = "datos_academia.db"
CURSOS_OFICIALES = [
    ("LEX", "LEXICON"),
    ("CG", "CULTURA GENERAL"),
    ("CPP", "CONSTITUCION POLITICA DEL PERU"),
    ("MAT", "MATEMATICA"),
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

    cursor.execute(
        "INSERT OR IGNORE INTO Usuarios_Sistema VALUES ('ADMIN', 'admin123', 'Administrador Maestro', 'Admin')"
    )
    sincronizar_cursos(cursor)

    conexion.commit()
    conexion.close()


def sincronizar_cursos(cursor):
    cursor.execute("DELETE FROM Cursos")
    cursor.executemany("INSERT INTO Cursos VALUES (?, ?)", CURSOS_OFICIALES)


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


def insertar_alumno(dni, nom, ape, tel, id_aula, user):
    conexion = conectar()
    try:
        cursor = conexion.cursor()
        cursor.execute("INSERT INTO Alumnos VALUES (?,?,?,?,?,?)", (dni, nom, ape, tel, id_aula, user))
        conexion.commit()
        return True, "Alumno registrado."
    except Exception as e:
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


def obtener_detalle_alumno(dni):
    conexion = conectar()
    if not conexion:
        return None

    cursor = conexion.cursor()
    cursor.execute(
        """
        SELECT A.DNI, A.Nombres, A.Apellidos, AU.Nombre_Aula, AU.Fecha_Inicio, AU.Fecha_Fin
        FROM Alumnos A
        INNER JOIN Aulas AU ON A.ID_Aula = AU.ID_Aula
        WHERE A.DNI = ?
        """,
        (dni,)
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
        SELECT DNI, Nombres, Apellidos
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
