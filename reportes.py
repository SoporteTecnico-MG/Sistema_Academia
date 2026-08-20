"""Generacion de constancias PDF de notas diarias.

El reporte toma el historial de evaluaciones de un alumno, agrupa las notas por
fecha y construye una constancia A4 vertical con membrete institucional, datos
del alumno, fecha/hora de emision y tablas compactas en dos columnas.
"""

import io
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from PIL import Image as ImagenPIL
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import database


CURSOS_REPORTE = [
    ("LEX", "LEXICON"),
    ("CG", "CULTURA GENERAL"),
    ("CPP", "CPP"),
    ("MAT", "MATEMATICA"),
]
DIAS_SEMANA_REPORTE = ("LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES", "SABADO", "DOMINGO")
LOGOS_REPORTE = (
    "assets/login_personaje.png",
    "assets/logo_apmipol_recortado.png",
    "assets/login_escudo.png",
)
FIRMA_REPORTE = "assets/firma_reporte.png"
FILAS_POR_BLOQUE = 35


def obtener_directorio_app():
    """Devuelve la carpeta de trabajo tanto en Python normal como en el ejecutable."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def obtener_directorio_recursos():
    """Devuelve la carpeta donde PyInstaller deja los recursos incluidos."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def generar_consolidado_pdf(identificador):
    """Genera y abre la constancia PDF para un alumno buscado por DNI o codigo."""
    detalle = database.obtener_detalle_alumno(identificador)

    if detalle == "AMBIGUO":
        return False, "Ese DNI tiene varias matriculas registradas. Ingrese el codigo de matricula exacto."
    if not detalle:
        return False, "Alumno no encontrado en los registros."

    codigo_matricula = detalle[0]
    historial = database.obtener_historial_notas(codigo_matricula)

    nombre_archivo = obtener_directorio_app() / f"Constancia_Notas_{sanitizar_nombre_archivo(codigo_matricula)}.pdf"
    ruta_pdf = str(nombre_archivo)
    doc = SimpleDocTemplate(
        ruta_pdf,
        pagesize=A4,
        rightMargin=12,
        leftMargin=12,
        topMargin=12,
        bottomMargin=12
    )

    elementos = []
    styles = getSampleStyleSheet()
    elementos.extend(crear_encabezado(detalle, historial, styles))
    elementos.append(crear_tablas_notas(historial))
    firma = crear_bloque_firma(styles)
    if firma:
        elementos.extend([Spacer(1, 3), firma])

    try:
        doc.build(elementos, onFirstPage=dibujar_marca_agua, onLaterPages=dibujar_marca_agua)
        os.startfile(ruta_pdf)
        return True, "Constancia de notas generada correctamente."
    except Exception as e:
        return False, f"Error al generar la constancia: {str(e)}"


def sanitizar_nombre_archivo(valor):
    """Elimina caracteres no permitidos por Windows para crear nombres de PDF."""
    return re.sub(r'[<>:"/\\|?*]', "_", str(valor)).strip() or "sin_codigo"


def dibujar_marca_agua(canvas, doc):
    """Dibuja una marca de agua diagonal detras del contenido del reporte."""
    ancho, alto = A4
    canvas.saveState()
    try:
        canvas.setFillAlpha(0.08)
    except AttributeError:
        pass
    canvas.setFillColor(colors.HexColor("#8f8f8f"))
    canvas.setFont("Helvetica-Bold", 72)
    canvas.translate(ancho / 2, alto / 2)
    canvas.rotate(42)
    canvas.drawCentredString(0, 0, "LEONCIO PRADO")
    canvas.restoreState()


