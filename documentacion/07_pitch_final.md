# 07 · Pitch final (10–12 minutos)

| | |
|---|---|
| **Solución** | ORCA v1.0 · Observatorio de Riesgo en Contratación de Antioquia |
| **Fecha** | 13-nov-2026 · en clase |
| **Estructura pedida** | Caso → solución → gobierno del dato → conclusiones |
| **Diapositivas** | 11 diapositivas con notas del orador: https://claude.ai/artifact/QbaRBMVabLoze6rsC5WxMF (se descargan como PowerPoint o PDF desde el menú *Share › Export*) |
| **Demo** | `streamlit run dashboard/app.py` (con respaldo en las capturas de [`dashboard/img/`](../dashboard/img/) si falla la red o el equipo) |

> Regla del equipo para el pitch: **cada afirmación con un número del lote real** (corte 5-nov-2026) y **cada número con su evidencia en el repositorio**.

## Guion por bloques

| # | Tiempo | Bloque | Quién | Mensaje (una idea por diapositiva) | Apoyo visual |
|---|---|---|---|---|---|
| 1 | 0:00–0:45 | Apertura | Luis | «En enero de 2026 Antioquia firmó 48.964 contratos: el 16 % de casi tres años, en un mes, justo antes de la Ley de Garantías. ¿Quién los revisó?» | Gráfico mensual (pestaña P2) |
| 2 | 0:45–2:00 | El caso | Luis | 294.409 contratos, $58,5 billones, 84 % por contratación directa, 81 % con personas naturales. La contraloría elige qué auditar por histórico y juicio experto, sobre Excel sin trazabilidad (dolores D1–D7 del AS-IS) | KPI del caso + BPMN AS-IS con los dolores en rojo |
| 3 | 2:00–3:00 | Estrategia y Data Office | Luis | Estrategia **60 % defensa / 40 % ataque** (Dallemule y Davenport): una contraloría no puede equivocarse con los datos. Modelo **hub & spoke** con CDO que reporta al Despacho, no a TIC | Organigrama (doc. 01 §6.3) |
| 4 | 3:00–4:00 | Proceso TO-BE y arquitectura | Katheryn | Del muestreo manual a un proceso diario en el que **la máquina mide y la persona decide**. Las 3 capas de ArchiMate: cada componente existe porque responde a un requisito | BPMN TO-BE + vista 04 de ArchiMate |
| 5 | 4:00–5:00 | Pipeline y automatización | Katheryn | API → raw → curated → mart en ≈ 95 s, programado a las 02:00. Si la calidad baja de 95 %, el lote **no se publica**. 3 automatizaciones con evidencia: GitHub Actions, Programador de tareas, Power Automate | Diagrama del pipeline + `registro_pipeline.csv` |
| 6 | 5:00–6:30 | **Demo del dashboard** | Jhon | Rol *auditor*: Resumen → Top 15 para el PVCF → P2 (pico de enero) → **Bandeja: 1.948 contratos** con la razón de cada alerta y el enlace a SECOP. Cambiar a rol *ciudadanía*: desaparecen las alertas | Dashboard en vivo |
| 7 | 6:30–7:30 | Score de riesgo | Jhon | 9 banderas versionadas responden P1–P6. R1 sola no alcanza: la directa es la regla, solo prioriza combinada. **De 185.337 contratos territoriales a 1.948 (1,05 %)** | Tabla de banderas y niveles |
| 8 | 7:30–10:00 | **Gobierno del dato (30 %)** | Julian | Los 8 artefactos **aplicados, no descritos**: catálogo generado desde los manifiestos; diccionario con cumplimiento medido; RACI con una sola A por tarea; quality gate 99,66 %; linaje con SHA-256 verificado; 95 campos clasificados y **0 PII en claro**; acceso por rol impuesto en el código. Madurez **2 → 13 / 16** | Tabla «artefacto → evidencia» del Plan + pestaña *Gobierno y calidad* |
| 9 | 10:00–11:00 | Conclusiones | Luis | (1) Cobertura total con priorización explicable. (2) El gobierno es lo que hace defendible cada alerta. (3) Límites honestos: Owner simulado, acceso sin IAM, falta medir la precisión de las alertas en operación | Tres ideas + próximos pasos |
| 10 | 11:00–12:00 | Cierre y preguntas | Todos | «La máquina mide, la persona decide» | — |

## Mensajes clave por bloque

**Caso (por qué importa).** La contratación directa no es ilegal, pero es la regla (84 %). Sin datos gobernados, la contraloría no puede ver patrones como el pico pre-Ley de Garantías ni explicar por qué eligió una muestra.

**Solución (qué cambia).** ORCA no reemplaza al auditor: cambia el orden de revisión. Cada contrato tiene un score de 0 a 100 y la lista de banderas que lo explican; el auditor abre SECOP desde el mismo dashboard.

**Gobierno (por qué confiar).**
- *Calidad antes de publicar:* 14 reglas en 6 dimensiones; el lote del 5-nov obtuvo 99,66 %. El punto débil (6,75 % de ciudades sin definir) se muestra, no se esconde.
- *Privacidad desde el diseño:* las cédulas se reemplazan por un seudónimo HMAC-SHA256 con sal secreta. Aun así se calcula P4 (523 contratistas en 3 a 13 entidades a la vez) sin ver ninguna cédula.
- *Trazable de extremo a extremo:* de la alerta se vuelve al lote, a la consulta SoQL y al contrato original.
- *Mínimo privilegio:* 6 roles × 4 capas; solo el custodio escribe; la ciudadanía ve agregados.

**Conclusiones.** El Data Office pasó de un gobierno **escrito** (entrega 2, 9/16) a un gobierno que **se ejecuta y se mide en cada lote** (13/16). Lo siguiente es operar el ciclo de retroalimentación con los auditores para medir la precisión de las alertas (meta ≥ 60 %) y recalibrar las reglas.

## Preguntas probables y respuesta corta

| Pregunta | Respuesta |
|---|---|
| ¿Una alerta significa corrupción? | No. Prioriza la revisión; la decisión es humana (política de uso aceptable, Plan §5.3) |
| ¿Por qué esos pesos? | Son la versión 1.0.0, propuesta por el Steward y aprobada por el Owner. Están en un JSON versionado precisamente para recalibrarlos con los falsos positivos sin tocar el código |
| ¿Si SECOP es público, por qué seudonimizar? | La Ley 1712 obliga a publicar; la Ley 1581 regula el tratamiento posterior. Para vigilar no necesitamos la cédula y por eso no la conservamos |
| ¿Qué pasa si la fuente trae un lote malo? | El gate lo deja en cuarentena: el mart no se actualiza y la corrida queda registrada. Decide el Steward |
| ¿Por qué Streamlit y no Power BI? | Mismo lenguaje que el pipeline, versionado en el repositorio y control de acceso con las mismas políticas en código (ArchiMate, cambios v0.1 → v1.0) |
| ¿Cómo sabemos que el linaje es real? | El notebook 04 recalcula los SHA-256 de cada eslabón; si alguien edita un archivo, la verificación falla |

## Checklist antes de presentar

- [ ] `python notebooks/orquestar_pipeline.py --sin-descarga` corre sin errores en el equipo del pitch
- [ ] `streamlit run dashboard/app.py` abierto en la pestaña Resumen con el rol *Auditor*
- [ ] Capturas de `dashboard/img/` a mano como respaldo
- [ ] Tiempos ensayados: demo ≤ 1:30 y gobierno ≥ 2:30 (es el 30 % de la nota)
