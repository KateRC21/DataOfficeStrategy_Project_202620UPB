"""Políticas del Plan de Gobierno de ORCA expresadas como código.

Lo que el Plan de Gobierno (documentacion/05_plan_gobierno_datos.md) escribe en prosa, aquí
se vuelve verificable: la matriz de acceso por capa y rol, la clasificación de cada capa, la
política de retención, el estándar de nomenclatura y las vistas del dashboard por rol.
Lo usan el dashboard (control de acceso), el orquestador (retención) y el notebook de gobierno.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- roles y capas
ROLES = {
    "data_owner": "Data Owner · Luis Ángel Seoanes Ovieso (Contralor Auxiliar simulado)",
    "data_steward": "Data Steward · Julian Amariles Taborda",
    "custodio": "Custodio técnico · Katheryn Ramírez Chimá",
    "analista": "Consumidor / Analista · Jhon Sebastian Rayo Posada",
    "auditor": "Auditor de la contraloría (consumidor final)",
    "ciudadania": "Ciudadanía / público externo",
}

CLASIFICACION = {
    "raw": ("Confidencial", "Contiene PII en claro (cédulas, nombres, cuentas bancarias). Evidencia inmutable del lote."),
    "curated": ("Interno", "PII seudonimizada con HMAC-SHA256; texto libre enmascarado; sin columnas bancarias."),
    "mart": ("Confidencial", "Sin PII en claro, pero las alertas de riesgo son reservadas hasta que exista actuación fiscal."),
    "dashboard_publico": ("Público", "Solo agregados (por mes, modalidad y municipio), sin alertas individuales."),
}

# L = lectura · E = escritura · - = sin acceso. Principio de mínimo privilegio.
MATRIZ_ACCESO = {
    #                     raw   curated  mart  dashboard_publico
    "data_owner":        {"raw": "L", "curated": "L", "mart": "L", "dashboard_publico": "L"},
    "data_steward":      {"raw": "L", "curated": "L", "mart": "L", "dashboard_publico": "L"},
    "custodio":          {"raw": "E", "curated": "E", "mart": "E", "dashboard_publico": "E"},
    "analista":          {"raw": "-", "curated": "L", "mart": "L", "dashboard_publico": "L"},
    "auditor":           {"raw": "-", "curated": "-", "mart": "L", "dashboard_publico": "L"},
    "ciudadania":        {"raw": "-", "curated": "-", "mart": "-", "dashboard_publico": "L"},
}

JUSTIFICACION_ACCESO = {
    "data_owner": "Responde por el dato y aprueba accesos; lee raw solo para resolver disputas sobre un lote.",
    "data_steward": "Mide la calidad y resuelve incidentes: necesita ver el dato original para diagnosticar.",
    "custodio": "Opera el pipeline: es el único rol que escribe en las capas (segregación de funciones).",
    "analista": "Construye banderas y dashboard sobre datos seudonimizados; nunca necesita la cédula.",
    "auditor": "Usa las alertas priorizadas; la evidencia la consulta en SECOP con el enlace del contrato.",
    "ciudadania": "Transparencia: ve agregados; las alertas individuales son reservadas (no son hallazgos).",
}

# Pestañas del dashboard que ve cada rol (derivado de la matriz: mart -> todo; solo público -> agregados)
VISTAS_DASHBOARD = {
    "Resumen": {"data_owner", "data_steward", "custodio", "analista", "auditor", "ciudadania"},
    "P1 · Entidades": {"data_owner", "data_steward", "analista", "auditor"},
    "P2 · Ventanas atípicas": {"data_owner", "data_steward", "custodio", "analista", "auditor", "ciudadania"},
    "P3 · Entidad–proveedor": {"data_owner", "data_steward", "analista", "auditor"},
    "P4–P6 · Contratos": {"data_owner", "data_steward", "analista", "auditor"},
    "Bandeja de alertas": {"data_owner", "analista", "auditor"},
    "Gobierno y calidad": {"data_owner", "data_steward", "custodio", "analista"},
}


class AccesoDenegado(PermissionError):
    pass


def puede(rol: str, capa: str, accion: str = "L") -> bool:
    permiso = MATRIZ_ACCESO.get(rol, {}).get(capa, "-")
    return permiso == "E" or (accion == "L" and permiso == "L")


def ruta_capa(rol: str, capa: str, accion: str = "L") -> Path:
    """Devuelve la carpeta de la capa solo si el rol tiene permiso; si no, AccesoDenegado."""
    if not puede(rol, capa, accion):
        raise AccesoDenegado(f"El rol '{rol}' no tiene permiso '{accion}' sobre la capa '{capa}'.")
    return RAIZ / "data" / capa


def vistas_para(rol: str) -> list[str]:
    return [v for v, roles in VISTAS_DASHBOARD.items() if rol in roles]


# ---------------------------------------------------------------- nomenclatura
PREFIJOS = {
    "id_": "Identificador (llave o seudónimo)", "nom_": "Nombre o etiqueta legible", "cod_": "Código o categoría",
    "fec_": "Fecha", "val_": "Valor monetario en COP corrientes", "cant_": "Cantidad o conteo (entero)",
    "pct_": "Proporción entre 0 y 1", "ind_": "Indicador booleano (bandera)", "url_": "Enlace",
    "txt_": "Texto libre (enmascarado)", "num_": "Índice o puntaje numérico", "niv_": "Nivel ordinal",
}
PATRON_COLUMNA = re.compile(r"^(" + "|".join(p.rstrip("_") for p in PREFIJOS) + r")_[a-z0-9_]+$")
PATRON_ARCHIVO_RAW = re.compile(r"^DS-\d{2}_[a-z0-9_]+_\d{8}\.(parquet|manifest\.json)$")


def columnas_no_conformes(columnas) -> list[str]:
    return [c for c in columnas if not PATRON_COLUMNA.match(c)]


# ---------------------------------------------------------------- retención
@dataclass(frozen=True)
class Retencion:
    capa: str
    lotes_a_conservar: int
    dias_maximos: int
    motivo: str


RETENCION = [
    Retencion("raw", 3, 90, "Evidencia del lote para re-procesar; contiene PII: se guarda lo mínimo (Ley 1581, principio de temporalidad)."),
    Retencion("curated", 1, 365, "Se sobrescribe en cada corrida; el linaje queda en el manifiesto."),
    Retencion("mart", 1, 365, "Se sobrescribe en cada corrida; las alertas gestionadas se archivan en el registro de alertas."),
    Retencion("automatizacion", 0, 1825, "Registros de ejecución y alertas: 5 años, como soporte de la vigilancia fiscal."),
]


def lotes_a_purgar(hoy: date | None = None) -> list[Path]:
    """Lotes raw que la política manda eliminar: fuera de los N más recientes por fuente Y más viejos que el máximo."""
    hoy = hoy or date.today()
    pol = next(r for r in RETENCION if r.capa == "raw")
    raw = RAIZ / "data" / "raw"
    purgar = []
    for codigo in ("DS-01", "DS-02", "DS-03"):
        lotes = sorted(raw.glob(f"{codigo}_*.parquet"), reverse=True)
        for p in lotes[pol.lotes_a_conservar:]:
            fecha = date(int(p.stem[-8:-4]), int(p.stem[-4:-2]), int(p.stem[-2:]))
            if (hoy - fecha).days > pol.dias_maximos:
                purgar += [p, p.with_suffix(".manifest.json")]
    return purgar


# ---------------------------------------------------------------- diccionario del mart (con linaje por campo)
# (columna, descripción, unidad / formato, valores válidos, sensibilidad, columna de origen en DS-01/DS-02, transformación)
DICCIONARIO_MART = [
    ("id_contrato", "Identificador único del contrato en SECOP II.", "texto", "patrón CO1.PCCNTR.<dígitos>; único", "Público", "DS-01.id_contrato", "sin cambio"),
    ("id_proceso_compra", "Proceso de compra (portafolio) que originó el contrato; llave hacia DS-02.", "texto", "patrón CO1.BDOS.<dígitos>", "Público", "DS-01.proceso_de_compra", "sin cambio"),
    ("nom_entidad", "Nombre canónico de la entidad contratante (un nombre por NIT).", "texto", "no vacío", "Público", "DS-01.nombre_entidad", "quita * y / finales; nombre más frecuente por NIT"),
    ("id_nit_entidad", "NIT de la entidad sin dígito de verificación.", "texto de 9 dígitos", "^[0-9]{9}$", "Público", "DS-01.nit_entidad", "deja 9 dígitos (retira el DV)"),
    ("cod_orden_entidad", "Orden administrativo de la entidad.", "categoría", "Territorial · Nacional · Corporación Autónoma", "Público", "DS-01.orden", "sin cambio"),
    ("nom_municipio", "Municipio de la entidad según DIVIPOLA.", "categoría", "125 municipios de Antioquia o 'Sin municipio'", "Público", "DS-01.ciudad + DS-03.nom_mpio", "normaliza tildes, alias y cruza con DIVIPOLA"),
    ("cod_municipio", "Código DIVIPOLA del municipio.", "texto de 5 dígitos", "^05[0-9]{3}$", "Público", "DS-03.cod_mpio", "cruce por nombre normalizado"),
    ("cod_modalidad", "Modalidad de contratación.", "categoría", "lista de SECOP II (13 valores)", "Público", "DS-01.modalidad_de_contratacion", "nulos disfrazados -> nulo"),
    ("cod_tipo_contrato", "Tipo de contrato.", "categoría", "lista de SECOP II", "Público", "DS-01.tipo_de_contrato", "nulos disfrazados -> nulo"),
    ("cod_causal_modalidad", "Causal que justifica la modalidad.", "categoría", "lista de SECOP II", "Público", "DS-01.justificacion_modalidad_de", "nulos disfrazados -> nulo"),
    ("cod_estado_contrato", "Estado del contrato en el corte.", "categoría", "7 estados (capitalizados)", "Público", "DS-01.estado_contrato", "capitaliza"),
    ("fec_firma", "Fecha de firma del contrato.", "fecha AAAA-MM-DD", "≥ 2024-01-01 y ≤ fecha de corte", "Público", "DS-01.fecha_de_firma", "ISO 8601 -> fecha"),
    ("fec_inicio", "Fecha de inicio de ejecución.", "fecha", "≥ fecha de firma (regla K3)", "Público", "DS-01.fecha_de_inicio_del_contrato", "ISO 8601 -> fecha"),
    ("fec_fin", "Fecha de terminación pactada.", "fecha", "≥ fecha de inicio (regla K1)", "Público", "DS-01.fecha_de_fin_del_contrato", "ISO 8601 -> fecha"),
    ("val_contrato", "Valor del contrato.", "COP corrientes", "≥ 0", "Público", "DS-01.valor_del_contrato", "texto -> número"),
    ("cant_dias_adicionados", "Días de prórroga adicionados.", "días", "0 a 3.650", "Público", "DS-01.dias_adicionados", "texto -> número"),
    ("ind_persona_natural", "El contratista es persona natural (documento distinto de NIT).", "booleano", "True/False", "Público (determina qué es PII)", "DS-01.tipodocproveedor", "tipo != NIT"),
    ("id_proveedor_seud", "Seudónimo del contratista: HMAC-SHA256 con sal secreta, 16 hex.", "texto hex", "^[0-9a-f]{16}$", "Interno (seudónimo)", "DS-01.documento_proveedor", "HMAC-SHA256(sal, documento) — irreversible sin la sal"),
    ("id_nit_proveedor", "NIT del contratista, solo si es persona jurídica.", "texto", "nulo si persona natural", "Público (persona jurídica)", "DS-01.documento_proveedor", "se conserva solo cuando tipo = NIT"),
    ("nom_proveedor_juridico", "Razón social del contratista, solo si es persona jurídica.", "texto", "nulo si persona natural", "Público (persona jurídica)", "DS-01.proveedor_adjudicado", "se conserva solo cuando tipo = NIT"),
    ("cant_respuestas_proceso", "Respuestas (ofertas) que recibió el proceso.", "conteo", "≥ 0; nulo si el proceso no está en DS-02", "Público", "DS-02.respuestas_al_procedimiento", "máximo por id_del_portafolio"),
    ("cant_entidades_simultaneas", "Máximo de entidades distintas con contratos vigentes del mismo contratista en un mes de este contrato.", "conteo", "≥ 0", "Interno (derivado de seudónimo)", "DS-01 (fechas + seudónimo)", "regla R4"),
    ("val_limite_atipico_grupo", "Límite Q3 + 1,5·IQR (escala log) de su grupo tipo × modalidad.", "COP", "> 0; nulo si el grupo tiene < 30 contratos", "Público", "derivado", "regla R5"),
    ("ind_sujeto_vigilancia", "La entidad es del orden territorial (alcance de la contraloría territorial).", "booleano", "True/False", "Público", "DS-01.orden", "orden = Territorial"),
    ("txt_objeto", "Objeto del contrato (primeros 300 caracteres), con documentos personales enmascarados como [DOC].", "texto", "sin documentos de personas naturales", "Interno", "DS-01.objeto_del_contrato", "enmascarado de PII en texto libre"),
    ("url_proceso_secop", "Enlace público al proceso en SECOP II (trazabilidad hasta el documento original).", "URL", "empieza por https://community.secop.gov.co", "Público", "DS-01.urlproceso", "extrae la URL del objeto JSON"),
    ("ind_r1_contratacion_directa", "Bandera R1 (P1).", "booleano", "True/False", "Confidencial (alerta)", "DS-01.modalidad_de_contratacion", "reglas_riesgo.json R1"),
    ("ind_r2_ventana_atipica", "Bandera R2 (P2).", "booleano", "True/False", "Confidencial (alerta)", "DS-01.fecha_de_firma + modalidad", "reglas_riesgo.json R2"),
    ("ind_r3_concentracion_par", "Bandera R3 (P3).", "booleano", "True/False", "Confidencial (alerta)", "DS-01 (entidad, seudónimo, valor)", "reglas_riesgo.json R3"),
    ("ind_r4_simultaneidad_pn", "Bandera R4 (P4).", "booleano", "True/False", "Confidencial (alerta)", "DS-01 (seudónimo, fechas)", "reglas_riesgo.json R4"),
    ("ind_r5_valor_atipico", "Bandera R5 (P5).", "booleano", "True/False", "Confidencial (alerta)", "DS-01.valor_del_contrato", "reglas_riesgo.json R5"),
    ("ind_r6_unico_oferente", "Bandera R6 (P6).", "booleano", "True/False", "Confidencial (alerta)", "DS-02.respuestas_al_procedimiento", "reglas_riesgo.json R6"),
    ("ind_r7_urgencia_manifiesta", "Bandera R7.", "booleano", "True/False", "Confidencial (alerta)", "DS-01.justificacion_modalidad_de", "reglas_riesgo.json R7"),
    ("ind_r8_prorroga_desproporcionada", "Bandera R8.", "booleano", "True/False", "Confidencial (alerta)", "DS-01.dias_adicionados + fechas", "reglas_riesgo.json R8"),
    ("ind_r9_inconsistencia_dato", "Bandera R9 (calidad).", "booleano", "True/False", "Confidencial (alerta)", "DS-01 (valor, causal, fechas)", "reglas_riesgo.json R9"),
    ("num_score_riesgo", "Score de riesgo: suma de pesos de las banderas activas, normalizada a 100.", "puntos 0–100", "0 a 100", "Confidencial (alerta)", "derivado", "Σ peso·bandera / Σ pesos × 100"),
    ("niv_riesgo", "Nivel de prioridad.", "ordinal", "Alto (≥ 40) · Medio (≥ 25) · Bajo (> 0) · Sin señales", "Confidencial (alerta)", "derivado", "umbrales de reglas_riesgo.json"),
    ("cant_banderas", "Número de banderas activas.", "conteo", "0 a 9", "Confidencial (alerta)", "derivado", "suma de ind_r*"),
    ("txt_banderas", "Códigos de las banderas activas (p. ej. R1,R3).", "texto", "subconjunto de R1…R9", "Confidencial (alerta)", "derivado", "concatenación"),
]
