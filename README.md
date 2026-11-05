# ORCA · Observatorio de Riesgo en Contratación de Antioquia

**Versión 1.0 · Entrega final · 13-nov-2026** · Proyecto final de *Data Office Strategy* · UPB · Docente: María Victoria Valencia Arango

> Un Data Office para una contraloría territorial que pasa de **auditar por muestreo y juicio experto** a **priorizar la vigilancia fiscal por riesgo**, con datos abiertos de SECOP II gobernados: calidad medida en cada lote, datos personales seudonimizados, linaje verificable y acceso por rol.

| Contratos analizados | Calidad del lote | PII en claro en consumo | Bandeja del auditor | Madurez de gobierno |
|---:|---:|---:|---:|---:|
| **294.409** (Antioquia, desde 2024) | **99,66 %** → PUBLICAR | **0** | **1.948** contratos (1,05 % del universo territorial) | **2 → 13 / 16** (Nivel 4 · Gestionado) |

*Lote de evidencia: corte del 5-nov-2026.*

---

## 1. El caso

La contraloría del caso (inspirada en la Contraloría General de Antioquia) vigila ≈ 110.000 contratos al año, el 84 % por contratación directa. Hoy elige qué revisar **por criterio histórico**, sobre extracciones manuales del SECOP que no se validan, no se trazan y copian cédulas en archivos de Excel. ORCA responde seis preguntas de negocio:

| # | Pregunta | Decisión que habilita |
|---|---|---|
| P1 | ¿Qué entidades contratan directo por encima de su propia historia? | Incluir la entidad en el Plan de Vigilancia (PVCF) |
| P2 | ¿Qué se firmó en ventanas atípicas (antes de la Ley de Garantías, fin de vigencia)? | Priorizar la revisión documental |
| P3 | ¿Qué proveedores concentran contratos o valor en una entidad? | Auditoría al par entidad–proveedor |
| P4 | ¿Qué personas naturales tienen contratos simultáneos con varias entidades? | Verificar la capacidad real de ejecución |
| P5 | ¿Qué contratos tienen valores atípicos para su tipo y modalidad? | Revisar los estudios de mercado |
| P6 | ¿Qué procesos «competitivos» tuvieron un único oferente? | Alerta temprana por posible direccionamiento |

**Hallazgos del lote final:** 47.352 contratos directos firmados en ventana atípica (45.885 en enero de 2026, justo antes de la restricción de la Ley de Garantías) · 12 entidades territoriales que subieron ≥ 10 puntos su contratación directa · 116 pares entidad–proveedor con concentración · 523 contratistas persona natural con contratos en 3 a 13 entidades a la vez · 16.276 contratos de procesos competitivos con una sola oferta. **Una alerta prioriza la revisión; no es un hallazgo ni prueba una irregularidad.**

## 2. Componentes y dónde está cada uno (mapa a la rúbrica)

| Criterio (peso) | Qué se entrega | Dónde |
|---|---|---|
| 1. Problema, estrategia y Data Office (10 %) | Problema medido, estrategia defensa/ataque, DOFA, modelo *hub & spoke*, CDO, roles, RACI organizacional, KPI | [documentacion/01_estrategia_y_organizacion.md](documentacion/01_estrategia_y_organizacion.md) · [taller de estrategia](documentacion/05_taller_estrategia_corporativa.md) |
| 2. Procesos BPMN (10 %) | AS-IS con 7 dolores, TO-BE con 6 mejoras, sub-proceso de calidad, excepciones y SLA; correspondencia modelo → implementación | [documentacion/03_procesos_bpmn.md](documentacion/03_procesos_bpmn.md) · [bpmn/](documentacion/bpmn/) |
| 3. Automatización (10 %) | 3 tareas: monitoreo diario (GitHub Actions), pipeline diario (Programador de tareas de Windows), alertas (Power Automate) | [automatizacion/](automatizacion/) |
| 4. Arquitectura ArchiMate (10 %) | Modelo v1.0: 92 elementos, 123 relaciones, 4 vistas (capas, motivación, flujo de información, despliegue y acceso) | [documentacion/04_arquitectura_archimate.md](documentacion/04_arquitectura_archimate.md) · [archimate/](documentacion/archimate/) |
| 5. Datos: ingesta, limpieza y EDA (10 %) | Ingesta por API, limpieza y normalización, quality gate, EDA, banderas rojas y score | [notebooks/](notebooks/) · [documentacion/06_limpieza_y_normalizacion.md](documentacion/06_limpieza_y_normalizacion.md) |
| **6. Gobierno de datos (30 %)** | **Plan de Gobierno v1.0** con los 8 artefactos **aplicados y verificados** sobre el lote | [documentacion/05_plan_gobierno_datos.md](documentacion/05_plan_gobierno_datos.md) ([Word](documentacion/ORCA-Plan-Gobierno-v1.0.docx)) · [notebooks/04_gobierno_datos.ipynb](notebooks/04_gobierno_datos.ipynb) · [documentacion/gobierno/](documentacion/gobierno/) |
| 7. Dashboard (10 %) | Streamlit con 7 pestañas, bandeja de alertas y control de acceso por rol | [dashboard/](dashboard/) |
| 8. Colaboración y documentación (10 %) | Repositorio, README, notebooks ejecutados con salidas | Este repositorio |

