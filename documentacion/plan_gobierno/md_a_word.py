"""Convierte documentacion/05_plan_gobierno_datos.md a Word (.docx) con el formato del proyecto.

Soporta el subconjunto de Markdown que usa el documento: títulos (#, ##, ###), tablas,
citas (>), listas (- y 1.), separadores (---) y formato en línea (**negrita**, *cursiva*,
`código`, [enlaces](url), <br/> dentro de celdas).

Uso:  python documentacion/plan_gobierno/md_a_word.py
"""
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

DOC = Path(__file__).resolve().parents[1]
ENTRADA = DOC / "05_plan_gobierno_datos.md"
SALIDA = DOC / "ORCA-Plan-Gobierno-v1.0.docx"

MAGENTA = RGBColor(0xB5, 0x00, 0x5B)
MORADO = RGBColor(0x3B, 0x1F, 0x4A)
GRIS = RGBColor(0x59, 0x59, 0x59)
LILA_HEX, MAGENTA_HEX = "F3E8F5", "B5005B"
COLOR_RACI = {"R": RGBColor(0x1E, 0x7B, 0x34), "A": MAGENTA, "C": RGBColor(0x2F, 0x5D, 0xAA), "I": RGBColor(0xC5, 0x8A, 0x00)}
ANCHO_UTIL_CM = 21.59 - 2 * 2.3

INLINE = re.compile(r"\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`|\[(.+?)\]\((.+?)\)")


def sombrear(celda, hex_color):
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)


def borde_parrafo(parrafo, lado, color, tam=12, espacio=4):
    p_pr = parrafo._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    b = OxmlElement(f"w:{lado}")
    b.set(qn("w:val"), "single")
    b.set(qn("w:sz"), str(tam))
    b.set(qn("w:space"), str(espacio))
    b.set(qn("w:color"), color)
    bdr.append(b)
    p_pr.append(bdr)


def hipervinculo(parrafo, texto, url, tam):
    rel = parrafo.part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    h = OxmlElement("w:hyperlink")
    h.set(qn("r:id"), rel)
    r = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    for etiqueta, valor in (("w:color", "2F5DAA"), ("w:u", "single")):
        e = OxmlElement(etiqueta)
        e.set(qn("w:val"), valor)
        r_pr.append(e)
    if tam:
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(tam.pt * 2)))
        r_pr.append(sz)
    r.append(r_pr)
    t = OxmlElement("w:t")
    t.text = texto
    t.set(qn("xml:space"), "preserve")
    r.append(t)
    h.append(r)
    parrafo._p.append(h)


def en_linea(parrafo, texto, negrita=False, cursiva=False, tam=None, color=None):
    """Agrega `texto` al párrafo interpretando el formato en línea (recursivo para anidar)."""
    pos = 0
    for m in INLINE.finditer(texto):
        if m.start() > pos:
            _run(parrafo, texto[pos:m.start()], negrita, cursiva, False, tam, color)
        bi, b, i, code, ltexto, url = m.groups()
        if bi is not None:
            en_linea(parrafo, bi, True, True, tam, color)
        elif b is not None:
            en_linea(parrafo, b, True, cursiva, tam, color)
        elif i is not None:
            en_linea(parrafo, i, negrita, True, tam, color)
        elif code is not None:
            _run(parrafo, code, negrita, cursiva, True, tam, color)
        elif url.startswith("http"):
            hipervinculo(parrafo, ltexto, url, tam)
        else:  # enlace interno del repositorio: se deja el texto
            en_linea(parrafo, ltexto, negrita, cursiva, tam, color)
        pos = m.end()
    if pos < len(texto):
        _run(parrafo, texto[pos:], negrita, cursiva, False, tam, color)


def _run(parrafo, texto, negrita, cursiva, code, tam, color):
    if code and tam:  # en tablas, los identificadores largos solo se parten después de un guion bajo
        texto = texto.replace("_", "_​")
    r = parrafo.add_run(texto)
    r.bold, r.italic = negrita or None, cursiva or None
    if code:
        r.font.name = "Consolas"
        r.font.color.rgb = MORADO
    if tam:
        r.font.size = tam
    if color is not None:
        r.font.color.rgb = color


def celdas(linea):
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def es_separador(fila):
    """Fila de bloque dentro de una tabla: solo la primera celda tiene texto, en negrita."""
    return len(fila) > 3 and fila[0].startswith("**") and all(c == "" for c in fila[1:])


