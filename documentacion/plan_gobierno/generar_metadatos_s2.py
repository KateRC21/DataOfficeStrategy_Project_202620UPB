"""Llena la plantilla oficial S2_Plantilla_Metadatos.xlsx con la pieza 2 del Plan de Gobierno de ORCA.

Sesión 2 · Metadatos y catálogo: ficha de catálogo (hoja 1), diccionario de datos (hoja 2),
glosario (hoja 3) y autoevaluación (hoja 4), sobre la tabla principal DS-01 (SECOP II Contratos).
La plantilla trae 12 filas de diccionario y 5 de glosario: se agregan las que faltan con el mismo
estilo y se extienden las fórmulas y listas desplegables. Se agrega una columna de "Resultado medido"
(diccionario) y una de "Por qué se presta a confusión" (glosario); el resto respeta la plantilla.

Las cifras salen de perfil_ds01.json, que produce src/perfilar_diccionario.py (API de datos.gov.co,
Antioquia con fecha de firma desde 2024-01-01, corte 19-oct-2026). El resumen en Markdown está en
documentacion/05_plan_gobierno_datos.md §4; si se cambia uno, se cambia el otro.

Uso:  python documentacion/plan_gobierno/generar_metadatos_s2.py
Entrada: S2_Plantilla_Metadatos.xlsx (raíz del repositorio) · Salida: S2_Metadatos_EquipoORCA.xlsx (misma carpeta)
"""
from copy import copy
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLA = RAIZ / "S2_Plantilla_Metadatos.xlsx"
SALIDA = Path(__file__).with_name("S2_Metadatos_EquipoORCA.xlsx")

OWNER, STEWARD, CUSTODIO, ANALISTA = (
    "Luis Ángel Seoanes Ovieso",
    "Julian Amariles Taborda",
    "Katheryn Ramírez Chimá",
    "Jhon Sebastian Rayo Posada",
)

# ---------------------------------------------------------------- Hoja 0 · Datos del equipo
EQUIPO = {
    "B4": "ORCA — Observatorio de Riesgo en Contratación de Antioquia",
    "B5": f"{OWNER} · {STEWARD} · {CUSTODIO} · {ANALISTA}",
    "B6": "SECOP II – Contratos Electrónicos (jbjy-vk9h, datos.gov.co): contratos de entidades públicas de Antioquia "
          "firmados desde el 01/01/2024",
    "B7": f"Data Owner: {OWNER} · Data Steward: {STEWARD} · Custodio técnico: {CUSTODIO} · "
          f"Consumidor / Analista: {ANALISTA}",
}

# ---------------------------------------------------------------- Hoja 1 · Ficha de catálogo (D5:D21) y notas (E)
FICHA = {
    5: "SECOP II – Contratos Electrónicos de entidades de Antioquia (desde 2024)",
    6: "Un registro por cada contrato que una entidad pública con sede en Antioquia firmó electrónicamente en SECOP II: "
       "quién contrató, con quién, por cuánto, con qué modalidad y en qué fechas. ORCA lo usa para priorizar qué "
       "contratos y entidades vigilar primero según señales de riesgo (contratación directa, firmas en ventanas "
       "atípicas, concentración de proveedores, valores atípicos).",
    7: "Contraloría territorial del caso ORCA (inspirada en la Contraloría General de Antioquia) · proceso de vigilancia "
       "y control fiscal: selección de qué contratos auditar. El dato lo produce el proceso de compra pública de cada "
       "entidad y lo publica Colombia Compra Eficiente.",
    8: f"{OWNER} (Data Owner del proyecto; en la entidad del caso, el Contralor Auxiliar del sector)",
    9: f"{STEWARD} (Data Steward)",
    10: f"{CUSTODIO} (custodio técnico del pipeline de ORCA). En la fuente: Colombia Compra Eficiente, Subdirección de "
        "Información y Desarrollo Tecnológico",
    11: "https://www.datos.gov.co/d/jbjy-vk9h — SECOP II, plataforma de compra pública. Lo registran las entidades "
        "contratantes y lo publica la Agencia Nacional de Contratación Pública – Colombia Compra Eficiente",
    12: "Fuente: datos.gov.co (API https://www.datos.gov.co/resource/jbjy-vk9h.json). En ORCA: "
        "data/raw/DS-01_secop2_contratos_<AAAAMMDD>.parquet + manifiesto de linaje .manifest.json, fuera del "
        "repositorio porque contiene datos personales",
    13: "API SODA (JSON), también descargable en CSV desde el portal · ORCA lo guarda en Parquet",
    14: "Diaria",
    15: "19/10/2026",
    16: "Firmas del 01/01/2024 al 17/10/2026 · entidades públicas con sede en Antioquia de los órdenes territorial, "
        "nacional y corporaciones autónomas (la fuente completa es nacional, desde 2019)",
    17: "291.406 registros · 95 columnas (corte 19/10/2026; 20 documentadas en la hoja 2)",
    18: "Confidencial",
    19: "Sí",
    20: "Licencia Creative Commons Atribución–CompartirIgual 4.0 (CC BY-SA 4.0): uso libre citando la fuente. Como "
        "contiene datos personales, ORCA lo usa solo para vigilancia fiscal (principio de finalidad, Ley 1581 de 2012): "
        "la copia con cédulas en claro tiene acceso restringido y lo que se publica va seudonimizado.",
    21: "Cargo: Data Steward del equipo ORCA (canal del equipo en Teams) · sobre la fuente: Colombia Compra Eficiente, "
        "https://colombiacompra.gov.co",
}
NOTAS_FICHA = {
    14: "La fuente se actualiza a diario. ORCA carga a diario con una ventana móvil de 90 días por fecha de firma.",
    15: "Fecha de la última carga de la fuente. La fecha de cambio de cada registro es Desconocida: la columna "
        "ultima_actualizacion está vacía en el 97,8 % de los registros y la marca de la plataforma se reescribe a "
        "diario para todo el dataset.",
    17: "La fuente cambia hacia atrás: con el mismo filtro había 302.507 registros el 27/09/2026. Por eso cada lote se "
        "congela con su hash y su fecha de corte. En toda la fuente hay 5.643.434 registros.",
    18: "Confidencial porque contiene datos personales en claro. La fuente es pública, pero la copia de ORCA no: "
        "versión seudonimizada = Uso interno; indicadores agregados = Pública.",
    19: "80,8 % de los contratos son con personas naturales (cédula): documento y nombre del contratista, más nombres "
        "y documentos de supervisores y ordenadores del gasto. No contiene datos sensibles (salud, religión, biometría).",
}

