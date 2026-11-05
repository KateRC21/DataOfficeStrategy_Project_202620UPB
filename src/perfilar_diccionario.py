"""Perfila las columnas de DS-01 (SECOP II Contratos) que documenta el diccionario de datos.

Consulta la API SODA de datos.gov.co con agregaciones (no descarga el dataset) sobre el
alcance de ORCA: departamento = 'Antioquia' y fecha_de_firma >= 2024-01-01. Para cada
columna calcula vacíos, nulos disfrazados, valores distintos, mínimo/máximo y los valores
más frecuentes. El resultado es la evidencia del diccionario (Sesión 2 · Gobernanza).

Uso:  python src/perfilar_diccionario.py
Salida: documentacion/plan_gobierno/perfil_ds01.json
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
ALCANCE = "departamento = 'Antioquia' AND fecha_de_firma >= '2024-01-01T00:00:00'"
SALIDA = Path(__file__).resolve().parents[1] / "documentacion" / "plan_gobierno" / "perfil_ds01.json"

# columna -> tipo de perfil ("cat" = categórica con frecuencias, "id" = identificador único, "num", "fecha",
# "texto" = texto libre o código que se repite, "url" = tipo URL de Socrata, solo admite conteo de vacíos)
COLUMNAS = {
    "id_contrato": "id",
    "proceso_de_compra": "id",
    "nombre_entidad": "texto",
    "nit_entidad": "num",
    "ciudad": "cat",
    "orden": "cat",
    "estado_contrato": "cat",
    "tipo_de_contrato": "cat",
    "modalidad_de_contratacion": "cat",
    "justificacion_modalidad_de": "cat",
    "fecha_de_firma": "fecha",
    "fecha_de_inicio_del_contrato": "fecha",
    "fecha_de_fin_del_contrato": "fecha",
    "tipodocproveedor": "cat",
    "documento_proveedor": "texto",
    "proveedor_adjudicado": "texto",
    "es_pyme": "cat",
    "valor_del_contrato": "num",
    "dias_adicionados": "num",
    "urlproceso": "url",
}
NULOS_DISFRAZADOS = ("No Definido", "No definido", "Sin Descripcion", "Sin descripcion", "NO DEFINIDO", "")


def consulta(params, reintentos=5):
    for intento in range(reintentos):
        try:
            r = requests.get(API, params=params, timeout=120)
            r.raise_for_status()
            return r.json()
        except requests.RequestException:
            if intento == reintentos - 1:
                raise
            time.sleep(2 ** intento)


def contar(where_extra=None):
    where = ALCANCE if not where_extra else f"{ALCANCE} AND ({where_extra})"
    return int(consulta({"$select": "count(*) AS n", "$where": where})[0]["n"])


def perfilar(col, tipo, total):
    p = {"tipo_perfil": tipo, "vacios": contar(f"{col} IS NULL")}
    texto = tipo in ("cat", "id", "texto")
    if texto:
        lista = ", ".join(f"'{v}'" for v in NULOS_DISFRAZADOS)
        p["nulos_disfrazados"] = contar(f"{col} IN ({lista})")
    if tipo not in ("fecha", "url"):
        p["distintos"] = int(consulta({"$select": f"count(distinct {col}) AS n", "$where": ALCANCE})[0]["n"])
    if tipo in ("num", "fecha"):
        r = consulta({"$select": f"min({col}) AS mn, max({col}) AS mx", "$where": ALCANCE})[0]
        p["min"], p["max"] = r.get("mn"), r.get("mx")
    if tipo == "num":
        p["ceros"] = contar(f"{col} = 0")
        p["negativos"] = contar(f"{col} < 0")
    if tipo == "fecha" and col != "fecha_de_firma":
        p["anteriores_a_2000"] = contar(f"{col} < '2000-01-01T00:00:00'")
    if tipo == "cat":
        filas = consulta({"$select": f"{col}, count(*) AS n", "$where": ALCANCE, "$group": col,
                          "$order": "n DESC", "$limit": 25})
        p["frecuencias"] = {str(f.get(col)): int(f["n"]) for f in filas}
    if tipo == "id":
        repetidos = consulta({"$select": f"{col}, count(*) AS n", "$where": ALCANCE, "$group": col,
                              "$having": "n > 1", "$limit": 50000})
        p["valores_repetidos"] = len(repetidos)
    p["pct_vacios"] = round(100 * p["vacios"] / total, 2)
    if texto:
        p["pct_nulos_disfrazados"] = round(100 * p["nulos_disfrazados"] / total, 2)
    return p


def main():
    total = contar()
    perfil = {
        "dataset": "jbjy-vk9h",
        "alcance": ALCANCE,
        "consultado": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_registros": total,
        "reglas": {},
        "columnas": {},
    }
    reglas = {
        "fin_antes_de_inicio": "fecha_de_fin_del_contrato < fecha_de_inicio_del_contrato",
        "inicio_antes_de_firma": "fecha_de_inicio_del_contrato < fecha_de_firma",
        "valor_mayor_100_mil_millones": "valor_del_contrato > 100000000000",
        "nit_con_menos_de_9_digitos": "tipodocproveedor = 'NIT' AND length(documento_proveedor) < 9",
        "firma_futura": "fecha_de_firma > '2026-12-31T00:00:00'",
    }
    for nombre, where in reglas.items():
        try:
            perfil["reglas"][nombre] = contar(where)
        except requests.RequestException as e:
            perfil["reglas"][nombre] = f"error: {e}"
    for col, tipo in COLUMNAS.items():
        print(f"  perfilando {col} …", flush=True)
        try:
            perfil["columnas"][col] = perfilar(col, tipo, total)
        except requests.RequestException as e:
            perfil["columnas"][col] = {"error": str(e)}
    SALIDA.write_text(json.dumps(perfil, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK -> {SALIDA} ({total} registros)")


if __name__ == "__main__":
    main()
