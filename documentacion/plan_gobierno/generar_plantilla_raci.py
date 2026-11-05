"""Genera la plantilla RACI diligenciada de ORCA (Sesión 1 · Gobernanza de Datos).

Hojas: Madurez (diagnóstico /16 con nivel calculado), Roles (asignación al equipo)
y RACI (con validación de la regla de oro: exactamente una 'A' por tarea).
El contenido es el mismo de documentacion/05_plan_gobierno_datos.md; si se cambia
uno, se cambia el otro.

Uso:  python documentacion/plan_gobierno/generar_plantilla_raci.py
"""
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

SALIDA = Path(__file__).with_name("ORCA-Plantilla-RACI-v1.0.xlsx")

OWNER, STEWARD, CUSTODIO, CONSUMIDOR = (
    "Luis Ángel Seoanes Ovieso",
    "Julian Amariles Taborda",
    "Katheryn Ramírez Chimá",
    "Jhon Sebastian Rayo Posada (principal) · Luis Ángel Seoanes Ovieso (valida P1–P6)",
)

MADUREZ = [  # (afirmación, AS-IS, hoy, meta)
    ("Sabemos quién es el responsable (dueño) de nuestros datos.", 0, 1, 1),
    ("Tenemos un inventario o catálogo de los datos que usamos.", 0, 1, 2),
    ("Cada campo está definido (existe un diccionario de datos).", 1, 1, 1),
    ("Medimos la calidad del dato (nulos, duplicados, errores).", 0, 1, 2),
    ("Clasificamos qué datos son sensibles o personales.", 0, 1, 2),
    ("Está claro quién puede ver o modificar cada dato.", 0, 1, 1),
    ("Podemos rastrear de dónde viene cada dato (linaje).", 0, 1, 2),
    ("Tenemos políticas o estándares escritos sobre el dato.", 1, 1, 2),
]

ROLES = [
    ("Data Owner (dueño)", "Decide alcance, reglas de calidad, clasificación y acceso; aprueba lo que se publica.", OWNER),
    ("Data Steward (custodio de negocio)", "Define el significado de cada campo, mantiene catálogo y diccionario, mide la calidad y resuelve incidentes.", STEWARD),
    ("Custodio técnico", "Implementa y opera ingesta, limpieza, seudonimización, linaje y automatización.", CUSTODIO),
    ("Consumidor / Analista", "Hace el EDA, banderas rojas y dashboard; reporta problemas de calidad al Steward.", CONSUMIDOR),
]

RACI = [  # (bloque, tarea, Owner, Steward, Custodio, Consumidor)
    ("Estrategia y políticas", "Definir alcance, fuentes y preguntas de negocio (P1–P6)", "A/R", "C", "C", "C"),
    ("Estrategia y políticas", "Redactar y aprobar las políticas y estándares del Plan de Gobierno", "A", "R", "C", "C"),
    ("Estrategia y políticas", "Asignar Owner y Steward a cada activo de datos", "A", "R", "C", "I"),
    ("Metadatos", "Construir y mantener el catálogo de activos", "I", "A/R", "R", "C"),
    ("Metadatos", "Elaborar el diccionario de datos (definición, tipo y dominio de cada campo)", "I", "A/R", "C", "C"),
    ("Metadatos", "Registrar el linaje por lote (SoQL, filas, SHA-256, transformaciones)", "I", "C", "A/R", "I"),
    ("Metadatos", "Gestionar cambios de esquema de SECOP (columnas nuevas o renombradas)", "I", "A", "R", "C"),
    ("Calidad", "Definir reglas y umbrales de calidad (6 dimensiones, quality gate ≥ 95 %)", "A", "R", "C", "C"),
    ("Calidad", "Implementar y ejecutar la medición de calidad en cada lote", "I", "A", "R", "I"),
    ("Calidad", "Reportar problemas de calidad encontrados durante el análisis", "I", "A", "I", "R"),
    ("Calidad", "Resolver incidentes de calidad (nulos disfrazados, joins fallidos con DS-02, atípicos)", "I", "A", "R", "C"),
    ("Seguridad y privacidad", "Clasificar los datos sensibles y personales (PII) por campo y por capa", "A", "R", "C", "I"),
    ("Seguridad y privacidad", "Implementar la seudonimización (hash con sal) y custodiar la sal", "A", "C", "R", "I"),
    ("Seguridad y privacidad", "Definir y aprobar quién accede a cada capa (raw, curated, mart)", "A", "C", "R", "I"),
    ("Operación y uso", "Operar la ingesta automatizada desde la API (ventana móvil + hash por registro)", "I", "I", "A/R", "I"),
    ("Operación y uso", "Definir banderas rojas y score de riesgo", "A", "C", "C", "R"),
    ("Operación y uso", "Publicar en el dashboard solo lotes que pasaron el quality gate", "A", "C", "I", "R"),
    ("Operación y uso", "Medir y reportar los KPI de gobierno (calidad, PII en claro, frescura)", "I", "A/R", "C", "I"),
]