# ---------------------------------------------------------------- Hoja 2 · Columnas que pide la plantilla
# columna original -> (nombre de negocio, tipo de dato [lista], ¿admite vacíos?, ejemplo, sensibilidad [lista])
EXTRA_DICCIONARIO = {
    "id_contrato": ("ID del contrato", "Texto", "No", "CO1.PCCNTR.9454993", "Pública"),
    "proceso_de_compra": ("ID del proceso de compra", "Texto", "No", "CO1.BDOS.10028279", "Pública"),
    "nombre_entidad": ("Entidad contratante", "Texto", "No", "ALCALDIA DE CAUCASIA", "Pública"),
    "nit_entidad": ("NIT de la entidad", "Entero", "No", "890906445", "Pública"),
    "ciudad": ("Municipio de la entidad", "Código/categoría", "No (pero trae «No Definido»)", "Envigado", "Pública"),
    "orden": ("Orden de la entidad", "Código/categoría", "No", "Territorial", "Pública"),
    "estado_contrato": ("Estado del contrato", "Código/categoría", "No", "En ejecución", "Pública"),
    "tipo_de_contrato": ("Tipo de contrato", "Código/categoría", "No", "Prestación de servicios", "Pública"),
    "modalidad_de_contratacion": ("Modalidad de contratación", "Código/categoría", "No", "Contratación directa", "Pública"),
    "justificacion_modalidad_de": ("Causal de la modalidad", "Código/categoría", "No",
                                   "Servicios profesionales y apoyo a la gestión", "Pública"),
    "fecha_de_firma": ("Fecha de firma", "Fecha", "No", "2026-05-07", "Pública"),
    "fecha_de_inicio_del_contrato": ("Fecha de inicio", "Fecha", "Sí (contratos sin iniciar)", "2026-08-27", "Pública"),
    "fecha_de_fin_del_contrato": ("Fecha de terminación", "Fecha", "No", "2026-12-31", "Pública"),
    "tipodocproveedor": ("Tipo de documento del contratista", "Código/categoría", "No", "Cédula de Ciudadanía", "Pública"),
    "documento_proveedor": ("Documento del contratista", "Texto", "No", "1234567890 (ficticio)", "Dato personal"),
    "proveedor_adjudicado": ("Contratista", "Texto", "No", "NOMBRE APELLIDO (ficticio)", "Dato personal"),
    "es_pyme": ("¿Es mipyme?", "Sí/No", "No", "No", "Pública"),
    "valor_del_contrato": ("Valor del contrato", "Entero", "No", "48954135", "Pública"),
    "dias_adicionados": ("Días de prórroga", "Entero", "No", "0", "Pública"),
    "urlproceso": ("Enlace al proceso en SECOP II", "Texto", "No",
                   "https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID=CO1.NTC.10106403…",
                   "Pública"),
}
FUENTE_COLUMNA = "SECOP II – Contratos (jbjy-vk9h), datos.gov.co"

