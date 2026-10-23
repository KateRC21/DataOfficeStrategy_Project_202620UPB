"""Descarga las fuentes de ORCA desde la API SODA de datos.gov.co a la zona raw.

Uso:
    python src/descargar_fuentes.py            # descarga DS-01, DS-02 y DS-03
    python src/descargar_fuentes.py DS-01      # solo una fuente

Salida (no versionada, contiene PII en claro):
    data/raw/<codigo>_<dataset>_<AAAAMMDD>.parquet
    data/raw/<codigo>_<dataset>_<AAAAMMDD>.manifest.json   <- linaje del lote
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.datos.gov.co/resource"
RAIZ = Path(__file__).resolve().parents[1]
RAW = RAIZ / "data" / "raw"
PAGINA = 50_000

FUENTES = {
    "DS-01": {
        "dataset": "jbjy-vk9h",
        "nombre": "secop2_contratos",
        "where": "departamento='Antioquia' AND fecha_de_firma >= '2024-01-01'",
    },
    "DS-02": {
        "dataset": "p6dx-8zbt",
        "nombre": "secop2_procesos",
        "where": "departamento_entidad='Antioquia' AND fecha_de_publicacion_del >= '2024-01-01'",
    },
    "DS-03": {
        "dataset": "gdxc-w37w",
        "nombre": "divipola_municipios",
        "where": None,
    },
}


def obtener_pagina(dataset: str, where: str | None, offset: int, reintentos: int = 5) -> list[dict]:
    params = {"$limit": PAGINA, "$offset": offset, "$order": ":id"}
    if where:
        params["$where"] = where
    for intento in range(1, reintentos + 1):
        try:
            r = requests.get(f"{BASE}/{dataset}.json", params=params, timeout=300)
            r.raise_for_status()
            r.encoding = "utf-8"
            return r.json()
        except requests.RequestException as e:
            if intento == reintentos:
                raise
            espera = 15 * intento
            print(f"    reintento {intento}/{reintentos} en {espera}s ({e.__class__.__name__})", flush=True)
            time.sleep(espera)
    return []


def descargar(codigo: str) -> Path:
    f = FUENTES[codigo]
    inicio = datetime.now(timezone.utc)
    print(f"[{codigo}] {f['dataset']} · {f['where'] or 'completo'}", flush=True)
    filas, offset = [], 0
    while True:
        pagina = obtener_pagina(f["dataset"], f["where"], offset)
        filas.extend(pagina)
        print(f"    {len(filas):>9,} filas", flush=True)
        if len(pagina) < PAGINA:
            break
        offset += PAGINA

    # zona raw: tal como llega (todo texto), sin transformar
    df = pd.DataFrame(filas).astype("string")
    RAW.mkdir(parents=True, exist_ok=True)
    base = f"{codigo}_{f['nombre']}_{inicio:%Y%m%d}"
    ruta = RAW / f"{base}.parquet"
    df.to_parquet(ruta, index=False)

    manifiesto = {
        "codigo": codigo,
        "dataset": f["dataset"],
        "fuente": f"{BASE}/{f['dataset']}.json",
        "filtro_soql": f["where"],
        "orden": ":id",
        "tamano_pagina": PAGINA,
        "inicio_utc": inicio.isoformat(timespec="seconds"),
        "fin_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "filas": len(df),
        "columnas": list(df.columns),
        "archivo": ruta.name,
        "sha256": hashlib.sha256(ruta.read_bytes()).hexdigest(),
        "clasificacion": "Confidencial (contiene PII en claro)" if codigo != "DS-03" else "Público",
    }
    (RAW / f"{base}.manifest.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{codigo}] OK -> {ruta.name} ({len(df):,} filas x {df.shape[1]} col, "
          f"{ruta.stat().st_size / 1e6:.1f} MB)", flush=True)
    return ruta


if __name__ == "__main__":
    for codigo in (sys.argv[1:] or ["DS-03", "DS-01", "DS-02"]):
        descargar(codigo)
