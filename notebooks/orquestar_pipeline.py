"""Orquestador de ORCA: ejecuta el proceso TO-BE completo sin intervención humana.

    1. Ingesta     descargar_fuentes.py    API SODA -> data/raw (+ manifiesto de linaje)
    2. Curated     limpieza.py + calidad.py raw -> curated, quality gate (6 dimensiones)
    3. Mart        riesgo.py               curated + DS-02 -> mart (9 banderas, score) si el gate dijo PUBLICAR
    4. Alertas     notificar_alertas.py    bandeja + correo de riesgo alto
    5. Retención   gobierno.py             purga lotes raw vencidos (solo con --aplicar-retencion)

Cada corrida agrega una fila a automatizacion/registro_pipeline.csv (evidencia de la automatización).
La programan el Programador de tareas de Windows (automatizacion/programar_tarea_windows.ps1)
o GitHub Actions. Si un paso falla, la corrida queda registrada con el error y sale con código 1.

Uso:
    python notebooks/orquestar_pipeline.py                 # corrida completa (descarga incluida)
    python notebooks/orquestar_pipeline.py --sin-descarga  # reutiliza el último lote raw
"""
import argparse
import csv
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
REGISTRO = RAIZ / "automatizacion" / "registro_pipeline.csv"
CAMPOS = ["inicio_utc", "duracion_s", "lote_ds01", "filas_raw", "filas_curated", "calidad_pct", "decision_gate",
          "pii_en_claro_curated", "pii_en_claro_mart", "alertas_alto", "banderas_reglas_version", "purgados", "estado", "detalle"]


def registrar(fila: dict) -> None:
    nuevo = not REGISTRO.exists()
    REGISTRO.parent.mkdir(parents=True, exist_ok=True)
    with REGISTRO.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()
        w.writerow({k: fila.get(k, "") for k in CAMPOS})


def main(sin_descarga: bool, aplicar_retencion: bool, corte: str | None) -> int:
    import descargar_fuentes, gobierno, limpieza, notificar_alertas, riesgo
    t0, fila = time.time(), {"inicio_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    try:
        if not sin_descarga:
            print("[1/5] Ingesta desde la API", flush=True)
            for codigo in ("DS-03", "DS-01", "DS-02"):
                descargar_fuentes.descargar(codigo)
        raw = RAIZ / "data" / "raw"
        ds01 = riesgo.ultimo(raw / "DS-01_*.parquet")
        fila["lote_ds01"] = ds01.name
        corte = corte or f"{ds01.stem[-8:-4]}-{ds01.stem[-4:-2]}-{ds01.stem[-2:]}"

        print(f"[2/5] raw -> curated ({ds01.name}, corte {corte})", flush=True)
        m = limpieza.procesar(str(ds01), str(riesgo.ultimo(raw / "DS-03_*.parquet")),
                              str(RAIZ / "data" / "curated"), str(RAIZ / "documentacion" / "calidad"), corte)
        fila.update(filas_raw=m["origen_filas"], filas_curated=m["filas_curated"], calidad_pct=m["calidad"]["puntaje_lote"],
                    decision_gate=m["calidad"]["decision"], pii_en_claro_curated=m["pii_en_claro_en_curated"])
        if m["calidad"]["decision"] != "PUBLICAR":
            fila.update(estado="CUARENTENA", detalle="El lote no supera el quality gate: el Data Steward decide (BPMN F4).")
            return 0

        print("[3/5] curated -> mart (banderas y score)", flush=True)
        mm = riesgo.procesar(str(RAIZ / "data" / "curated"), str(raw / "DS-02_*.parquet"), str(RAIZ / "data" / "mart"))
        fila.update(pii_en_claro_mart=mm["controles_gobierno"]["pii_en_claro_mart"],
                    banderas_reglas_version=mm["entradas"]["reglas"]["version"])

        print("[4/5] Alertas de riesgo alto", flush=True)
        al = notificar_alertas.generar(RAIZ / "data" / "mart")
        fila["alertas_alto"] = al["alertas"]

        print("[5/5] Política de retención", flush=True)
        purgar = gobierno.lotes_a_purgar()
        if aplicar_retencion:
            for p in purgar:
                p.unlink(missing_ok=True)
        fila["purgados"] = f"{len(purgar)} archivos" + ("" if aplicar_retencion else " (simulado)")
        fila.update(estado="OK", detalle=f"{al['alertas']} alertas -> {al['csv']}")
        return 0
    except Exception as e:                                       # la corrida fallida también deja evidencia
        fila.update(estado="ERROR", detalle=f"{type(e).__name__}: {e}"[:300])
        traceback.print_exc()
        return 1
    finally:
        fila["duracion_s"] = round(time.time() - t0, 1)
        registrar(fila)
        print(json.dumps(fila, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sin-descarga", action="store_true", help="usa el último lote de data/raw")
    ap.add_argument("--aplicar-retencion", action="store_true", help="borra de verdad los lotes raw vencidos")
    ap.add_argument("--corte", default=None, help="AAAA-MM-DD; por defecto la fecha del lote")
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(a.sin_descarga, a.aplicar_retencion, a.corte))