# ---------------------------------------------------------------- Hoja 3 · Columnas que pide la plantilla
# término -> (otros nombres, columnas relacionadas)
EXTRA_GLOSARIO = {
    "Contrato": ("Contrato electrónico, acuerdo", "id_contrato"),
    "Contratación directa": ("Adjudicación directa; «a dedo» (coloquial)", "modalidad_de_contratacion, justificacion_modalidad_de"),
    "Entidad contratante": ("Entidad estatal, comprador público", "nit_entidad, nombre_entidad"),
    "Sujeto de vigilancia": ("Sujeto de control, entidad vigilada", "orden, ciudad (y la lista oficial de sujetos de control, pendiente)"),
    "Contratista persona natural": ("Proveedor persona natural, contratista individual",
                                    "tipodocproveedor, documento_proveedor, proveedor_adjudicado"),
    "Alerta temprana": ("Bandera roja, señal de riesgo", "No es columna de la fuente: la produce el score de riesgo de ORCA"),
    "Valor contratado": ("Monto contratado, valor comprometido", "valor_del_contrato, fecha_de_firma"),
}

# ---------------------------------------------------------------- Hoja 2 · Diccionario
# (original, estándar, descripción, tipo, formato/unidad, valores permitidos, obligatoria, sensibilidad,
#  regla de calidad, resultado medido 19/10/2026, uso en ORCA)
DICCIONARIO = [
    ("id_contrato", "id_contrato",
     "Identificador único que SECOP II asigna a cada contrato electrónico al crearlo. Es la llave primaria: un registro = "
     "un contrato. No cambia aunque el contrato se modifique o se ceda.",
     "Texto", "CO1.PCCNTR.<número> (ej.: CO1.PCCNTR.9454993)", "Prefijo fijo «CO1.PCCNTR.» seguido de dígitos", "Sí",
     "Público", "0 vacíos · 0 duplicados · 100 % cumple el patrón CO1.PCCNTR.<dígitos>",
     "0 vacíos · 0 duplicados en 291.406 registros", "Llave del pipeline y del linaje"),
    ("proceso_de_compra", "id_proceso_compra",
     "Identificador del proceso de selección (la convocatoria) del que salió el contrato. Un proceso puede generar varios "
     "contratos, por ejemplo cuando se adjudica por lotes, por eso se repite. Une con DS-02 Procesos (id_del_portafolio).",
     "Texto", "CO1.BDOS.<número> (ej.: CO1.BDOS.10028279)", "Prefijo fijo «CO1.BDOS.» seguido de dígitos", "Sí",
     "Público", "0 vacíos · ≥ 95 % de los valores existen en DS-02 (integridad referencial)",
     "0 vacíos · 281.650 procesos distintos; 1.782 con más de un contrato · cruce con DS-02: se mide en la Sesión 3",
     "P6 (procesos con un solo oferente)"),
    ("nombre_entidad", "nom_entidad",
     "Nombre con el que la entidad pública contratante se registró en SECOP II. Lo digita la entidad, por eso tiene "
     "variantes (asteriscos, siglas, «//») y las dependencias de un municipio (alcaldía, concejo, personería) aparecen con "
     "nombres distintos bajo un mismo NIT. Para agrupar por entidad se usa el NIT, no este nombre.",
     "Texto", "Texto libre en mayúsculas", "Texto libre; tras normalizar, un nombre por NIT", "Sí",
     "Público (persona jurídica)", "0 vacíos · 0 nombres terminados en «*» o «/» tras normalizar · cada NIT con un único nombre normalizado",
     "0 vacíos · 567 nombres para 446 NIT · 84 NIT con más de un nombre (ej.: 890905211 = Concejo, Distrito y Personería de Medellín): NO cumple",
     "P1, filtros del dashboard"),
    ("nit_entidad", "id_nit_entidad",
     "Número de Identificación Tributaria (DIAN) de la entidad contratante. Identifica a la persona jurídica, no a la "
     "dependencia: el concejo y la alcaldía de un municipio comparten NIT. Algunas entidades lo registran con el dígito de "
     "verificación pegado al final (10 dígitos) y otras sin él (9 dígitos).",
     "Número entero en la fuente; se trata como texto", "9 dígitos, sin puntos, guiones ni dígito de verificación",
     "800000000 – 999999999 (rango de entidades públicas)", "Sí", "Público (persona jurídica)",
     "0 vacíos · 100 % con 9 dígitos después de quitar el dígito de verificación · existe en la lista de sujetos de control",
     "0 vacíos · 446 NIT distintos · rango 800.003.935 – 9.020.055.758 (los de 10 dígitos traen el dígito de verificación)",
     "Agrupación por entidad (P1, P3)"),
    ("ciudad", "nom_municipio_entidad",
     "Municipio donde está registrada la sede de la entidad contratante, no el lugar donde se ejecuta el contrato. Viene "
     "sin código DANE y con tildes inconsistentes («Itagui», «Sonson»); se estandariza contra DIVIPOLA (DS-03).",
     "Texto", "Nombre del municipio", "Uno de los 125 municipios de Antioquia en DIVIPOLA · «No Definido» = la entidad no "
     "registró municipio (vacío disfrazado)", "Sí", "Público",
     "≤ 1 % de «No Definido» · 100 % cruza con un municipio de Antioquia en DIVIPOLA después de normalizar tildes",
     "119 valores distintos · 19.670 «No Definido» (6,75 %): NO cumple", "Mapa del dashboard, sujetos de control"),
    ("orden", "cod_orden_entidad",
     "Nivel del Estado al que pertenece la entidad contratante. Define quién la vigila: las del orden territorial son "
     "sujetos de control de la contraloría territorial; las del orden nacional, de la Contraloría General.",
     "Texto (categoría)", "Etiqueta", "Territorial · Nacional · Corporación Autónoma", "Sí", "Público",
     "0 vacíos · 100 % de valores en la lista permitida",
     "0 vacíos · Territorial 183.202 · Nacional 106.081 · Corporación Autónoma 2.123: cumple", "Filtro del alcance de vigilancia"),
    ("estado_contrato", "cod_estado_contrato",
     "Situación del contrato en SECOP II en la fecha de corte. Mezcla etapas del ciclo de vida con eventos: un contrato "
     "«Modificado» tuvo al menos un cambio registrado y no dice si sigue en ejecución. El valor cambia con el tiempo, por "
     "eso se lee junto con la fecha de corte del lote.",
     "Texto (categoría)", "Etiqueta; la fuente mezcla mayúsculas y minúsculas",
     "Aprobado = firmado, sin iniciar ejecución · En ejecución · Modificado = con al menos una modificación · Suspendido · "
     "cedido = el contratista lo traspasó a otro · terminado = venció el plazo, falta liquidar · Cerrado = liquidado",
     "Sí", "Público", "0 vacíos · 100 % en la lista de 7 estados (sin distinguir mayúsculas)",
     "0 vacíos · 7 estados: cumple · «terminado» y «cedido» vienen en minúscula", "Separar contratos vigentes de cerrados"),
    ("tipo_de_contrato", "cod_tipo_contrato",
     "Clase de contrato según lo que se compra (servicios, obra, suministro, arriendo…). No dice cómo se escogió al "
     "contratista: eso es la modalidad.",
     "Texto (categoría)", "Etiqueta", "21 valores. Principales: Prestación de servicios (84,7 %), Otro, Suministros, "
     "Decreto 092 de 2017 (convenios con entidades sin ánimo de lucro), Arrendamiento de inmuebles, Compraventa, Obra · "
     "«No Definido» y «No Especificado» = sin dato", "Sí", "Público",
     "0 vacíos · «No Definido» + «No Especificado» ≤ 0,1 %",
     "0 vacíos · 46 sin dato (5 «No Definido» + 41 «No Especificado») = 0,02 %: cumple", "P5 (valores atípicos por tipo)"),
    ("modalidad_de_contratacion", "cod_modalidad_contratacion",
     "Procedimiento legal con el que la entidad escogió al contratista. Es la variable central de riesgo: en la "
     "contratación directa la entidad elige sin competencia; en licitación, selección abreviada, mínima cuantía o concurso "
     "hay competencia pública. Las variantes «(con ofertas)» indican que, siendo directa o de régimen especial, se "
     "recibieron ofertas.",
     "Texto (categoría)", "Etiqueta", "14 valores agrupados en 3: sin competencia (Contratación directa, Régimen especial) · "
     "con ofertas (variantes «con ofertas») · competitiva (Licitación pública, Selección abreviada, Mínima cuantía, "
     "Concurso de méritos, Enajenación) · «No Definido» = sin dato", "Sí", "Público",
     "0 vacíos · «No Definido» ≤ 0,1 % · 100 % de valores asignados a uno de los 3 grupos",
     "62 «No Definido» (0,02 %): cumple · Contratación directa = 240.305 (82,5 %)", "P1 · bandera roja principal"),
    ("justificacion_modalidad_de", "cod_causal_modalidad",
     "Causal legal que la entidad invoca para usar la modalidad elegida, sobre todo para justificar la contratación "
     "directa. Distingue la directa habitual (servicios profesionales) de causales excepcionales como la urgencia manifiesta.",
     "Texto (categoría)", "Etiqueta; algunas llegan como códigos técnicos en inglés",
     "36 valores. Ej.: «Servicios profesionales y apoyo a la gestión» · «Urgencia manifiesta» · "
     "«Law2166of2021_Article95_SolidarityAgreements» = convenios solidarios, art. 95 Ley 2166 de 2021 · "
     "«Article30_1993» = art. 30 Ley 80 de 1993 (licitación) · «No Definido» = sin dato", "Sí", "Público",
     "0 vacíos · «No Definido» ≤ 0,1 % · 100 % de los códigos en inglés traducidos en la tabla de equivalencias",
     "43 «No Definido» (0,01 %): cumple · 357 por urgencia manifiesta", "Bandera roja «urgencia manifiesta»"),
    ("fecha_de_firma", "fec_firma_contrato",
     "Día en que el contrato quedó firmado electrónicamente por ambas partes. Define el alcance de ORCA (desde el "
     "01/01/2024) y es la fecha con la que se detectan firmas en ventanas atípicas (antes de la Ley de Garantías, fin de año).",
     "Fecha", "AAAA-MM-DD (la API agrega «T00:00:00.000»; la hora no tiene significado)",
     "Desde 2024-01-01 hasta la fecha de corte", "Sí", "Público",
     "0 vacíos · 0 fechas posteriores a la fecha de corte",
     "0 vacíos dentro del alcance (en todo Antioquia hay 5.796 sin fecha y quedan fuera) · rango 2024-01-01 a 2026-10-17 · "
     "0 en el futuro: cumple", "P2 (ventanas atípicas)"),
    ("fecha_de_inicio_del_contrato", "fec_inicio_contrato",
     "Fecha desde la que el contratista empieza a responder por sus obligaciones (acta de inicio). Puede ser posterior a "
     "la firma; si es anterior, el contrato se habría ejecutado antes de existir.",
     "Fecha", "AAAA-MM-DD", "Igual o posterior a la fecha de firma e igual o anterior a la fecha de fin",
     "Sí, salvo contratos aún sin iniciar", "Público",
     "≤ 1 % vacíos · 0 fechas de inicio anteriores a la firma · 0 posteriores a la fecha de fin",
     "2.625 vacíos (0,90 %) · 10 inician antes de la firma: NO cumple · rango 2017-10-19 a 2035-11-07",
     "Duración del contrato, P4 (simultaneidad)"),
    ("fecha_de_fin_del_contrato", "fec_fin_contrato",
     "Fecha pactada en que terminan las obligaciones del contratista según el contrato registrado en SECOP II.",
     "Fecha", "AAAA-MM-DD", "Igual o posterior a la fecha de inicio y como máximo 30 años después", "Sí", "Público",
     "0 vacíos · 0 fechas de fin anteriores al inicio · 0 a más de 30 años del inicio",
     "1 vacío · 85 terminan antes de iniciar · 6 después de 2050 (máximo: año 2925): NO cumple", "P4 (simultaneidad)"),
    ("tipodocproveedor", "cod_tipo_documento_proveedor",
     "Tipo de documento con que se identifica el contratista. Dice si es una persona natural (cédula, pasaporte, permiso "
     "de permanencia…) o una empresa (NIT), y por eso decide si el documento y el nombre del contratista son datos personales.",
     "Texto (categoría)", "Etiqueta", "Cédula de Ciudadanía (80,8 %) · NIT (18,8 %) · Cédula de Extranjería · Permiso por "
     "Protección Temporal · Pasaporte · Tarjeta de Identidad · Registro Civil · Permiso especial de permanencia · Otro · "
     "«No Definido» = sin dato", "Sí", "Público por sí sola; determina qué columnas son datos personales",
     "0 vacíos · «No Definido» ≤ 0,5 %",
     "396 «No Definido» (0,14 %): cumple · 6 Tarjeta de Identidad y 4 Registro Civil (documentos de menores de edad: revisar)",
     "Regla de seudonimización"),
    ("documento_proveedor", "id_documento_proveedor",
     "Número del documento de identidad del contratista, sin puntos: cédula si es persona, NIT si es empresa. Identifica "
     "a la persona de forma única y es lo que permite cruzar a un mismo contratista entre entidades.",
     "Texto", "Solo dígitos (puede traer ceros a la izquierda; algunos NIT traen el dígito de verificación)",
     "Dígitos · «No Definido» = sin dato", "Sí",
     "DATO PERSONAL cuando el tipo de documento no es NIT (80,8 % de los registros) → seudonimizar con hash y sal",
     "0 vacíos · «No Definido» ≤ 0,5 % · 100 % solo dígitos · NIT con 9 o 10 dígitos",
     "552 «No Definido» (0,19 %): cumple · 82.859 contratistas distintos · 650 NIT con menos de 9 dígitos: NO cumple",
     "P3, P4 (siempre seudonimizado)"),
    ("proveedor_adjudicado", "nom_proveedor",
     "Nombre o razón social del contratista al que se adjudicó el contrato, tal como aparece en su registro de SECOP II.",
     "Texto", "Texto libre", "Texto libre · «No Definido» = sin dato", "Sí",
     "DATO PERSONAL si el contratista es persona natural (nombre completo) → no se muestra en el dashboard",
     "0 vacíos · «No Definido» ≤ 0,1 % · un mismo documento tiene un solo nombre",
     "76 «No Definido» (0,03 %): cumple · 82.451 nombres para 82.859 documentos", "Dashboard (solo empresas)"),
    ("es_pyme", "ind_pyme",
     "Indica si el contratista se declaró micro, pequeña o mediana empresa en su registro de SECOP II. Es autodeclarado y "
     "nadie lo verifica; para personas naturales casi siempre viene «No».",
     "Texto (Sí/No)", "Si / No (la fuente escribe «Si» sin tilde)", "Si · No", "Sí", "Público",
     "0 vacíos · 100 % en {Si, No}", "0 vacíos · Si 35.553 (12,2 %) · No 255.853: cumple", "Contexto: participación de mipymes"),
    ("valor_del_contrato", "val_contrato",
     "Valor total del contrato registrado en SECOP II, en pesos colombianos corrientes. Un valor de $0 es legítimo solo en "
     "convenios interadministrativos sin valor. La fuente no aclara si, tras una adición, este valor es el inicial o el "
     "actualizado (ver duda 1).",
     "Número", "Pesos colombianos (COP), sin decimales ni separadores", "≥ 0 · $0 solo con causal «convenio "
     "interadministrativo (valor cero)» · > $100.000 millones requiere revisión manual", "Sí", "Público",
     "0 vacíos · 0 negativos · 0 contratos en $0 sin causal de valor cero · contratos > $100.000 millones revisados al 100 %",
     "0 vacíos · 0 negativos · 2.804 en $0 (cruce con la causal de valor cero: se mide en la Sesión 3) · 47 por encima de $100.000 millones · máximo $1,16 billones", "P5, KPI de valor contratado"),
    ("dias_adicionados", "cant_dias_adicionados",
     "Número de días que se ha extendido el plazo del contrato mediante prórrogas registradas en SECOP II. 0 = sin prórrogas.",
     "Número entero", "Días calendario", "0 a 3.650 (10 años)", "Sí", "Público",
     "0 vacíos · 0 negativos · 0 valores mayores a 3.650",
     "0 vacíos · 249.772 en 0 (85,7 %) · 7 por encima de 3.650 · máximo 730.546 días (≈ 2.000 años, error de digitación): NO cumple",
     "Bandera roja de prórrogas"),
    ("urlproceso", "url_proceso_secop",
     "Enlace a la página pública del proceso en SECOP II, donde están los documentos (estudios previos, ofertas, contrato "
     "firmado). Es lo que usa el auditor para ir de la alerta a la evidencia. Se propone el prefijo url_, que no está en la "
     "lista estándar, porque ninguno de los existentes describe un enlace.",
     "URL (en la API llega como objeto {url})", "https://community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID=CO1.NTC.<número>…",
     "Enlace a community.secop.gov.co", "Sí", "Público",
     "0 vacíos · 100 % empieza por https://community.secop.gov.co",
     "0 vacíos · prefijo: se mide en la Sesión 3 sobre el lote descargado (la API no filtra texto en columnas URL)",
     "Trazabilidad alerta → evidencia"),
]

