"""Genera ORCA-Arquitectura-v1.0.archimate a partir del boceto v0.1.

1. Alinea los nombres de los componentes con lo implementado (scripts, archivos y herramientas reales).
2. Agrega la vista 04 · Despliegue final, seguridad y control de acceso, con sus elementos y relaciones.
   Todas las relaciones usadas están permitidas en ArchiMate 3.2 (serving, realization, access,
   assignment, composition, flow).
3. Renderiza la vista 04 a PNG (documentacion/img/archimate-04-despliegue-acceso.png) con el mismo
   código de colores por capa de Archi. Para la vista nativa, abrir el .archimate en Archi.

Uso:  python documentacion/archimate/actualizar_modelo_v1.py
"""
import re
import textwrap
import uuid
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

AQUI = Path(__file__).resolve().parent
ORIGEN, DESTINO = AQUI / "ORCA-Arquitectura-v0.1.archimate", AQUI / "ORCA-Arquitectura-v1.0.archimate"
PNG = AQUI.parent / "img" / "archimate-04-despliegue-acceso.png"

RENOMBRAR = {
    "ORCA · Observatorio de Riesgo en Contratación de Antioquia · v0.1 (boceto)": "ORCA · Observatorio de Riesgo en Contratación de Antioquia · v1.0 (entrega final)",
    "Pipeline ORCA (Python · notebooks)": "Pipeline ORCA (descargar_fuentes.py · limpieza.py)",
    "Motor de calidad de datos": "Motor de calidad (calidad.py · 6 dimensiones · gate 95 %)",
    "Motor de reglas de riesgo": "Motor de reglas de riesgo (riesgo.py · 9 banderas)",
    "Dashboard ORCA": "Dashboard ORCA (Streamlit · dashboard/app.py)",
    "Notificador de alertas (Power Automate)": "Notificador de alertas (notificar_alertas.py + Power Automate)",
    "Catálogo de datos y linaje": "Catálogo y linaje (manifiestos + 04_gobierno_datos.ipynb)",
    "Módulo de privacidad (seudonimización)": "Módulo de privacidad (HMAC-SHA256 · enmascarado)",
    "Servicio de BI (Power BI / Streamlit)": "Servidor Streamlit (dashboard)",
    "Servidor de analítica ORCA": "Equipo de analítica ORCA (Windows · Python 3.13)",
    "raw/contratos_AAAAMMDD.parquet": "data/raw/DS-01_secop2_contratos_AAAAMMDD.parquet",
    "curated/contratos_curados.parquet": "data/curated/DS-01_contratos_curated.parquet",
    "mart/riesgo_contratos.parquet": "data/mart/mart_contratos_riesgo.parquet",
}
REFERENCIAS = {  # elementos existentes que la vista 04 reutiliza
    "dashboard": "id-b0427d6a31244d1d8dfcf8975b5620f0", "notificador": "id-0c92fed0e4ea49a8a991fa979210116a",
    "servidor": "id-b9a5fbd5f54846949c91b220cbc7abb2", "programador": "id-6137dc3dd5584c98813e9ad1a14e8f38",
    "streamlit": "id-10b7ab5c9ddd48bd8844983d3ce4b544", "github": "id-baf858f569194062ba282027f3fb4e94",
    "art_raw": "id-c3651ffb88904697adde10db4ce40c21", "art_cur": "id-5f9cde15ca5a4fcaaee547c3d2454997",
    "art_mart": "id-45e28fb0e183429b9ccd5a96e2fe2dc4", "linaje": "id-1404edf18cf0489f9c687f7ac1a5afb7",
    "actor_owner": "id-2f31da150778492f85faa40615e0ff58", "actor_steward": "id-79fc36dbe0cb4f72af3e043165af2bc4",
    "actor_auditor": "id-bc5068ea8ef14d118e15eef2cfc1d58b",
}
NUEVOS = {  # clave: (tipo, nombre, carpeta, documentación)
    "rol_owner": ("BusinessRole", "Data Owner", "Business", "Aprueba alcance, reglas, clasificación, accesos y publicación. Lee raw, curated y mart."),
    "rol_steward": ("BusinessRole", "Data Steward", "Business", "Define significado y calidad; resuelve incidentes. Lee raw, curated y mart."),
    "rol_custodio": ("BusinessRole", "Custodio técnico", "Business", "Opera el pipeline: único rol que escribe en las capas (segregación)."),
    "rol_analista": ("BusinessRole", "Analista (consumidor)", "Business", "Construye banderas y dashboard sobre datos seudonimizados. Lee curated y mart."),
    "rol_auditor": ("BusinessRole", "Auditor (consumidor final)", "Business", "Gestiona la bandeja de alertas. Lee solo mart."),
    "rol_ciudadania": ("BusinessRole", "Ciudadanía", "Business", "Ve solo agregados públicos; las alertas son reservadas."),
    "srv_acceso": ("ApplicationService", "Control de acceso por rol y capa", "Application", "Mínimo privilegio: matriz MATRIZ_ACCESO de notebooks/gobierno.py."),
    "cmp_acceso": ("ApplicationComponent", "Políticas como código (gobierno.py)", "Application", "Matriz de acceso, clasificación, nomenclatura, retención y diccionario del mart."),
    "cmp_orquestador": ("ApplicationComponent", "Orquestador (orquestar_pipeline.py)", "Application", "Ingesta → curated → gate → mart → alertas → retención; deja registro por corrida."),
    "do_raw": ("DataObject", "Zona raw · Confidencial (PII en claro)", "Application", "Retención: 3 lotes / 90 días."),
    "do_cur": ("DataObject", "Zona curated · Interno (PII seudonimizada)", "Application", "Retención: se sobrescribe; linaje en el manifiesto."),
    "do_mart": ("DataObject", "Zona mart · Confidencial (alertas reservadas)", "Application", "Lo único que lee el dashboard."),
    "art_reglas": ("Artifact", "notebooks/reglas_riesgo.json (v1.0.0)", "Technology & Physical", "Reglas versionadas (AD-4)."),
    "art_registro": ("Artifact", "automatizacion/registro_pipeline.csv", "Technology & Physical", "Evidencia de cada corrida automática."),
    "art_gha": ("SystemSoftware", "GitHub Actions (monitoreo diario)", "Technology & Physical", ".github/workflows/monitoreo-fuente.yml"),
}
RELACIONES = [  # (tipo, origen, destino, nombre, extra)
    *[("Serving", "srv_acceso", r, "", "") for r in ("rol_owner", "rol_steward", "rol_custodio", "rol_analista", "rol_auditor", "rol_ciudadania")],
    ("Realization", "cmp_acceso", "srv_acceso", "", ""),
    ("Serving", "cmp_acceso", "dashboard", "filtra vistas por rol", ""),
    ("Access", "srv_acceso", "do_raw", "", ' accessType="1"'),
    ("Access", "srv_acceso", "do_cur", "", ' accessType="1"'),
    ("Access", "srv_acceso", "do_mart", "", ' accessType="1"'),
    ("Flow", "cmp_orquestador", "notificador", "alertas de riesgo alto", ""),
    ("Flow", "cmp_orquestador", "dashboard", "mart publicado", ""),
    ("Realization", "art_raw", "do_raw", "", ""),
    ("Realization", "art_cur", "do_cur", "", ""),
    ("Realization", "art_mart", "do_mart", "", ""),
    ("Assignment", "servidor", "art_raw", "", ""),
    ("Assignment", "servidor", "art_cur", "", ""),
    ("Assignment", "servidor", "art_mart", "", ""),
    ("Assignment", "servidor", "art_reglas", "", ""),
    ("Assignment", "servidor", "art_registro", "", ""),
    ("Composition", "servidor", "programador", "", ""),
    ("Serving", "programador", "cmp_orquestador", "02:00 diario", ""),
    ("Serving", "streamlit", "dashboard", "", ""),
    ("Composition", "github", "art_gha", "", ""),
    ("Assignment", "actor_owner", "rol_owner", "", ""),
    ("Assignment", "actor_steward", "rol_steward", "", ""),
    ("Assignment", "actor_auditor", "rol_auditor", "", ""),
]
# Disposición de la vista 04: clave -> (x, y, ancho, alto)
LAYOUT = {
    "rol_owner": (20, 40, 170, 55), "rol_steward": (210, 40, 170, 55), "rol_custodio": (400, 40, 170, 55),
    "rol_analista": (590, 40, 170, 55), "rol_auditor": (780, 40, 170, 55), "rol_ciudadania": (970, 40, 170, 55),
    "srv_acceso": (400, 170, 360, 55),
    "cmp_acceso": (20, 280, 240, 65), "dashboard": (330, 280, 240, 65), "cmp_orquestador": (640, 280, 220, 65),
    "notificador": (920, 280, 220, 65),
    "do_raw": (20, 410, 300, 55), "do_cur": (420, 410, 300, 55), "do_mart": (820, 410, 300, 55),
    "art_raw": (20, 540, 300, 50), "art_cur": (420, 540, 300, 50), "art_mart": (820, 540, 300, 50),
    "servidor": (20, 660, 380, 60), "programador": (20, 760, 300, 50), "art_reglas": (420, 660, 260, 50),
    "art_registro": (420, 740, 260, 50), "streamlit": (720, 660, 200, 60), "github": (950, 660, 190, 60),
    "art_gha": (950, 760, 190, 50),
}
CAPA = {"BusinessRole": "#ffffb5", "BusinessActor": "#ffffb5", "ApplicationService": "#b5ffff", "ApplicationComponent": "#b5ffff",
        "DataObject": "#b5ffff", "Artifact": "#c9e7b7", "Node": "#c9e7b7", "SystemSoftware": "#c9e7b7"}


