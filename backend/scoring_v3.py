"""
scoring_v3.py — Motor de evaluación de evidencia de pago (4 dimensiones).

Reemplaza el concepto de "un solo score de riesgo" por 4 señales separadas,
porque mezclar "¿se ve auténtico?" con "¿puedo verificarlo?" con "¿llegó el
dinero?" castiga comprobantes legítimos solo por falta de evidencia externa.

Fuentes verificadas (no inventadas):
- Circular 14/2017, art. 19a: el banco receptor debe abonar en 30s (montos
  <=$8,000) o 5s (montos >$8,000) tras el Aviso de Liquidación de Banxico;
  el emisor tiene 30s para introducir la instrucción al SPEI.
- "Definicion del estado de tu transferencia bancaria" (banxico.org.mx,
  seccion Ley de Transparencia): los 8 estados de consulta de pago
  (en_proceso, liquidado, cancelado, rechazado, en_proceso_devolucion,
  devuelto, no_liquidado, no_encontrado), verificado via cobertura
  convergente de El Financiero e Infobae citando esa pagina oficial.

Lo que NO esta anclado a normativa (decision de producto, marcado
explicitamente en el codigo): los umbrales de minutos/horas para el
contexto temporal, y los pesos para fusionar dimensiones en el score
legacy.
"""
import datetime
from enum import Enum
from typing import Optional


class EstadoOperacion(str, Enum):
    """
    Normalizacion interna de los 8 estados oficiales de consulta SPEI.
    Usamos nuestros propios valores (no el texto crudo de Banxico) para
    que si Banxico cambia el texto de una etiqueta, no se rompe la logica
    que depende de este enum en otras partes del sistema.
    """
    ACREDITADA = "acreditada"            # CEP disponible -- evidencia mas fuerte
    LIQUIDADA = "liquidada"              # liquidado, CEP aun no generado
    EN_PROCESO = "en_proceso"            # SPEI recibio la orden, no liquido aun
    DEVUELTA = "devuelta"                # devolucion liquidada e informada
    EN_DEVOLUCION = "en_devolucion"      # devolucion en curso
    RECHAZADA = "rechazada"              # rechazada por errores/seguridad
    CANCELADA = "cancelada"              # cancelada antes de liquidar
    NO_LIQUIDADA = "no_liquidada"        # no se liquido en la jornada, se elimino
    DESCONOCIDA = "desconocida"          # no encontrada / sin datos suficientes para consultar


# Mapeo: estado_operacion -> impacto en verificabilidad.
#
# OJO -- separar lo que SI tiene fuente de lo que NO:
#   - El ORDEN relativo SI tiene base documental: Banxico distingue
#     acreditada > liquidada > devuelta/en_devolucion > en_proceso, y
#     distingue rechazada/cancelada/no_liquidada como resultados firmes
#     (se sabe con certeza que no se acredito) de desconocida (no se pudo
#     consultar, sin conclusion).
#   - Los NUMEROS EXACTOS de abajo (100, 85, 80, 75, 50, 70, 70, 65, 20)
#     NO vienen de Banxico. Banxico no publica una escala 0-100 de
#     "verificabilidad". Son una escala que construimos nosotros para
#     poder ordenar y combinar estos estados en un numero -- decision de
#     producto, no normativa. Si se ajustan estos valores en el futuro,
#     no hace falta volver a la documentacion de Banxico, basta con
#     justificar el cambio como mejora de producto.
#
# IMPORTANTE (correccion clave de esta version): DEVUELTA/EN_DEVOLUCION
# implican que la operacion SI existio y SI fue procesada por SPEI -- eso
# es evidencia fuerte de que algo real ocurrio. Pero NO es evidencia de
# que el pago quedo acreditado. Por eso afecta verificabilidad (alta,
# porque hay rastro real) sin tocar estado_operacion como si fuera
# "exitosa". Son dos preguntas distintas: "?existio la operacion?" vs
# "?el dinero quedo en la cuenta destino?".
IMPACTO_VERIFICABILIDAD = {
    EstadoOperacion.ACREDITADA: 100,
    EstadoOperacion.LIQUIDADA: 85,
    EstadoOperacion.DEVUELTA: 80,        # rastro real, pero no acreditado
    EstadoOperacion.EN_DEVOLUCION: 75,
    EstadoOperacion.EN_PROCESO: 50,      # neutro, no concluye nada
    EstadoOperacion.RECHAZADA: 70,       # se sabe con certeza que no se acredito
    EstadoOperacion.CANCELADA: 70,
    EstadoOperacion.NO_LIQUIDADA: 65,
    EstadoOperacion.DESCONOCIDA: 20,     # no se pudo consultar, no es evidencia de fraude
}


