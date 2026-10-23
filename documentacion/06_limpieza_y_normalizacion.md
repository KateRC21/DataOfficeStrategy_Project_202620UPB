# 06 · Pipeline de datos ORCA

Ingesta, transformación, calidad, análisis exploratorio y automatización.


|                      |                                                                                                                          |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Solución**         | ORCA · corte de evidencia 23-oct-2026                                                                                    |
| **Carpeta revisada** | `[notebooks/](../notebooks/)`                                                                                            |
| **Capas**            | `data/raw` → `data/curated` → `dashboard/eda`                                                                            |
| **Este documento**   | Describe lo que el código hace hoy. Donde un notebook, el README o un workflow dicen otra cosa, se señala la diferencia. |


---



## 1. Mapa de la carpeta `notebooks`

Los módulos ejecutables están en `notebooks/`.


| Archivo                                                                                                 | Etapa                    | Qué hace                                       | Quién lo llama                               |
| ------------------------------------------------------------------------------------------------------- | ------------------------ | ---------------------------------------------- | -------------------------------------------- |
| `[00_perfilamiento_fuente.ipynb](../notebooks/00_perfilamiento_fuente.ipynb)`                           | Ingesta (decisión)       | Agregados SoQL. No descarga el lote            | Se ejecuta solo                              |
| `[descargar_fuentes.py](../notebooks/descargar_fuentes.py)`                                             | Ingesta (lote)           | Baja DS-01, DS-02 y DS-03 a Parquet            | Consola. El notebook de limpieza no lo llama |
| `[limpieza.py](../notebooks/limpieza.py)`                                                               | Transformación           | `raw` → `curated` de DS-01                     | El notebook de limpieza y la consola         |
| `[calidad.py](../notebooks/calidad.py)`                                                                 | Calidad                  | 14 reglas y quality gate                       | Solo `limpieza.procesar`                     |
| `[01_limpieza_normalizacion_ORCA_final.ipynb](../notebooks/01_limpieza_normalizacion_ORCA_final.ipynb)` | Transformación y calidad | Orquesta `procesar` y deja evidencia           | Se ejecuta solo                              |
| `[02_EDA_ORCA.ipynb](../notebooks/02_EDA_ORCA.ipynb)`                                                   | EDA                      | Lee curated y escribe gráficos                 | Se ejecuta solo                              |
| `[monitoreo_fuente.py](../notebooks/monitoreo_fuente.py)`                                               | Automatización           | Agregados diarios de frescura y calidad básica | Pensado para GitHub Actions                  |


```text
00_perfilamiento_fuente.ipynb     consultas SoQL (no persiste el lote)
        │
descargar_fuentes.py
        │
        ├── data/raw/DS-01_secop2_contratos_AAAAMMDD.parquet + .manifest.json
        ├── data/raw/DS-02_secop2_procesos_AAAAMMDD.parquet + .manifest.json
        └── data/raw/DS-03_divipola_municipios_AAAAMMDD.parquet + .manifest.json
                │
                │  DS-02 no entra a limpieza ni al EDA
                ▼
limpieza.py :: procesar()  ──usa──  calidad.py :: medir()
                │
                ├── data/curated/DS-01_contratos_curated.parquet
                ├── data/curated/DS-01_contratos_curated.manifest.json
                └── documentacion/calidad/reporte_calidad_DS-01.csv
                        │
                        ▼
              02_EDA_ORCA.ipynb
                        │
                        ▼
              dashboard/eda/*.png

monitoreo_fuente.py  ──aparte──  API de DS-01 (no lee raw ni curated)
                        │
                        ▼
              automatizacion/registro_ejecuciones.csv
```

`data/raw/*` y `data/curated/*` están en `.gitignore` porque el raw trae datos personales en claro.

---



## 2. Ingesta

Hay dos piezas distintas. El perfilamiento justifica la fuente. La descarga materializa el lote.

### 2.1 Perfilamiento: `00_perfilamiento_fuente.ipynb`

