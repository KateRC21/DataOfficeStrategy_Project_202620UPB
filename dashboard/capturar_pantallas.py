"""Levanta el dashboard y guarda capturas de cada pestaña en dashboard/img/ (evidencia de la entrega).

Requiere: pip install playwright  (usa el navegador Edge o Chrome instalado: no descarga navegadores).
Uso:  python dashboard/capturar_pantallas.py
"""
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
IMG = RAIZ / "dashboard" / "img"
PUERTO = 8599
CAPTURAS = [  # (archivo, pestaña, rol a elegir o None)
    ("01_resumen.png", "Resumen", None),
    ("02_p1_entidades.png", "P1 · Entidades", None),
    ("03_p2_ventanas.png", "P2 · Ventanas atípicas", None),
    ("04_bandeja.png", "Bandeja de alertas", None),
    ("05_gobierno.png", "Gobierno y calidad", "Data Owner"),
    ("06_vista_ciudadania.png", "Resumen", "Ciudadanía"),
]


def esperar(page):
    page.wait_for_selector('[data-testid="stApp"]')
    time.sleep(2)
    page.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=120_000)
    time.sleep(3)


def main():
    IMG.mkdir(exist_ok=True)
    srv = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "dashboard/app.py", "--server.headless", "true",
                            "--server.port", str(PUERTO), "--browser.gatherUsageStats", "false",
                            "--theme.base", "light"], cwd=RAIZ, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(8)
        with sync_playwright() as p:
            nav = None
            for canal in ("msedge", "chrome"):
                try:
                    nav = p.chromium.launch(channel=canal)
                    break
                except Exception:
                    continue
            page = nav.new_page(viewport={"width": 1500, "height": 1000}, device_scale_factor=1)
            for archivo, pestana, rol in CAPTURAS:
                page.goto(f"http://localhost:{PUERTO}")
                esperar(page)
                if rol:
                    page.locator('[data-testid="stSidebar"] [data-baseweb="select"]').first.click()
                    page.get_by_role("option", name=rol).first.click()
                    esperar(page)
                page.get_by_role("tab", name=pestana).click()
                esperar(page)
                page.screenshot(path=str(IMG / archivo), full_page=False)
                print("ok", archivo)
            nav.close()
    finally:
        srv.terminate()


if __name__ == "__main__":
    main()
