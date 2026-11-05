# 04 · Arquitectura de la solución (ArchiMate) · v1.0

| | |
|---|---|
| **Modelo** | [`archimate/ORCA-Arquitectura-v1.0.archimate`](archimate/ORCA-Arquitectura-v1.0.archimate) (formato nativo de **Archi**). El boceto de la Entrega 1 se conserva en [`ORCA-Arquitectura-v0.1.archimate`](archimate/ORCA-Arquitectura-v0.1.archimate) |
| **Versión** | v1.0, entrega final · 13-nov-2026 (v0.1: boceto de la Entrega 1, 28-sep-2026) |
| **Contenido** | 92 elementos · 123 relaciones · 4 vistas (v0.1: 77 · 95 · 3) |
| **Validación** | Las relaciones de v0.1 se verificaron contra la tabla de relaciones permitidas de Archi 5.10 (ArchiMate 3.2) y sus imágenes se exportaron con Archi. Las 28 relaciones nuevas de v1.0 usan solo *serving, realization, access, assignment, composition y flow* entre tipos permitidos. La vista 04 se genera con [`actualizar_modelo_v1.py`](archimate/actualizar_modelo_v1.py), que también la renderiza a PNG |
| **Criterio de rúbrica** | 4. Arquitectura de datos: modelo de las 3 capas coherente y justificado (10 %) |

---

## Vista 01 · Por capas (negocio · aplicación · tecnología)

![Vista por capas](img/archimate-01-vista-por-capas.png)

**Capa de negocio.** Los procesos son los mismos del BPMN TO-BE, con el mismo lenguaje: *Monitorear la contratación → Analizar y validar alertas → Programar la actuación fiscal* (relaciones de *disparo*), más el proceso de apoyo *Gobernar los datos de contratación*, asignado al Data Steward y al CDO. Cada actor se asigna al proceso que ejecuta, igual que los carriles del BPMN. El proceso de monitoreo realiza el servicio *Alertas tempranas*, que sirve al auditor. La actuación fiscal realiza la *Vigilancia fiscal preventiva*, que sirve a la entidad sujeta de control.

**Capa de aplicación.** Cada servicio de aplicación lo realiza un componente con una sola responsabilidad:

| Componente | Servicio que realiza | Proceso de negocio al que sirve |
|---|---|---|
| Pipeline ORCA (Python) | Ingesta incremental | Monitorear |
| Motor de reglas de riesgo | Scoring de riesgo | Monitorear |
| Dashboard ORCA + Notificador (Power Automate) | Visualización y alertas | Analizar alertas |
| Motor de calidad | Validación de calidad | Gobernar datos |
| Módulo de privacidad | Seudonimización y clasificación | Gobernar datos |
| Catálogo de datos y linaje | Catálogo y linaje | Gobernar datos |

SECOP II / datos.gov.co aparece como **componente externo** que expone la **interfaz API SODA**. La contraloría **consume** datos de SECOP y **nunca escribe** en él.

**Capa de tecnología.** Un *Servidor de analítica ORCA* (Python 3.13, pandas, Jupyter y un programador de tareas) realiza el almacenamiento de archivos (Parquet por zonas) y la programación de tareas. GitHub realiza el control de versiones y un servicio de BI (Power BI o Streamlit) publica el dashboard. Todo se conecta por Internet (HTTPS) a la plataforma Socrata de datos.gov.co.

## Vista 02 · Motivación y estrategia

![Vista de motivación](img/archimate-02-motivacion.png)

Esta vista es la **trazabilidad del porqué**: une cada decisión de arquitectura con la estrategia del documento 01.

- **Drivers medidos en los datos, no supuestos:** 302.507 contratos, 85,5 % por contratación directa, el pico de 49.906 contratos en enero de 2026 y el marco normativo.
- **Evaluaciones** → **metas** → **resultados** medibles (≥ 95 % de calidad, 0 PII en claro, 100 % de los contratos con score en ≤ 24 h).
- Los **principios** (calidad antes de publicar, privacidad desde el diseño, la máquina mide y la persona decide) influyen en los resultados.
- Los **requisitos** los realizan componentes concretos de la capa de aplicación. Así, cada componente de la vista 01 existe porque responde a un requisito.
- **Estrategia:** el curso de acción *Crear un Data Office híbrido (hub & spoke)* realiza la meta de datos gobernados. La capacidad *Analítica de riesgo en contratación* realiza la meta de priorizar por riesgo.

## Vista 03 · Flujo de información (boceto de linaje)

![Vista de flujo de información](img/archimate-03-flujo-informacion.png)

Esta vista es el primer boceto del **linaje** exigido por el gobierno de datos (fuente → transformación → dataset → dashboard). Las relaciones de *flujo* etiquetadas muestran el lote atravesando pipeline → calidad → privacidad → reglas de riesgo → dashboard y notificador. Cada objeto de datos está realizado por un artefacto físico de su zona (*raw*, *curated*, *mart*). En la entrega 2 se completa con el catálogo y el linaje a nivel de campo.

---

## Decisiones de arquitectura (justificación)