Consulta la API pública de datos.gov.co con agregaciones SoQL. No baja los cerca de 6 millones de contratos nacionales. 

La ingesta se realiza en `descargar_fuentes.py`.

Alcance de las consultas: `departamento = 'Antioquia'` y `fecha_de_firma >= '2024-01-01'`, el mismo filtro que después usa la descarga de DS-01.


| Sección            | Qué mide                                                                                                                                                                |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Metadatos          | Nombre, publicador, licencia, número de columnas, frecuencia y última actualización de `jbjy-vk9h` y `p6dx-8zbt`, vía `/api/views/{id}.json`                            |
| Dimensión          | Contratos, valor, entidades y proveedores distintos en Antioquia desde 2024                                                                                             |
| Modalidad          | Participación de la contratación directa                                                                                                                                |
| Ley de Garantías   | Contratos y proporción de directa por mes, de enero de 2025 a septiembre de 2026                                                                                        |
| PII                | Tipo de documento del proveedor y, en una muestra de 5.000 contratos de 2025, porcentaje con valor real en documentos, nombres, supervisor, ordenador y cuenta bancaria |
| Calidad preliminar | Conteos SoQL de firma nula, ciudad `No Definido`, valor cero, valor mayor a 100.000 millones y fin anterior al inicio                                                   |
| Cruce con procesos | Ejemplo de `proceso_de_compra` = `id_del_portafolio` para ver oferentes                                                                                                 |


Esas consultas de calidad no son el quality gate. Algunas cubren todo Antioquia (firma nula) y otras el filtro del caso. Sirvieron para diseñar las reglas de `calidad.py`.

### 2.2 Descarga del lote: `descargar_fuentes.py`

Cliente de la API SODA (`https://www.datos.gov.co/resource/{dataset}.json`). Página de 50.000 filas, orden `:id`, hasta cinco reintentos. Todo queda como texto (`string`): la zona raw no transforma.


| Código | Dataset     | Nombre de archivo     | Filtro                                                                          |
| ------ | ----------- | --------------------- | ------------------------------------------------------------------------------- |
| DS-01  | `jbjy-vk9h` | `secop2_contratos`    | `departamento='Antioquia' AND fecha_de_firma >= '2024-01-01'`                   |
| DS-02  | `p6dx-8zbt` | `secop2_procesos`     | `departamento_entidad='Antioquia' AND fecha_de_publicacion_del >= '2024-01-01'` |
| DS-03  | `gdxc-w37w` | `divipola_municipios` | Sin filtro (maestro nacional DANE)                                              |


Sin argumentos descarga DS-03, luego DS-01 y luego DS-02. Con un código descarga solo esa fuente.

```powershell
.\.venv\Scripts\python.exe notebooks\descargar_fuentes.py
.\.venv\Scripts\python.exe notebooks\descargar_fuentes.py DS-01
```

Por cada fuente escribe, en `data/raw/`:

- `<codigo>_<nombre>_<AAAAMMDD>.parquet`
- `<codigo>_<nombre>_<AAAAMMDD>.manifest.json` con dataset, filtro SoQL, filas, columnas, inicio y fin UTC, SHA-256 y clasificación.

DS-01 y DS-02 se clasifican como confidenciales (PII en claro). DS-03 se clasifica como público.

El corte usado por el resto del pipeline tiene **291.719 filas y 95 columnas** en DS-01.

### 2.3 Qué sigue y qué se queda en raw

`limpieza.py` y el EDA consumen DS-01. La homologación territorial consume DS-03, filtrado a Antioquia (`cod_dpto = 05`). DS-02 queda descargado y no se cruza en ningún notebook posterior. El perfilamiento solo muestra un ejemplo de tres filas. La pregunta de competencia (proceso con un único oferente) sigue abierta.

---



## 3. Transformación



### 3.1 Cómo se integran el notebook y `limpieza.py`

`[01_limpieza_normalizacion_ORCA_final.ipynb](../notebooks/01_limpieza_normalizacion_ORCA_final.ipynb)` no reimplementa el pipeline. Agrega `notebooks/` a `sys.path` e importa solo `procesar`:

