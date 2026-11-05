"""Motor de reglas de riesgo de ORCA: curated (+ DS-02) -> mart.

Calcula 9 banderas rojas por contrato (reglas versionadas en reglas_riesgo.json),
un score de 0 a 100 y un nivel (Alto / Medio / Bajo / Sin señales). Escribe la zona
mart, que es la única que lee el dashboard:

    data/mart/mart_contratos_riesgo.parquet        un registro por contrato (sin PII en claro)
    data/mart/mart_entidades.parquet               una fila por entidad (P1 y priorización)
    data/mart/mart_pares_entidad_proveedor.parquet una fila por par entidad–proveedor (P3)
    data/mart/mart_mensual.parquet                 serie mensual (P2)
    data/mart/mart.manifest.json                   linaje, versión de reglas y controles

Política aplicada: solo se publica un lote cuyo quality gate dijo PUBLICAR (tarea 17 del RACI).
Las columnas del mart siguen el estándar de nomenclatura del Plan de Gobierno (§6.1).

Uso:
    python notebooks/riesgo.py [--curated data/curated] [--procesos "data/raw/DS-02_*.parquet"]
"""
import argparse
import glob
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
REGLAS = Path(__file__).resolve().parent / "reglas_riesgo.json"
COLUMNAS_DS02 = ["id_del_portafolio", "respuestas_al_procedimiento", "proveedores_unicos_con"]  # sin PII
PREFIJOS_VALIDOS = ("id_", "nom_", "cod_", "fec_", "val_", "cant_", "pct_", "ind_", "url_", "txt_", "num_", "niv_")
PII_PROHIBIDA = ("documento_proveedor", "proveedor_adjudicado", "nombre_representante_legal", "nombre_supervisor",
                 "nombre_ordenador_del_gasto", "nombre_ordenador_de_pago", "n_mero_de_cuenta",
                 "identificaci_n_representante_legal", "n_mero_de_documento_supervisor")
COMPETITIVAS = ("licitación", "selección abreviada", "seleccion abreviada", "concurso", "mínima cuantía",
                "con ofertas", "enajenación", "subasta")


def ultimo(patron: str) -> Path:
    rutas = sorted(glob.glob(str(patron)))
    if not rutas:
        raise FileNotFoundError(patron)
    return Path(rutas[-1])