| # | Decisión | Alternativa descartada | Por qué |
|---|---|---|---|
| AD-1 | Ingesta por **API SODA** con ventana móvil y hash por registro | Descargar el CSV completo (6 M de filas) cada día | Solo se trae el alcance (Antioquia). La marca de agua `:updated_at` no sirve porque el publicador reescribe todo a diario (ver doc. 02). |
| AD-2 | **Almacenamiento en Parquet por zonas** (raw → curated → mart) | Una única tabla o archivos Excel | Zonas = linaje y control de acceso por nivel de sensibilidad. *raw* es inmutable (evidencia legal). Parquet es columnar, tipado y comprimido. |
| AD-3 | **Módulo de privacidad separado** del pipeline | Seudonimizar "donde toque" dentro del notebook | Un único punto de control para la PII, fácil de auditar por el Oficial de Protección de Datos |
| AD-4 | **Motor de reglas de riesgo con reglas versionadas** | Umbrales fijos dentro del código | El Steward recalibra sin reescribir el pipeline (mejora M6); cada score queda asociado a la versión de las reglas |
| AD-5 | **Local + GitHub**, sin nube | AWS/Azure/GCP | La nube es opcional en el curso y no agrega valor para un volumen de ≈ 300 mil filas. La arquitectura queda preparada: las zonas se mapean 1:1 a un lago de datos en la nube si se escala. |
| AD-6 | **Notificador en Power Automate** | Correo desde Python | Es la herramienta de automatización vista en el curso y lo que usaría una entidad pública con Microsoft 365 |

## Vista 04 · Despliegue final, seguridad y control de acceso (nueva en v1.0)

![Vista de despliegue y acceso](img/archimate-04-despliegue-acceso.png)

Esta vista cierra lo que el boceto dejó pendiente: **dónde corre cada pieza**, **qué clasificación tiene cada zona** y **qué rol accede a cuál**.

- **Negocio:** los seis roles del Plan de Gobierno (Owner, Steward, custodio, analista, auditor y ciudadanía). Los actores de la vista 01 (Contralor Auxiliar, Data Steward, Equipo Auditor) se *asignan* a estos roles.
- **Aplicación:** el servicio *Control de acceso por rol y capa* lo realiza *Políticas como código* ([`notebooks/gobierno.py`](../notebooks/gobierno.py)) y sirve a los seis roles. Lee las tres zonas de datos (*access* de lectura), cada una con su clasificación en el nombre: raw **Confidencial**, curated **Interno** y mart **Confidencial (alertas reservadas)**. El mismo componente sirve al dashboard: filtra las pestañas por rol. El *Orquestador* hace fluir el mart publicado hacia el dashboard y las alertas hacia el notificador.
- **Tecnología:** el *Equipo de analítica ORCA* (Windows · Python 3.13) aloja los artefactos reales de cada zona, las reglas versionadas `reglas_riesgo.json` y el registro de corridas. Su *Programador de tareas* dispara el orquestador a las 02:00. GitHub contiene GitHub Actions (monitoreo diario). El servidor Streamlit sirve el dashboard.

## Cambios de v0.1 a v1.0 (alineación con lo implementado)

| Elemento del boceto | En v1.0 | Por qué |
|---|---|---|
| Pipeline ORCA (Python · notebooks) | Pipeline ORCA (`descargar_fuentes.py` · `limpieza.py`) | El componente ya existe y tiene nombre de archivo |
| Motor de calidad de datos | `calidad.py` · 6 dimensiones · gate 95 % | Implementado y medido por lote |
| Motor de reglas de riesgo | `riesgo.py` · 9 banderas + `reglas_riesgo.json` v1.0.0 | AD-4 implementada: reglas versionadas fuera del código |
| Servicio de BI (Power BI / Streamlit) | Servidor Streamlit | Se eligió Streamlit: es Python como el resto del pipeline, se versiona en el mismo repositorio y el control de acceso por rol se programa con las mismas políticas (Power BI exigiría licencias Pro para compartir y duplicaría las reglas en DAX) |
| Artefactos `raw/…`, `curated/…`, `mart/…` | Rutas reales de `data/` | Trazabilidad directa del modelo al repositorio |
| — | Orquestador, Políticas como código, roles, zonas clasificadas, registro de corridas | Vista 04 |

## Coherencia entre las tres capas

| Proceso de negocio (BPMN TO-BE) | Servicio de aplicación | Componente implementado | Tecnología |
|---|---|---|---|
| Monitorear la contratación | Ingesta incremental · Validación de calidad · Seudonimización · Scoring | `orquestar_pipeline.py` → `descargar_fuentes.py`, `limpieza.py`, `calidad.py`, `riesgo.py` | Programador de tareas 02:00 · Python 3.13 · Parquet |
| Analizar y validar alertas | Visualización y alertas | `dashboard/app.py` · `notificar_alertas.py` | Streamlit · Power Automate |
| Gobernar los datos | Catálogo y linaje · Control de acceso | `gobierno.py` · manifiestos · `04_gobierno_datos.ipynb` | GitHub (versionado) · GitHub Actions |
| Programar la actuación fiscal | — (decisión humana) | Bandeja exportada a CSV | — |

## Cómo abrir el modelo

1. Descargar **Archi** (gratuito): <https://www.archimatetool.com/download/>
2. *File → Open* → `documentacion/archimate/ORCA-Arquitectura-v1.0.archimate`
3. Las 4 vistas están en la carpeta *Views*. Cada elemento tiene documentación en la pestaña *Properties*.
