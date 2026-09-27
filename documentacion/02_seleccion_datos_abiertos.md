# 02 · Selección de datos abiertos

| | |
|---|---|
| **Solución** | ORCA v1.0 · Entrega 1 · 28-sep-2026 |
| **Evidencia reproducible** | [`notebooks/00_perfilamiento_fuente.ipynb`](../notebooks/00_perfilamiento_fuente.ipynb) (consultas a la API ejecutadas el 27-sep-2026) |

---

## 1. Criterios de selección

Se buscaron datasets que **sirvan al problema de negocio** y que, además, **permitan demostrar el gobierno del dato**, que pesa el 30 % de la nota. Un dataset "limpio y sin datos personales" facilita el análisis, pero deja poco que gobernar.

| Criterio | Peso | Qué se evalúa |
|---|---:|---|
| C1 · Relevancia para un problema real | 25 % | ¿Soporta decisiones concretas de una organización? |
| C2 · Riqueza para el gobierno del dato | 25 % | PII que obligue a clasificar, problemas de calidad medibles, varias entidades y relaciones |
| C3 · Oportunidad (frescura) | 15 % | Frecuencia de actualización y fecha del último cargue |
| C4 · Acceso automatizable | 15 % | API estable que permita ingesta programada (automatización) |
| C5 · Volumen y cobertura | 10 % | Suficiente para EDA y patrones; filtrable a un alcance manejable |
| C6 · Licencia y documentación | 10 % | Uso permitido, publicador oficial, metadatos |

## 2. Candidatos evaluados (metadatos verificados vía API de datos.gov.co, 27-sep-2026)

| ID | Dataset | Publicador | Filas | Col. | Actualización | Último cargue |
|---|---|---|---:|---:|---|---|
| `jbjy-vk9h` | **SECOP II – Contratos Electrónicos** | Colombia Compra Eficiente | 6.070.870 | 95 | Diaria | 27-sep-2026 |
| `p6dx-8zbt` | SECOP II – Procesos de Contratación | Colombia Compra Eficiente | ≈ 9,2 M | 59 | Diaria | 26-sep-2026 |
| `rpmr-utcd` | SECOP Integrado (SECOP I + II) | Colombia Compra Eficiente | ≈ 20,8 M | 22 | Diaria | 21-sep-2026 |
| `kgxf-xxbe` | Resultados únicos Saber 11 | ICFES | ≈ 7,1 M | 51 | Semestral | **23-ago-2023** |

Los cuatro tienen licencia **Creative Commons Attribution-ShareAlike 4.0**.

### Matriz de decisión (1 = bajo · 5 = alto)

| Dataset | C1 (25 %) | C2 (25 %) | C3 (15 %) | C4 (15 %) | C5 (10 %) | C6 (10 %) | **Puntaje** |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **SECOP II – Contratos** | 5 | 5 | 5 | 5 | 5 | 5 | **5,00** ✅ |
| SECOP II – Procesos | 4 | 3 | 5 | 5 | 5 | 5 | 4,25 |
| SECOP Integrado | 4 | 3 | 4 | 5 | 5 | 5 | 4,10 |
| Saber 11 | 3 | 4 | 1 | 5 | 5 | 5 | 3,65 |

**Por qué se descartan los demás como fuente principal:**
- **SECOP Integrado:** agrega SECOP I, pero con solo 22 columnas pierde lo que el gobierno necesita trabajar (supervisores, ordenadores del gasto, fuentes de recursos, días adicionados, estado de ejecución).
- **Saber 11:** tiene PII sensible (fecha de nacimiento, condiciones socioeconómicas), pero su último cargue es de 2023 y cubre 2010–2022. Falla en *oportunidad*, que es una de las 6 dimensiones de calidad exigidas.
- **SECOP II – Procesos** no se descarta: entra como **fuente complementaria** porque es la que permite medir competencia (número de oferentes).

## 3. Datasets seleccionados

| Código | Dataset | Rol en ORCA | Llave de integración |
|---|---|---|---|
| **DS-01** | SECOP II – Contratos Electrónicos (`jbjy-vk9h`) | **Principal**: hechos de contratación | `id_contrato` (única) |
| **DS-02** | SECOP II – Procesos de Contratación (`p6dx-8zbt`) | Complementario: competencia (ofertas, proveedores invitados) | `DS-01.proceso_de_compra` = `DS-02.id_del_portafolio` |
| **DS-03** | DIVIPOLA – Códigos de municipios (`gdxc-w37w`, DANE, 1.122 filas, corte 30-dic-2024) | **Dato de referencia** (maestro) para normalizar municipios | Nombre normalizado de municipio → código DANE |