def crear_encabezado(detalle, historial, styles):
    """Construye el membrete, titulo y bloque de datos del alumno."""
    codigo_matricula, dni, nombres, apellidos, aula, _fecha_inicio, _fecha_fin = detalle
    nombre_alumno = f"{apellidos}, {nombres}"
    fecha_generacion = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    estilo_titulo = ParagraphStyle(
        "TituloConstancia",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        alignment=1,
        leading=16
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloConstancia",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        alignment=1,
        leading=9
    )
    estilo_texto = ParagraphStyle(
        "TextoInfoConstancia",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.2,
        leading=8.2
    )

    data_info = [
        [
            Paragraph("<b>Codigo</b>", estilo_texto),
            Paragraph(f"<b>{codigo_matricula}</b>", estilo_texto),
            Paragraph("<b>Aula</b>", estilo_texto),
            Paragraph(f"<b>{aula}</b>", estilo_texto),
        ],
        [
            Paragraph("<b>DNI</b>", estilo_texto),
            Paragraph(f"<b>{dni}</b>", estilo_texto),
            Paragraph("<b>Generado</b>", estilo_texto),
            Paragraph(f"<b>{fecha_generacion}</b>", estilo_texto),
        ],
        [
            Paragraph("<b>Alumno</b>", estilo_texto),
            Paragraph(f"<b>{nombre_alumno}</b>", estilo_texto),
            "",
            "",
        ],
    ]
    tabla_info = Table(data_info, colWidths=[50, 220, 58, 219])
    tabla_info.setStyle(TableStyle([
        ("SPAN", (1, 2), (3, 2)),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.2),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
    ]))

    elementos = []
    banner = crear_banner_logos()
    if banner:
        elementos.extend([banner, Spacer(1, 3)])

    elementos.extend([
        Paragraph("CONSTANCIA DE NOTAS DIARIAS", estilo_titulo),
        Paragraph("Reporte generado por el Sistema de Gestion Academica", estilo_subtitulo),
        Spacer(1, 4),
        tabla_info,
        Spacer(1, 4),
    ])
    return elementos