```python
resultado = procesar(
    contratos=str(RAW / "DS-01_*.parquet"),
    divipola=str(RAW / "DS-03_*.parquet"),
    salida=str(CURATED),
    reporte=str(CALIDAD),
    corte="2026-10-23",
)
```

Si la ruta trae `*`, se usa el archivo más reciente. La misma función es el punto de entrada por consola:

```powershell
.\.venv\Scripts\python.exe notebooks\limpieza.py --contratos data/raw/DS-01_*.parquet --divipola data/raw/DS-03_*.parquet
```

La sal del seudónimo sale de `ORCA_SALT`. Si no está definida, se usa una sal de desarrollo y el manifiesto lo deja escrito. En la corrida del 23-oct-2026 se usó la sal de desarrollo.

Todas las funciones de `limpieza.py` participan en `procesar`. No hay funciones muertas. `calidad.py` no se importa desde el notebook: el cuaderno muestra el diccionario devuelto y el CSV escrito.


| Función                                                                                     | Rol                                                     |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| `leer`                                                                                      | Parquet o CSV más reciente; todo a texto                |
| `a_nulos`                                                                                   | Nulos disfrazados, también sobre DIVIPOLA               |
| `tipar`                                                                                     | Fechas, montos y booleanos                              |
| `nit_9_digitos`                                                                             | NIT de entidad a 9 dígitos, antes de unificar el nombre |
| `normalizar_entidad`                                                                        | Un nombre canónico por NIT                              |
| `sin_tildes` / `asignar_municipio`                                                          | Cruce con el maestro de Antioquia                       |
| `calidad.medir`                                                                             | Quality gate                                            |
| `seudonimo` / `seudonimizar`                                                                | HMAC-SHA256 de documentos                               |
| `conjunto_sensible` / `enmascarar_texto` / `retirar_coincidencias_exactas` / `pii_en_claro` | Protección y verificación de PII                        |


El notebook, además, hace inventario de `DS-*.parquet`, tablas de resumen, cobertura DIVIPOLA y tres pruebas que no reescriben el parquet. `numpy` y el módulo `glob` se importan en la primera celda y no se usan.

### 3.2 Orden real de `procesar`

La calidad no se mide sobre el archivo crudo ni sobre la salida final. Se mide después de nulos, tipado, nombre de entidad y municipio, y antes de quitar duplicados, crear banderas, seudonimizar y enmascarar.

1. Leer DS-01.
2. Crear en blanco cualquier columna de `REQUERIDAS` que la API haya omitido por venir vacía en todo el lote.
3. Nulos disfrazados y tipado.
4. Dejar `nit_entidad` en 9 dígitos, sin dígito de verificación.
5. Unificar `nombre_entidad` por ese NIT ya estandarizado.
6. Leer DS-03, aplicar nulos disfrazados y asignar municipio.
7. Medir calidad con la fecha de corte.
8. Eliminar duplicados de `id_contrato` y conservar la última aparición.
9. Crear banderas.
10. Seudonimizar y separar proveedor organización de persona natural.
11. Eliminar PII, campos sin finalidad y columnas vacías al 99 % o más.
12. Construir el conjunto sensible con el lote anterior a la seudonimización.
13. Enmascarar documentos numéricos en texto libre.
14. Reemplazar por `[PII]` las celdas cuyo valor completo está en el conjunto sensible.
15. Contar la PII que sigue en claro y escribir parquet, CSV de reglas y manifiesto.



### 3.3 Nulos, tipos y nombre de entidad

Tras recortar espacios, estos textos pasan a nulo: vacío, `no definido`, `no definida`, `sin descripcion`, `sin descripción`, `no aplica`, `n/a`, `na`, `null`.