def mapear_estado_cep_a_estado_operacion(status_cep: str, found: bool) -> EstadoOperacion:
    """
    Traduce el 'status' interno que ya devuelve verify_cep() (EXISTE,
    PARCIAL, NO_EXISTE, etc.) al nuevo EstadoOperacion. Esto es deliberadamente
    conservador: con el endpoint actual de banxico.org.mx/cep/ solo podemos
    distinguir con certeza "CEP disponible" vs "no disponible" -- los 8
    estados completos (rechazado, cancelado, devuelto, etc.) requieren leer
    ese campo de estado si el HTML lo expone, lo cual se deja preparado
    pero no se fuerza una distincion que el scraping actual no puede dar.
    """
    if not found:
        return EstadoOperacion.DESCONOCIDA
    if status_cep == "EXISTE":
        return EstadoOperacion.ACREDITADA
    if status_cep == "PARCIAL":
        return EstadoOperacion.LIQUIDADA
    return EstadoOperacion.DESCONOCIDA


# ─────────────────────────────────────────────────────────────────────────────
# CONTEXTO TEMPORAL
# ─────────────────────────────────────────────────────────────────────────────
# Ancla regulatoria real: Circular 14/2017 art. 19a -- ventana de punta a
# punta (emisor introduce a SPEI: 30s: + liquidacion: segundos + receptor
# abona: 30s/5s + aviso: 5s) es de el orden de 1-2 minutos en el caso
# normal. Los CORTES de banda (15 min, 24h) son decision de producto,
# marcados explicitamente -- no provienen de la Circular.

def evaluar_contexto_temporal(fecha_comprobante: Optional[str], hora_comprobante: Optional[str],
                                estado_operacion: EstadoOperacion) -> dict:
    """
    Devuelve un score 0-100 y una explicacion. NO penaliza confianza
    documental ni verificabilidad -- es una dimension independiente.

    Si estado_operacion ya es ACREDITADA/LIQUIDADA/DEVUELTA (es decir, ya
    hay evidencia de que SPEI proceso la operacion), el tiempo transcurrido
    deja de ser relevante: la operacion ya se sabe que curso. El contexto
    temporal solo importa cuando estado_operacion es DESCONOCIDA o
    EN_PROCESO -- ahi es donde "cuanto tiempo ha pasado sin poder
    confirmar nada" sí aporta información.
    """
    from iat import parse_date as _parse_date_helper  # reutiliza el parser existente de fechas en español

    if estado_operacion in (EstadoOperacion.ACREDITADA, EstadoOperacion.LIQUIDADA,
                              EstadoOperacion.DEVUELTA, EstadoOperacion.EN_DEVOLUCION,
                              EstadoOperacion.RECHAZADA, EstadoOperacion.CANCELADA,
                              EstadoOperacion.NO_LIQUIDADA):
        return {
            "score": 100,
            "minutos_transcurridos": None,
            "explicacion": (
                "El estado de la operacion ya fue determinado independientemente del "
                "tiempo transcurrido; el contexto temporal no aplica penalizacion."
            ),
        }

    if not fecha_comprobante:
        return {
            "score": 70,
            "minutos_transcurridos": None,
            "explicacion": "No fue posible determinar la fecha del comprobante para evaluar el contexto temporal.",
        }

    fecha_parsed = _parse_date_helper(fecha_comprobante)
    if fecha_parsed is None:
        return {
            "score": 70,
            "minutos_transcurridos": None,
            "explicacion": "La fecha del comprobante no pudo interpretarse en un formato reconocido.",
        }

    # Si hay hora, la incorporamos; si no, asumimos mediodia para no sesgar
    # el calculo hacia un extremo del dia.
    hora_int = 12
    minuto_int = 0
    if hora_comprobante:
        import re as _re
        m = _re.search(r"(\d{1,2}):(\d{2})", hora_comprobante)
        if m:
            hora_int, minuto_int = int(m.group(1)), int(m.group(2))

    momento_comprobante = fecha_parsed.replace(hour=hora_int, minute=minuto_int)
    ahora = datetime.datetime.now()
    minutos_transcurridos = (ahora - momento_comprobante).total_seconds() / 60

    if minutos_transcurridos < 0:
        # Fecha futura -- esto ya lo penaliza el motor IAT por separado
        # (analyze_temporal). Aqui solo lo reportamos sin doble penalizar.
        return {
            "score": 50,
            "minutos_transcurridos": round(minutos_transcurridos, 1),
            "explicacion": "La fecha del comprobante es posterior al momento del analisis.",
        }

    # Bandas de tolerancia -- DECISION DE PRODUCTO, no de Banxico.
    # 15 min de margen amplio sobre la ventana regulatoria real (~1-2 min)
    # para absorber variabilidad normal de uso (el usuario tarda en subir
    # el comprobante, diferencias de reloj, etc.)
    if minutos_transcurridos <= 15:
        return {
            "score": 100,
            "minutos_transcurridos": round(minutos_transcurridos, 1),
            "explicacion": "El tiempo transcurrido es consistente con una operacion SPEI reciente.",
        }
    if minutos_transcurridos <= 24 * 60:
        return {
            "score": 75,
            "minutos_transcurridos": round(minutos_transcurridos, 1),
            "explicacion": (
                "Ha transcurrido mas tiempo del esperado para una confirmacion SPEI sin que "
                "exista evidencia de liquidacion. Esto no es prueba de fraude, solo reduce la "
                "verificabilidad temporal de la operacion."
            ),
        }
    return {
        "score": 40,
        "minutos_transcurridos": round(minutos_transcurridos, 1),
        "explicacion": (
            "Han transcurrido mas de 24 horas sin evidencia de liquidacion ni acreditacion. "
            "Se recomienda corroboracion adicional; esto no concluye fraude por si solo."
        ),
    }