def sha256(ruta: Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()


def cargar_reglas(ruta: Path = REGLAS) -> dict:
    return json.loads(ruta.read_text(encoding="utf-8"))


def url_limpia(s: pd.Series) -> pd.Series:
    return s.str.extract(r"(https?://[^'\"&]+(?:\?noticeUID=[A-Z0-9.]+)?)", expand=False).astype("string")


def competencia_ds02(ruta: Path) -> pd.DataFrame:
    """Número de respuestas por proceso (id_del_portafolio). Solo columnas sin PII."""
    p = pd.read_parquet(ruta, columns=COLUMNAS_DS02)
    for c in COLUMNAS_DS02[1:]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    return (p.dropna(subset=["id_del_portafolio"]).groupby("id_del_portafolio")
             .agg(cant_respuestas_proceso=("respuestas_al_procedimiento", "max"),
                  cant_oferentes_unicos=("proveedores_unicos_con", "max")))


# ---------------------------------------------------------------- banderas

def r2_ventana(df: pd.DataFrame, cfg: dict) -> pd.Series:
    en = pd.Series(False, index=df.index)
    for v in cfg["ventanas"]:
        en |= df["fecha_de_firma"].between(pd.Timestamp(v["desde"]), pd.Timestamp(v["hasta"]) + pd.Timedelta(hours=23, minutes=59))
    return en & df["es_contratacion_directa"].fillna(False)


def r3_pares(df: pd.DataFrame, cfg: dict) -> tuple[pd.Series, pd.DataFrame]:
    con_prov = df[df["proveedor_id"].notna()]
    ent = df.groupby("nit_entidad").agg(ent_contratos=("id_contrato", "size"), ent_valor=("valor_del_contrato", "sum"))
    par = (con_prov.groupby(["nit_entidad", "proveedor_id"])
           .agg(cant_contratos=("id_contrato", "size"), val_total=("valor_del_contrato", "sum"),
                cant_directa=("es_contratacion_directa", "sum"),
                ind_persona_natural=("proveedor_es_persona_natural", "max"))
           .reset_index().join(ent, on="nit_entidad"))
    par["pct_valor_entidad"] = (par["val_total"] / par["ent_valor"].replace(0, np.nan)).fillna(0)
    par["pct_contratos_entidad"] = par["cant_contratos"] / par["ent_contratos"]
    par["ind_concentracion"] = (par["cant_contratos"] >= cfg["min_contratos_par"]) & (
        ((par["pct_valor_entidad"] >= cfg["pct_valor"]) & (par["ent_contratos"] >= cfg["min_contratos_entidad_valor"]))
        | ((par["pct_contratos_entidad"] >= cfg["pct_contratos"]) & (par["ent_contratos"] >= cfg["min_contratos_entidad_conteo"])))
    marcados = par.loc[par["ind_concentracion"], ["nit_entidad", "proveedor_id"]].assign(_f=True)
    flag = df[["nit_entidad", "proveedor_id"]].merge(marcados, how="left", on=["nit_entidad", "proveedor_id"])["_f"]
    return pd.Series(flag.eq(True).to_numpy(), index=df.index), par


def r4_simultaneidad(df: pd.DataFrame, cfg: dict) -> tuple[pd.Series, pd.Series]:
    """Persona natural con contratos vigentes en >= N entidades el mismo mes."""
    pn = df[df["proveedor_es_persona_natural"].fillna(False) & df["proveedor_id"].notna()].copy()
    ini = pn["fecha_de_inicio_del_contrato"].fillna(pn["fecha_de_firma"])
    fin = pn["fecha_de_fin_del_contrato"].where(pn["fecha_de_fin_del_contrato"] >= ini, ini)
    m0 = ini.dt.year * 12 + ini.dt.month
    m1 = np.minimum(fin.dt.year * 12 + fin.dt.month, m0 + cfg["max_meses_por_contrato"] - 1)
    pn = pn.assign(m0=m0, n=(m1 - m0 + 1).clip(lower=1)).dropna(subset=["m0"])
    rep = pn.loc[pn.index.repeat(pn["n"].astype(int)), ["proveedor_id", "nit_entidad", "m0"]]
    rep["mes"] = rep["m0"] + rep.groupby(level=0).cumcount()
    rep["contrato"] = rep.index
    ent_mes = rep.groupby(["proveedor_id", "mes"])["nit_entidad"].nunique().rename("ent_mes")
    rep = rep.join(ent_mes, on=["proveedor_id", "mes"])
    max_ent = rep.groupby("contrato")["ent_mes"].max()
    max_ent = max_ent.reindex(df.index).fillna(0).astype(int)
    return max_ent >= cfg["min_entidades"], max_ent


def r5_atipico(df: pd.DataFrame, cfg: dict) -> tuple[pd.Series, pd.Series]:
    v = df["valor_del_contrato"].astype(float)
    lv = np.log10(v.where(v > 0))
    g = [df["tipo_de_contrato"].fillna("NA"), df["modalidad_de_contratacion"].fillna("NA")]
    q1 = lv.groupby(g).transform(lambda s: s.quantile(0.25))
    q3 = lv.groupby(g).transform(lambda s: s.quantile(0.75))
    n = lv.groupby(g).transform("count")
    limite = q3 + cfg["k_iqr"] * (q3 - q1)
    flag = (lv > limite) & (n >= cfg["min_grupo"])
    return flag.fillna(False), (10 ** limite).where(n >= cfg["min_grupo"])


def calcular_banderas(df: pd.DataFrame, reglas: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = reglas["banderas"]
    modalidad = df["modalidad_de_contratacion"].str.lower().fillna("")
    causal = df["justificacion_modalidad_de"].str.lower().fillna("")
    f = pd.DataFrame(index=df.index)
    f["ind_r1_contratacion_directa"] = df["es_contratacion_directa"].fillna(False)
    f["ind_r2_ventana_atipica"] = r2_ventana(df, b["R2"])
    f["ind_r3_concentracion_par"], pares = r3_pares(df, b["R3"])
    f["ind_r4_simultaneidad_pn"], df["cant_entidades_simultaneas"] = r4_simultaneidad(df, b["R4"])
    f["ind_r5_valor_atipico"], df["val_limite_atipico_grupo"] = r5_atipico(df, b["R5"])
    competitiva = modalidad.apply(lambda m: any(k in m for k in COMPETITIVAS))
    f["ind_r6_unico_oferente"] = competitiva & df["cant_respuestas_proceso"].eq(1).fillna(False)
    f["ind_r7_urgencia_manifiesta"] = causal.str.contains("urgencia")
    plazo = (df["fecha_de_fin_del_contrato"] - df["fecha_de_inicio_del_contrato"]).dt.days
    dias = df["dias_adicionados"].astype(float).fillna(0)
    f["ind_r8_prorroga_desproporcionada"] = ((dias >= 60) & (dias >= 0.5 * plazo)).fillna(False)
    cero_sin_causal = df["flag_valor_cero"].fillna(False) & ~causal.str.contains("valor cero")
    f["ind_r9_inconsistencia_dato"] = cero_sin_causal | df["flag_fechas_inconsistentes"].fillna(False)
    return f.astype(bool), pares


def puntuar(f: pd.DataFrame, reglas: dict) -> pd.DataFrame:
    pesos = {c: reglas["banderas"][c.split("_")[1].upper()]["peso"] for c in f.columns}
    total = sum(r["peso"] for r in reglas["banderas"].values())
    score = sum(f[c].astype(int) * p for c, p in pesos.items()) * 100 / total
    alto, medio = reglas["niveles"]["alto"], reglas["niveles"]["medio"]
    nivel = np.select([score >= alto, score >= medio, score > 0], ["Alto", "Medio", "Bajo"], "Sin señales")
    codigos = f.apply(lambda fila: ",".join(c.split("_")[1].upper() for c, v in fila.items() if v), axis=1)
    return pd.DataFrame({"num_score_riesgo": score.round(1), "niv_riesgo": nivel,
                         "cant_banderas": f.sum(axis=1), "txt_banderas": codigos}, index=f.index)


# ---------------------------------------------------------------- tablas del mart

def tabla_contratos(df: pd.DataFrame, f: pd.DataFrame, s: pd.DataFrame) -> pd.DataFrame:
    pn = df["proveedor_es_persona_natural"].fillna(True)
    out = pd.DataFrame({
        "id_contrato": df["id_contrato"], "id_proceso_compra": df["proceso_de_compra"],
        "nom_entidad": df["nombre_entidad"], "id_nit_entidad": df["nit_entidad"],
        "cod_orden_entidad": df["orden"], "nom_municipio": df["municipio"].fillna("Sin municipio"),
        "cod_municipio": df["cod_municipio"], "cod_modalidad": df["modalidad_de_contratacion"],
        "cod_tipo_contrato": df["tipo_de_contrato"], "cod_causal_modalidad": df["justificacion_modalidad_de"],
        "cod_estado_contrato": df["estado_contrato"], "fec_firma": df["fecha_de_firma"],
        "fec_inicio": df["fecha_de_inicio_del_contrato"], "fec_fin": df["fecha_de_fin_del_contrato"],
        "val_contrato": df["valor_del_contrato"].astype(float), "cant_dias_adicionados": df["dias_adicionados"],
        "ind_persona_natural": pn,
        "id_proveedor_seud": df["proveedor_id"],                          # HMAC-SHA256, nunca la cédula
        "id_nit_proveedor": df["proveedor_nit"].where(~pn),               # solo personas jurídicas (público)
        "nom_proveedor_juridico": df["proveedor_nombre"].where(~pn),
        "cant_respuestas_proceso": df["cant_respuestas_proceso"],
        "cant_entidades_simultaneas": df["cant_entidades_simultaneas"],
        "val_limite_atipico_grupo": df["val_limite_atipico_grupo"],
        "ind_sujeto_vigilancia": df["orden"].eq("Territorial"),
        "txt_objeto": df["objeto_del_contrato"].str.slice(0, 300),
        "url_proceso_secop": url_limpia(df["urlproceso"]),
    })
    return pd.concat([out, f, s], axis=1)


def tabla_entidades(m: pd.DataFrame) -> pd.DataFrame:
    anio = m["fec_firma"].dt.year
    base = m.assign(hist=anio < 2026, act=anio >= 2026, alto=m["niv_riesgo"].eq("Alto"),
                    val_alto=m["val_contrato"].where(m["niv_riesgo"].eq("Alto"), 0))
    g = base.groupby(["id_nit_entidad", "nom_entidad", "cod_orden_entidad", "nom_municipio"], dropna=False)
    e = g.agg(cant_contratos=("id_contrato", "size"), val_total=("val_contrato", "sum"),
              pct_directa=("ind_r1_contratacion_directa", "mean"),
              cant_alto=("alto", "sum"), val_riesgo_alto=("val_alto", "sum"),
              num_score_medio=("num_score_riesgo", "mean"),
              cant_proveedores=("id_proveedor_seud", "nunique")).reset_index()
    def pct_dir(mask):
        sub = base[mask]
        return sub.groupby("id_nit_entidad").agg(n=("id_contrato", "size"), d=("ind_r1_contratacion_directa", "mean"))
    h, a = pct_dir(base["hist"]), pct_dir(base["act"])
    e = e.join(h.rename(columns={"n": "cant_contratos_2024_2025", "d": "pct_directa_2024_2025"}), on="id_nit_entidad")
    e = e.join(a.rename(columns={"n": "cant_contratos_2026", "d": "pct_directa_2026"}), on="id_nit_entidad")
    e["num_delta_directa_pp"] = 100 * (e["pct_directa_2026"] - e["pct_directa_2024_2025"])
    # P1: más directa que su propia historia, con volumen suficiente para que la diferencia signifique algo
    e["ind_p1_directa_sobre_historia"] = ((e["num_delta_directa_pp"] >= 10) & (e["cant_contratos_2026"] >= 30)
                                          & (e["cant_contratos_2024_2025"] >= 30)).fillna(False)
    e["pct_alto"] = e["cant_alto"] / e["cant_contratos"]
    # Índice de priorización: valor expuesto en riesgo alto (escala log) + intensidad del riesgo + señal P1
    e["num_indice_prioridad"] = (
        40 * np.log10(1 + e["val_riesgo_alto"]) / max(np.log10(1 + e["val_riesgo_alto"].max()), 1)
        + 40 * e["num_score_medio"] / max(e["num_score_medio"].max(), 1)
        + 20 * e["ind_p1_directa_sobre_historia"].astype(int)).round(1)
    e["ind_sujeto_vigilancia"] = e["cod_orden_entidad"].eq("Territorial")
    e["cant_ranking"] = e["num_indice_prioridad"].rank(ascending=False, method="first").astype(int)
    return e.sort_values("cant_ranking")


def tabla_pares(pares: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    nombres = m.drop_duplicates("id_nit_entidad").set_index("id_nit_entidad")["nom_entidad"]
    prov = (m.dropna(subset=["nom_proveedor_juridico"]).drop_duplicates("id_proveedor_seud")
              .set_index("id_proveedor_seud")["nom_proveedor_juridico"])
    p = pares.rename(columns={"nit_entidad": "id_nit_entidad", "proveedor_id": "id_proveedor_seud",
                              "ent_contratos": "cant_contratos_entidad", "ent_valor": "val_total_entidad"})
    p["nom_entidad"] = p["id_nit_entidad"].map(nombres)
    # Persona natural: solo seudónimo. Persona jurídica: nombre público.
    p["nom_proveedor"] = p["id_proveedor_seud"].map(prov).fillna("Persona natural · " + p["id_proveedor_seud"].str[:8])
    p["ind_persona_natural"] = p["ind_persona_natural"].fillna(True).astype(bool)
    p = p.rename(columns={"ind_concentracion": "ind_r3_concentracion_par"})
    p = p[(p["cant_contratos"] >= 3) | p["ind_r3_concentracion_par"]]
    return p.sort_values("val_total", ascending=False).reset_index(drop=True)


def tabla_mensual(m: pd.DataFrame) -> pd.DataFrame:
    t = m.dropna(subset=["fec_firma"]).assign(fec_mes=lambda x: x["fec_firma"].dt.to_period("M").dt.to_timestamp())
    g = t.groupby("fec_mes").agg(cant_contratos=("id_contrato", "size"), val_total=("val_contrato", "sum"),
                                  pct_directa=("ind_r1_contratacion_directa", "mean"),
                                  cant_alto=("niv_riesgo", lambda s: int((s == "Alto").sum())),
                                  cant_territorial=("ind_sujeto_vigilancia", "sum")).reset_index()
    return g


# ---------------------------------------------------------------- controles de gobierno

def controles(m: pd.DataFrame) -> dict:
    malas = [c for c in m.columns if not c.startswith(PREFIJOS_VALIDOS)]
    pii_columnas = [c for c in m.columns if c in PII_PROHIBIDA]
    pn_expuesta = int((m["ind_persona_natural"] & (m["id_nit_proveedor"].notna() | m["nom_proveedor_juridico"].notna())).sum())
    seud_ok = bool(m["id_proveedor_seud"].dropna().str.fullmatch(r"[0-9a-f]{16}").all())
    return {"columnas_fuera_de_nomenclatura": malas, "columnas_pii_prohibidas": pii_columnas,
            "personas_naturales_con_documento_o_nombre": pn_expuesta, "seudonimos_validos": seud_ok,
            "pii_en_claro_mart": len(pii_columnas) + pn_expuesta + (0 if seud_ok else 1)}


def procesar(curated: str, procesos: str, salida: str, reglas_ruta: Path = REGLAS) -> dict:
    inicio = datetime.now(timezone.utc)
    reglas = cargar_reglas(reglas_ruta)
    cur_dir = Path(curated)
    ruta_cur = cur_dir / "DS-01_contratos_curated.parquet"
    man_cur = json.loads((cur_dir / "DS-01_contratos_curated.manifest.json").read_text(encoding="utf-8"))
    decision = man_cur["calidad"]["decision"]
    if decision != "PUBLICAR":                                # política: solo lotes que pasan el gate
        raise SystemExit(f"Lote en {decision}: el mart no se actualiza (puntaje {man_cur['calidad']['puntaje_lote']}).")

    df = pd.read_parquet(ruta_cur)
    ruta_p = ultimo(procesos)
    comp = competencia_ds02(ruta_p)
    df = df.join(comp, on="proceso_de_compra")
    cruce = float(df["cant_respuestas_proceso"].notna().mean())

    f, pares = calcular_banderas(df, reglas)
    s = puntuar(f, reglas)
    mart_c = tabla_contratos(df, f, s)
    mart_e = tabla_entidades(mart_c)
    mart_p = tabla_pares(pares, mart_c)
    mart_m = tabla_mensual(mart_c)
    ctrl = controles(mart_c)
    if ctrl["pii_en_claro_mart"]:
        raise SystemExit(f"Control de PII falló: {ctrl}. El mart no se publica.")

    out = Path(salida)
    out.mkdir(parents=True, exist_ok=True)
    archivos = {"mart_contratos_riesgo": mart_c, "mart_entidades": mart_e,
                "mart_pares_entidad_proveedor": mart_p, "mart_mensual": mart_m}
    salidas = {}
    for nombre, tabla in archivos.items():
        ruta = out / f"{nombre}.parquet"
        tabla.to_parquet(ruta, index=False)
        salidas[nombre] = {"archivo": ruta.name, "filas": len(tabla), "columnas": tabla.shape[1], "sha256": sha256(ruta)}

    banderas = {c: int(f[c].sum()) for c in f.columns}
    niveles = mart_c["niv_riesgo"].value_counts().to_dict()
    manifiesto = {
        "capa": "mart", "clasificacion": "Confidencial · reservado al control fiscal (alertas no son hallazgos)",
        "inicio_utc": inicio.isoformat(timespec="seconds"), "fin_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corte": man_cur.get("corte"),
        "entradas": {"curated": {"archivo": str(ruta_cur.name), "sha256": sha256(ruta_cur),
                                 "sha256_declarado_en_curated": man_cur.get("sha256_curated"),
                                 "origen_raw": man_cur.get("origen"), "decision_quality_gate": decision,
                                 "puntaje_calidad": man_cur["calidad"]["puntaje_lote"]},
                     "procesos_DS-02": {"archivo": ruta_p.name, "sha256": sha256(ruta_p), "columnas_usadas": COLUMNAS_DS02,
                                        "pct_contratos_con_proceso_en_DS02": round(100 * cruce, 2)},
                     "reglas": {"archivo": reglas_ruta.name, "version": reglas["version"], "sha256": sha256(reglas_ruta)}},
        "salidas": salidas, "banderas": banderas, "niveles": niveles,
        "controles_gobierno": ctrl,
    }
    (out / "mart.manifest.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return manifiesto


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--curated", default=str(RAIZ / "data" / "curated"))
    ap.add_argument("--procesos", default=str(RAIZ / "data" / "raw" / "DS-02_*.parquet"))
    ap.add_argument("--salida", default=str(RAIZ / "data" / "mart"))
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    m = procesar(a.curated, a.procesos, a.salida)
    print(json.dumps({k: m[k] for k in ("corte", "banderas", "niveles", "controles_gobierno")}, ensure_ascii=False, indent=2))
    print("DS-02 cruce:", m["entradas"]["procesos_DS-02"]["pct_contratos_con_proceso_en_DS02"], "%")
