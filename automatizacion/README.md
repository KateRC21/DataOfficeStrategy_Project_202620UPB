# Automatización · ORCA v1.0

**Criterio 3 de la rúbrica (10 %):** al menos una tarea repetitiva automatizada con una herramienta realista.
ORCA automatiza **tres** tareas del BPMN TO-BE ([03_procesos_bpmn.md](../documentacion/03_procesos_bpmn.md) §3), cada una con evidencia en esta carpeta.

| # | Tarea del BPMN TO-BE | Mejora | Herramienta | Disparador | Evidencia |
|---|---|---|---|---|---|
| A1 | Monitorear la fuente (frescura y calidad básica de DS-01) | M1 | Script Python + **GitHub Actions** | Diario 06:00 (cron) y manual | [`registro_ejecuciones.csv`](registro_ejecuciones.csv) · resumen en la pestaña *Actions* |
| A2 | Pipeline completo: ingesta → limpieza y quality gate → banderas y score → publicación del mart | M1, M2, M3, M4 | [`orquestar_pipeline.py`](../notebooks/orquestar_pipeline.py) + **Programador de tareas de Windows** | Diario 02:00 (el temporizador del BPMN) | [`registro_pipeline.csv`](registro_pipeline.csv) |
| A3 | Notificar alertas de riesgo alto al equipo auditor | M5 | [`notificar_alertas.py`](../notebooks/notificar_alertas.py) + **Power Automate** (o SMTP) | Al final de A2 | [`alertas/`](alertas/) (CSV + cuerpo HTML del correo) |

## Por qué estas tareas

Se automatiza lo **determinista, repetible y sin juicio de valor** (frontera manual/automático del BPMN): extraer, medir la calidad, seudonimizar, calcular el score, publicar y notificar. Queda humano lo que exige criterio: liberar un lote en cuarentena (Data Steward), decidir si una alerta es pertinente (auditor) y la actuación fiscal (Data Owner). **La máquina mide, la persona decide.**

Antes (AS-IS) estas tareas tomaban días: pedir la extracción a TIC, depurar en Excel y elegir la muestra a mano (dolores D2–D6). Ahora una corrida completa tarda unos 3 minutos sin la descarga y unos 15 minutos con ella.

## A1 · Monitoreo diario con GitHub Actions

- Workflow: [`.github/workflows/monitoreo-fuente.yml`](../.github/workflows/monitoreo-fuente.yml).
- Ejecuta [`notebooks/monitoreo_fuente.py`](../notebooks/monitoreo_fuente.py), que solo consulta **agregados** por la API (no descarga datos ni toca PII): total de contratos, última fecha de firma, % de valores en $0 y % de ciudad «No Definido».
- Cada corrida agrega una fila a `registro_ejecuciones.csv`, la publica como artefacto y la versiona con un commit automático de `orca-bot`. Así el repositorio acumula la serie histórica de la fuente y deja ver cambios (p. ej. que SECOP modifique registros hacia atrás).
- Ejecución manual para la evidencia: pestaña *Actions* → *Monitoreo diario de la fuente* → *Run workflow*.

## A2 · Pipeline diario con el Programador de tareas de Windows

```powershell
# registrar la tarea (una vez, desde la raíz del repo)
powershell -ExecutionPolicy Bypass -File automatizacion\programar_tarea_windows.ps1
# o ejecutar a mano
python notebooks/orquestar_pipeline.py                 # con descarga
python notebooks/orquestar_pipeline.py --sin-descarga  # reutiliza el último lote raw
```

[`programar_tarea_windows.ps1`](programar_tarea_windows.ps1) registra la tarea `ORCA-Pipeline-Diario` a las 02:00, con 3 reintentos cada hora (el *backoff* de 1 h del evento de error del BPMN). El orquestador aplica las políticas del Plan de Gobierno sin intervención:

| Paso | Control de gobierno que aplica |
|---|---|
| Ingesta | Manifiesto de linaje por lote (SoQL, filas, SHA-256) |
| Curated | Quality gate ≥ 95 %. Si no se cumple: **CUARENTENA**, no se publica y se registra (estado final F4 del BPMN) |
| Mart | Solo con gate = PUBLICAR · control de PII en claro = 0 y de nomenclatura; si falla, el mart no se escribe |
| Alertas | Solo sujetos de vigilancia (orden territorial) en riesgo Alto |
| Retención | Lotes raw fuera de los 3 más recientes y con más de 90 días se purgan (con `--aplicar-retencion`) |

Cada corrida, exitosa o fallida, agrega una fila a `registro_pipeline.csv` con lote, filas, calidad, decisión del gate, PII en claro, alertas, versión de reglas, purga y estado.

## A3 · Notificación de alertas con Power Automate

`notificar_alertas.py` escribe en `automatizacion/alertas/`:

- `alertas_<corte>.csv`: la bandeja de riesgo alto, **sin PII en claro** (personas naturales solo por seudónimo), con enlace a SECOP II.
- `alertas_<corte>.html`: el cuerpo del correo (resumen, 5 entidades con más valor en alerta y top 20 contratos).

**Flujo de Power Automate** (nube, con la cuenta Microsoft 365 institucional de la UPB):

1. Desencadenador: **OneDrive para la Empresa → «Cuando se crea un archivo»** en la carpeta sincronizada `ORCA/automatizacion/alertas`, filtrando nombres que terminan en `.html`.
2. Acción **«Obtener contenido de archivo»** del HTML y del CSV del mismo corte (mismo nombre con extensión `.csv`).
3. Acción **Office 365 Outlook → «Enviar un correo electrónico (V2)»** al grupo del equipo auditor: asunto `ORCA · alertas de riesgo alto · <corte>`, cuerpo = contenido del HTML, adjunto = CSV.
4. Acción **«Crear elemento»** en una lista de SharePoint *Bandeja ORCA* (corte, número de alertas, fecha de envío) para medir el SLA de 3 días hábiles (temporizador P3D del BPMN) y la precisión de alertas.

Si la entidad no tiene Microsoft 365, el mismo script envía el correo por SMTP al definir `ORCA_SMTP_HOST`, `ORCA_SMTP_USER`, `ORCA_SMTP_PASS` y `ORCA_DESTINATARIOS` (las credenciales nunca se versionan).

## Secretos

| Variable | Uso | Dónde vive |
|---|---|---|
| `ORCA_SALT` | Sal del HMAC-SHA256 de la seudonimización | Variable de entorno del usuario del servidor. La custodia el custodio técnico (tarea 13 del RACI) |
| `ORCA_SMTP_*` | Envío de correo alternativo | Variables de entorno; en GitHub, *Secrets* del repositorio |