def anchos(filas):
    """Ancho de columna proporcional al contenido, sin bajar del mínimo que evita partir palabras."""
    n = len(filas[0])
    pesos, minimos = [], []
    for j in range(n):
        textos = [re.sub(r"\*|`|<br/>|\[|\]\(.*?\)", "", f[j]) for f in filas if not es_separador(f)]
        pesos.append(max(4, min(max(len(t) for t in textos), 160)) ** 0.7)
        # palabra más larga; un identificador (con "_") puede partirse en dos líneas
        palabra = max((len(w) if "_" not in w else -(-len(w) // 2) for t in textos for w in t.split()), default=1)
        minimos.append(0.19 * min(palabra, 30) + 0.4)  # cm a 9 pt + márgenes de celda
    fijos = {}
    while True:  # las columnas que no alcanzan su mínimo se fijan y el resto se reparte de nuevo
        libre = ANCHO_UTIL_CM - sum(fijos.values())
        peso_libre = sum(p for j, p in enumerate(pesos) if j not in fijos)
        nuevos = {j: minimos[j] for j in range(n) if j not in fijos and libre * pesos[j] / peso_libre < minimos[j]}
        if not nuevos:
            break
        fijos.update(nuevos)
    return [Cm(fijos.get(j, libre * pesos[j] / peso_libre if peso_libre else 0)) for j in range(n)]


def tabla(doc, lineas):
    filas = [celdas(l) for l in lineas]
    alineacion = []
    if len(filas) > 1 and all(re.fullmatch(r":?-+:?", c) for c in filas[1]):
        alineacion = [c.startswith(":") and c.endswith(":") for c in filas[1]]
        filas = [filas[0]] + filas[2:]
    n = len(filas[0])
    filas = [f + [""] * (n - len(f)) for f in filas]
    sin_encabezado = all(c == "" for c in filas[0])  # tablas de metadatos "| | |"
    if sin_encabezado:
        filas = filas[1:]
    t = doc.add_table(rows=len(filas), cols=n)
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    w = anchos(filas)
    tam = Pt(9)
    for i, fila in enumerate(filas):
        encabezado = i == 0 and not sin_encabezado
        separador = not encabezado and es_separador(fila)
        total = fila[1].startswith("**TOTAL") or fila[1].startswith("**Nivel")
        for j, texto in enumerate(fila):
            c = t.cell(i, j)
            c.width = w[j]
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            c.paragraphs[0].text = ""
            partes = texto.split("<br/>")
            for k, parte in enumerate(partes):
                p = c.paragraphs[0] if k == 0 else c.add_paragraph()
                p.paragraph_format.space_after = Pt(0)
                if (alineacion and alineacion[j]) or encabezado and j > 1 and n > 4:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                letra = parte.replace("*", "").strip()
                if encabezado:
                    p.paragraph_format.keep_with_next = True  # el encabezado no queda solo al pie de página
                    en_linea(p, parte, negrita=True, tam=tam, color=RGBColor(0xFF, 0xFF, 0xFF))
                elif letra in ("R", "A", "C", "I", "A/R"):
                    en_linea(p, parte, negrita="A" in letra, tam=tam, color=COLOR_RACI[letra[0]])
                else:
                    en_linea(p, parte, negrita=sin_encabezado and j == 0, tam=tam)
            if encabezado:
                sombrear(c, MAGENTA_HEX)
            elif separador or total or (sin_encabezado and j == 0):
                sombrear(c, LILA_HEX)
        no_partir = OxmlElement("w:cantSplit")
        no_partir.set(qn("w:val"), "true")
        t.rows[i]._tr.get_or_add_trPr().append(no_partir)
        if separador:
            fila_t = t.rows[i]
            unida = fila_t.cells[0].merge(fila_t.cells[n - 1])
            for parrafo in unida.paragraphs[1:]:
                parrafo._p.getparent().remove(parrafo._p)
        if encabezado:  # repetir encabezado si la tabla cruza de página
            tr_pr = t.rows[i]._tr.get_or_add_trPr()
            h = OxmlElement("w:tblHeader")
            h.set(qn("w:val"), "true")
            tr_pr.append(h)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def pie_de_pagina(seccion):
    p = seccion.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("ORCA · Plan de Gobierno de Datos v0.2 · Página ")
    r.font.size, r.font.color.rgb = Pt(8), GRIS
    for tipo, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        r = p.add_run()
        r.font.size, r.font.color.rgb = Pt(8), GRIS
        if tipo:
            f = OxmlElement("w:fldChar")
            f.set(qn("w:fldCharType"), tipo)
            r._r.append(f)
        else:
            instr = OxmlElement("w:instrText")
            instr.set(qn("xml:space"), "preserve")
            instr.text = txt
            r._r.append(instr)


def configurar(doc):
    s = doc.sections[0]
    s.page_width, s.page_height = Cm(21.59), Cm(27.94)  # Carta
    s.left_margin = s.right_margin = Cm(2.3)
    s.top_margin = s.bottom_margin = Cm(2.2)
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Calibri")
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.1
    for nombre, tam, color in (("Title", 22, MAGENTA), ("Heading 1", 15, MAGENTA), ("Heading 2", 12, MORADO)):
        st = doc.styles[nombre]
        st.font.name, st.font.size, st.font.color.rgb, st.font.bold = "Calibri", Pt(tam), color, True
        rfonts = st.element.rPr.find(qn("w:rFonts"))
        for attr in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            if rfonts is not None and rfonts.get(qn(attr)) is not None:
                del rfonts.attrib[qn(attr)]
        st.paragraph_format.space_before = Pt(14 if nombre != "Title" else 0)
        st.paragraph_format.space_after = Pt(6)
    pie_de_pagina(s)


def convertir():
    doc = Document()
    configurar(doc)
    lineas = ENTRADA.read_text(encoding="utf-8").splitlines()
    i = 0
    while i < len(lineas):
        l = lineas[i]
        if l.startswith("|"):
            bloque = []
            while i < len(lineas) and lineas[i].startswith("|"):
                bloque.append(lineas[i])
                i += 1
            tabla(doc, bloque)
            continue
        if l.startswith(">"):
            cita = []
            while i < len(lineas) and lineas[i].startswith(">"):
                cita.append(lineas[i].lstrip(">").strip())
                i += 1
            tabla_cita = [c for c in cita if c.startswith("|")]
            cita = [c for c in cita if not c.startswith("|")]
            for parrafo in _parrafos_cita(cita):
                p = doc.add_paragraph()
                p.paragraph_format.left_indent = Cm(0.4)
                borde_parrafo(p, "left", MAGENTA_HEX, 18, 8)
                en_linea(p, parrafo, tam=Pt(10), color=GRIS)
            if tabla_cita:
                tabla(doc, tabla_cita)
            continue
        if l.startswith("```"):
            i += 1
            while i < len(lineas) and not lineas[i].startswith("```"):
                i += 1
            i += 1
            nota = doc.add_paragraph()
            en_linea(nota, "[Diagrama de linaje: ver la versión Markdown del plan o la vista 03 de ArchiMate]", cursiva=True, color=GRIS)
            continue
        if l.startswith("# "):
            doc.add_paragraph(l[2:], style="Title")
            sub = doc.add_paragraph()
            en_linea(sub, "Versión 1.0 · Entrega final · Catálogo, diccionario, RACI, políticas, calidad, linaje, clasificación y acceso", cursiva=True, color=GRIS)
        elif l.startswith("## "):
            doc.add_heading(l[3:], level=1)
        elif l.startswith("### "):
            doc.add_heading(l[4:], level=2)
        elif l.strip() == "---":
            p = doc.add_paragraph()
            borde_parrafo(p, "bottom", "D9D9D9", 6, 1)
        elif re.match(r"^\d+\. ", l):
            en_linea(doc.add_paragraph(style="List Number"), re.sub(r"^\d+\. ", "", l))
        elif l.startswith("- "):
            en_linea(doc.add_paragraph(style="List Bullet"), l[2:])
        elif l.strip():
            en_linea(doc.add_paragraph(), l)
        i += 1
    doc.core_properties.title = "ORCA · Plan de Gobierno de Datos v1.0"
    doc.core_properties.author = "Equipo ORCA"
    doc.save(SALIDA)
    print(f"OK -> {SALIDA}")


def _parrafos_cita(lineas):
    """Separa una cita en párrafos por las líneas '>' vacías."""
    parrafos, actual = [], []
    for l in lineas:
        if l:
            actual.append(l)
        elif actual:
            parrafos.append(" ".join(actual))
            actual = []
    if actual:
        parrafos.append(" ".join(actual))
    return parrafos


if __name__ == "__main__":
    convertir()