# ─────────────────────────────────────────────────────────────────────────────
# VERIFICABILIDAD
# ─────────────────────────────────────────────────────────────────────────────

def evaluar_verificabilidad(campos_planos: dict, estado_operacion: EstadoOperacion,
                              cep_resultado: Optional[dict]) -> dict:
    """
    0-100. Responde: ?que tanto puedo corroborar esta operacion
    externamente? Independiente de si el documento "se ve" autentico.
    """
    base = IMPACTO_VERIFICABILIDAD.get(estado_operacion, 20)

    tiene_clave = bool((campos_planos.get("clave_rastreo") or "").strip())
    tiene_referencia = bool((campos_planos.get("referencia") or "").strip())
    tiene_folio = bool((campos_planos.get("folio") or "").strip())

    # Si el estado de operacion ya es DESCONOCIDA (no se pudo consultar
    # CEP), la presencia de identificadores SI suma -- son la razon por la
    # que un analisis futuro o manual podria verificarlo, aunque hoy no se
    # haya logrado. Los pesos +15/+8/+5 son decision de producto (no de
    # Banxico): refleja que clave de rastreo es el identificador mas fuerte
    # para una consulta posterior (es el que usa banxico.org.mx/cep/ como
    # primer criterio), referencia es secundario, folio es el mas debil
    # porque ni siquiera es el campo que el CEP consulta directamente.
    bonus_identificadores = 0
    if estado_operacion == EstadoOperacion.DESCONOCIDA:
        if tiene_clave:
            bonus_identificadores += 15
        if tiene_referencia:
            bonus_identificadores += 8
        if tiene_folio:
            bonus_identificadores += 5

    score = min(100, base + bonus_identificadores)

    detalles = []
    if tiene_clave:
        detalles.append("clave de rastreo presente")
    if tiene_referencia:
        detalles.append("referencia presente")
    if tiene_folio:
        detalles.append("folio presente")
    if cep_resultado and cep_resultado.get("found"):
        detalles.append("operacion localizada en CEP Banxico")

    return {
        "score": round(score, 1),
        "elementos_disponibles": detalles,
    }


# ─────────────────────────────────────────────────────────────────────────────
# INTERPRETACION TEXTUAL
# ─────────────────────────────────────────────────────────────────────────────