| Patrón                                                                                                                                                                                   | Tipo de salida                    |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------- |
| Empieza por `fecha_` o se llama `ultima_actualizacion`                                                                                                                                   | Fecha ISO-8601, sin zona horaria  |
| Empieza por `valor_`, `saldo_`, `presupuesto_general`, `sistema_general`, `recursos_` o `dias_adicionados`                                                                               | `Float64`                         |
| `es_grupo`, `es_pyme`, `habilita_pago_adelantado`, `liquidaci_n`, `obligaci_n_ambiental`, `obligaciones_postconsumo`, `reversion`, `espostconflicto`, `el_contrato_puede_ser_prorrogado` | `si` / `sí` verdadero, `no` falso |
| `estado_contrato`                                                                                                                                                                        | Primera letra en mayúscula        |


`nombre_entidad` pierde asteriscos o barras finales y espacios repetidos. Para cada `nit_entidad` se elige el nombre limpio más frecuente; si hay empate, el más largo. En el corte, después de unificar por el NIT de 9 dígitos, se reescribieron **33.945** nombres.

### 3.4 Municipio

DS-03 se restringe a `cod_dpto = 05`. La clave es el nombre sin tildes, en mayúsculas y con espacios colapsados. Alias aplicados a `ciudad`:


| Texto normalizado    | Se busca como          |
| -------------------- | ---------------------- |
| DON MATIAS           | DONMATIAS              |
| SANTAFE DE ANTIOQUIA | SANTA FE DE ANTIOQUIA  |
| SAN VICENTE          | SAN VICENTE FERRER     |
| SAN ANDRES           | SAN ANDRES DE CUERQUIA |


`SAN PEDRO` no se asigna: es ambiguo. El texto original permanece en `ciudad`. El maestro aporta `cod_municipio` y `municipio`.

Cobertura sobre todas las filas curated: **271.395 / 291.719 = 93,03 %**. La regla V3 usa otro denominador: solo ciudades no nulas (272.024), de las cuales 629 no están en el maestro (99,77 %).

### 3.5 Duplicados y banderas que sí se guardan

Duplicados de `id_contrato` eliminados en este corte: **0**. Las anomalías no borran filas.


| Columna en curated           | Condición                                       |
| ---------------------------- | ----------------------------------------------- |
| `es_contratacion_directa`    | La modalidad empieza por «contratación directa» |
| `flag_valor_cero`            | Valor igual a cero                              |
| `flag_valor_atipico`         | Valor mayor a 100.000 millones                  |
| `flag_fechas_inconsistentes` | Fin anterior al inicio                          |
| `flag_sin_fecha_firma`       | Firma nula                                      |


El notebook cuenta otras tres condiciones sobre una copia en memoria y no las escribe: inicio anterior a la firma (**11**), prórroga negativa (**0**) y prórroga mayor a 3.650 días (**7**). La regla K2 (firma posterior al fin, **262** filas) entra al puntaje y tampoco queda como columna.

### 3.6 Seudonimización, columnas que salen y texto libre

Si `tipodocproveedor` es NIT, se conservan `proveedor_nit` y `proveedor_nombre`, y `proveedor_es_persona_natural` queda en falso. Si no es NIT, esos dos campos quedan nulos y la persona solo viaja como seudónimo.

Cada documento se reduce a letras y dígitos en mayúscula y se hashea con HMAC-SHA256. Se guardan 16 caracteres hexadecimales en `proveedor_id`, `representante_legal_id`, `supervisor_id`, `ordenador_gasto_id` y `ordenador_pago_id`.

Después se eliminan documentos y nombres en claro, tipo y código de proveedor, datos bancarios, nacionalidad, domicilio y género del representante, tipos de documento de supervisor y ordenadores, y la dirección de ejecución. Una columna que no esté protegida (`id_contrato`, `nit_entidad`, `fecha_de_firma`, `valor_del_contrato`, `modalidad_de_contratacion`) y que tenga 99 % o más de nulos también sale. En este corte salieron 11 columnas de acuerdos, ambiente, reversión y posconsumo.

Balance: **95 columnas de origen, 76 en curated**. El manifiesto lista las 23 de PII o sin finalidad y las 11 vacías.

