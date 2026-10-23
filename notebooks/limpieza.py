"""Pipeline raw -> curated de ORCA para SECOP II Contratos (DS-01).

Pasos: leer -> nulos disfrazados -> tipado -> normalización (entidad, municipio)
-> medición de calidad -> banderas -> seudonimización -> verificación de PII -> escritura.

Uso:
    python src/limpieza.py --contratos data/raw/DS-01_*.parquet --divipola data/raw/DS-03_*.parquet

La sal del seudónimo se lee de la variable de entorno ORCA_SALT (no se versiona).
Sin ella se usa una sal de desarrollo y el manifiesto lo deja registrado.
"""
import argparse
import glob
import hashlib
import hmac
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calidad  # noqa: E402

NULOS = {"", "no definido", "no definida", "sin descripcion", "sin descripción", "no aplica", "n/a", "na", "null"}
ALIAS_MUNICIPIO = {"DON MATIAS": "DONMATIAS", "SANTAFE DE ANTIOQUIA": "SANTA FE DE ANTIOQUIA",
                   "SAN VICENTE": "SAN VICENTE FERRER",
                   "SAN ANDRES": "SAN ANDRES DE CUERQUIA"}   # "SAN PEDRO" es ambiguo: no se asigna
PREFIJOS_NUMERICOS = ("valor_", "saldo_", "presupuesto_general", "sistema_general", "recursos_", "dias_adicionados")
BOOLEANAS = ["es_grupo", "es_pyme", "habilita_pago_adelantado", "liquidaci_n", "obligaci_n_ambiental",
             "obligaciones_postconsumo", "reversion", "espostconflicto", "el_contrato_puede_ser_prorrogado"]
DOCUMENTOS = {"proveedor_id": "documento_proveedor", "representante_legal_id": "identificaci_n_representante_legal",
              "supervisor_id": "n_mero_de_documento_supervisor",
              "ordenador_gasto_id": "n_mero_de_documento_ordenador_del_gasto",
              "ordenador_pago_id": "n_mero_de_documento_ordenador_de_pago"}
NOMBRES_PERSONA = ["nombre_representante_legal", "nombre_supervisor", "nombre_ordenador_del_gasto",
                   "nombre_ordenador_de_pago"]
ELIMINAR = (list(DOCUMENTOS.values()) + NOMBRES_PERSONA + [
    "proveedor_adjudicado", "tipodocproveedor", "codigo_proveedor",           # se resumen en proveedor_*
    "nombre_del_banco", "tipo_de_cuenta", "n_mero_de_cuenta",                 # sin finalidad legítima
    "nacionalidad_representante_legal", "domicilio_representante_legal",
    "tipo_de_identificaci_n_representante_legal", "g_nero_representante_legal",
    "tipo_de_documento_supervisor", "tipo_de_documento_ordenador_del_gasto",
    "tipo_de_documento_ordenador_de_pago", "direcci_n_de_ejecuci_n_del_contrato"])
PROTEGIDAS = {"id_contrato", "nit_entidad", "fecha_de_firma", "valor_del_contrato", "modalidad_de_contratacion"}
UMBRAL_COLUMNA_VACIA = 0.99
REQUERIDAS = (list(DOCUMENTOS.values()) + NOMBRES_PERSONA + [
    "tipodocproveedor", "proveedor_adjudicado", "nit_entidad", "nombre_entidad", "ciudad", "id_contrato",
    "estado_contrato", "modalidad_de_contratacion", "fecha_de_firma", "fecha_de_inicio_del_contrato",
    "fecha_de_fin_del_contrato", "valor_del_contrato"])

# Identificadores que ya fueron pseudonimizados mediante HMAC-SHA256.
COLUMNAS_SEUDONIMIZADAS = {
    "proveedor_id", "representante_legal_id", "supervisor_id",
    "ordenador_gasto_id", "ordenador_pago_id",
}

# Campos públicos que no constituyen PII por sí mismos.
COLUMNAS_PUBLICAS_NO_PII = {
    "nombre_entidad", "nit_entidad", "ciudad", "municipio",
    "cod_municipio", "departamento", "localizaci_n", "codigo_entidad",
}

# Campos donde una coincidencia exacta con el conjunto sensible sí es relevante.
CAMPOS_A_VERIFICAR_PII = {
    "proveedor_nombre", "referencia_del_contrato", "objeto_del_contrato",
    "descripcion_del_proceso", "justificacion_modalidad_de", "condiciones_de_entrega",
}


def leer(ruta: str) -> pd.DataFrame:
    ruta = sorted(glob.glob(ruta))[-1] if "*" in ruta else ruta
    if str(ruta).endswith(".parquet"):
        return pd.read_parquet(ruta).astype("string")
    return pd.read_csv(ruta, dtype="string", keep_default_na=False)


def sin_tildes(s: pd.Series) -> pd.Series:
    f = lambda v: re.sub(r"\s+", " ", "".join(c for c in unicodedata.normalize("NFKD", v) if not unicodedata.combining(c))).upper().strip() if isinstance(v, str) else v
    return s.map(f).astype("string")