def generar_interpretacion(confianza_documental: float, verificabilidad: float,
                             contexto_temporal: float, estado_operacion: EstadoOperacion) -> str:
    """
    Genera una explicacion en prosa de las 4 dimensiones, sin dar un solo
    numero como veredicto. Los cortes 80/50 usados abajo para decidir entre
    "alta/moderada/limitada" son decision de producto (umbral editorial
    para el texto), no normativa de Banxico.
    """
    partes = []

    if confianza_documental >= 80:
        partes.append(f"El comprobante presenta alta consistencia documental ({confianza_documental:.0f}/100).")
    elif confianza_documental >= 50:
        partes.append(f"El comprobante presenta consistencia documental moderada ({confianza_documental:.0f}/100).")
    else:
        partes.append(f"El comprobante presenta inconsistencias documentales relevantes ({confianza_documental:.0f}/100).")

    if verificabilidad >= 80:
        partes.append(f"La verificabilidad es alta ({verificabilidad:.0f}/100): existen elementos suficientes para corroborar la operacion.")
    elif verificabilidad >= 50:
        partes.append(f"La verificabilidad es moderada ({verificabilidad:.0f}/100).")
    else:
        partes.append(
            f"La verificabilidad es limitada ({verificabilidad:.0f}/100), lo cual no es evidencia de fraude "
            "sino ausencia de elementos para corroborar la operacion externamente."
        )

    estado_textos = {
        EstadoOperacion.ACREDITADA: "Banxico confirma que la operacion fue acreditada (CEP disponible).",
        EstadoOperacion.LIQUIDADA: "La operacion fue liquidada por SPEI; el banco receptor ya esta en posibilidad de abonarla.",
        EstadoOperacion.EN_PROCESO: "La operacion se encuentra en proceso segun SPEI.",
        EstadoOperacion.DEVUELTA: "La operacion fue liquidada pero posteriormente devuelta al emisor: existio una operacion real, pero no quedo acreditada en el destino.",
        EstadoOperacion.EN_DEVOLUCION: "La operacion esta en proceso de devolucion al emisor.",
        EstadoOperacion.RECHAZADA: "La operacion fue rechazada por SPEI.",
        EstadoOperacion.CANCELADA: "La operacion fue cancelada antes de liquidarse.",
        EstadoOperacion.NO_LIQUIDADA: "La operacion no pudo liquidarse durante la jornada y fue eliminada.",
        EstadoOperacion.DESCONOCIDA: "No fue posible determinar el estado de la operacion ante SPEI; esto no implica fraude, solo ausencia de informacion disponible.",
    }
    partes.append(estado_textos.get(estado_operacion, ""))

    if contexto_temporal < 75:
        partes.append("El tiempo transcurrido desde la fecha del comprobante es mayor al esperado para una confirmacion SPEI.")

    return " ".join(p for p in partes if p)


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR 1: Estado SPEI (fuente: Banxico) — independiente del análisis documental
# ─────────────────────────────────────────────────────────────────────────────

class NivelEvidencia(str):
    """
    Grado de certeza de la verificacion SPEI.
    Jerarquia: xml_oficial > cep_html > documental > no_disponible.
    Un nivel mas alto de evidencia nunca cambia el estado SPEI ya obtenido
    por un nivel inferior -- solo lo reemplaza si viene de una fuente
    de mayor jerarquia.
    """
    XML_OFICIAL  = "xml_oficial"   # XML descargado directamente de banxico.org.mx/cep/
    CEP_HTML     = "cep_html"      # Respuesta HTML del scraping de CEP (ya existia antes)
    DOCUMENTAL   = "documental"    # Inferido del analisis del comprobante, sin consultar Banxico
    NO_DISPONIBLE = "no_disponible"


# Jerarquia numerica para comparar niveles de evidencia
_JERARQUIA_EVIDENCIA = {
    NivelEvidencia.XML_OFICIAL:   4,
    NivelEvidencia.CEP_HTML:      3,
    NivelEvidencia.DOCUMENTAL:    2,
    NivelEvidencia.NO_DISPONIBLE: 1,
}

def evidencia_mas_alta(actual: str, nueva: str) -> bool:
    """Devuelve True si 'nueva' tiene mayor jerarquia que 'actual'."""
    return _JERARQUIA_EVIDENCIA.get(nueva, 0) > _JERARQUIA_EVIDENCIA.get(actual, 0)