En `objeto_del_contrato`, `descripcion_del_proceso`, `justificacion_modalidad_de` y `condiciones_de_entrega`, toda secuencia de cinco o más dígitos que pertenezca al conjunto sensible se reemplaza por `[DOC]`. Se modificaron **24** celdas. El conjunto sensible excluye NIT y nombres de organizaciones, porque son públicos.

El conteo de PII en claro busca coincidencia exacta de la celda en `proveedor_nombre`, `referencia_del_contrato` y los cuatro textos libres. No recorre el resto de columnas y no detecta un nombre incrustado en una frase. Esas coincidencias exactas se reemplazan por `[PII]` antes de contar. En el corte se reemplazaron **34** celdas y el residual quedó en **0**.

### 3.7 NIT de entidad

`nit_9_digitos` corre dentro de `procesar`, sobre `nit_entidad`, antes de `normalizar_entidad`. Conserva 9 dígitos y, si hay 10 o más, quita el último. Menos de 9 dígitos quedan nulos. El valor sigue siendo texto. No se aplica a documentos de persona natural: esos se seudonimizan.

En el corte, 24.215 NIT tenían 10 dígitos y quedaron en 9. Ninguno quedó nulo por formato. Las 291.719 filas de curated tienen `nit_entidad` de 9 dígitos. Unificar por ese NIT reescribió 33.945 nombres, 1.187 más que cuando el dígito de verificación partía la misma entidad en dos grupos.

### 3.8 Productos

- `data/curated/DS-01_contratos_curated.parquet`
- `data/curated/DS-01_contratos_curated.manifest.json` (SHA-256, conteos, decisión de calidad, sal usada, clasificación «Interno»)
- `documentacion/calidad/reporte_calidad_DS-01.csv`

---



## 4. Calidad



### 4.1 Reglas formales

`calidad.py` define seis dimensiones. El puntaje de una dimensión es el promedio de sus reglas. El puntaje del lote es el promedio de las seis. Umbral: **95 %**. Decisión `PUBLICAR` o `CUARENTENA`. Un nulo en la serie de la regla significa «no aplica» y no entra al denominador. Las reglas están propuestas para aprobación del Data Steward.


| Id  | Dimensión    | Regla                                                              |
| --- | ------------ | ------------------------------------------------------------------ |
| C1  | Completitud  | `fecha_de_firma` presente                                          |
| C2  | Completitud  | `valor_del_contrato` presente                                      |
| C3  | Completitud  | `documento_proveedor` presente                                     |
| C4  | Completitud  | `ciudad` definida                                                  |
| C5  | Completitud  | `modalidad_de_contratacion` presente                               |
| V1  | Validez      | Valor no negativo                                                  |
| V2  | Validez      | Firma no posterior al corte                                        |
| V3  | Validez      | Ciudad no nula reconocida en DIVIPOLA Antioquia                    |
| E1  | Exactitud    | Valor mayor que cero                                               |
| E2  | Exactitud    | Valor ≤ 100.000 millones                                           |
| K1  | Consistencia | Fin no anterior al inicio                                          |
| K2  | Consistencia | Firma no posterior al fin                                          |
| U1  | Unicidad     | `id_contrato` sin duplicados                                       |
| O1  | Oportunidad  | La firma más reciente cae dentro de los 7 días anteriores al corte |


O1 no se evalúa fila a fila. Es un solo booleano del lote, guardado en la primera fila. El reporte muestra 1 evaluado.

`VALOR_ATIPICO` (100.000 millones) lo reutiliza `limpieza.py` para `flag_valor_atipico`. Esa bandera se crea después de medir, así que no altera el puntaje.

### 4.2 Resultado del corte 23-oct-2026

Medido sobre 291.719 filas, antes de deduplicar. En este lote no había duplicados, así que el orden no cambió el puntaje.