MAGENTA = "B5005B"
LILA = "F3E8F5"
FINO = Side(style="thin", color="BFBFBF")
BORDE = Border(left=FINO, right=FINO, top=FINO, bottom=FINO)
ENVOLVER = Alignment(wrap_text=True, vertical="center")
CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)
COLOR_LETRA = {"R": "1E7B34", "A": "B5005B", "C": "2F5DAA", "I": "C58A00"}


def encabezado(ws, fila, valores):
    for col, valor in enumerate(valores, 1):
        c = ws.cell(fila, col, valor)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=MAGENTA)
        c.alignment = CENTRO
        c.border = BORDE


def titulo(ws, texto, subtitulo):
    ws["A1"] = texto
    ws["A1"].font = Font(bold=True, size=14, color=MAGENTA)
    ws["A2"] = subtitulo
    ws["A2"].font = Font(italic=True, color="595959")


def hoja_madurez(wb):
    ws = wb.active
    ws.title = "Madurez"
    titulo(ws, "Parte 1 · Diagnóstico de madurez", "ORCA · Sí = 2 · Parcial = 1 · No = 0 · AS-IS = contraloría antes de ORCA · Hoy = 9-oct-2026 · Meta = 13-nov-2026")
    encabezado(ws, 4, ["#", "Afirmación", "AS-IS", "Hoy", "Meta"])
    puntos = DataValidation(type="whole", operator="between", formula1="0", formula2="2", showErrorMessage=True,
                            error="Use 2 (Sí), 1 (Parcial) o 0 (No).")
    ws.add_data_validation(puntos)
    for i, (afirmacion, *valores) in enumerate(MADUREZ, 1):
        fila = 4 + i
        ws.cell(fila, 1, i).alignment = CENTRO
        ws.cell(fila, 2, afirmacion).alignment = ENVOLVER
        for col, v in enumerate(valores, 3):
            ws.cell(fila, col, v).alignment = CENTRO
            puntos.add(ws.cell(fila, col))
        for col in range(1, 6):
            ws.cell(fila, col).border = BORDE
    ultima = 4 + len(MADUREZ)
    total, nivel = ultima + 1, ultima + 2
    ws.cell(total, 2, "TOTAL (/16)")
    ws.cell(nivel, 2, "Nivel de madurez")
    for col in "CDE":
        ws[f"{col}{total}"] = f"=SUM({col}5:{col}{ultima})"
        ws[f"{col}{nivel}"] = (f'=IF({col}{total}<=3,"1 · Inicial",IF({col}{total}<=6,"2 · Repetible",'
                              f'IF({col}{total}<=10,"3 · Definido",IF({col}{total}<=13,"4 · Gestionado","5 · Optimizado"))))')
    for fila in (total, nivel):
        for col in range(1, 6):
            c = ws.cell(fila, col)
            c.font = Font(bold=True)
            c.fill = PatternFill("solid", fgColor=LILA)
            c.alignment = CENTRO if col > 2 else ENVOLVER
            c.border = BORDE

    escala = nivel + 2
    ws.cell(escala, 2, "Escala").font = Font(bold=True)
    for k, (rango, nombre) in enumerate([("0 – 3", "Nivel 1 · Inicial"), ("4 – 6", "Nivel 2 · Repetible"),
                                         ("7 – 10", "Nivel 3 · Definido"), ("11 – 13", "Nivel 4 · Gestionado"),
                                         ("14 – 16", "Nivel 5 · Optimizado")], 1):
        ws.cell(escala + k, 2, f"{rango}  →  {nombre}")

    reflexion = escala + 7
    ws.cell(reflexion, 2, "Reflexión").font = Font(bold=True, color=MAGENTA)
    ws.cell(reflexion + 1, 2, (
        "Partimos de Nivel 1 · Inicial (2/16). Con la Entrega 1, ORCA suma 8/16 (Nivel 3 · Definido), pero las ocho "
        "respuestas son 'Parcial': el gobierno está diseñado y documentado, no operando; en rigor estamos entre el "
        "Nivel 2 y el 3. Meta al 13-nov: Nivel 4 · Gestionado (13/16), con calidad, PII y linaje medidos en cada lote. "
        "No apuntamos al Nivel 5 porque exige mejora continua demostrada en varios ciclos. Para el salto faltan: "
        "catálogo y diccionario (Sesión 2), reglas de calidad por lote con quality gate ≥ 95 %, política de "
        "seudonimización aprobada, linaje en curated y mart, políticas escritas y matriz de acceso por rol. "
        "Detalle en documentacion/05_plan_gobierno_datos.md §1.2."))
    ws.merge_cells(start_row=reflexion + 1, start_column=2, end_row=reflexion + 1, end_column=5)
    ws.cell(reflexion + 1, 2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[reflexion + 1].height = 150

    for col, ancho in zip("ABCDE", (5, 62, 10, 10, 10)):
        ws.column_dimensions[col].width = ancho


def hoja_roles(wb):
    ws = wb.create_sheet("Roles")
    titulo(ws, "Parte 2 · Roles del Data Office en el equipo", "Una persona puede tener más de un rol")
    encabezado(ws, 4, ["Rol de gobierno", "Qué hace en ORCA", "Integrante"])
    for i, fila in enumerate(ROLES, 5):
        for col, valor in enumerate(fila, 1):
            c = ws.cell(i, col, valor)
            c.alignment = ENVOLVER
            c.border = BORDE
        ws.cell(i, 1).font = Font(bold=True)
    nota = 5 + len(ROLES) + 1
    ws.cell(nota, 1, "Control de segregación").font = Font(bold=True, color=MAGENTA)
    ws.cell(nota + 1, 1, (
        "Quien construye el dato (custodio) y quien lo usa (analista) son personas distintas, y ninguno aprueba su "
        "propio trabajo: la calidad de cada lote la aprueba el Data Steward (A) y lo que se publica en el dashboard "
        "lo aprueba el Data Owner (A)."))
    ws.merge_cells(start_row=nota + 1, start_column=1, end_row=nota + 1, end_column=3)
    ws.cell(nota + 1, 1).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[nota + 1].height = 45
    for col, ancho in zip("ABC", (32, 70, 40)):
        ws.column_dimensions[col].width = ancho


def hoja_raci(wb):
    ws = wb.create_sheet("RACI")
    titulo(ws, "Parte 3 · Matriz RACI", "R = ejecuta · A = responde (solo uno por tarea) · C = consultado · I = informado")
    encabezado(ws, 4, ["#", "Bloque", "Tarea de gobierno",
                       f"Data Owner\n{OWNER}", f"Data Steward\n{STEWARD}", f"Custodio técnico\n{CUSTODIO}",
                       "Consumidor / Analista\nJhon Sebastian Rayo Posada", "Nº de A", "Regla de oro"])
    ws.row_dimensions[4].height = 48
    letras = DataValidation(type="list", formula1='"R,A,C,I,A/R"', allow_blank=True)
    ws.add_data_validation(letras)
    for i, (bloque, tarea, *asignacion) in enumerate(RACI, 1):
        fila = 4 + i
        ws.cell(fila, 1, i)
        ws.cell(fila, 2, bloque)
        ws.cell(fila, 3, tarea)
        for col, letra in enumerate(asignacion, 4):
            c = ws.cell(fila, col, letra)
            c.font = Font(bold="A" in letra, color=COLOR_LETRA[letra[0]])
            letras.add(c)
        ws.cell(fila, 8, f'=COUNTIF(D{fila}:G{fila},"*A*")')
        ws.cell(fila, 9, f'=IF(AND(H{fila}=1,COUNTIF(D{fila}:G{fila},"*R*")>=1),"OK","Revisar")')
        for col in range(1, 10):
            c = ws.cell(fila, col)
            c.border = BORDE
            c.alignment = ENVOLVER if col in (2, 3) else CENTRO
    ultima = 4 + len(RACI)
    rango = f"I5:I{ultima}"
    ws.conditional_formatting.add(rango, CellIsRule(operator="equal", formula=['"OK"'],
                                                    fill=PatternFill("solid", fgColor="D9F2DF")))
    ws.conditional_formatting.add(rango, FormulaRule(formula=[f'I5<>"OK"'],
                                                     fill=PatternFill("solid", fgColor="F8D7DA")))

    resumen = ultima + 2
    ws.cell(resumen, 3, "Total de A por rol").font = Font(bold=True)
    for col in "DEFG":
        ws[f"{col}{resumen}"] = f'=COUNTIF({col}5:{col}{ultima},"*A*")'
        ws[f"{col}{resumen}"].alignment = CENTRO
        ws[f"{col}{resumen}"].font = Font(bold=True)
    ws.cell(resumen + 1, 3, "Tareas que cumplen la regla de oro").font = Font(bold=True)
    ws[f"D{resumen + 1}"] = f'=COUNTIF({rango},"OK")&" / {len(RACI)}"'
    ws[f"D{resumen + 1}"].font = Font(bold=True)

    for col, ancho in zip("ABCDEFGHI", (5, 20, 62, 16, 16, 16, 16, 9, 12)):
        ws.column_dimensions[col].width = ancho
    ws.freeze_panes = "D5"


def validar():
    for i, (_, tarea, *asignacion) in enumerate(RACI, 1):
        n_a = sum("A" in letra for letra in asignacion)
        assert n_a == 1, f"Tarea {i} ({tarea}) tiene {n_a} A"
        assert any("R" in letra for letra in asignacion), f"Tarea {i} ({tarea}) no tiene R"


if __name__ == "__main__":
    validar()
    wb = Workbook()
    hoja_madurez(wb)
    hoja_roles(wb)
    hoja_raci(wb)
    wb.save(SALIDA)
    totales = [sum(fila[k] for fila in MADUREZ) for k in (1, 2, 3)]
    a_por_rol = [sum("A" in fila[k] for fila in RACI) for k in (2, 3, 4, 5)]
    print(f"OK -> {SALIDA.name} | madurez AS-IS/hoy/meta = {totales} | A por rol (Owner, Steward, Custodio, Consumidor) = {a_por_rol}")