def nid() -> str:
    return "id-" + uuid.uuid4().hex


def insertar_en_carpeta(xml: str, carpeta: str, bloque: str) -> str:
    patron = re.compile(r'(<folder name="' + re.escape(escape(carpeta)) + r'"[^>]*>)')
    return patron.sub(lambda m: m.group(1) + "\n" + bloque, xml, count=1)


def main() -> None:
    xml = ORIGEN.read_text(encoding="utf-8")
    for viejo, nuevo in RENOMBRAR.items():
        xml = xml.replace(f'name="{escape(viejo)}"', f'name="{escape(nuevo)}"')
    xml = xml.replace("<purpose>Boceto de arquitectura (Entrega 1)", "<purpose>Arquitectura v1.0 (entrega final, 13-nov-2026). Boceto original: Entrega 1")

    ids = dict(REFERENCIAS)
    tipos = {}
    for k, (tipo, nombre, carpeta, doc) in NUEVOS.items():
        ids[k], tipos[k] = nid(), tipo
        xml = insertar_en_carpeta(xml, carpeta, f'<element xsi:type="archimate:{tipo}" name="{escape(nombre)}" id="{ids[k]}">'
                                                f'<documentation>{escape(doc)}</documentation></element>')
    nombres = {k: re.search(r'id="' + v + r'"', xml) and re.search(r'name="([^"]*)" id="' + v + '"', xml).group(1) for k, v in ids.items()}
    tipos.update({k: re.search(r'xsi:type="archimate:(\w+)" name="[^"]*" id="' + v + '"', xml).group(1) for k, v in REFERENCIAS.items()})

    rels = []
    for tipo, o, d, nombre, extra in RELACIONES:
        rid = nid()
        rels.append((rid, tipo, o, d, nombre))
        nm = f' name="{escape(nombre)}"' if nombre else ""
        xml = insertar_en_carpeta(xml, "Relations", f'<element xsi:type="archimate:{tipo}Relationship"{nm} id="{rid}" '
                                                    f'source="{ids[o]}" target="{ids[d]}"{extra}/>')

    # vista 04
    dobj = {k: nid() for k in LAYOUT}
    conex = {rid: nid() for rid, *_ in rels}
    entrantes = {k: [] for k in LAYOUT}
    for rid, _, o, d, _ in rels:
        if o in LAYOUT and d in LAYOUT:
            entrantes[d].append(conex[rid])
    hijos = []
    for k, (x, y, w, h) in LAYOUT.items():
        salientes = "".join(f'<sourceConnection xsi:type="archimate:Connection" id="{conex[rid]}" source="{dobj[k]}" '
                            f'target="{dobj[d]}" archimateRelationship="{rid}"/>'
                            for rid, _, o, d, _ in rels if o == k and d in LAYOUT)
        tc = f' targetConnections="{" ".join(entrantes[k])}"' if entrantes[k] else ""
        hijos.append(f'<child xsi:type="archimate:DiagramObject" id="{dobj[k]}"{tc} textAlignment="2" archimateElement="{ids[k]}">'
                     f'<bounds x="{x}" y="{y}" width="{w}" height="{h}"/>{salientes}</child>')
    nota = ('<child xsi:type="archimate:Note" id="' + nid() + '" textAlignment="1"><bounds x="20" y="840" width="1120" height="45"/>'
            '<content>Mínimo privilegio: raw solo Owner/Steward (lectura) y custodio (escritura) · curated + analista · mart + auditor · '
            'ciudadanía solo agregados. Solo el custodio escribe (segregación de funciones).</content></child>')
    vista = (f'<element xsi:type="archimate:ArchimateDiagramModel" name="04 · Despliegue final, seguridad y control de acceso" id="{nid()}">'
             '<documentation>Vista de la entrega final: dónde corre cada pieza, qué clasificación tiene cada zona y qué rol accede a cuál.</documentation>'
             + "".join(hijos) + nota + "</element>")
    xml = insertar_en_carpeta(xml, "Views", vista)
    DESTINO.write_text(xml, encoding="utf-8")
    print("Modelo:", DESTINO.name, "· elementos nuevos:", len(NUEVOS), "· relaciones nuevas:", len(rels))
    dibujar({k: nombres[k] for k in LAYOUT}, {k: tipos[k] for k in LAYOUT}, rels)