| Regla                              | Evaluados | Fallan | Cumplimiento |
| ---------------------------------- | --------- | ------ | ------------ |
| C1 firma presente                  | 291.719   | 0      | 100 %        |
| C2 valor presente                  | 291.719   | 0      | 100 %        |
| C3 documento de proveedor          | 291.719   | 554    | 99,81 %      |
| C4 ciudad definida                 | 291.719   | 19.695 | 93,25 %      |
| C5 modalidad presente              | 291.719   | 62     | 99,98 %      |
| V1 valor no negativo               | 291.719   | 0      | 100 %        |
| V2 firma no futura                 | 291.719   | 0      | 100 %        |
| V3 ciudad en DIVIPOLA              | 272.024   | 629    | 99,77 %      |
| E1 valor mayor que cero            | 291.719   | 2.809  | 99,04 %      |
| E2 sin atípico de 100.000 millones | 291.719   | 47     | 99,98 %      |
| K1 fin no anterior al inicio       | 289.126   | 85     | 99,97 %      |
| K2 firma no posterior al fin       | 291.718   | 262    | 99,91 %      |
| U1 contrato único                  | 291.719   | 0      | 100 %        |
| O1 firma reciente                  | 1         | 0      | 100 %        |



| Dimensión    | Cumplimiento           |
| ------------ | ---------------------- |
| Completitud  | 98,61 %                |
| Validez      | 99,92 %                |
| Exactitud    | 99,51 %                |
| Consistencia | 99,94 %                |
| Unicidad     | 100 %                  |
| Oportunidad  | 100 %                  |
| **Lote**     | **99,66 % → PUBLICAR** |


Las 34 coincidencias exactas de PII se reemplazan por `[PII]` y no forman parte de las catorce reglas. Después del reemplazo el residual del corte es 0.

### 4.3 Tres mediciones distintas


| Medición                       | Dónde                                                      | Para qué sirve                                                           |
| ------------------------------ | ---------------------------------------------------------- | ------------------------------------------------------------------------ |
| Conteos SoQL del perfilamiento | `00_perfilamiento_fuente.ipynb`                            | Descubrir problemas antes de tener el lote local. No es el gate          |
| `calidad.medir`                | Dentro de `procesar`, sobre el lote ya tipado y homologado | Decisión `PUBLICAR` / `CUARENTENA`                                       |
| Banderas y recuentos del EDA   | `02_EDA_ORCA.ipynb` sobre curated                          | Cuántos casos quedan etiquetados para priorizar. No recalcula el puntaje |


El EDA vuelve a contar las banderas persistidas: 2.809 valores cero (0,96 %), 47 atípicos de la regla estricta, 85 fechas inconsistentes (0,03 %) y 0 sin fecha de firma. Esas cifras coinciden con E1, E2, K1 y C1.

---



## 5. Análisis exploratorio



### 5.1 Entrada y preparación

`[02_EDA_ORCA.ipynb](../notebooks/02_EDA_ORCA.ipynb)` lee el Parquet de contratos en `data/curated/` (prefiere un nombre con `DS-01` o `contratos`). No vuelve a limpiar, no llama a `limpieza.py` y no abre DS-02 ni DS-03.

Crea `_fecha_eda` y `_valor_eda` a partir de `fecha_de_firma` y `valor_del_contrato`. Las columnas analíticas se resuelven por el primer nombre que exista:


| Variable  | Orden de búsqueda                      | Columna que usa curated                                       |
| --------- | -------------------------------------- | ------------------------------------------------------------- |
| Fecha     | `fecha_de_firma`, `fecha_firma`        | `fecha_de_firma`                                              |
| Valor     | `valor_del_contrato`, `valor_contrato` | `valor_del_contrato`                                          |
| Modalidad | `modalidad_de_contratacion`            | esa                                                           |
| Municipio | `ciudad`, `municipio`                  | `ciudad`, el texto original, no el nombre DANE                |
| Entidad   | `nombre_entidad`                       | el nombre ya unificado                                        |
| Proveedor | `proveedor_id`, `proveedor_nombre`     | `proveedor_id`, el seudónimo, no el nombre de la organización |
| Contrato  | `id_contrato`                          | esa                                                           |


