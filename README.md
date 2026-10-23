# ORCA · Observatorio de Riesgo en Contratación de Antioquia

**Versión 2.0 · Segunda entrega parcial · 23-oct-2026**  
Proyecto final de *Data Office Strategy · UPB*

> Un Data Office para una contraloría territorial que pasa de **auditar por muestreo y juicio experto** a **priorizar la vigilancia fiscal por riesgo**, utilizando datos abiertos de SECOP II gobernados, con calidad medida, datos personales protegidos y trazabilidad del proceso.

---

## 1. Propósito del proyecto

**ORCA** es una solución de apoyo a la decisión para la vigilancia de la contratación pública en Antioquia.

El proyecto busca identificar y priorizar **señales de riesgo** a partir de variables como:

- modalidad de contratación;
- valor contractual;
- entidad contratante;
- territorio;
- proveedor;
- concentración entidad–proveedor;
- comportamiento temporal;
- inconsistencias de fechas;
- valores cero y valores atípicos.

Las señales generadas por ORCA sirven para **priorizar casos de revisión**, no constituyen por sí mismas evidencia de irregularidad.

---

## 2. Fuentes de datos

| Código | Dataset | Rol |
|---|---|---|
| **DS-01** | SECOP II – Contratos Electrónicos (`jbjy-vk9h`) | Fuente principal |
| **DS-02** | SECOP II – Procesos de Contratación (`p6dx-8zbt`) | Fuente complementaria |
| **DS-03** | DIVIPOLA – Códigos de municipios (`gdxc-w37w`) | Fuente de referencia territorial |

Las fuentes se consultan mediante la API SODA de datos.gov.co.

El proceso de ingesta genera archivos Parquet en `data/raw/` junto con manifiestos de linaje.

---

## 3. Pipeline de datos

La arquitectura implementada sigue el flujo:

```text
SECOP II / DIVIPOLA
        │
        ▼
   INGESTA API
        │
        ▼
    data/raw/
        │
        ▼
LIMPIEZA Y NORMALIZACIÓN
        │
        ├── Tratamiento de nulos disfrazados
        ├── Tipificación de variables
        ├── Normalización de entidades
        ├── Normalización territorial
        ├── Estandarización de NIT
        ├── Validación temporal
        ├── Medición de calidad
        ├── Pseudonimización
        └── Eliminación de PII directa
        │
        ▼
  data/curated/
        │
        ▼
      EDA
        │
        ▼
dashboard/eda/
```

### Resultados del lote procesado

**DS-01 · Contratos SECOP II**

- **291.719 registros**
- **95 columnas de origen**
- **76 columnas en curated**
- **0 duplicados eliminados**
- **32.758 nombres de entidad unificados**
- **24 celdas de texto libre enmascaradas**
- NIT estandarizado a **9 dígitos**
- Calidad del lote: **99,66 %**
- Decisión del quality gate: **PUBLICAR**

---

## 4. Calidad de datos

La calidad se mide mediante reglas agrupadas en seis dimensiones:

- **Completitud**
- **Validez**
- **Exactitud**
- **Consistencia**
- **Unicidad**
- **Oportunidad**

El quality gate definido para publicación es de **95 %**.

El último lote procesado obtuvo:

| Dimensión | Resultado |
|---|---:|
| Completitud | 98,61 % |
| Validez | 99,92 % |
| Exactitud | 99,51 % |
| Consistencia | 99,94 % |
| Unicidad | 100,00 % |
| Oportunidad | 100,00 % |
| **Puntaje del lote** | **99,66 %** |

Por superar el umbral establecido, el lote fue clasificado como **PUBLICAR**.

---

## 5. EDA inicial

El análisis exploratorio se encuentra en:

```text
notebooks/02_EDA_ORCA.ipynb
```

Las visualizaciones generadas se almacenan en:

```text
dashboard/eda/
```

### Principales señales encontradas

**Concentración territorial**

Medellín concentra aproximadamente el **45,9 % de los contratos y 63,5 % del valor total** analizado.

**Modalidad de contratación**

La contratación directa y la contratación directa con ofertas representan aproximadamente el **84,5 % de los contratos y 67,3 % del valor total**.

**Concentración económica**

El Distrito Especial de Ciencia, Tecnología e Innovación de Medellín concentra aproximadamente el **26,6 % del valor total**, aunque representa alrededor del 2,2 % de los contratos.

**Valores elevados**

29.379 contratos, equivalentes aproximadamente al **10,07 %**, se encuentran por encima del límite superior estadístico del IQR. Esto representa una señal exploratoria de valor y no una evidencia automática de irregularidad.

**Señales de calidad**

Se identificaron:

- 2.809 contratos con valor cero (**0,96 %**).
- 85 inconsistencias temporales (**0,03 %**).
- 47 valores marcados como atípicos por la regla estricta de calidad.
- 0 contratos sin fecha de firma.

**Entidad–proveedor**

El análisis muestra que la frecuencia de contratación y la exposición económica no necesariamente coinciden. Por ello, ORCA debe considerar simultáneamente **número de contratos y valor acumulado** en las relaciones entidad–proveedor.

---

## 6. Variables para priorización de riesgo

A partir del EDA, las principales variables candidatas para alimentar el ranking de riesgo de ORCA son:

- modalidad de contratación;
- valor del contrato;
- entidad contratante;
- municipio;
- proveedor;
- número de contratos;
- valor acumulado por proveedor;
- concentración entidad–proveedor;
- comportamiento temporal;
- valores cero;
- valores atípicos;
- inconsistencias de fechas;
- cobertura y calidad de los datos.

Estas variables se utilizarán para generar **señales de priorización**, no para determinar automáticamente la existencia de fraude o irregularidad.

---

## 7. Automatización

El proyecto incorpora una tarea automatizada para monitorear la fuente principal DS-01.

Componentes:

```text
notebooks/monitoreo_fuente.py
.github/workflows/monitoreo_fuente.yml
automatizacion/registro_ejecuciones.csv
```

El monitoreo verifica, entre otros aspectos:

- cantidad de registros disponibles;
- fecha máxima de firma;
- presencia de valores contractuales en cero;
- registros con ciudad `No Definido`;
- fecha de ejecución.

Las ejecuciones quedan registradas para facilitar el seguimiento de la fuente y detectar cambios que puedan afectar el pipeline.

---

## 8. Gobierno de Datos

El proyecto incluye un primer borrador del **Plan de Gobierno de Datos**, integrado con la solución ORCA.

Los componentes desarrollados incluyen:

- estructura organizacional y roles;
- RACI;
- catálogo de datos;
- diccionario de datos;
- clasificación de información;
- políticas de gobierno;
- reglas de calidad;
- medición de calidad;
- linaje de datos;
- criterios de acceso y protección de información personal.

El gobierno de datos busca garantizar que la información utilizada por ORCA sea **confiable, trazable, protegida y utilizable para la toma de decisiones**.

---

## 9. Protección de datos personales

Los datos de SECOP II pueden contener información personal.
