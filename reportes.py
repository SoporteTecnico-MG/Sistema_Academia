import os
from collections import defaultdict
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import database


CURSOS_REPORTE = [
    ("LEX", "LEXICON"),
    ("CG", "CULTURA GENERAL"),
    ("CPP", "CPP"),
    ("MAT", "MATEMATICA"),
]
FILAS_POR_BLOQUE = 23


def generar_consolidado_pdf(dni):
    detalle = database.obtener_detalle_alumno(dni)
    historial = database.obtener_historial_notas(dni)

    if not detalle:
        return False, "Alumno no encontrado en los registros."

    nombre_archivo = f"Constancia_Notas_{dni}.pdf"
    doc = SimpleDocTemplate(
        nombre_archivo,
        pagesize=landscape(A4),
        rightMargin=18,
        leftMargin=18,
        topMargin=18,
        bottomMargin=18
    )

    elementos = []
    styles = getSampleStyleSheet()
    elementos.extend(crear_encabezado(detalle, historial, styles))
    elementos.append(crear_tablas_notas(historial))

    try:
        doc.build(elementos)
        os.startfile(nombre_archivo)
        return True, "Constancia de notas generada correctamente."
    except Exception as e:
        return False, f"Error al generar la constancia: {str(e)}"


def crear_encabezado(detalle, historial, styles):
    dni, nombres, apellidos, aula, fecha_inicio, fecha_fin = detalle
    nombre_alumno = f"{apellidos}, {nombres}"

    estilo_titulo = ParagraphStyle(
        "TituloConstancia",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        alignment=1,
        leading=22
    )
    estilo_subtitulo = ParagraphStyle(
        "SubtituloConstancia",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=1,
        leading=14
    )

    data_info = [
        [
            Paragraph("<b>Codigo</b>", styles["Normal"]),
            Paragraph(f"<b>{dni}</b>", styles["Normal"]),
            Paragraph("<b>Aula</b>", styles["Normal"]),
            Paragraph(f"<b>{aula}</b>", styles["Normal"]),
        ],
        [
            Paragraph("<b>Alumno</b>", styles["Normal"]),
            Paragraph(f"<b>{nombre_alumno}</b>", styles["Normal"]),
            "",
            "",
        ],
    ]
    tabla_info = Table(data_info, colWidths=[55, 250, 50, 160])
    tabla_info.setStyle(TableStyle([
        ("SPAN", (1, 1), (3, 1)),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    return [
        Paragraph("CONSTANCIA DE NOTAS", estilo_titulo),
        Paragraph("Modalidad: REGULARES G-8 DOBLE T", estilo_subtitulo),
        Paragraph(
            f"Inicio del aula: {formatear_fecha(fecha_inicio)} &nbsp;&nbsp; "
            f"Termino del aula: {formatear_fecha(fecha_fin)}",
            estilo_subtitulo
        ),
        Spacer(1, 10),
        tabla_info,
        Spacer(1, 8),
    ]


def obtener_fecha_referencia(historial):
    if not historial:
        return datetime.today().strftime("%d/%m/%Y")

    fechas = [reg[1] for reg in historial]
    fecha_max = max(fechas)
    return formatear_fecha(fecha_max)


def crear_tablas_notas(historial):
    filas = construir_filas_por_fecha(historial)
    bloques = [
        filas[:FILAS_POR_BLOQUE],
        filas[FILAS_POR_BLOQUE:FILAS_POR_BLOQUE * 2],
    ]

    tablas = []
    for bloque in bloques:
        tablas.append(crear_bloque_notas(bloque))

    tabla_doble = Table([tablas], colWidths=[390, 390])
    tabla_doble.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return tabla_doble


def construir_filas_por_fecha(historial):
    notas_por_fecha = defaultdict(dict)
    for curso, fecha, nota, estado in historial:
        fecha_key = fecha.split(" ")[0] if isinstance(fecha, str) else fecha.strftime("%Y-%m-%d")
        id_curso = obtener_id_curso_por_nombre(curso)
        notas_por_fecha[fecha_key][id_curso] = (nota, estado)

    filas = []
    for fecha in sorted(notas_por_fecha):
        notas_fecha = notas_por_fecha[fecha]
        valores_numericos = []
        fila = [formatear_fecha(fecha)]

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

    filas.append(crear_fila_promedios(filas))
    return filas


def obtener_id_curso_por_nombre(nombre_curso):
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
    fila_promedios = ["PROMEDIO CURSO"]
    for indice_columna in range(1, len(CURSOS_REPORTE) + 1):
        valores = []
        for fila in filas:
            valor = fila[indice_columna]
            if valor != "--":
                valores.append(float(valor))
        promedio = sum(valores) / len(valores) if valores else None
        fila_promedios.append(formatear_nota(promedio) if promedio is not None else "--")
    fila_promedios.append("")
    return fila_promedios


def crear_bloque_notas(filas):
    encabezado = ["FECHA"] + [nombre for _, nombre in CURSOS_REPORTE] + ["PROM."]
    data = [encabezado] + filas if filas else [encabezado]

    tabla = Table(data, colWidths=[58, 62, 80, 44, 70, 48], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#bfbfbf")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f2f2f2")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
    ]))
    return tabla


def formatear_fecha(fecha):
    if isinstance(fecha, str):
        try:
            fecha_obj = datetime.strptime(fecha.split(" ")[0], "%Y-%m-%d")
        except ValueError:
            return fecha
    else:
        fecha_obj = fecha
    return fecha_obj.strftime("%d/%m/%Y")


def formatear_nota(nota):
    return f"{float(nota):.2f}"