El gráfico territorial no usa `cod_municipio`. Una misma ciudad con variantes de escritura que el cruce DIVIPOLA ya resolvió puede seguir partida en el EDA. El ranking de proveedores mezcla organizaciones y personas naturales bajo el hash, y deja fuera del nombre visible a quien sí es NIT (`proveedor_nombre`).

`numpy` y `glob` se importan y no se usan. Las figuras se guardan en `dashboard/eda/`.

### 5.2 Qué analiza


| Sección             | Operación                                                                                     | Salida                       |
| ------------------- | --------------------------------------------------------------------------------------------- | ---------------------------- |
| Perfil              | Tipo, nulos y únicos; muestra las 20 columnas con más nulos                                   | Tabla                        |
| Tiempo              | Contratos y valor por mes de firma                                                            | `01_evolucion_contratos.png` |
| Modalidad           | Contratos y valor; gráfico de las 10 con más contratos                                        | `02_modalidades.png`         |
| Territorio          | Igual, agrupando por `ciudad`                                                                 | `03_municipios.png`          |
| Entidad             | Igual, por `nombre_entidad`                                                                   | `04_entidades.png`           |
| Proveedor           | Top por número de contratos entre filas con `proveedor_id`; participación de los 10 primeros  | `05_proveedores.png`         |
| Atípicos IQR        | Límite `Q3 + 1,5 × IQR` sobre valores ≥ 0. Señal exploratoria, distinta de los 47 casos de E2 | Tabla de los 20 mayores      |
| Banderas            | Conteo de las cuatro banderas de `limpieza.py`                                                | Tabla                        |
| Entidad × proveedor | Pares ordenados por número de contratos y valor acumulado                                     | Top 20                       |




### 5.3 Hallazgos escritos en el notebook

Estas cifras son la lectura del propio cuaderno sobre el curated del corte. Sirven para priorizar revisión. No son evidencia de irregularidad.

1. **Territorio y entidad.** Medellín concentra cerca del **45,9 % de los contratos y el 63,5 % del valor**. El Distrito Especial de Ciencia, Tecnología e Innovación de Medellín concentra cerca del **26,6 % del valor** con alrededor del **2,2 % de los contratos**. Volumen y exposición económica no coinciden.
2. **Modalidad.** Contratación directa y contratación directa con ofertas suman cerca del **84,5 % de los contratos y el 67,3 % del valor**.
3. **Entidades de mayor volumen de contratos.** El cuaderno destaca ITM, Instituto de Deportes y Recreación de Medellín y SENA Regional Antioquia. En el cruce entidad–proveedor, una relación con pocos contratos puede acumular más valor que una relación frecuente.
4. **Señales de valor y de tiempo.** **29.379 contratos (10,07 %)** superan el límite IQR. La regla estricta marca **47**. Hay **2.809** valores cero y **85** inconsistencias de fin anterior al inicio. Enero de 2026 concentra **48.964** contratos: el pico es una señal para contextualizar, no una anomalía cerrada.
5. **Variables candidatas al ranking.** Modalidad, valor, municipio, entidad, proveedor, número de contratos, valor acumulado del par entidad–proveedor, comportamiento temporal, valores cero, atípicos e inconsistencias de fechas.

El tablero de `dashboard/` todavía no existe como aplicación. `dashboard/README.md` lo deja para la entrega final y prevé que consuma una zona `mart`, que este pipeline aún no construye. Hoy `dashboard/eda/` solo guarda los cinco PNG del EDA.

---



## 6. Automatización



### 6.1 Qué está implementado

`[monitoreo_fuente.py](../notebooks/monitoreo_fuente.py)` no descarga microdatos y no lee `data/raw` ni `data/curated`. Hace cuatro agregados SoQL de DS-01 con el mismo filtro de Antioquia desde 2024:


