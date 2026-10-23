"""Monitoreo diario de SECOP II (DS-01): frescura y calidad básica.

Solo consulta agregados por la API (no descarga datos ni toca PII).
Imprime una tabla en Markdown y agrega una fila a automatizacion/registro_ejecuciones.csv.

Uso:  python notebooks/monitoreo_fuente.py
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

import requests

URL = "https://www.datos.gov.co/resource/jbjy-vk9h.json"
BASE = "departamento='Antioquia' AND fecha_de_firma >= '2024-01-01'"
REGISTRO = Path(__file__).resolve().parents[1] / "automatizacion" / "registro_ejecuciones.csv"


def consultar(select: str, where: str = BASE) -> dict:
    r = requests.get(URL, params={"$select": select, "$where": where}, timeout=120)
    r.raise_for_status()
    return r.json()[0]


def main() -> None:
    total = int(consultar("count(*) as n")["n"])
    ultima = consultar("max(fecha_de_firma) as f")["f"][:10]
    cero = int(consultar("count(*) as n", f"{BASE} AND valor_del_contrato = 0")["n"])
    sin_ciudad = int(consultar("count(*) as n", f"{BASE} AND ciudad = 'No Definido'")["n"])

    fila = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_contratos": total,
        "ultima_fecha_firma": ultima,
        "pct_valor_cero": round(100 * cero / total, 2),
        "pct_ciudad_no_definida": round(100 * sin_ciudad / total, 2),
        "estado": "OK" if total > 0 else "SIN DATOS",
    }
    nuevo = not REGISTRO.exists()
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fila))
        if nuevo:
            w.writeheader()
        w.writerow(fila)

    print("### Monitoreo de SECOP II (DS-01)\n")
    print("| Indicador | Valor |\n|---|---|")
    for k, v in fila.items():
        print(f"| {k} | {v} |")


if __name__ == "__main__":
    main()