def crear_banner_logos():
    """Crea el banner con personaje, logo APMIPOL y escudo institucional.

    El orden (personaje-letras-escudo) replica el banner de la aplicacion. El
    personaje mira hacia su izquierda en el archivo original, asi que aqui se
    refleja horizontalmente para que quede mirando hacia el centro del banner.
    """
    directorio_recursos = obtener_directorio_recursos()
    rutas = [directorio_recursos / ruta for ruta in LOGOS_REPORTE]
    if not all(ruta.exists() for ruta in rutas):
        return None

    imagenes = [
        crear_imagen_ajustada(rutas[0], max_ancho=100, max_alto=86, espejo=True),
        crear_imagen_ajustada(rutas[1], max_ancho=410, max_alto=108),
        crear_imagen_ajustada(rutas[2], max_ancho=100, max_alto=86),
    ]
    tabla = Table([imagenes], colWidths=[75, 410, 65], hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return tabla


def crear_imagen_ajustada(ruta, max_ancho, max_alto, espejo=False):
    """Escala una imagen manteniendo su proporcion dentro de un tamano maximo.

    Con `espejo=True` la imagen se refleja horizontalmente antes de escalarla
    (util para que un personaje que mira hacia un lado quede mirando hacia el
    centro del layout al cambiar de posicion).
    """
    lector = ImageReader(str(ruta))
    ancho_original, alto_original = lector.getSize()
    escala = min(max_ancho / ancho_original, max_alto / alto_original)
    ancho, alto = ancho_original * escala, alto_original * escala

    if not espejo:
        return Image(str(ruta), width=ancho, height=alto)

    imagen_reflejada = ImagenPIL.open(ruta).transpose(ImagenPIL.FLIP_LEFT_RIGHT)
    buffer = io.BytesIO()
    imagen_reflejada.save(buffer, format="PNG")
    buffer.seek(0)
    return Image(buffer, width=ancho, height=alto)


def crear_bloque_firma(styles):
    """Agrega la firma institucional al cierre de la constancia."""
    ruta_firma = obtener_directorio_recursos() / FIRMA_REPORTE
    if not ruta_firma.exists():
        return None

    imagen_firma = crear_imagen_ajustada(ruta_firma, max_ancho=68, max_alto=82)
    estilo_frase = ParagraphStyle(
        "FraseLeoncito",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=13.2,
        alignment=1,
    )
    frase = Paragraph(
        "Cada hora de estudio y sacrificio hoy, se verán reflejados el día de tu examen<br/>"
        "Con disciplina todo se consigue; no te rindas!!!<br/>"
        "<b>¡NUESTRA META ES TU INGRESO!</b>",
        estilo_frase,
    )

    bloque = Table([[frase, imagen_firma]], colWidths=[420, 126], hAlign="CENTER")
    bloque.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([bloque])


def obtener_fecha_referencia(historial):
    """Devuelve la ultima fecha disponible del historial, o la fecha actual."""
    if not historial:
        return datetime.today().strftime("%d/%m/%Y")

    fechas = [reg[1] for reg in historial]
    fecha_max = max(fechas)
    return formatear_fecha(fecha_max)


def crear_tablas_notas(historial):
    """Organiza las filas en dos bloques de 35 registros por pagina."""
    filas, fila_promedios = construir_filas_por_fecha(historial)
    pares_bloques = []
    for indice in range(0, len(filas), FILAS_POR_BLOQUE * 2):
        bloque_izquierdo = filas[indice:indice + FILAS_POR_BLOQUE]
        bloque_derecho = filas[indice + FILAS_POR_BLOQUE:indice + FILAS_POR_BLOQUE * 2]
        pares_bloques.append([
            crear_bloque_notas(bloque_izquierdo, indice),
            "",
            crear_bloque_notas(bloque_derecho, indice + FILAS_POR_BLOQUE) if bloque_derecho else "",
        ])

    tabla_doble = Table(pares_bloques, colWidths=[274, 10, 274], hAlign="CENTER")
    tabla_doble.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    return KeepTogether([tabla_doble, Spacer(1, 6), crear_tabla_promedios(fila_promedios)])


def construir_filas_por_fecha(historial):
    """Agrupa evaluaciones por fecha y calcula el promedio diario."""
    notas_por_fecha = defaultdict(dict)
    for curso, fecha, nota, estado in historial:
        fecha_key = fecha.split(" ")[0] if isinstance(fecha, str) else fecha.strftime("%Y-%m-%d")
        id_curso = obtener_id_curso_por_nombre(curso)
        notas_por_fecha[fecha_key][id_curso] = (nota, estado)

    filas = []
    fechas_ordenadas = sorted(notas_por_fecha)
    for fecha in fechas_ordenadas:
        notas_fecha = notas_por_fecha[fecha]
        valores_numericos = []
        fila = [formatear_fecha_examen(fecha)]

        for id_curso, _ in CURSOS_REPORTE:
            nota, estado = notas_fecha.get(id_curso, (None, ""))
            if estado == "NSP" or nota is None:
                fila.append("--")
            else:
                valores_numericos.append(float(nota))
                fila.append(formatear_nota(nota))

        promedio = sum(valores_numericos) / len(valores_numericos) if valores_numericos else None
        fila.append(formatear_nota(promedio) if promedio is not None else "--")
        filas.append(fila)

    fila_promedios = crear_fila_promedios(filas)
    return filas, fila_promedios


def obtener_id_curso_por_nombre(nombre_curso):
    """Mapea el nombre completo del curso al identificador usado en el reporte."""
    nombre = nombre_curso.upper()
    if "LEXICON" in nombre:
        return "LEX"
    if "CULTURA" in nombre:
        return "CG"
    if "CONSTITUCION" in nombre or nombre == "CPP":
        return "CPP"
    if "MATEMATICA" in nombre:
        return "MAT"
    return nombre


def crear_fila_promedios(filas):
    """Calcula los promedios por curso para la fila final de la tabla."""
    fila_promedios = ["PROM.<br/>CURSO"]
    promedios_curso = []
    for indice_columna in range(1, len(CURSOS_REPORTE) + 1):
        valores = []
        for fila in filas:
            valor = fila[indice_columna]
            if valor != "--":
                valores.append(float(valor))
        promedio = sum(valores) / len(valores) if valores else None
        if promedio is not None:
            promedios_curso.append(promedio)
            fila_promedios.append(formatear_nota(promedio))
        else:
            fila_promedios.append("--")

    promedio_general = sum(promedios_curso) / len(promedios_curso) if promedios_curso else None
    fila_promedios.append(formatear_nota(promedio_general) if promedio_general is not None else "--")
    return fila_promedios


def crear_tabla_promedios(fila_promedios):
    """Dibuja el resumen de promedios fuera de la numeracion de registros."""
    estilo = ParagraphStyle(
        "ResumenPromedios",
        fontName="Helvetica-Bold",
        fontSize=6,
        leading=6.5,
        alignment=1
    )
    etiquetas = ["LEX", "C.G.", "CPP", "MAT", "PROM."]
    fila = [Paragraph("PROM.<br/>CURSO", estilo)] + [
        Paragraph(f"{etiqueta}<br/>{valor}", estilo)
        for etiqueta, valor in zip(etiquetas, fila_promedios[1:])
    ]
    tabla = Table([fila], colWidths=[85, 78, 78, 78, 78, 85], hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 2, colors.HexColor("#bfbfbf")),
        ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#f2f2f2")),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 0.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0.8),
    ]))
    return tabla