| Indicador                | Consulta                                               |
| ------------------------ | ------------------------------------------------------ |
| `total_contratos`        | `count(*)`                                             |
| `ultima_fecha_firma`     | `max(fecha_de_firma)`, primeros 10 caracteres          |
| `pct_valor_cero`         | proporción con `valor_del_contrato = 0`                |
| `pct_ciudad_no_definida` | proporción con `ciudad = 'No Definido'`                |
| `estado`                 | `OK` si el total es mayor que cero; si no, `SIN DATOS` |
| `fecha_utc`              | instante de la ejecución                               |


Agrega una fila a `automatizacion/registro_ejecuciones.csv` e imprime una tabla Markdown. `[.github/workflows/monitoreo-fuente.yml](../.github/workflows/monitoreo-fuente.yml)` programa la consulta todos los días a las 11:00 UTC (6:00 a. m. en Colombia) y permite dispararla a mano. Instala `requests`, vuelca la tabla al resumen del job y sube el CSV como artefacto.

El workflow ejecuta `python notebooks/monitoreo_fuente.py` desde la raíz del repositorio.

### 6.2 Qué está solo enunciado

`automatizacion/README.md` lista dos mejoras del BPMN TO-BE que no tienen código:

1. Ingesta programada del lote completo (el script de descarga existe; no hay workflow que lo lance).
2. Aviso de alertas de riesgo alto por Power Automate sobre un data mart. No hay mart ni flujo exportado.

El monitoreo diario no dispara limpieza, calidad ni EDA. Si la fuente crece o cambia la última firma, alguien tiene que volver a correr `descargar_fuentes.py` y `procesar`.

---



## 7. Evidencia del corte y brechas


| Indicador                                           | Valor                                |
| --------------------------------------------------- | ------------------------------------ |
| Filas raw y curated                                 | 291.719                              |
| Columnas raw → curated                              | 95 → 76                              |
| Duplicados eliminados                               | 0                                    |
| Nombres de entidad unificados                       | 33.945                               |
| Cobertura DIVIPOLA sobre todas las filas            | 93,03 %                              |
| Celdas de texto enmascaradas                        | 24                                   |
| Celdas reemplazadas por `[PII]`                     | 34                                   |
| PII en claro después del reemplazo                  | 0                                    |
| NIT de entidad recortados a 9 dígitos               | 24.215                               |
| Quality gate                                        | 99,66 % · PUBLICAR                   |
| Sal                                                 | desarrollo (`ORCA_SALT` no definida) |
| Contratos sobre el límite IQR (EDA)                 | 29.379 (10,07 %)                     |
| Valores cero / fin anterior al inicio / atípicos E2 | 2.809 / 85 / 47                      |



| Criterio de cierre que el notebook de limpieza deja marcado                  | Estado en el código                                                       |
| ---------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| Parquet curated, gate de seis dimensiones, decisión y manifiesto con SHA-256 | Cumplido en la corrida del 23-oct-2026                                    |
| Raw fuera de Git                                                             | Cumplido por `.gitignore`                                                 |
| Homologación DIVIPOLA medida                                                 | Cumplido como métrica del notebook; `cod_municipio` sí queda en curated   |
| Inconsistencias de fechas etiquetadas                                        | Parcial: solo fin anterior al inicio queda como columna                   |
| NIT a 9 dígitos dentro del pipeline                                          | Cumplido: 291.719 NIT de 9 dígitos en curated                             |
| PII en claro = 0                                                             | Cumplido después de reemplazar 34 celdas por `[PII]`                      |
| EDA sobre curated, sin volver a limpiar                                      | Cumplido, con la salvedad de que agrupa por `ciudad` y por `proveedor_id` |
| DS-02 integrado al análisis de competencia                                   | No cumplido                                                               |
| Monitoreo diario ejecutable desde Actions                                    | El workflow llama `notebooks/monitoreo_fuente.py`                         |
| Zona `mart` y tablero de priorización                                        | No implementados                                                          |


El linaje reproducible es: nueva descarga con `notebooks/descargar_fuentes.py`, nuevo `procesar`, nuevo puntaje, nuevo manifiesto y un EDA que solo lee curated.