def dibujar(nombres: dict, tipos: dict, rels: list) -> None:
    fig, ax = plt.subplots(figsize=(17, 13.5), dpi=110)
    ax.set_xlim(0, 1160); ax.set_ylim(900, 0); ax.axis("off")
    for y0, y1, capa, col in ((25, 235, "Negocio · roles", "#fffff0"), (265, 480, "Aplicación y datos", "#f0ffff"),
                              (525, 825, "Tecnología · despliegue", "#f2f9ee")):
        ax.add_patch(FancyBboxPatch((10, y0), 1140, y1 - y0, boxstyle="round,pad=0,rounding_size=6", fc=col, ec="#dddddd", lw=1))
        ax.text(1145, y0 + 14, capa, ha="right", va="center", fontsize=10, color="#777", style="italic")
    centro = {}
    for k, (x, y, w, h) in LAYOUT.items():
        t = tipos[k]
        estilo = "round,pad=0,rounding_size=12" if t.endswith("Service") else "square,pad=0"
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=estilo, fc=CAPA.get(t, "#eee"), ec="#555", lw=1))
        ax.text(x + w / 2, y + h / 2 + 4, textwrap.fill(nombres[k].replace("&amp;", "&"), max(14, int(w / 6.6))),
                ha="center", va="center", fontsize=8.6, linespacing=1.15)
        ax.text(x + w - 4, y + 10, t.replace("Application", "App ").replace("Business", "").replace("System", "Sys "),
                ha="right", va="center", fontsize=6.5, color="#888")
        centro[k] = (x + w / 2, y + h / 2, w, h)
    estilos = {"Serving": ("-|>", "-"), "Realization": ("-|>", "--"), "Access": ("->", ":"), "Flow": ("-|>", "--"),
               "Assignment": ("-|>", "-"), "Composition": ("-", "-")}
    for _, tipo, o, d, nombre in rels:
        if o not in LAYOUT or d not in LAYOUT:
            continue
        (xo, yo, wo, ho), (xd, yd, wd, hd) = centro[o], centro[d]
        p0 = (xo, yo + ho / 2) if yd > yo + 5 else (xo, yo - ho / 2) if yd < yo - 5 else (xo + wo / 2 * (1 if xd > xo else -1), yo)
        p1 = (xd, yd - hd / 2) if yd > yo + 5 else (xd, yd + hd / 2) if yd < yo - 5 else (xd - wd / 2 * (1 if xd > xo else -1), yd)
        flecha, linea = estilos[tipo]
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=flecha, linestyle=linea, mutation_scale=11, color="#444", lw=0.9,
                                     connectionstyle="arc3,rad=0.0"))
        if nombre:
            horizontal = abs(p0[1] - p1[1]) < 5
            lx = (p0[0] + p1[0]) / 2 if horizontal else p0[0] + 0.25 * (p1[0] - p0[0]) + 6
            ly = p0[1] - 12 if horizontal else p0[1] + 0.25 * (p1[1] - p0[1])
            ax.text(lx, ly, nombre, ha="center" if horizontal else "left", fontsize=7.2, color="#333",
                    bbox=dict(fc="white", ec="none", pad=1))
    ax.text(10, 10, "ORCA v1.0 · Vista 04 · Despliegue final, seguridad y control de acceso", fontsize=13, weight="bold", va="center")
    ax.text(20, 862, "Mínimo privilegio: raw solo Owner/Steward (lectura) y custodio (escritura) · curated + analista · mart + auditor · "
            "ciudadanía solo agregados. Solo el custodio escribe (segregación de funciones).", fontsize=9, color="#444")
    ax.text(20, 885, "Relaciones: ── serving / assignment   - - realization / flow   ··· access (lectura)   ── sin flecha: composition",
            fontsize=8, color="#666")
    PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG, bbox_inches="tight", facecolor="white")
    print("Imagen:", PNG.name)


if __name__ == "__main__":
    main()