# ---------------------------------------------------------------- Hoja 3 · Glosario
GLOSARIO = [
    ("Contrato",
     "Acuerdo firmado entre una entidad pública y un contratista, con un objeto, un valor y un plazo. No es lo mismo que el "
     "proceso de contratación: una convocatoria puede terminar en varios contratos o en ninguno. Cuando ORCA cuenta "
     "contratos, cuenta acuerdos firmados.",
     "Los auditores hablan de «procesos» y SECOP publica procesos y contratos en conjuntos de datos distintos: contar uno "
     "por otro cambia las cifras."),
    ("Contratación directa",
     "Contratación en la que la entidad escoge al contratista sin convocatoria pública abierta, apoyada en una causal que "
     "la ley permite (servicios profesionales, convenios entre entidades, urgencia manifiesta…). Para ORCA incluye la "
     "modalidad directa y el régimen especial sin ofertas; cuando se recibieron ofertas se cuenta aparte.",
     "Jurídica la entiende como modalidad legal; analítica, como «sin competencia». Según qué variantes se incluyan, el "
     "porcentaje en Antioquia va de 82,5 % (solo la modalidad directa) a 92,7 % (sumando régimen especial y variantes con ofertas)."),
    ("Entidad contratante",
     "Persona jurídica pública que firma el contrato y responde por él, identificada por su NIT. Las dependencias que "
     "comparten NIT (alcaldía, concejo y personería de un mismo municipio) son una sola entidad para contar; cada "
     "dependencia se reporta como unidad dentro de ella.",
     "SECOP la identifica por el nombre que digitó cada dependencia: en el alcance hay 567 nombres pero 446 NIT."),
    ("Sujeto de vigilancia",
     "Entidad cuyo manejo de recursos públicos le corresponde vigilar a la contraloría territorial del caso: entidades del "
     "orden territorial de Antioquia que no tienen contraloría propia. No basta con tener sede en Antioquia: las entidades "
     "nacionales con sede en Medellín las vigila la Contraloría General.",
     "Para el área de sistemas es «toda entidad de Antioquia» (ubicación); para la de vigilancia, las que le asigna la ley (competencia)."),
    ("Contratista persona natural",
     "Contratista que es un individuo y no una empresa, identificado con un documento personal (cédula, pasaporte, permiso "
     "de permanencia). Sus datos de identificación son datos personales: en ORCA solo se analizan y se muestran seudonimizados.",
     "Transparencia dice que el dato es público porque está en SECOP; protección de datos dice que reutilizarlo es un "
     "tratamiento nuevo con reglas propias."),
    ("Alerta temprana",
     "Señal que genera ORCA cuando un contrato o una entidad muestra un patrón de riesgo y merece revisión prioritaria. "
     "No es un hallazgo, no prueba ninguna irregularidad y no es la «advertencia» del control fiscal, que la ley reserva "
     "al Contralor General.",
     "Para un auditor «alerta» puede sonar a hallazgo o a advertencia formal; para el equipo de datos es solo una prioridad de revisión."),
    ("Valor contratado",
     "Suma de los valores de los contratos firmados en un periodo, en pesos corrientes. No es lo ejecutado ni lo pagado: "
     "un contrato firmado puede no haberse pagado nunca.",
     "Presupuesto y finanzas hablan de lo pagado u obligado; un tablero de contratación muestra lo comprometido."),
]

