# ORCA · Observatorio de Riesgo en Contratación de Antioquia

**Versión 1.0 · Entrega 1 (28-sep-2026)** · Proyecto final de *Data Office Strategy*, UPB · Docente: María Victoria Valencia Arango

> Un Data Office para una contraloría territorial que pasa de **auditar por muestreo y juicio experto** a **priorizar la vigilancia fiscal por riesgo**, usando los datos abiertos de SECOP II **gobernados**: con calidad medida, datos personales protegidos y trazabilidad completa.

## El caso en cifras (datos abiertos reales, consultados el 27-sep-2026)

| | |
|---|---|
| Contratos firmados por entidades de Antioquia (2024 → sep-2026) | **302.507** · $56,4 billones COP |
| Adjudicados por **contratación directa** | **85,5 %** |
| Contratos firmados en **enero de 2026**, justo antes de la Ley de Garantías | **49.906** (93,8 % directa); de febrero a mayo, entre 1.382 y 1.741 por mes |
| Contratos con **personas naturales** (PII) | **81,5 %** |

## Datos abiertos utilizados

| Código | Dataset | Rol |
|---|---|---|
| DS-01 | [SECOP II – Contratos Electrónicos](https://www.datos.gov.co/d/jbjy-vk9h) (`jbjy-vk9h`) | Principal |
| DS-02 | [SECOP II – Procesos de Contratación](https://www.datos.gov.co/d/p6dx-8zbt) (`p6dx-8zbt`) | Complementario (competencia) |
| DS-03 | [DIVIPOLA – Códigos de municipios](https://www.datos.gov.co/d/gdxc-w37w) (`gdxc-w37w`) | Dato de referencia |

La justificación y la matriz de decisión están en [documentacion/02_seleccion_datos_abiertos.md](documentacion/02_seleccion_datos_abiertos.md).

## Estructura del repositorio

```
├── README.md
├── requirements.txt
├── documentacion/
│   ├── 01_estrategia_y_organizacion.md    ← problema, estrategia, diseño del Data Office (CDO, roles, RACI)
│   ├── 02_seleccion_datos_abiertos.md      ← selección, alcance, PII, calidad inicial
│   ├── 03_procesos_bpmn.md                 ← AS-IS, TO-BE y mejoras
│   ├── 04_arquitectura_archimate.md        ← boceto de arquitectura (3 vistas)
│   ├── bpmn/                               ← .bpmn (BPMN 2.0 XML)
│   ├── archimate/                          ← .archimate (Archi)
│   └── img/                                ← diagramas exportados
├── src/
│   └── descargar_fuentes.py                ← descarga las fuentes por API a data/raw (+ manifiesto de linaje)
├── notebooks/
│   └── 00_perfilamiento_fuente.ipynb       ← evidencia reproducible de las cifras
├── automatizacion/                         ← Entrega 2
├── dashboard/                              ← Entrega final
└── data/                                   ← local, no versionado (raw / curated / mart)
```

## Avance por entrega

| Entrega | Contenido | Estado |
|---|---|---|
| **1 · 28-sep** | Problema y necesidad de negocio · estrategia y diseño del Data Office · BPMN · selección de datos abiertos · boceto ArchiMate | ✅ |
| 2 · 23-oct | Pipeline de ingesta, limpieza y normalización · EDA inicial · tarea automatizada · borrador del Plan de Gobierno de Datos | ⏳ |
| Final · 13-nov | Solución completa · Plan de Gobierno implementado · dashboard · pitch | ⏳ |

## Herramientas

Python 3.13 (pandas, requests, matplotlib, Jupyter) · API SODA de datos.gov.co · BPMN 2.0 (bpmn.io / Camunda Modeler) · ArchiMate 3.2 (Archi) · GitHub · Power Automate (entrega 2) · Power BI o Streamlit (entrega final).

## Cómo ejecutar

```bash
git clone <url-del-repositorio>
cd <repositorio>
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
python src/descargar_fuentes.py   # descarga DS-01, DS-02 y DS-03 a data/raw (≈ 15-30 min)
jupyter notebook notebooks/00_perfilamiento_fuente.ipynb
```

**Los datos no están en el repositorio a propósito:** la zona `raw` contiene cédulas y nombres de personas naturales (PII, Ley 1581 de 2012), así que se excluye en `.gitignore`. Cada integrante los regenera con `src/descargar_fuentes.py`. El script deja junto a cada archivo un `*.manifest.json` con el linaje del lote: consulta SoQL, filas, hash SHA-256, fecha de corte y clasificación.

El notebook consulta la API pública en vivo. No requiere credenciales ni descarga el dataset completo. Las cifras pueden variar un poco porque SECOP se actualiza a diario.

**Abrir los diagramas:** los `.bpmn` se abren arrastrándolos a <https://demo.bpmn.io>. El `.archimate` se abre con [Archi](https://www.archimatetool.com/download/).

## Equipo

| Integrante | Rol en ORCA |
|---|---|
| Luis Ángel Seoanes Ovieso | CDO / Arquitecto(a) de datos · Product Owner |
| *Integrante 2* | Líder de Gobierno de Datos · Data Steward |
| *Integrante 3* | Ingeniero(a) de Datos · Analista |

## Licencia de los datos

Los datos de SECOP II y DIVIPOLA se publican con licencia **CC BY-SA 4.0** (Colombia Compra Eficiente y DANE). Los datos personales que contienen se tratan según la **Ley 1581 de 2012**: ver la política de seudonimización en el documento 02 §6.
