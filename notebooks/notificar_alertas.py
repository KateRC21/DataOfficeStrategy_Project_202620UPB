"""Notificación de alertas de riesgo alto (tarea 'Notificar alertas' del BPMN TO-BE, mejora M5).

Lee el mart y deja en automatizacion/alertas/:
    alertas_<corte>.csv     bandeja de contratos en riesgo Alto (sin PII en claro)
    alertas_<corte>.html    cuerpo del correo para el equipo auditor (resumen + top 20)

Ese par de archivos es el disparador del flujo de Power Automate documentado en
automatizacion/README.md (carpeta sincronizada con OneDrive -> 'Cuando se crea un archivo'
-> 'Enviar correo (V2)'). Si existen las variables ORCA_SMTP_HOST, ORCA_SMTP_USER,
ORCA_SMTP_PASS y ORCA_DESTINATARIOS, el script además envía el correo por SMTP.

Uso:  python notebooks/notificar_alertas.py [--mart data/mart] [--top 20]
"""
import argparse
import html
import json
import os
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "automatizacion" / "alertas"
COLUMNAS = ["num_score_riesgo", "txt_banderas", "id_contrato", "nom_entidad", "nom_municipio", "cod_modalidad",
            "fec_firma", "val_contrato", "nom_proveedor_juridico", "id_proveedor_seud", "url_proceso_secop"]


def cop(v: float) -> str:
    return f"${v:,.0f}".replace(",", ".")


def generar(mart: Path, top: int = 20) -> dict:
    man = json.loads((mart / "mart.manifest.json").read_text(encoding="utf-8"))
    c = pd.read_parquet(mart / "mart_contratos_riesgo.parquet")
    a = (c[(c["niv_riesgo"] == "Alto") & c["ind_sujeto_vigilancia"]]
         .sort_values(["num_score_riesgo", "val_contrato"], ascending=False))
    corte = man.get("corte", "sin-corte")
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta_csv = SALIDA / f"alertas_{corte}.csv"
    a[COLUMNAS].to_csv(ruta_csv, index=False, encoding="utf-8-sig")

    por_ent = a.groupby("nom_entidad").agg(n=("id_contrato", "size"), v=("val_contrato", "sum")).nlargest(5, "v")
    filas = "".join(
        f"<tr><td>{r.num_score_riesgo:.0f}</td><td>{html.escape(r.txt_banderas)}</td><td>{html.escape(str(r.nom_entidad))}</td>"
        f"<td style='text-align:right'>{cop(r.val_contrato)}</td><td><a href='{r.url_proceso_secop}'>{r.id_contrato}</a></td></tr>"
        for r in a.head(top).itertuples())
    ents = "".join(f"<li>{html.escape(str(n))}: {r.n} contratos · {cop(r.v)}</li>" for n, r in por_ent.iterrows())
    cuerpo = f"""<html><body style="font-family:Segoe UI,Arial,sans-serif;color:#222">
<h2>ORCA · {len(a)} alertas de riesgo alto (lote {corte})</h2>
<p>Sujetos de vigilancia del orden territorial · valor expuesto: <b>{cop(a['val_contrato'].sum())}</b> ·
calidad del lote: {man['entradas']['curated']['puntaje_calidad']} % ({man['entradas']['curated']['decision_quality_gate']}) ·
reglas v{man['entradas']['reglas']['version']}.</p>
<p><b>Entidades con más valor en alerta:</b></p><ul>{ents}</ul>
<table border="1" cellpadding="4" cellspacing="0" style="border-collapse:collapse;font-size:13px">
<tr><th>Score</th><th>Banderas</th><th>Entidad</th><th>Valor</th><th>Contrato (SECOP)</th></tr>{filas}</table>
<p style="font-size:12px;color:#666">Una alerta prioriza la revisión; no es un hallazgo. SLA de gestión: 3 días hábiles
(después se escala al Contralor Auxiliar). Registre en la bandeja si la alerta fue pertinente. Bandeja completa adjunta (CSV, sin PII en claro).</p>
</body></html>"""
    ruta_html = SALIDA / f"alertas_{corte}.html"
    ruta_html.write_text(cuerpo, encoding="utf-8")
    enviado = enviar_smtp(f"ORCA · {len(a)} alertas de riesgo alto · lote {corte}", cuerpo, ruta_csv)
    return {"corte": corte, "alertas": len(a), "valor": float(a["val_contrato"].sum()),
            "csv": str(ruta_csv.relative_to(RAIZ)), "html": str(ruta_html.relative_to(RAIZ)), "correo_smtp": enviado}


def enviar_smtp(asunto: str, cuerpo: str, adjunto: Path) -> str:
    host, user, pwd, dest = (os.environ.get(k) for k in ("ORCA_SMTP_HOST", "ORCA_SMTP_USER", "ORCA_SMTP_PASS", "ORCA_DESTINATARIOS"))
    if not all((host, user, pwd, dest)):
        return "no configurado (lo envía Power Automate)"
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = asunto, user, dest
    msg.set_content("Ver versión HTML.")
    msg.add_alternative(cuerpo, subtype="html")
    msg.add_attachment(adjunto.read_bytes(), maintype="text", subtype="csv", filename=adjunto.name)
    with smtplib.SMTP(host, 587, timeout=60) as s:
        s.starttls()
        s.login(user, pwd)
        s.send_message(msg)
    return "enviado"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mart", default=str(RAIZ / "data" / "mart"))
    ap.add_argument("--top", type=int, default=20)
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(generar(Path(a.mart), a.top), ensure_ascii=False, indent=2))