# ---------------------------------------------------------------- Hoja 4 · Autoevaluación
COLUMNA_DIFICIL = (
    "estado_contrato. Mezcla etapas del ciclo de vida (Aprobado → En ejecución → terminado → Cerrado) con eventos "
    "(Modificado, cedido, Suspendido), así que un contrato «Modificado» no dice si sigue en ejecución. Además el valor cambia "
    "con el tiempo y la fuente no publica una tabla oficial de significados: los documentamos deduciéndolos de la plataforma."
)
DUDAS = [
    "valor_del_contrato: cuando un contrato tiene adiciones, ¿SECOP publica el valor inicial o el actualizado? ¿Cómo lo "
    "documentamos si la fuente no lo dice?",
    "La fuente cambia hacia atrás (302.507 contratos el 27/09 y 291.406 el 19/10 con el mismo filtro). Para la Sesión 3, "
    "¿medimos la calidad sobre un lote congelado con su fecha de corte o sobre la API en vivo?",
    "El nombre y la cédula del contratista son públicos en SECOP por transparencia (Ley 1712). ¿Igual los marcamos como "
    "«dato personal» en el diccionario? Nosotros lo hicimos, por la Ley 1581.",
]
REPORTES = [
    "Reporte 1 (16:05): «Equipo ORCA conectado · dataset: SECOP II – Contratos Electrónicos (jbjy-vk9h), Antioquia desde 2024»",
    "Reporte 2 (16:45): «Equipo ORCA · columnas documentadas: 20»",
    "Reporte 3 (17:00): «Equipo ORCA · archivo subido · puntaje 19/20»",
]