# Tabla de colores del semáforo SPEI (usada en frontend también).
# Basada en el comportamiento oficial de SPEI según Banxico.
SEMAFORO_SPEI = {
    EstadoOperacion.ACREDITADA:    {"color": "verde",        "etiqueta": "Acreditada",          "icono": "✅"},
    EstadoOperacion.LIQUIDADA:     {"color": "verde",        "etiqueta": "Liquidada",            "icono": "✅"},
    EstadoOperacion.EN_PROCESO:    {"color": "amarillo",     "etiqueta": "En proceso",           "icono": "🟡"},
    EstadoOperacion.DEVUELTA:      {"color": "naranja",      "etiqueta": "Devuelta",             "icono": "🟠"},
    EstadoOperacion.EN_DEVOLUCION: {"color": "naranja",      "etiqueta": "En devolución",        "icono": "🟠"},
    EstadoOperacion.RECHAZADA:     {"color": "rojo",         "etiqueta": "Rechazada",            "icono": "🔴"},
    EstadoOperacion.CANCELADA:     {"color": "rojo",         "etiqueta": "Cancelada",            "icono": "🔴"},
    EstadoOperacion.NO_LIQUIDADA:  {"color": "rojo",         "etiqueta": "No liquidada",         "icono": "🔴"},
    EstadoOperacion.DESCONOCIDA:   {"color": "gris",         "etiqueta": "No verificado",        "icono": "⚪"},
}


def extraer_estado_de_xml(xml_datos: dict) -> EstadoOperacion:
    """
    Extrae el estado SPEI a partir de los datos del XML del CEP.
    Un XML descargado exitosamente de Banxico implica que la operacion
    fue procesada por SPEI -- minimo LIQUIDADA. Si el XML tiene un campo
    de estado explicito, se usa ese; si no, LIQUIDADA es el minimo
    garantizado por el hecho de que el XML existe.
    """
    # El XML del CEP de Banxico actualmente no incluye un campo de estado
    # textual explicito (al momento de implementar este modulo) -- la
    # presencia del XML ya es evidencia de que la operacion fue procesada.
    # Si en el futuro el XML incluye un campo de estado, se puede mapear aqui.
    estado_raw = xml_datos.get("estado_operacion") or ""
    mapeo = {
        "LIQUIDADO": EstadoOperacion.LIQUIDADA,
        "ACREDITADO": EstadoOperacion.ACREDITADA,
        "DEVUELTO": EstadoOperacion.DEVUELTA,
        "RECHAZADO": EstadoOperacion.RECHAZADA,
        "CANCELADO": EstadoOperacion.CANCELADA,
        "EN PROCESO": EstadoOperacion.EN_PROCESO,
    }
    if estado_raw.upper() in mapeo:
        return mapeo[estado_raw.upper()]
    # Sin campo de estado explicito: el XML existe -> operacion fue procesada
    return EstadoOperacion.LIQUIDADA


# ─────────────────────────────────────────────────────────────────────────────
# MOTOR 2: Integridad documental (fuente: VerificaPago) — independiente de SPEI
# ─────────────────────────────────────────────────────────────────────────────

class IntegridadComprobante(str):
    SIN_OBSERVACIONES   = "sin_observaciones"   # Todo consistente, sin señales de alteración
    CON_OBSERVACIONES   = "con_observaciones"    # Algunas señales menores, no concluyentes
    POSIBLE_ALTERACION  = "posible_alteracion"   # Señales fuertes de manipulación documental


def calcular_integridad_comprobante(
    confianza_documental: float,
    tiene_anomalias_altas: bool = False,
) -> str:
    """
    Determina el estado de integridad documental a partir del Motor 2
    (confianza_documental de scoring_v3 + anomalias graves del IAT).
    Este resultado es COMPLETAMENTE independiente del estado SPEI:
    un comprobante puede ser LIQUIDADA en SPEI y tener observaciones
    documentales (el dinero llego pero el comprobante fue editado), o
    puede estar SIN_OBSERVACIONES documentalmente pero DESCONOCIDA en SPEI
    (comprobante impecable, pero Banxico no lo encontro aun).
    """
    if tiene_anomalias_altas or confianza_documental < 45:
        return IntegridadComprobante.POSIBLE_ALTERACION
    if confianza_documental >= 75:
        return IntegridadComprobante.SIN_OBSERVACIONES
    return IntegridadComprobante.CON_OBSERVACIONES


INTEGRIDAD_CONFIG = {
    IntegridadComprobante.SIN_OBSERVACIONES:  {"color": "verde",  "etiqueta": "Sin observaciones",  "icono": "✅"},
    IntegridadComprobante.CON_OBSERVACIONES:  {"color": "naranja","etiqueta": "Con observaciones",  "icono": "🟠"},
    IntegridadComprobante.POSIBLE_ALTERACION: {"color": "rojo",   "etiqueta": "Posible alteración", "icono": "🔴"},
}