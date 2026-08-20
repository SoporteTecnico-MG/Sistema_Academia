# Sistema de Gestion Academica

Aplicacion de escritorio para registrar alumnos, programar aulas, cargar notas diarias y generar constancias PDF.

## Archivos principales

- `main.py`: interfaz grafica del sistema. Controla login, formularios, carga de notas y botones de reportes.
- `database.py`: capa de datos SQLite. Crea tablas, valida usuarios, guarda alumnos, aulas y evaluaciones.
- `reportes.py`: generador de constancias PDF con logo, datos del alumno, fecha/hora de emision y tabla de notas.
- `excel_io.py`: importacion y exportacion de estudiantes en formato Excel (.xlsx).
- `datos_academia.db`: base de datos local. Debe viajar junto al ejecutable portable si se quieren conservar los datos.
- `assets/`: imagenes e iconos usados por la interfaz y los reportes.
- `Sistema_Academia.spec`: configuracion de PyInstaller para construir la version portable.
- `requirements.txt`: dependencias de Python necesarias para ejecutar o reconstruir el sistema.

## Usuarios iniciales

- Administrador: `ADMIN` / `admin123`
- Gestion: `GESTION` / `gestion123`

## Flujo de uso

1. Iniciar sesion.
2. Crear o seleccionar un aula activa.
3. Registrar estudiantes con codigo de matricula, DNI, nombres, apellidos y celular.
4. Cargar notas por aula y fecha.
5. Generar la constancia PDF ingresando DNI o codigo de matricula.

## Importar / Exportar Excel

Disponible solo para el rol Administrador, en "5. Importar/Exportar Excel":

- **Exportar**: genera un `.xlsx` con todos los estudiantes registrados (Codigo_Matricula, DNI, Nombres, Apellidos, Telefono, Aula).
- **Importar**: lee un `.xlsx` con columnas `DNI`, `Nombres`, `Apellidos`, `Telefono` (obligatorias) y `Codigo_Matricula`, `Aula` (opcionales). Si una fila no trae `Aula`, se usa el aula seleccionada en pantalla. Las filas invalidas (DNI/celular con formato incorrecto, aula inexistente, etc.) se reportan sin detener la importacion del resto.

## Reportes PDF

La constancia se genera como `Constancia_Notas_<codigo>.pdf` en la misma carpeta del programa. El reporte incluye:

- Logo institucional.
- Titulo `CONSTANCIA DE NOTAS DIARIAS`.
- Codigo, aula, DNI, alumno y fecha/hora de generacion.
- Tabla vertical en dos columnas, con 45 filas por lado.
- Promedio diario y promedio por curso.

## Portable

La version portable se genera con PyInstaller en:

`dist/Sistema_Academia/Sistema_Academia.exe`

Para llevarlo a otra PC, copiar completa la carpeta:

`dist/Sistema_Academia`

No copiar solo el `.exe`, porque el programa necesita los archivos incluidos en esa carpeta.

## Datos

La base incluida en el portable es `datos_academia.db`. Si desea conservar informacion registrada en una PC, respalde ese archivo antes de reemplazar o actualizar la carpeta del programa.
