"""Dashboard ORCA · priorización de la vigilancia fiscal (Streamlit).

Responde las preguntas de negocio P1–P6 (documentacion/01 §3) leyendo SOLO la zona mart.
El rol elegido en la barra lateral aplica la matriz de acceso del Plan de Gobierno
(notebooks/gobierno.py): cada rol ve únicamente las pestañas que su permiso autoriza.

Ejecutar desde la raíz del repositorio:
    streamlit run dashboard/app.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "notebooks"))
import gobierno  # noqa: E402

AZUL, AZUL_CLARO, GRIS, TINTA = "#2a78d6", "#9ec5f4", "#8a8985", "#52514e"
NIVEL_COLOR = {"Alto": "#d03b3b", "Medio": "#ec835a", "Bajo": "#c3c2b7", "Sin señales": "#e4e3df"}
NIVEL_ICONO = {"Alto": "🔴 Alto", "Medio": "🟠 Medio", "Bajo": "⚪ Bajo", "Sin señales": "· Sin señales"}
ORDEN_NIVEL = ["Alto", "Medio", "Bajo", "Sin señales"]

st.set_page_config(page_title="ORCA · Priorización de la vigilancia fiscal", page_icon="🐋", layout="wide")


def cop(v: float) -> str:
    if pd.isna(v):
        return "—"
    for div, suf in ((1e12, " billones"), (1e9, " mil millones"), (1e6, " millones")):
        if abs(v) >= div:
            return f"${v / div:,.1f}{suf}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${v:,.0f}".replace(",", ".")


def cop_corto(v: float) -> str:
    """Para tarjetas KPI: 'bill.' = billones (10^12), 'mil M' = miles de millones."""
    if abs(v) >= 1e12:
        return f"${v / 1e12:.1f} bill.".replace(".", ",", 1)
    if abs(v) >= 1e9:
        return f"${v / 1e9:,.0f} mil M".replace(",", ".")
    return cop(v)


def miles(n) -> str:
    return f"{int(n):,}".replace(",", ".")


def estilo(fig, alto=380):
    fig.update_layout(height=alto, margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="white", paper_bgcolor="white",
                      font=dict(color=TINTA, size=13), legend=dict(orientation="h", y=-0.15), hoverlabel=dict(bgcolor="white"))
    fig.update_xaxes(showgrid=False, linecolor="#d6d5d0")
    fig.update_yaxes(gridcolor="#eeede9", zeroline=False)
    return fig


@st.cache_data(show_spinner="Cargando la zona mart…")
def cargar(carpeta: str):
    d = Path(carpeta)
    c = pd.read_parquet(d / "mart_contratos_riesgo.parquet")
    e = pd.read_parquet(d / "mart_entidades.parquet")
    p = pd.read_parquet(d / "mart_pares_entidad_proveedor.parquet")
    m = pd.read_parquet(d / "mart_mensual.parquet")
    man = json.loads((d / "mart.manifest.json").read_text(encoding="utf-8"))
    cur = RAIZ / "data" / "curated" / "DS-01_contratos_curated.manifest.json"
    man_cur = json.loads(cur.read_text(encoding="utf-8")) if cur.exists() else {}
    return c, e, p, m, man, man_cur


# ---------------------------------------------------------------- control de acceso
st.sidebar.title("ORCA")
st.sidebar.caption("Observatorio de Riesgo en Contratación de Antioquia")
rol = st.sidebar.selectbox("Rol (control de acceso)", list(gobierno.ROLES), index=4,
                           format_func=lambda r: gobierno.ROLES[r])
st.sidebar.caption(f"Por qué: {gobierno.JUSTIFICACION_ACCESO[rol]}")

try:
    carpeta_mart = gobierno.ruta_capa(rol, "mart")
    detalle = True
except gobierno.AccesoDenegado:
    carpeta_mart = RAIZ / "data" / "mart"     # el rol público solo recibe agregados mensuales (abajo)
    detalle = False

if not (carpeta_mart / "mart.manifest.json").exists():
    st.error("No existe la zona mart. Ejecute primero: `python notebooks/orquestar_pipeline.py`")
    st.stop()

C, E, P, M, MAN, MAN_CUR = cargar(str(carpeta_mart))
if not detalle:                                # mínimo privilegio: se descarta el detalle antes de dibujar
    C = C[["fec_firma", "cod_modalidad", "nom_municipio", "val_contrato", "ind_r1_contratacion_directa",
           "ind_sujeto_vigilancia"]].copy()
    E = P = None

# ---------------------------------------------------------------- filtros
st.sidebar.divider()
st.sidebar.subheader("Filtros")
solo_territorial = st.sidebar.toggle("Solo sujetos de vigilancia (orden territorial)", value=True)
fmin, fmax = C["fec_firma"].min().date(), C["fec_firma"].max().date()
rango = st.sidebar.date_input("Fecha de firma", (fmin, fmax), min_value=fmin, max_value=fmax)
municipios = sorted(C["nom_municipio"].dropna().unique())
sel_mun = st.sidebar.multiselect("Municipio", municipios, placeholder="Todos")

f = C
if solo_territorial:
    f = f[f["ind_sujeto_vigilancia"]]
if isinstance(rango, tuple) and len(rango) == 2:
    f = f[f["fec_firma"].between(pd.Timestamp(rango[0]), pd.Timestamp(rango[1]) + pd.Timedelta(days=1))]
if sel_mun:
    f = f[f["nom_municipio"].isin(sel_mun)]

st.sidebar.divider()
st.sidebar.caption(f"Corte del lote: **{MAN.get('corte')}** · Reglas de riesgo v{MAN['entradas']['reglas']['version']}")
st.sidebar.caption("Las alertas priorizan la revisión: **no son hallazgos ni prueban irregularidad.**")

# ---------------------------------------------------------------- encabezado
st.title("ORCA · ¿Qué contratación vigilar primero?")
cal = MAN["entradas"]["curated"]
st.caption(f"SECOP II · Antioquia · contratos firmados desde 2024 · lote {MAN.get('corte')} · "
           f"calidad del lote {cal['puntaje_calidad']} % → **{cal['decision_quality_gate']}** · "
           f"PII en claro en el mart: **{MAN['controles_gobierno']['pii_en_claro_mart']}**")

vistas = gobierno.vistas_para(rol)
tabs = st.tabs(vistas)
T = dict(zip(vistas, tabs))

# ---------------------------------------------------------------- Resumen
with T["Resumen"]:
    k = st.columns(5)
    k[0].metric("Contratos", miles(len(f)))
    k[1].metric("Valor contratado", cop_corto(f["val_contrato"].sum()), help="bill. = billones de pesos (10¹²)")
    k[2].metric("% contratación directa", f"{100 * f['ind_r1_contratacion_directa'].mean():.1f} %")
    if detalle:
        alto = f[f["niv_riesgo"] == "Alto"]
        k[3].metric("Contratos en riesgo alto", miles(len(alto)), help="Score ≥ 40 / 100")
        k[4].metric("Valor en riesgo alto", cop_corto(alto["val_contrato"].sum()))

        c1, c2 = st.columns([1, 1])
        niv = f["niv_riesgo"].value_counts().reindex(ORDEN_NIVEL).fillna(0).reset_index()
        niv.columns = ["nivel", "contratos"]
        niv["etiqueta"] = niv["nivel"].map(NIVEL_ICONO)
        fig = px.bar(niv, x="contratos", y="etiqueta", orientation="h", color="nivel", color_discrete_map=NIVEL_COLOR,
                     text=niv["contratos"].map(miles), title="Contratos por nivel de riesgo")
        fig.update_traces(textposition="outside", marker_line_width=0, showlegend=False, cliponaxis=False)
        fig.update_yaxes(title=None, autorange="reversed")
        fig.update_xaxes(range=[0, niv["contratos"].max() * 1.18])
        c1.plotly_chart(estilo(fig, 320), width="stretch")

        reglas = json.loads((RAIZ / "notebooks" / "reglas_riesgo.json").read_text(encoding="utf-8"))["banderas"]
        bcols = [c for c in f.columns if c.startswith("ind_r")]
        bd = pd.DataFrame({"bandera": [f"{c.split('_')[1].upper()} · {reglas[c.split('_')[1].upper()]['nombre']}" for c in bcols],
                           "contratos": [int(f[c].sum()) for c in bcols]}).sort_values("contratos")
        fig = px.bar(bd, x="contratos", y="bandera", orientation="h", text=bd["contratos"].map(miles),
                     title="Contratos que activan cada bandera roja", log_x=True)
        fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
        fig.update_yaxes(title=None)
        fig.update_xaxes(title="contratos (escala log)", dtick=1, range=[1.5, 6])
        c2.plotly_chart(estilo(fig, 320), width="stretch")

        st.subheader("Top 15 entidades para el Plan de Vigilancia (PVCF)")
        st.caption("Índice de priorización = 40 % valor expuesto en riesgo alto + 40 % score medio + 20 % si su contratación directa supera su propia historia (P1).")
        ent = E[E["ind_sujeto_vigilancia"]] if solo_territorial else E
        if sel_mun:
            ent = ent[ent["nom_municipio"].isin(sel_mun)]
        top = ent.nsmallest(15, "cant_ranking")
        fig = px.bar(top.iloc[::-1], x="num_indice_prioridad", y="nom_entidad", orientation="h",
                     text=top.iloc[::-1]["num_indice_prioridad"].round(1),
                     hover_data={"cant_contratos": True, "cant_alto": True, "val_riesgo_alto": ":,.0f"})
        fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
        fig.update_yaxes(title=None)
        fig.update_xaxes(title="índice de priorización (0–100)")
        st.plotly_chart(estilo(fig, 520), width="stretch")
    else:
        st.info("Vista pública: solo agregados. Las alertas individuales son información reservada del control fiscal.")
        mod = f.groupby("cod_modalidad").agg(contratos=("val_contrato", "size"), valor=("val_contrato", "sum")).reset_index()
        mod = mod.sort_values("contratos").tail(8)
        fig = px.bar(mod, x="contratos", y="cod_modalidad", orientation="h", text=mod["contratos"].map(miles),
                     title="Contratos por modalidad")
        fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
        fig.update_yaxes(title=None)
        st.plotly_chart(estilo(fig), width="stretch")

# ---------------------------------------------------------------- P1
if "P1 · Entidades" in T:
    with T["P1 · Entidades"]:
        st.subheader("P1 · ¿Qué entidades contratan directo por encima de su propia historia?")
        st.caption("Cada punto es una entidad con ≥ 30 contratos en 2024–2025 y en 2026. Arriba de la diagonal: más contratación directa que antes.")
        ent = E.dropna(subset=["pct_directa_2024_2025", "pct_directa_2026"])
        ent = ent[(ent["cant_contratos_2024_2025"] >= 30) & (ent["cant_contratos_2026"] >= 30)]
        if solo_territorial:
            ent = ent[ent["ind_sujeto_vigilancia"]]
        ent = ent.assign(senal=ent["ind_p1_directa_sobre_historia"].map({True: "Sube ≥ 10 pp (señal P1)", False: "Sin cambio relevante"}))
        ent = ent.assign(tam=(np.log10(ent["val_total"].clip(lower=1)) - 7).clip(lower=1))   # tamaño legible: escala log del valor
        fig = px.scatter(ent, x=100 * ent["pct_directa_2024_2025"], y=100 * ent["pct_directa_2026"], size="tam",
                         color="senal", color_discrete_map={"Sube ≥ 10 pp (señal P1)": "#d03b3b", "Sin cambio relevante": AZUL_CLARO},
                         hover_name="nom_entidad", size_max=22, hover_data={"tam": False, "val_total": ":,.0f"},
                         labels={"x": "% contratación directa 2024–2025", "y": "% contratación directa 2026", "senal": ""})
        fig.add_shape(type="line", x0=0, y0=0, x1=100, y1=100, line=dict(color=GRIS, dash="dot", width=1))
        fig.update_traces(marker=dict(line=dict(width=2, color="white")))
        st.plotly_chart(estilo(fig, 520), width="stretch")
        tabla = ent[ent["ind_p1_directa_sobre_historia"]].sort_values("num_delta_directa_pp", ascending=False)
        st.markdown(f"**{len(tabla)} entidades** con la señal P1 → candidatas a incluir en el PVCF.")
        st.dataframe(tabla[["nom_entidad", "nom_municipio", "cant_contratos_2026", "pct_directa_2024_2025", "pct_directa_2026",
                            "num_delta_directa_pp", "cant_alto"]],
                     column_config={"pct_directa_2024_2025": st.column_config.NumberColumn("% directa 24–25", format="percent"),
                                    "pct_directa_2026": st.column_config.NumberColumn("% directa 2026", format="percent"),
                                    "num_delta_directa_pp": st.column_config.NumberColumn("Δ pp", format="%.1f"),
                                    "nom_entidad": "Entidad", "nom_municipio": "Municipio",
                                    "cant_contratos_2026": "Contratos 2026", "cant_alto": "Alertas altas"},
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- P2
with T["P2 · Ventanas atípicas"]:
    st.subheader("P2 · ¿Qué se firmó en ventanas atípicas?")
    st.caption("La Ley de Garantías (Ley 996 de 2005) restringe la contratación directa desde el 31-ene-2026. Firmar en bloque justo antes es una bandera roja de planeación.")
    mes = f.assign(mes=f["fec_firma"].dt.to_period("M").dt.to_timestamp()).groupby("mes").agg(
        contratos=("val_contrato", "size"), directa=("ind_r1_contratacion_directa", "sum")).reset_index()
    mes["otras"] = mes["contratos"] - mes["directa"]
    fig = go.Figure()
    fig.add_bar(x=mes["mes"], y=mes["directa"], name="Contratación directa", marker_color=AZUL)
    fig.add_bar(x=mes["mes"], y=mes["otras"], name="Otras modalidades", marker_color=AZUL_CLARO)
    fig.add_vrect(x0="2026-01-31", x1="2026-06-21", fillcolor="#eeede9", opacity=0.6, line_width=0,
                  annotation_text="Restricción Ley de Garantías", annotation_position="top left")
    fig.update_layout(barmode="stack", bargap=0.15, title="Contratos firmados por mes")
    fig.update_traces(marker_line_color="white", marker_line_width=1)
    st.plotly_chart(estilo(fig, 420), width="stretch")
    if detalle:
        v = f[f["ind_r2_ventana_atipica"]]
        c1, c2, c3 = st.columns(3)
        c1.metric("Contratos directos en ventana atípica", miles(len(v)))
        c2.metric("Valor", cop(v["val_contrato"].sum()))
        c3.metric("De ellos, riesgo alto", miles((v["niv_riesgo"] == "Alto").sum()))
        top = v.groupby("nom_entidad").agg(contratos=("id_contrato", "size"), valor=("val_contrato", "sum")).nlargest(15, "contratos").reset_index()
        st.markdown("**Entidades con más contratos directos firmados en ventana atípica**")
        st.dataframe(top, hide_index=True, width="stretch",
                     column_config={"valor": st.column_config.NumberColumn("Valor (COP)", format="%,.0f"), "nom_entidad": "Entidad"})

# ---------------------------------------------------------------- P3
if "P3 · Entidad–proveedor" in T:
    with T["P3 · Entidad–proveedor"]:
        st.subheader("P3 · ¿Qué proveedores concentran contratos o valor en una misma entidad?")
        st.caption("Personas naturales aparecen solo con su seudónimo (HMAC-SHA256). Las personas jurídicas, con su nombre público.")
        pr = P[P["ind_r3_concentracion_par"]]
        if solo_territorial:
            pr = pr[pr["id_nit_entidad"].isin(E.loc[E["ind_sujeto_vigilancia"], "id_nit_entidad"])]
        c1, c2 = st.columns(2)
        c1.metric("Pares con concentración (R3)", miles(len(pr)))
        c2.metric("Valor de esos pares", cop(pr["val_total"].sum()))
        top = pr.nlargest(20, "pct_valor_entidad").iloc[::-1].assign(
            par=lambda x: x["nom_entidad"].str.slice(0, 40) + " ← " + x["nom_proveedor"].str.slice(0, 30),
            pct=lambda x: (100 * x["pct_valor_entidad"]).round(1))
        fig = px.bar(top, x="pct", y="par", orientation="h", text="pct",
                     labels={"pct": "% del valor de la entidad", "par": "", "cant_contratos": "contratos"},
                     title="Top 20 pares por % del valor contratado por la entidad",
                     hover_data={"cant_contratos": True, "val_total": ":,.0f"})
        fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
        st.plotly_chart(estilo(fig, 620), width="stretch")
        st.dataframe(pr[["nom_entidad", "nom_proveedor", "cant_contratos", "val_total", "pct_valor_entidad", "pct_contratos_entidad",
                         "cant_directa"]].sort_values("val_total", ascending=False),
                     column_config={"val_total": st.column_config.NumberColumn("Valor (COP)", format="%,.0f"),
                                    "pct_valor_entidad": st.column_config.NumberColumn("% valor entidad", format="percent"),
                                    "pct_contratos_entidad": st.column_config.NumberColumn("% contratos entidad", format="percent"),
                                    "nom_entidad": "Entidad", "nom_proveedor": "Proveedor", "cant_contratos": "Contratos",
                                    "cant_directa": "Directos"},
                     hide_index=True, width="stretch")

# ---------------------------------------------------------------- P4–P6
if "P4–P6 · Contratos" in T:
    with T["P4–P6 · Contratos"]:
        c1, c2, c3 = st.columns(3)
        c1.metric("P4 · Personas naturales en ≥ 3 entidades a la vez", miles(f["ind_r4_simultaneidad_pn"].sum()))
        c2.metric("P5 · Valor atípico para su tipo y modalidad", miles(f["ind_r5_valor_atipico"].sum()))
        c3.metric("P6 · Proceso competitivo con un único oferente", miles(f["ind_r6_unico_oferente"].sum()))
        st.caption(f"P6 se calcula cruzando con SECOP II Procesos (DS-02): el {MAN['entradas']['procesos_DS-02']['pct_contratos_con_proceso_en_DS02']} % de los contratos encontró su proceso.")

        st.markdown("#### P4 · Contratistas persona natural con contratos simultáneos (por seudónimo)")
        pn = (f[f["ind_r4_simultaneidad_pn"]].groupby("id_proveedor_seud")
              .agg(entidades_simultaneas=("cant_entidades_simultaneas", "max"), contratos=("id_contrato", "size"),
                   entidades=("id_nit_entidad", "nunique"), valor=("val_contrato", "sum"))
              .sort_values(["entidades_simultaneas", "valor"], ascending=False).reset_index().head(50))
        st.dataframe(pn, hide_index=True, width="stretch",
                     column_config={"id_proveedor_seud": "Seudónimo del contratista",
                                    "valor": st.column_config.NumberColumn("Valor (COP)", format="%,.0f")})

        st.markdown("#### P5 · Valores atípicos para su grupo (tipo × modalidad)")
        at = f[f["ind_r5_valor_atipico"]].copy()
        at["veces_el_limite"] = at["val_contrato"] / at["val_limite_atipico_grupo"]
        st.dataframe(at.nlargest(50, "val_contrato")[["id_contrato", "nom_entidad", "cod_tipo_contrato", "cod_modalidad",
                                                        "val_contrato", "veces_el_limite", "niv_riesgo", "url_proceso_secop"]],
                     hide_index=True, width="stretch",
                     column_config={"val_contrato": st.column_config.NumberColumn("Valor (COP)", format="%,.0f"),
                                    "veces_el_limite": st.column_config.NumberColumn("× límite del grupo", format="%.1f"),
                                    "url_proceso_secop": st.column_config.LinkColumn("SECOP", display_text="abrir")})

        st.markdown("#### P6 · Procesos competitivos con un único oferente, por modalidad")
        u = f[f["ind_r6_unico_oferente"]].groupby("cod_modalidad").agg(contratos=("id_contrato", "size"), valor=("val_contrato", "sum")).reset_index().sort_values("contratos")
        fig = px.bar(u, x="contratos", y="cod_modalidad", orientation="h", text=u["contratos"].map(miles))
        fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
        fig.update_yaxes(title=None)
        st.plotly_chart(estilo(fig, 340), width="stretch")

# ---------------------------------------------------------------- Bandeja
if "Bandeja de alertas" in T:
    with T["Bandeja de alertas"]:
        st.subheader("Bandeja de alertas priorizadas")
        st.caption("Ordenadas por score y valor. Cada fila enlaza al contrato en SECOP II para la revisión documental. El auditor registra si la alerta fue pertinente (mejora M6).")
        niveles = st.multiselect("Nivel", ORDEN_NIVEL[:3], default=["Alto"])
        b = f[f["niv_riesgo"].isin(niveles)].sort_values(["num_score_riesgo", "val_contrato"], ascending=False)
        st.markdown(f"**{miles(len(b))} contratos** · {cop(b['val_contrato'].sum())}")
        cols = ["niv_riesgo", "num_score_riesgo", "txt_banderas", "id_contrato", "nom_entidad", "nom_municipio", "cod_modalidad",
                "fec_firma", "val_contrato", "nom_proveedor_juridico", "id_proveedor_seud", "txt_objeto", "url_proceso_secop"]
        vista = b[cols].head(2000).assign(niv_riesgo=lambda x: x["niv_riesgo"].map(NIVEL_ICONO))
        st.dataframe(vista, hide_index=True, width="stretch", height=520,
                     column_config={"niv_riesgo": "Nivel", "num_score_riesgo": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="%.0f"),
                                    "txt_banderas": "Banderas", "id_contrato": "Contrato", "nom_entidad": "Entidad",
                                    "nom_municipio": "Municipio", "cod_modalidad": "Modalidad", "val_contrato": st.column_config.NumberColumn("Valor (COP)", format="%,.0f"),
                                    "fec_firma": st.column_config.DateColumn("Firma"), "nom_proveedor_juridico": "Proveedor (jurídico)",
                                    "id_proveedor_seud": "Seudónimo proveedor", "txt_objeto": "Objeto",
                                    "url_proceso_secop": st.column_config.LinkColumn("SECOP", display_text="abrir")})
        st.download_button("Descargar bandeja (CSV)", b[cols].to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"ORCA_bandeja_{MAN.get('corte')}.csv", mime="text/csv")

# ---------------------------------------------------------------- Gobierno
if "Gobierno y calidad" in T:
    with T["Gobierno y calidad"]:
        st.subheader("Gobierno del dato aplicado a este lote")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Calidad del lote", f"{cal['puntaje_calidad']} %", help="Umbral de publicación: 95 %")
        c2.metric("Quality gate", cal["decision_quality_gate"])
        c3.metric("PII en claro en el mart", MAN["controles_gobierno"]["pii_en_claro_mart"])
        c4.metric("Columnas fuera del estándar de nombres", len(MAN["controles_gobierno"]["columnas_fuera_de_nomenclatura"]))
        if MAN_CUR:
            dim = pd.Series(MAN_CUR["calidad"]["puntaje_por_dimension"]).rename_axis("dimension").reset_index(name="pct")
            fig = px.bar(dim, x="pct", y="dimension", orientation="h", text=dim["pct"].map(lambda v: f"{v:.2f} %"),
                         title="Cumplimiento por dimensión de calidad", range_x=[90, 100.5],
                         labels={"pct": "% de cumplimiento", "dimension": ""})
            fig.add_vline(x=95, line_dash="dot", line_color="#d03b3b", annotation_text="umbral 95 %")
            fig.update_traces(marker_color=AZUL, textposition="outside", cliponaxis=False)
            fig.update_yaxes(title=None, autorange="reversed")
            st.plotly_chart(estilo(fig, 320), width="stretch")
        st.markdown("#### Linaje del lote: fuente → transformación → dataset → dashboard")
        lin = pd.DataFrame([
            {"paso": "1 · Fuente", "artefacto": "API SODA datos.gov.co (jbjy-vk9h, p6dx-8zbt, gdxc-w37w)", "evidencia": MAN_CUR.get("origen", "")},
            {"paso": "2 · raw", "artefacto": "data/raw/DS-0X_*.parquet + manifest", "evidencia": "SHA-256 y filtro SoQL en el manifiesto"},
            {"paso": "3 · curated", "artefacto": "limpieza.py + calidad.py", "evidencia": MAN["entradas"]["curated"]["sha256"][:16] + "…"},
            {"paso": "4 · mart", "artefacto": f"riesgo.py + reglas v{MAN['entradas']['reglas']['version']}",
             "evidencia": MAN["salidas"]["mart_contratos_riesgo"]["sha256"][:16] + "…"},
            {"paso": "5 · dashboard", "artefacto": "dashboard/app.py (lee solo mart)", "evidencia": f"rol actual: {rol}"},
        ])
        st.dataframe(lin, hide_index=True, width="stretch")
        st.markdown("#### Matriz de acceso por capa (Plan de Gobierno §8)")
        acc = pd.DataFrame(gobierno.MATRIZ_ACCESO).T
        st.dataframe(acc, width="stretch")
        with st.expander("Manifiesto completo del mart"):
            st.json(MAN)