def crear_bloque_notas(filas, inicio_numeracion=0):
    """Dibuja una tabla compacta de notas para una columna del reporte."""
    estilo_numero = ParagraphStyle(
        "NumeroTablaNotas",
        fontName="Helvetica",
        fontSize=7.5,
        leading=7.7,
        alignment=1
    )
    estilo_fecha = ParagraphStyle(
        "FechaTablaNotas",
        fontName="Helvetica",
        fontSize=5.8,
        leading=6.2,
        alignment=1
    )
    estilo_nota = ParagraphStyle(
        "CeldaTablaNotas",
        fontName="Helvetica",
        fontSize=7.7,
        leading=8.2,
        alignment=1
    )
    estilo_promedio = ParagraphStyle(
        "PromedioTablaNotas",
        parent=estilo_nota,
        fontName="Helvetica-Bold"
    )
    estilo_encabezado = ParagraphStyle(
        "EncabezadoTablaNotas",
        parent=estilo_nota,
        fontName="Helvetica-Bold",
        fontSize=6.3,
        leading=6.7
    )
    encabezado = [
        Paragraph("Nro", estilo_encabezado),
        Paragraph("FECHA", estilo_encabezado),
        Paragraph("LEX", estilo_encabezado),
        Paragraph("C.G.", estilo_encabezado),
        Paragraph("CPP", estilo_encabezado),
        Paragraph("MAT", estilo_encabezado),
        Paragraph("PROM.", estilo_encabezado),
    ]
    filas_tabla = []
    for indice_fila, fila in enumerate(filas):
        es_fila_promedio = fila[0] == "PROM.<br/>CURSO"
        numero = "" if es_fila_promedio else str(inicio_numeracion + indice_fila + 1)
        fila_tabla = [
            Paragraph(numero, estilo_promedio if es_fila_promedio else estilo_numero),
            Paragraph(str(fila[0]), estilo_promedio if es_fila_promedio else estilo_fecha),
        ]
        for indice_columna, valor in enumerate(fila[1:], start=1):
            es_columna_promedio = indice_columna == len(fila) - 1
            estilo = estilo_promedio if es_fila_promedio or es_columna_promedio else estilo_nota
            fila_tabla.append(Paragraph(str(valor), estilo))
        filas_tabla.append(fila_tabla)
    data = [encabezado] + filas_tabla if filas_tabla else [encabezado]

    tabla = Table(data, colWidths=[22, 54, 36, 37, 32, 36, 57], repeatRows=1, hAlign="CENTER")
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 2, colors.HexColor("#bfbfbf")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.4),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, 0), 1),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("TOPPADDING", (0, 1), (-1, -1), 0.6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 0.6),
    ]))
    return tabla


def formatear_fecha(fecha):
    """Convierte fechas SQLite o datetime al formato dd/mm/aaaa."""
    if isinstance(fecha, str):
        try:
            fecha_obj = datetime.strptime(fecha.split(" ")[0], "%Y-%m-%d")
        except ValueError:
            return fecha
    else:
        fecha_obj = fecha
    return fecha_obj.strftime("%d/%m/%Y")


def formatear_fecha_examen(fecha):
    """Muestra el nombre del dia encima de la fecha de examen."""
    if isinstance(fecha, str):
        try:
            fecha_obj = datetime.strptime(fecha.split(" ")[0], "%Y-%m-%d")
        except ValueError:
            return fecha
    else:
        fecha_obj = fecha

    dia_semana = DIAS_SEMANA_REPORTE[fecha_obj.weekday()]
    return f"{dia_semana}<br/>{fecha_obj.strftime('%d/%m/%Y')}"


def formatear_nota(nota):
    """Muestra las notas con dos decimales para mantener columnas uniformes."""
    return f"{float(nota):.2f}"