### Gobierno del dato: los 8 artefactos y su evidencia

| Artefacto | Evidencia verificable |
|---|---|
| Catálogo de activos | 8 activos (3 fuentes + curated + 4 tablas del mart) generados desde los manifiestos, 100 % con Owner y Steward → [`catalogo_activos.csv`](documentacion/gobierno/catalogo_activos.csv) |
| Diccionario de datos | 20 columnas de la fuente ([Excel S2](documentacion/Gobierno%20de%20datos/S2_Metadatos_EquipoORCA_Completo.xlsx)) + 39 del mart con tipo, unidad, valores válidos y cumplimiento medido → [`diccionario_mart.csv`](documentacion/gobierno/diccionario_mart.csv) |
| RACI | 4 roles × 18 tareas, regla de oro (una sola A) verificada → [`raci_proyecto.csv`](documentacion/gobierno/raci_proyecto.csv) |
| Políticas y estándares | Nomenclatura (0 de 79 columnas fuera del estándar), retención de raw (3 lotes / 90 días), uso aceptable, seudonimización |
| Reglas de calidad | 6 dimensiones, 14 reglas por lote + 7 del mart, gate ≥ 95 % → [`reporte_calidad_DS-01.csv`](documentacion/calidad/reporte_calidad_DS-01.csv), [`calidad_mart.csv`](documentacion/gobierno/calidad_mart.csv) |
| Linaje | Fuente → raw → curated → mart → dashboard con cadena de SHA-256 verificada (4/4) y linaje por campo → [`linaje.csv`](documentacion/gobierno/linaje.csv) |
| Clasificación y PII | 95 campos clasificados (21 personales eliminados o seudonimizados con HMAC-SHA256) · PII en claro = 0 → [`clasificacion_campos_DS-01.csv`](documentacion/gobierno/clasificacion_campos_DS-01.csv) |
| Control de acceso | Matriz 6 roles × 4 capas impuesta en el dashboard (`gobierno.ruta_capa`) y probada → [`matriz_acceso.csv`](documentacion/gobierno/matriz_acceso.csv) |

Marco: DAMA-DMBOK (10 áreas mapeadas) y Ley 1581 de 2012 (8 principios mapeados) en el §10 del Plan.

## 3. Arquitectura del pipeline

```text
API SODA datos.gov.co (DS-01 contratos · DS-02 procesos · DS-03 DIVIPOLA)
        │  descargar_fuentes.py ─ manifiesto por lote (SoQL, filas, SHA-256)
        ▼
data/raw        Confidencial · PII en claro · fuera de Git · retención 3 lotes / 90 días
        │  limpieza.py + calidad.py ─ nulos disfrazados, tipos, NIT a 9 dígitos, nombre canónico,
        │  DIVIPOLA, 14 reglas de calidad → quality gate ≥ 95 %, HMAC-SHA256, enmascarado de texto libre
        ▼
data/curated    Interno · PII seudonimizada
        │  riesgo.py + reglas_riesgo.json v1.0.0 ─ 9 banderas rojas, score 0–100, nivel
        │  (+ DS-02 sin PII para P6) · bloquea la publicación si hay PII o columnas fuera del estándar
        ▼
data/mart       Confidencial · alertas reservadas
        ├──► dashboard/app.py (Streamlit, acceso por rol)
        └──► notificar_alertas.py → Power Automate (correo al equipo auditor)

orquestar_pipeline.py ejecuta todo a las 02:00 y registra cada corrida en automatizacion/registro_pipeline.csv
```

## 4. Herramientas

| Uso | Herramienta |
|---|---|
| Lenguaje y datos | Python 3.13 · pandas · numpy · pyarrow (Parquet) · requests |
| Notebooks | Jupyter (5 notebooks ejecutados con salidas) |
| Dashboard | Streamlit + Plotly |
| Automatización | GitHub Actions · Programador de tareas de Windows · Power Automate |
| Procesos | BPMN 2.0 (bpmn.io / Camunda Modeler) |
| Arquitectura | ArchiMate 3.2 (Archi) |
| Versionamiento | Git + GitHub |
| Nube | No se usa (opcional en el curso). La arquitectura de zonas se mapea 1:1 a un lago de datos si se escala (AD-5) |

## 5. Cómo ejecutar el proyecto

**Requisitos:** Python 3.11+ y conexión a internet (la API de datos.gov.co es pública y no requiere token).

```bash
git clone https://github.com/KateRC21/DataOfficeStrategy_Project_202620UPB.git
cd DataOfficeStrategy_Project_202620UPB
pip install -r requirements.txt

# (opcional) sal secreta de la seudonimización; sin ella se usa una sal de desarrollo y el manifiesto lo declara
#   PowerShell:  $env:ORCA_SALT = "<valor secreto>"      bash:  export ORCA_SALT="<valor secreto>"

# 1. Pipeline completo: descarga (~15 min) → curated → quality gate → mart → alertas
python notebooks/orquestar_pipeline.py
#    o, si ya hay un lote en data/raw:
python notebooks/orquestar_pipeline.py --sin-descarga

# 2. Dashboard
streamlit run dashboard/app.py

# 3. Notebooks (en orden; todos detectan la raíz del proyecto)
jupyter notebook notebooks/
```