DS-03 resuelve un problema real de DS-01: la ciudad viene como **texto libre** (con "No Definido" en 20.706 contratos). Tener un maestro de referencia es, en sí mismo, una práctica de gobierno (dominio *Datos maestros y de referencia* de DAMA-DMBOK).

## 4. Alcance del caso

| Filtro | Valor | Justificación |
|---|---|---|
| Territorio | `departamento = 'Antioquia'` | Jurisdicción de la contraloría del caso; contexto regional de la UPB |
| Periodo | `fecha_de_firma >= '2024-01-01'` | Vigencias recientes (actuaciones oportunas); incluye el ciclo electoral de 2026 |
| Orden | Se conserva todo; se **marca** `orden = 'Territorial'` como universo de vigilancia | Nacional (113.333 contratos) y Corporaciones Autónomas (2.115) los vigila la CGR. Se conservan como comparación, fuera del score. |

**Tamaño del alcance:** 302.507 contratos · $56,4 billones COP · 565 entidades · 83.932 proveedores. Territorial: 187.059 contratos ($45,8 billones).

## 5. Estructura de DS-01 (95 campos agrupados)

| Grupo | Campos principales | Uso en ORCA |
|---|---|---|
| Identificación | `id_contrato`, `referencia_del_contrato`, `proceso_de_compra`, `urlproceso` | Llave, cruce con DS-02, enlace a la evidencia |
| Entidad | `nombre_entidad`, `nit_entidad`, `codigo_entidad`, `departamento`, `ciudad`, `orden`, `sector`, `rama` | Dimensión entidad; alcance de vigilancia |
| Contratación | `modalidad_de_contratacion`, `justificacion_modalidad_de`, `tipo_de_contrato`, `objeto_del_contrato`, `codigo_de_categoria_principal` | Banderas de modalidad y objeto |
| Proveedor | `tipodocproveedor`, `documento_proveedor`, `proveedor_adjudicado`, `es_pyme`, `es_grupo` | Concentración y simultaneidad (**PII** si es persona natural) |
| Fechas | `fecha_de_firma`, `fecha_de_inicio_del_contrato`, `fecha_de_fin_del_contrato`, `dias_adicionados` | Ventanas atípicas, prórrogas |
| Valores | `valor_del_contrato`, `valor_pagado`, `valor_facturado`, `valor_pendiente_de_ejecucion` | Atípicos, ejecución |
| Fuentes de recursos | `sistema_general_de_participaciones`, `sistema_general_de_regal_as`, `recursos_propios`, … | Contexto (regalías = mayor riesgo) |
| Personas del contrato | `nombre_representante_legal`, `identificaci_n_representante_legal`, `nombre_supervisor`, `n_mero_de_documento_supervisor`, `nombre_ordenador_del_gasto`, `n_mero_de_documento_ordenador_del_gasto` | **PII**: se seudonimizan |
| Bancarios | `nombre_del_banco`, `tipo_de_cuenta`, `n_mero_de_cuenta` | Se **excluyen** (100 % "No definido" en la muestra y sin finalidad legítima) |

## 6. Datos personales detectados (insumo para la clasificación)

Porcentaje de registros con valor real en los campos PII (muestra de 5.000 contratos de Antioquia, 2025–2026):

| Campo | % con valor real | Clasificación preliminar |
|---|---:|---|
| `documento_proveedor` (81,5 % son cédulas) | 99,6 % | **PII**: seudonimizar cuando `tipodocproveedor` ≠ NIT |
| `proveedor_adjudicado` (nombre) | 100 % | **PII** si es persona natural |
| `nombre_representante_legal` | 99,9 % | **PII** |
| `identificaci_n_representante_legal` | 18,0 % | **PII** (el resto: "Sin Descripcion") |
| `nombre_supervisor` / `n_mero_de_documento_supervisor` | 76,7 % | **PII** (servidor público) |
| `nombre_ordenador_del_gasto` / documento | 79,7 % | **PII** (servidor público) |
| `n_mero_de_cuenta` | 0,0 % | Excluir |

> **Tensión que el Plan de Gobierno debe resolver:** el dato es **público** en la fuente (Ley 1712 de 2014, transparencia), pero la **reutilización** por parte de la contraloría es un nuevo tratamiento, sujeto a la Ley 1581 de 2012 (finalidad, circulación restringida, seguridad). Decisión preliminar: la capa *raw* se conserva íntegra y con acceso restringido para la trazabilidad legal; las capas *curated* y *mart* solo tienen seudónimos (hash con sal). El dashboard nunca muestra una cédula.