def a_nulos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.apply(lambda c: c.str.strip())
    return df.apply(lambda c: c.mask(c.str.lower().isin(NULOS)))


def tipar(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if c.startswith("fecha_") or c == "ultima_actualizacion":
            df[c] = pd.to_datetime(df[c], errors="coerce", utc=True, format="ISO8601").dt.tz_localize(None)
        elif c.startswith(PREFIJOS_NUMERICOS):
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Float64")
    for c in BOOLEANAS:
        if c in df:
            m = df[c].str.lower().map({"si": True, "sí": True, "no": False})
            df[c] = m.astype("boolean")
    df["estado_contrato"] = df["estado_contrato"].str.capitalize()
    return df


def normalizar_entidad(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    limpio = df["nombre_entidad"].str.replace(r"[*/]+\s*$", "", regex=True).str.replace(r"\s+", " ", regex=True).str.strip()
    tmp = pd.DataFrame({"nit": df["nit_entidad"], "n": limpio}).dropna()
    canon = tmp.groupby("nit")["n"].agg(lambda g: max(g.value_counts()[lambda v: v == v.max()].index, key=len))
    nuevo = df["nit_entidad"].map(canon).fillna(limpio)
    unificados = int((nuevo != df["nombre_entidad"]).sum())
    df["nombre_entidad"] = nuevo
    return df, unificados


def asignar_municipio(df: pd.DataFrame, divipola: pd.DataFrame) -> pd.DataFrame:
    dv = divipola[divipola["cod_dpto"] == "05"].copy()
    dv["k"] = sin_tildes(dv["nom_mpio"])
    cod, nom = dv.set_index("k")["cod_mpio"], dv.set_index("k")["nom_mpio"]
    k = sin_tildes(df["ciudad"]).replace(ALIAS_MUNICIPIO)
    df["cod_municipio"], df["municipio"] = k.map(cod), k.map(nom)
    return df


def seudonimo(serie: pd.Series, sal: bytes) -> pd.Series:
    def h(v):
        if not isinstance(v, str):
            return pd.NA
        v = re.sub(r"[^A-Z0-9]", "", v.upper())
        return hmac.new(sal, v.encode(), hashlib.sha256).hexdigest()[:16] if v else pd.NA
    return serie.map(h).astype("string")


def seudonimizar(df: pd.DataFrame, sal: bytes) -> pd.DataFrame:
    tipo = df["tipodocproveedor"].str.upper()
    nit = tipo.eq("NIT").fillna(False)
    out = df.copy()
    out["proveedor_es_persona_natural"] = (~nit).astype("boolean")
    out["proveedor_nit"] = df["documento_proveedor"].where(nit)
    out["proveedor_nombre"] = df["proveedor_adjudicado"].where(nit)
    for nuevo, col in DOCUMENTOS.items():
        out[nuevo] = seudonimo(df[col], sal)
    return out


def conjunto_sensible(original: pd.DataFrame) -> set:
    """Documentos y nombres de personas del lote. NIT y nombres de organizaciones no cuentan:
    son públicos y a veces aparecen en campos de persona por errores de captura de la fuente."""
    nit = original["tipodocproveedor"].str.upper().eq("NIT").fillna(False)
    sens = set()
    for col in list(DOCUMENTOS.values()) + NOMBRES_PERSONA:
        s = original[col] if col != "documento_proveedor" else original[col].where(~nit)
        sens |= set(s.dropna().astype(str)[lambda x: x.str.len() >= 5])
    sens |= set(original["proveedor_adjudicado"].where(~nit).dropna().astype(str))
    publico = (set(original["nit_entidad"].dropna().astype(str)) | set(original["nombre_entidad"].dropna().astype(str))
               | set(original["documento_proveedor"].where(nit).dropna().astype(str))
               | set(original["proveedor_adjudicado"].where(nit).dropna().astype(str)))
    return sens - publico


TEXTO_LIBRE = ["objeto_del_contrato", "descripcion_del_proceso", "justificacion_modalidad_de", "condiciones_de_entrega"]


def enmascarar_texto(curado: pd.DataFrame, sens: set) -> int:
    """Reemplaza por [DOC] los documentos sensibles encontrados en texto libre."""
    # Solo necesitamos documentos numéricos. Preparar este conjunto una vez
    # evita recalcular/ordenar valores sensibles por cada celda.
    documentos_sensibles = {str(v) for v in sens if str(v).isdigit() and len(str(v)) >= 5}
    if not documentos_sensibles:
        return 0

    cambios = 0
    patron = re.compile(r"\d{5,}")
    for c in (c for c in TEXTO_LIBRE if c in curado):
        original = curado[c]
        def f(v):
            if not isinstance(v, str):
                return v
            return patron.sub(lambda m: "[DOC]" if m.group(0) in documentos_sensibles else m.group(0), v)
        nuevo = original.map(f).astype("string")
        cambios += int((nuevo.fillna("") != original.fillna("")).sum())
        curado[c] = nuevo
    return cambios


def pii_en_claro(curado: pd.DataFrame, sens: set) -> int:
    """Cuenta posibles coincidencias de PII solo en columnas relevantes.

    No cuenta como PII: campos públicos de entidad/territorio ni
    identificadores que ya fueron pseudonimizados mediante HMAC-SHA256.
    """
    columnas = [
        c for c in CAMPOS_A_VERIFICAR_PII
        if c in curado
        and c not in COLUMNAS_PUBLICAS_NO_PII
        and c not in COLUMNAS_SEUDONIMIZADAS
    ]
    return int(sum(curado[c].isin(sens).sum() for c in columnas))


def procesar(contratos: str, divipola: str, salida: str, reporte: str, corte: str | None = None) -> dict:
    inicio = datetime.now(timezone.utc)
    corte_ts = pd.Timestamp(corte) if corte else pd.Timestamp.now().normalize()
    sal_txt = os.environ.get("ORCA_SALT")
    sal = (sal_txt or "orca-desarrollo-NO-USAR-EN-PRODUCCION").encode()
    crudo = leer(contratos)
    for col in REQUERIDAS:                      # la API omite columnas que vienen vacías en todo el lote
        if col not in crudo:
            crudo[col] = pd.NA
    df = tipar(a_nulos(crudo))
    df, unificados = normalizar_entidad(df)
    df = asignar_municipio(df, a_nulos(leer(divipola)))

    tabla, resumen = calidad.medir(df, corte_ts)          # se mide antes de corregir nada
    duplicados = int(df["id_contrato"].duplicated().sum())
    df = df.drop_duplicates("id_contrato", keep="last")

    df["es_contratacion_directa"] = df["modalidad_de_contratacion"].str.lower().str.startswith("contratación directa").astype("boolean")
    df["flag_valor_cero"] = (df["valor_del_contrato"] == 0).astype("boolean")
    df["flag_valor_atipico"] = (df["valor_del_contrato"] > calidad.VALOR_ATIPICO).astype("boolean")
    df["flag_fechas_inconsistentes"] = (df["fecha_de_fin_del_contrato"] < df["fecha_de_inicio_del_contrato"]).astype("boolean")
    df["flag_sin_fecha_firma"] = df["fecha_de_firma"].isna()

    cur = seudonimizar(df, sal)
    vacias = [c for c in cur.columns if c not in PROTEGIDAS and cur[c].isna().mean() >= UMBRAL_COLUMNA_VACIA
              and c not in ELIMINAR]
    cur = cur.drop(columns=[c for c in ELIMINAR if c in cur] + vacias)
    sens = conjunto_sensible(df)
    textos_enmascarados = enmascarar_texto(cur, sens)
    pii = pii_en_claro(cur, sens)

    salida, reporte = Path(salida), Path(reporte)
    salida.mkdir(parents=True, exist_ok=True)
    reporte.mkdir(parents=True, exist_ok=True)
    ruta = salida / "DS-01_contratos_curated.parquet"
    cur.to_parquet(ruta, index=False)
    tabla.to_csv(reporte / "reporte_calidad_DS-01.csv", index=False, encoding="utf-8")
    manifiesto = {
        "capa": "curated", "origen": str(contratos), "origen_filas": len(crudo), "filas_curated": len(cur),
        "columnas_origen": crudo.shape[1], "columnas_curated": cur.shape[1],
        "inicio_utc": inicio.isoformat(timespec="seconds"), "fin_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "corte": str(corte_ts.date()), "calidad": resumen, "duplicados_eliminados": duplicados,
        "nombres_de_entidad_unificados": unificados, "columnas_eliminadas_pii_o_sin_finalidad": [c for c in ELIMINAR if c in crudo],
        "columnas_eliminadas_por_vacias": vacias, "celdas_de_texto_libre_enmascaradas": textos_enmascarados, "pii_en_claro_en_curated": pii,
        "sal": "ORCA_SALT (entorno)" if sal_txt else "desarrollo (no usar en producción)",
        "sha256_curated": hashlib.sha256(ruta.read_bytes()).hexdigest(),
        "clasificacion": "Interno (PII seudonimizada con HMAC-SHA256)"}
    (salida / "DS-01_contratos_curated.manifest.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifiesto


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contratos", required=True)
    ap.add_argument("--divipola", required=True)
    ap.add_argument("--salida", default="data/curated")
    ap.add_argument("--reporte", default="documentacion/calidad")
    ap.add_argument("--corte", default=None, help="AAAA-MM-DD; por defecto hoy")
    a = ap.parse_args()
    m = procesar(a.contratos, a.divipola, a.salida, a.reporte, a.corte)
    print(json.dumps({k: m[k] for k in ("origen_filas", "filas_curated", "columnas_origen", "columnas_curated",
          "duplicados_eliminados", "nombres_de_entidad_unificados", "celdas_de_texto_libre_enmascaradas", "pii_en_claro_en_curated", "calidad")}, ensure_ascii=False, indent=2))