| Notebook | Qué hace |
|---|---|
| [`00_perfilamiento_fuente.ipynb`](notebooks/00_perfilamiento_fuente.ipynb) | Justifica la fuente con consultas agregadas a la API (Entrega 1) |
| [`01_limpieza_normalizacion_ORCA_final.ipynb`](notebooks/01_limpieza_normalizacion_ORCA_final.ipynb) | raw → curated, quality gate y controles de privacidad |
| [`calculoMetricas_calidad.ipynb`](notebooks/calculoMetricas_calidad.ipynb) | Métricas de calidad de las 76 columnas de curated |
| [`02_EDA_ORCA.ipynb`](notebooks/02_EDA_ORCA.ipynb) | Análisis exploratorio y señales candidatas |
| [`03_riesgo_y_mart.ipynb`](notebooks/03_riesgo_y_mart.ipynb) | Banderas rojas, score y respuestas a P1–P6 |
| [`04_gobierno_datos.ipynb`](notebooks/04_gobierno_datos.ipynb) | Demuestra los 8 artefactos de gobierno sobre el lote |

Otros: monitoreo de la fuente `python notebooks/monitoreo_fuente.py` · programar la tarea diaria `powershell -ExecutionPolicy Bypass -File automatizacion\programar_tarea_windows.ps1` · capturas del dashboard `python dashboard/capturar_pantallas.py` · regenerar ArchiMate v1.0 `python documentacion/archimate/actualizar_modelo_v1.py` · regenerar el Plan en Word `python documentacion/plan_gobierno/md_a_word.py`.

## 6. Estructura del repositorio

```text
├── notebooks/            código Python del pipeline (.py) y notebooks ejecutados (.ipynb)
│   ├── descargar_fuentes.py · limpieza.py · calidad.py · riesgo.py · reglas_riesgo.json
│   ├── gobierno.py · notificar_alertas.py · orquestar_pipeline.py · monitoreo_fuente.py
│   └── 00 … 04 *.ipynb
├── dashboard/            app.py (Streamlit) · img/ (capturas) · eda/ (figuras del EDA)
├── automatizacion/       README (3 automatizaciones) · registros de ejecución · tarea programada
├── documentacion/
│   ├── 01 estrategia · 02 selección de datos · 03 BPMN · 04 ArchiMate · 05 Plan de Gobierno · 06 pipeline
│   ├── ORCA-Plan-Gobierno-v1.0.docx · bpmn/ · archimate/ · img/
│   ├── gobierno/         evidencia generada por el notebook 04 (catálogo, diccionario, linaje, acceso, KPI…)
│   ├── calidad/          reportes de calidad del lote
│   └── plan_gobierno/    plantillas de clase diligenciadas (S1 RACI, S2 metadatos) y generadores
├── data/                 raw · curated · mart (solo estructura en Git: los datos no se versionan)
└── .github/workflows/    monitoreo diario de la fuente
```

## 7. Protección de datos personales

SECOP II es público por transparencia (Ley 1712), pero reutilizarlo es un tratamiento nuevo sujeto a la Ley 1581. Por eso ORCA:

- elimina nombres de personas naturales, datos bancarios y datos del representante legal;
- seudonimiza los documentos con HMAC-SHA256 y sal secreta (P4 se calcula sin conocer la cédula);
- enmascara cédulas encontradas en texto libre;
- nunca versiona raw, curated, el mart ni las alertas individuales;
- bloquea la publicación del mart si detecta PII en claro (resultado: 0).

## 8. Equipo y roles

| Integrante | Rol en el Data Office | Rol de gobierno |
|---|---|---|
| Luis Ángel Seoanes Ovieso | CDO · Arquitecto de datos · Product Owner | Data Owner |
| Julian Amariles Taborda | Líder de Gobierno de Datos | Data Steward |
| Katheryn Ramírez Chimá | Ingeniera de datos | Custodio técnico |
| Jhon Sebastian Rayo Posada | Ingeniero de datos · Analista | Consumidor / Analista |

## 9. Versiones

| Versión | Fecha | Contenido |
|---|---|---|
| 0.1 | 28-sep-2026 | Entrega 1: problema, estrategia, Data Office, BPMN, selección de datos, boceto ArchiMate |
| 0.2 | 23-oct-2026 | Entrega 2: ingesta, limpieza, quality gate, EDA, monitoreo automatizado, Plan de Gobierno (borrador) |
| **1.0** | **13-nov-2026** | **Entrega final: score de riesgo y mart, dashboard, 3 automatizaciones, Plan de Gobierno v1.0 aplicado, ArchiMate v1.0, pitch** |

Pitch final (10–12 min): guion en [documentacion/07_pitch_final.md](documentacion/07_pitch_final.md).
