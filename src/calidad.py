"""Reglas de calidad de ORCA: 6 dimensiones sobre SECOP II Contratos (DS-01).

Cada regla devuelve una serie booleana: True cumple, False falla, <NA> no aplica.
El puntaje de una dimensión es el promedio de cumplimiento de sus reglas; el puntaje
del lote es el promedio de las 6 dimensiones. El quality gate publica el lote solo si
el puntaje es >= UMBRAL (95 %). Las reglas son propuestas: las aprueba el Data Steward.
"""
import pandas as pd

UMBRAL = 95.0
VALOR_ATIPICO = 1e11          # $100.000 millones: candidato a error de digitación
VENTANA_OPORTUNIDAD_DIAS = 7  # la fuente debe traer firmas de la última semana
DIMENSIONES = ["Completitud", "Validez", "Exactitud", "Consistencia", "Unicidad", "Oportunidad"]


def _reglas(df: pd.DataFrame, corte: pd.Timestamp):
    """Lista de (dimensión, id, descripción, serie booleana) del lote ya tipado."""
    firma, ini, fin = df["fecha_de_firma"], df["fecha_de_inicio_del_contrato"], df["fecha_de_fin_del_contrato"]
    valor = df["valor_del_contrato"]
    ciudad_ok = df["ciudad"].notna()
    nn = lambda s: s.notna().astype("boolean")
    b = lambda s: s.astype("boolean")
    ultima = firma.max()
    oport = pd.Series([pd.NA] * len(df), index=df.index, dtype="boolean")
    if len(df):
        oport.iloc[0] = bool(pd.notna(ultima) and ultima >= corte - pd.Timedelta(days=VENTANA_OPORTUNIDAD_DIAS))
    return [
        ("Completitud", "C1", "fecha_de_firma presente", nn(firma)),
        ("Completitud", "C2", "valor_del_contrato presente", nn(valor)),
        ("Completitud", "C3", "documento_proveedor presente", nn(df["documento_proveedor"])),
        ("Completitud", "C4", "ciudad definida (no 'No Definido')", nn(df["ciudad"])),
        ("Completitud", "C5", "modalidad_de_contratacion presente", nn(df["modalidad_de_contratacion"])),
        ("Validez", "V1", "valor_del_contrato no negativo", b(valor >= 0)),
        ("Validez", "V2", "fecha_de_firma no es futura", b(firma <= corte).where(firma.notna())),
        ("Validez", "V3", "ciudad reconocida en DIVIPOLA", b(df["cod_municipio"].notna()).where(ciudad_ok)),
        ("Exactitud", "E1", "valor_del_contrato mayor que cero", b(valor > 0)),
        ("Exactitud", "E2", "valor_del_contrato sin atípico (<= $100.000 millones)", b(valor <= VALOR_ATIPICO)),
        ("Consistencia", "K1", "fecha de fin no anterior a la de inicio", b(fin >= ini).where(fin.notna() & ini.notna())),
        ("Consistencia", "K2", "fecha de firma no posterior al fin del contrato", b(firma <= fin).where(firma.notna() & fin.notna())),
        ("Unicidad", "U1", "id_contrato único", b(~df["id_contrato"].duplicated(keep=False))),
        ("Oportunidad", "O1", f"última firma dentro de {VENTANA_OPORTUNIDAD_DIAS} días del corte", oport),
    ]


def medir(df: pd.DataFrame, corte: pd.Timestamp) -> tuple[pd.DataFrame, dict]:
    """Devuelve (tabla de reglas, resumen con puntaje por dimensión y decisión del gate)."""
    filas = []
    for dim, rid, desc, ok in _reglas(df, corte):
        evaluados = int(ok.notna().sum())
        cumplen = int(ok.fillna(False).sum())
        filas.append({"dimension": dim, "regla": rid, "descripcion": desc, "evaluados": evaluados,
                      "cumplen": cumplen, "fallan": evaluados - cumplen,
                      "cumplimiento_pct": round(100 * cumplen / evaluados, 2) if evaluados else None})
    tabla = pd.DataFrame(filas)
    por_dim = {d: round(float(tabla.loc[tabla.dimension == d, "cumplimiento_pct"].mean()), 2) for d in DIMENSIONES}
    puntaje = round(sum(por_dim.values()) / len(por_dim), 2)
    resumen = {"puntaje_por_dimension": por_dim, "puntaje_lote": puntaje, "umbral": UMBRAL,
               "decision": "PUBLICAR" if puntaje >= UMBRAL else "CUARENTENA"}
    return tabla, resumen