# Respuestas a los 10 criterios de la plantilla (hoja 4, C5:C14) y qué falta cuando no es «Sí»
RESPUESTAS = [
    ("Sí", ""),
    ("Sí", "20 columnas documentadas."),
    ("Sí", ""),
    ("Sí", ""),
    ("Parcial", "El significado de algunos estados del contrato (Aprobado, Modificado) y de causales que llegan como "
                "códigos en inglés es deducido de la plataforma, no confirmado por la fuente."),
    ("Sí", "Se propone además el prefijo url_ para enlaces."),
    ("Sí", "documento_proveedor y proveedor_adjudicado (Dato personal); tipodocproveedor decide cuándo."),
    ("Sí", "Cada regla tiene su resultado medido el 19/10/2026 (columna O de la hoja 2)."),
    ("Sí", "7 términos."),
    ("Sí", ""),
]


def copiar_estilo(origen, destino):
    destino.font, destino.fill, destino.border = copy(origen.font), copy(origen.fill), copy(origen.border)
    destino.alignment, destino.number_format = copy(origen.alignment), origen.number_format


def alto(textos_y_anchos, minimo=30):
    """Altura de fila aproximada para que el texto envuelto se vea completo."""
    lineas = max(max(1, -(-len(str(t)) // max(1, int(a * 1.05)))) for t, a in textos_y_anchos)
    return max(minimo, 13.5 * lineas + 4)


def ampliar_validacion(ws, rango_viejo, rango_nuevo):
    for dv in ws.data_validations.dataValidation:
        if str(dv.sqref) == rango_viejo:
            dv.sqref = rango_nuevo  # type: ignore[assignment]
            return
    raise ValueError(f"No se encontró la validación {rango_viejo} en {ws.title}")


def hoja_equipo(wb):
    ws = wb["0_Instrucciones"]
    for celda, valor in EQUIPO.items():
        ws[celda] = valor


def hoja_ficha(wb):
    ws = wb["1_Ficha_Catalogo"]
    ws.column_dimensions["D"].width = 70
    ws.column_dimensions["E"].width = 55
    ws["E4"] = "Nota del equipo"
    copiar_estilo(ws["D4"], ws["E4"])
    for fila, valor in FICHA.items():
        c = ws.cell(fila, 4, valor)
        if valor.startswith("http"):
            c.hyperlink = valor.split(" ")[0]
        nota = NOTAS_FICHA.get(fila, "")
        n = ws.cell(fila, 5, nota)
        copiar_estilo(ws.cell(fila, 3), n)  # gris en cursiva: comentario, no dato
        ws.row_dimensions[fila].height = alto([(valor, 70), (nota, 55), (ws.cell(fila, 3).value, 46)])


def hoja_diccionario(wb):
    ws = wb["2_Diccionario"]
    n = len(DICCIONARIO)
    ultima = 5 + n
    # el pie (conteos) baja para dejar espacio a las filas nuevas
    pie = {}
    for fila in (19, 20):
        for col in range(1, 16):
            c = ws.cell(fila, col)
            if c.value is not None:
                pie[(fila, col)] = (c.value, copy(c.font))
                c.value = None
    desplazamiento = ultima + 2 - 19
    for (fila, col), (valor, fuente) in pie.items():
        if isinstance(valor, str) and valor.startswith("="):
            valor = valor.replace("B6:B17", f"B6:B{ultima}").replace("B6:N17", f"B6:N{ultima}")
        c = ws.cell(fila + desplazamiento, col, valor)
        c.font = fuente
    ampliar_validacion(ws, "F6:F17", f"F6:F{ultima}")
    ampliar_validacion(ws, "K6:K17", f"K6:K{ultima}")

    ws["O4"] = "Resultado medido (19/10/2026)"
    copiar_estilo(ws["N4"], ws["O4"])
    ws["O5"] = "Lo agregó el equipo: resultado de la regla de calidad sobre 291.406 registros (evidencia: perfil_ds01.json)"
    copiar_estilo(ws["N5"], ws["O5"])
    ws.column_dimensions["O"].width = 40
    anchos = {col: ws.column_dimensions[col].width for col in "BCDEFGHIJKLMNO"}
    for i, (original, estandar, descripcion, _tipo, formato, valores, _oblig, _sens, regla, medido, _uso) in enumerate(DICCIONARIO):
        fila = 6 + i
        negocio, tipo, vacios, ejemplo, sensibilidad = EXTRA_DICCIONARIO[original]
        fila_valores = [i + 1, original, estandar, negocio, descripcion, tipo, formato, valores, vacios, ejemplo,
                        sensibilidad, regla, FUENTE_COLUMNA, STEWARD, medido]
        for col, valor in enumerate(fila_valores, 1):
            c = ws.cell(fila, col, valor)
            copiar_estilo(ws.cell(6, min(col, 14)), c)
        if sensibilidad == "Dato personal":
            ws.cell(fila, 11).font = Font(bold=True, color="B5005B")
        if "NO cumple" in medido:
            ws.cell(fila, 15).fill = PatternFill("solid", fgColor="F8D7DA")
        ws.row_dimensions[fila].height = alto([(v, anchos[col]) for v, col in zip(fila_valores[1:], "BCDEFGHIJKLMNO")])


def hoja_glosario(wb):
    ws = wb["3_Glosario"]
    ws["G4"] = "Por qué se presta a confusión"
    copiar_estilo(ws["F4"], ws["G4"])
    ws["G5"] = "Columna agregada por el equipo"
    copiar_estilo(ws["F5"], ws["G5"])
    ws.column_dimensions["E"].width = 30
    ws.column_dimensions["G"].width = 50
    for i, (termino, definicion, confusion) in enumerate(GLOSARIO):
        fila = 6 + i
        otros, columnas = EXTRA_GLOSARIO[termino]
        valores = [i + 1, termino, definicion, otros, columnas, f"{OWNER} (Data Owner)", confusion]
        for col, valor in enumerate(valores, 1):
            c = ws.cell(fila, col, valor)
            copiar_estilo(ws.cell(6, min(col, 6)), c)
        ws.row_dimensions[fila].height = alto([(definicion, 56), (confusion, 50), (columnas, 30)], minimo=36)


def hoja_autoevaluacion(wb):
    ws = wb["4_Autoevaluacion"]
    for i, (respuesta, falta) in enumerate(RESPUESTAS):
        ws.cell(5 + i, 3, respuesta)
        ws.cell(5 + i, 5, falta)
        ws.row_dimensions[5 + i].height = alto([(ws.cell(5 + i, 2).value, 78), (falta, 40)], minimo=27.75)
    ws["B19"] = COLUMNA_DIFICIL
    ws.row_dimensions[19].height = alto([(COLUMNA_DIFICIL, 140)])
    for k, duda in enumerate(DUDAS):
        ws.cell(22 + k, 2, duda)
        ws.row_dimensions[22 + k].height = alto([(duda, 140)])


if __name__ == "__main__":
    assert len(RESPUESTAS) == 10 and len(GLOSARIO) >= 5 and len(DICCIONARIO) >= 8
    wb = load_workbook(PLANTILLA)
    hoja_equipo(wb)
    hoja_ficha(wb)
    hoja_diccionario(wb)
    hoja_glosario(wb)
    hoja_autoevaluacion(wb)
    wb.save(SALIDA)
    puntaje = sum({"Sí": 2, "Parcial": 1, "No": 0}[r] for r, _ in RESPUESTAS)
    print(f"OK -> {SALIDA.name} | columnas: {len(DICCIONARIO)} | glosario: {len(GLOSARIO)} | puntaje: {puntaje}/20")