Clasificación preliminar de los activos derivados: *raw* = **Confidencial** (contiene PII en claro) · *curated* = **Interno** · *mart* de riesgo = **Confidencial**, porque las alertas previas a una auditoría no deben divulgarse · indicadores agregados = **Público**.

## 7. Hallazgos iniciales de calidad (se formalizan como reglas en la Entrega 2)

| Dimensión | Regla observada | Registros afectados |
|---|---|---:|
| Completitud | `fecha_de_firma` nula (Antioquia, todo el histórico) | 40.638 |
| Completitud | Nulos disfrazados: "No definido", "Sin Descripcion" en campos de personas y bancos | ver §6 |
| Validez | `ciudad = 'No Definido'` (alcance 2024+) | 20.706 |
| Exactitud | `valor_del_contrato = 0` | 2.848 |
| Exactitud | `valor_del_contrato` > $100.000 millones (candidatos a error de digitación) | 47 |
| Consistencia | `fecha_de_fin` < `fecha_de_inicio` | 187 |
| Consistencia | Nombres de entidad no normalizados (p. ej. `MUNICIPIO DE ENVIGADO*`) | por medir |
| Integridad referencial | Contratos cuyo `proceso_de_compra` no aparece en DS-02 (en la muestra, 2 de 3 no cruzaron) | por medir |
| Unicidad | `id_contrato` duplicado | 0 en la muestra |
| Oportunidad | Último cargue de DS-01 | 27-sep-2026 (≤ 24 h) ✅ |
| Oportunidad (metadato) | `ultima_actualizacion` vacío; `:updated_at` se reescribe para todo el dataset cada día | 97,8 % vacío / 576.686 registros con la misma marca |

## 8. Estrategia de ingesta (se implementa en la Entrega 2)

- **API SODA** de Socrata: `https://www.datos.gov.co/resource/jbjy-vk9h.json` con filtros SoQL en el servidor.
- **Paginación:** `$limit=50000` + `$offset`, con `$order=:id` para que las páginas sean estables.
- **Incremental, con un hallazgo que cambia el diseño:** se probaron dos marcas de agua y ninguna sirve.
  - El campo del negocio `ultima_actualizacion` viene vacío en el 97,8 % de los registros.
  - El campo de sistema `:updated_at` sí funciona, pero el publicador **recarga el dataset completo cada día**: 576.686 registros de Antioquia tenían la misma marca (`2026-09-27T03:05:29Z`). Filtrar por `:updated_at` traería todo, siempre.

  **Diseño adoptado:** se re-extrae una **ventana móvil** (contratos firmados en los últimos 120 días, más los que no están en estado terminal) y se detectan cambios con un **hash por registro** (`id_contrato` + campos de negocio). Una vez por semana se refresca el alcance completo para conciliar. Este hallazgo va al catálogo como metadato operativo de la fuente.
- **Zonas de almacenamiento:** `raw` (JSON → Parquet, inmutable, particionado por fecha de corte) → `curated` (limpio, tipado, PII seudonimizada) → `mart` (agregados de riesgo).
- **Linaje:** cada lote registra consulta SoQL, marca de agua, número de filas, hash del archivo y score de calidad.

## 9. Banderas rojas preliminares (hipótesis para el EDA)

| # | Bandera roja | Campos | Pregunta (doc. 01) |
|---|---|---|---|
| BR1 | Contratación directa por encima del patrón histórico de la entidad | `modalidad_de_contratacion`, `nombre_entidad`, `fecha_de_firma` | P1 |
| BR2 | Firma en ventana pre-Ley de Garantías o en los últimos días de la vigencia | `fecha_de_firma`, `modalidad_de_contratacion` | P2 |
| BR3 | Concentración proveedor–entidad (% del valor de la entidad) | `documento_proveedor`, `nombre_entidad`, `valor_del_contrato` | P3 |
| BR4 | Persona natural con contratos simultáneos en varias entidades | `documento_proveedor`, fechas de inicio y fin | P4 |
| BR5 | Valor atípico para su tipo y modalidad (IQR / z-robusto) | `valor_del_contrato`, `tipo_de_contrato` | P5 |
| BR6 | Proceso competitivo con un solo oferente | DS-02 `respuestas_al_procedimiento` | P6 |
| BR7 | Prórrogas excesivas | `dias_adicionados`, duración | — |
| BR8 | Fraccionamiento: varios contratos del mismo par entidad–proveedor en pocos días | par + `fecha_de_firma` + `objeto_del_contrato` | P3 |

> Las banderas rojas **no son hallazgos**: solo indican qué revisar primero. Así lo dice el principio "la máquina mide, la persona decide".
