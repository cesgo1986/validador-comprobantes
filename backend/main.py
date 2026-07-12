import json
import csv
import io
import logging
from fastapi.responses import StreamingResponse
import base64
import datetime
import re
import os
import time
import httpx
from fastapi import FastAPI, UploadFile, File, Form, APIRouter, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import anthropic
from dotenv import load_dotenv
from iat import calculate_iat, fuse_scores, iat_anomalias_to_validaciones
from services.hash_service import registrar_y_consultar_hash
from services.auditoria_service import guardar_analisis
from services import dashboard_service
from services import metrics_service
from services import alerta_service
from alert_engine import engine as alert_engine
from database import init_db, DEFAULT_EMPRESA_ID
from services.cep_xml_service import parsear_xml_cep, comparar_xml_contra_comprobante, construir_resultado_xml, XMLCepInvalido
from services.cep_xml_auto_service import datos_suficientes_para_consulta, descargar_xml_cep_automatico
from scoring_v3 import (
    EstadoOperacion, mapear_estado_cep_a_estado_operacion,
    evaluar_contexto_temporal, evaluar_verificabilidad, generar_interpretacion,
    NivelEvidencia, evidencia_mas_alta, SEMAFORO_SPEI,
    extraer_estado_de_xml, calcular_integridad_comprobante, INTEGRIDAD_CONFIG,
)
 
load_dotenv()
 
# ─────────────────────────────────────────────────────────────────────────────
# Item 6.1 (Etapa 6, Hardening): logging estructurado.
# Primer paso -- reemplaza los print(...) de ESTE archivo. Otros archivos
# (services/*.py, alert_engine/*.py) todavía usan print() -- se convierten
# en un paso posterior de 6.1, no en este mismo cambio, para no mezclar un
# cambio grande de un solo archivo con una migración completa del proyecto.
# ─────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("verificapago")
 
app = FastAPI()
 
# ─────────────────────────────────────────────────────────────────────────────
# Item 6.1 (Etapa 6, Hardening): CORS restringido.
# Antes: allow_origins=["*"] -- cualquier dominio podía llamar a la API.
# Ahora: se lee de la variable de entorno ALLOWED_ORIGINS (coma-separada).
#
# IMPORTANTE: ALLOWED_ORIGINS ya debe estar configurada en Render:
#     ALLOWED_ORIGINS=https://validador-comprobantes.vercel.app,http://localhost:3000
# ─────────────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
if not ALLOWED_ORIGINS:
    logger.warning("ALLOWED_ORIGINS no está configurada -- CORS bloqueará todas las peticiones de navegador.")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Item 6.1: headers de seguridad.
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def agregar_headers_seguridad(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Item 6.1: rate limiting por IP.
# No requiere identidad -- limita por dirección de origen, no por cuenta
# (eso es 6.3, cuando exista Identity Layer). /analizar tiene un límite
# más estricto (se decora aparte, más abajo en el archivo) porque es el
# endpoint costoso (Claude Vision + Banxico).
# ─────────────────────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
app.state.limiter = limiter
 
 
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    # Registro de eventos de seguridad sin identidad (item 6.1): no
    # sabemos "quién" hasta que exista Identity Layer (6.2), pero sí
    # podemos registrar "qué pasó" -- IP y ruta que dispararon el límite.
    logger.warning("Rate limit excedido: IP=%s ruta=%s", get_remote_address(request), request.url.path)
    return await _rate_limit_exceeded_handler(request, exc)
 
 
# ─────────────────────────────────────────────────────────────────────────────
# Item 6.1: registro de eventos de seguridad -- errores 500.
# Middleware que solo OBSERVA la respuesta ya generada, no altera el
# manejo de excepciones existente.
# ─────────────────────────────────────────────────────────────────────────────
@app.middleware("http")
async def registrar_errores_500(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        logger.error("Excepcion no manejada en %s %s", request.method, request.url.path, exc_info=True)
        raise
    if response.status_code >= 500:
        logger.error("Error 500 en %s %s", request.method, request.url.path)
    return response
 

# Crea las tablas (hashes_documentos, analisis) si no existen y si
# DATABASE_URL está configurada. Si no está configurada, init_db()
# devuelve False sin lanzar excepción — la app sigue funcionando, solo
# sin persistencia (ver database.py y hash_service.py para el detalle
# de cómo se degrada con gracia).
try:
    init_db()
except Exception as e:
    logger.warning("No fue posible inicializar la base de datos: %s", e)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: Modelo configurable via variable de entorno
# Cambiar de modelo (ej. cuando salga uno mejor) ya no requiere tocar código,
# solo actualizar CLAUDE_MODEL en el .env / panel de Render.
# ─────────────────────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")

BANKS = {
    "002": "BBVA", "006": "BANCOMEXT", "009": "BANOBRAS", "012": "HSBC",
    "014": "SANTANDER", "021": "HSBC", "030": "BAJIO", "036": "INBURSA",
    "037": "MULTIVA", "044": "SCOTIABANK", "058": "BANREGIO", "059": "INVEX",
    "062": "AFIRME", "072": "BANORTE", "127": "AZTECA", "128": "AUTOFIN",
    "130": "COMPARTAMOS", "137": "BANCOPPEL", "145": "BANJERCITO",
    "147": "BANKAOOL", "600": "MONEXCB", "601": "GBM", "646": "STP",
    "706": "ARCUS", "722": "MERCADO PAGO", "723": "CUENCA",
    "728": "SPIN BY OXXO", "741": "KLAR", "748": "BINEO",
}


# ─────────────────────────────────────────────────────────────────────────────
# CLABE
# ─────────────────────────────────────────────────────────────────────────────

def validate_clabe(clabe: str) -> dict:
    clean = clabe.replace(" ", "")
    if len(clean) != 18:
        return {"valid": False, "reason": "Longitud incorrecta (debe ser 18 digitos)"}
    if not clean.isdigit():
        return {"valid": False, "reason": "Contiene caracteres no numericos"}
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7]
    total = sum(int(clean[i]) * weights[i] for i in range(17))
    check = (10 - (total % 10)) % 10
    if check != int(clean[17]):
        return {"valid": False, "reason": "Digito verificador incorrecto"}
    bank_code = clean[:3]
    bank = BANKS.get(bank_code, "Banco no reconocido")
    return {"valid": True, "bank": bank, "bank_code": bank_code}


# ─────────────────────────────────────────────────────────────────────────────
# FECHA PASADA
# ─────────────────────────────────────────────────────────────────────────────

def fecha_es_pasada(fecha_str: str) -> tuple:
    """
    Retorna (es_pasada: bool, dias_diferencia: int).
    Umbral > 1 dia para evitar falsos positivos por zona horaria.
    Soporta todos los formatos de fecha de bancos mexicanos.
    """
    if not fecha_str:
        return False, 0
    formatos = [
        "%Y-%m-%d",        # 2026-06-13
        "%d/%m/%Y",        # 13/06/2026
        "%d-%m-%Y",        # 13-06-2026
        "%d/%m/%y",        # 13/06/26
        "%Y/%m/%d",        # 2026/06/13
        "%d/%b/%Y",        # 13/Jun/2026
        "%d/%b/%y",        # 13/Jun/26
        "%d de %B de %Y",  # 19 de mayo de 2026
        "%d %B %Y",        # 19 mayo 2026
        "%d %B, %Y",       # 19 mayo, 2026
        "%B %d, %Y",       # mayo 19, 2026
        "%d %b %Y",        # 19 may 2026
    ]
    meses = {
        "enero": "January", "febrero": "February", "marzo": "March",
        "abril": "April", "mayo": "May", "junio": "June",
        "julio": "July", "agosto": "August", "septiembre": "September",
        "octubre": "October", "noviembre": "November", "diciembre": "December",
        "ene": "Jan", "feb": "Feb", "mar": "Mar", "abr": "Apr",
        "may": "May", "jun": "Jun", "jul": "Jul", "ago": "Aug",
        "sep": "Sep", "oct": "Oct", "nov": "Nov", "dic": "Dec",
    }
    fecha_norm = fecha_str.lower().strip()
    for es, en in meses.items():
        fecha_norm = fecha_norm.replace(es, en)
    for fmt in formatos:
        try:
            dt = datetime.datetime.strptime(fecha_norm, fmt)
            hoy = datetime.date.today()
            dias = (hoy - dt.date()).days
            return dias > 1, dias
        except ValueError:
            continue
    return False, 0


# ─────────────────────────────────────────────────────────────────────────────
# MONTO — normalización robusta
# ─────────────────────────────────────────────────────────────────────────────

def normalize_monto_float(monto_str: str) -> float:
    """
    Convierte cualquier representación de monto a float.
    Soporta: $1,234.56 / 1.234,56 / MXN 1234.56 / 180 / 1 234.56
    """
    if not monto_str:
        return 0.0
    s = re.sub(r'(?i)(mxn|usd|pesos?|mx|\$)', '', str(monto_str)).strip()
    if re.search(r'\d\.\d{3},\d{1,2}$', s):           # europeo: 1.234,56
        s = s.replace('.', '').replace(',', '.')
    elif re.search(r'\d,\d{3}\.', s) or re.search(r'\d,\d{3}$', s):  # 1,234.56 o 1,234
        s = s.replace(',', '')
    elif re.search(r'^\d+,\d{1,2}$', s):              # solo coma decimal: 45,01
        s = s.replace(',', '.')
    s = re.sub(r'[,\s]', '', s)
    m = re.search(r'\d+\.?\d*', s)
    if not m:
        return 0.0
    try:
        return round(float(m.group()), 2)
    except ValueError:
        return 0.0


def extract_montos_from_html(html: str) -> list:
    """
    Extrae todos los montos posibles del HTML del CEP de Banxico.
    Aplica 9 patrones para cubrir todos los formatos y estructuras posibles.
    """
    montos = set()

    # 1. Inputs con name que contenga monto/importe (formularios CEP)
    for m in re.finditer(
        r'(?i)<input[^>]*name=["\'][^"\']*(?:monto|importe|amount|valor|total)[^"\']*["\'][^>]*value=["\']([^"\']+)["\']', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000: montos.add(v)
    for m in re.finditer(
        r'(?i)<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\'][^"\']*(?:monto|importe|amount|valor|total)[^"\']*["\']', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000: montos.add(v)

    # 2. Etiqueta de monto seguida de <td>
    for m in re.finditer(
        r'(?i)(?:monto|importe|cantidad|amount|total|valor)[^<]{0,30}</td>\s*<td[^>]*>\s*\$?\s*([\d\s,\.]+)', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000: montos.add(v)

    # 3. $1,234.56
    for m in re.finditer(r'\$\s*([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000: montos.add(v)

    # 4. MXN prefijo/sufijo
    for m in re.finditer(r'(?i)mxn\s*([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', html):
        v = normalize_monto_float(m.group(1)); 
        if 0 < v < 1_000_000: montos.add(v)
    for m in re.finditer(r'(?i)([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*mxn', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000: montos.add(v)

    # 5. Palabras clave + valor
    for patron in [
        r'(?i)importe[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)\bmonto[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)cantidad[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)\btotal[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)amount[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)\bvalor[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
    ]:
        for m in re.finditer(patron, html):
            v = normalize_monto_float(m.group(1))
            if 0 < v < 1_000_000: montos.add(v)

    # 6. <td> con número solo (excluir IDs largos)
    for m in re.finditer(r'<td[^>]*>\s*([\d]{1,7}(?:\.\d{1,2})?)\s*</td>', html):
        raw = m.group(1)
        if len(re.sub(r'[^\d]', '', raw)) <= 9:
            v = normalize_monto_float(raw)
            if 0 < v < 1_000_000: montos.add(v)

    # 7. Formato europeo en TD: 45,01
    for m in re.finditer(r'<td[^>]*>\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*</td>', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000: montos.add(v)

    # 8. Cualquier número con exactamente 2 decimales fuera de URLs
    for m in re.finditer(r'(?<![/\d\-])([\d]{1,7}\.\d{2})(?!\d)', html):
        raw = m.group(1)
        if len(raw.replace('.', '')) <= 9:
            v = normalize_monto_float(raw)
            if 0 < v < 1_000_000: montos.add(v)

    return sorted(montos)


def montos_coinciden(monto_comprobante: float, montos_cep: list, tolerancia: float = 1.0) -> bool:
    if monto_comprobante <= 0:
        return False
    return any(abs(m - monto_comprobante) <= tolerancia for m in montos_cep)


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

def clean_clave_rastreo(clave: str) -> str:
    return clave.strip()


def build_system_prompt(fecha_hoy: str, fecha_legible: str, banco_hint: str, clabe_hint: str, fecha_confirmada: bool = False) -> str:
    banco_hint_text = ""
    if banco_hint.strip():
        banco_hint_text = '\nBANCO EMISOR DECLARADO POR EL USUARIO: "' + banco_hint + '". Usalo como banco origen.'

    clabe_hint_text = ""
    if len(clabe_hint) == 18:
        clabe_hint_text = "\nCLABE INGRESADA POR USUARIO: " + clabe_hint + ". Compara con la cuenta destino visible en el comprobante."
    elif len(clabe_hint) > 0:
        clabe_hint_text = "\nCUENTA PARCIAL INGRESADA: " + clabe_hint + " (" + str(len(clabe_hint)) + " digitos)."

    fecha_confirmada_text = (
        "\nIMPORTANTE: El usuario ha confirmado que este comprobante es de una fecha pasada y lo esta validando de manera retroactiva. "
        "NO marques la fecha como sospechosa ni como futura. Analiza el resto del comprobante normalmente.\n"
        if fecha_confirmada else ""
    )

    return (
        "Eres VerificaPago AI, un analista forense especializado en comprobantes de transferencia bancaria en Mexico.\n\n"
        "OBJETIVO:\n"
        "Determinar el nivel de riesgo de fraude de un comprobante de pago mediante analisis documental, estructural, semantico, temporal y contextual.\n\n"
        "FECHA ACTUAL DEL SISTEMA: " + fecha_legible + " (" + fecha_hoy + "). "
        "ESTA ES LA FECHA REAL Y CORRECTA. NO asumas que estamos en 2024 ni en ningun otro año. "
        "El año actual es " + fecha_hoy[:4] + ". Usa esta fecha para todas las validaciones temporales."
        + banco_hint_text + clabe_hint_text + fecha_confirmada_text + "\n\n"
        "REGLAS IMPORTANTES:\n"
        "- NO confirmes que una transferencia ocurrio realmente.\n"
        "- NO afirmes que el dinero fue recibido.\n"
        "- Evalua unicamente la evidencia presente en el comprobante.\n"
        "- Si un dato no puede determinarse con seguridad, devuelve null.\n\n"
        "REGLAS SOBRE FORMATOS VALIDOS EN MEXICO:\n"
        "- Numeros de cuenta ocultos con asteriscos (****1234), puntos (•4023) o cualquier mascara son NORMALES. NO los marques como error.\n"
        "- El diseno visual NO identifica un banco. Usa SOLO el texto visible.\n"
        "- La clave de rastreo SPEI puede ser alfanumerica y terminar en letra (ej: 260608077756961262I, MBAN010026061500901361189). Longitudes entre 16 y 25 caracteres son VALIDAS. NO marques esto como error.\n"
        "- Claves de rastreo solo numericas (ej: 08590066034031646) tambien son VALIDAS.\n"
        "- La diferencia de segundos entre fecha de aceptacion y fecha de liquidacion es NORMAL en SPEI. NO la marques como sospechosa.\n"
        "- Comprobantes con fechas pasadas son NORMALES. El usuario puede estar verificando una transferencia anterior. Solo marca como sospechoso si la fecha es FUTURA.\n"
        "- La leyenda 'Datos no verificados por esta institucion' es ESTANDAR en transferencias SPEI. Significa que el banco receptor aun no confirma, NO es senal de fraude.\n"
        "- El concepto de pago puede ser CUALQUIER texto libre (tacos, renta, gasolina, etc.) o estar ausente. Es opcional en SPEI. NO lo uses como indicador de riesgo.\n"
        "- NO inferas inconsistencia entre el tipo de cuenta origen y el concepto del pago. Una cuenta de nomina puede pagar tacos, renta o cualquier concepto.\n"
        "- El campo 'cuenta origen' o 'realizado con' muestra la cuenta DEL EMISOR, no del receptor. No confundas ambos campos.\n"
        "- Capturas de pantalla recortadas son NORMALES. El usuario puede haber cortado el encabezado o pie de pagina. No lo marques como señal de fraude.\n"
        "- Nombres de cuenta como 'Switch Banamex', 'Nomina', 'Debito' seguidos de digitos parciales son FORMATOS VALIDOS de los bancos mexicanos.\n"
        "- Un asterisco al final de un nombre (ej: 'Cesar Gomez Montañez *') es formato valido de algunas apps bancarias.\n\n"
        "- Algunos bancos (ej. BBVA) muestran el monto con signo negativo (ej. '-$40.00') para indicar que es un cargo/egreso de la cuenta — es una convencion de despliegue del banco, NO una senal de alteracion. Extrae el monto como valor absoluto (positivo) y NO lo marques como riesgo por tener signo negativo en pantalla.\n"
        "REGLAS SOBRE LO QUE SI DEBES MARCAR COMO RIESGO:\n"
        "- Fecha futura (posterior a hoy).\n"
        "- Monto en cero, o un monto negativo que NO corresponda a una convencion normal de despliegue bancario (ej. un valor negativo inconsistente con el resto del comprobante, distinto del signo estandar que algunos bancos usan para mostrar egresos).\n"
        "- Campos criticos completamente ausentes (monto, fecha, banco).\n"
        "- Evidencia visual clara de edicion: pixelacion localizada en monto o fecha, fuentes mixtas en el mismo campo, elementos pegados.\n"
        "- Referencias o folios con valores genericos (000000, 123456, 111111).\n\n"
        "REGLAS SOBRE LO QUE NO DEBES MARCAR COMO RIESGO:\n"
        "- Horario de la transferencia: SPEI opera las 24 horas, los 7 dias. Madrugada, noche, fin de semana son VALIDOS.\n"
        "- Montos bajos: no existe monto minimo en SPEI. $1, $9.54, $50 son completamente validos.\n"
        "- Concepto 'reverso', 'devolucion', 'reembolso' u otros: son conceptos libres validos, NO son operaciones automaticas del banco necesariamente.\n"
        "- Cualquier concepto libre escrito por el usuario: tacos, renta, reverso, pago, etc.\n\n"
        "CRITERIOS DE ANALISIS:\n"
        "1. ESTRUCTURAL: Consistencia de folios, referencias, montos, fechas, horas, campos obligatorios.\n"
        "2. SEMANTICO: Coherencia entre texto y operacion, banco y terminologia, conceptos y formato.\n"
        "3. TEMPORAL: Fechas futuras, fechas imposibles, horas imposibles, operaciones excesivamente antiguas.\n"
        "4. VISUAL: Recortes sospechosos, campos truncados, elementos inconsistentes, calidad anormal, manipulaciones visibles.\n"
        "5. CONTEXTUAL: Datos incompletos, inconsistencias entre origen y destino.\n\n"
        "EXTRACCION DE CAMPOS:\n"
        "Extrae unicamente si son visibles. Para cada campo genera valor y confianza:\n"
        "1.00 = completamente visible | 0.80 = muy probable | 0.60 = parcialmente visible | 0.40 = incierto | 0.20 = especulacion minima\n\n"
        "IMPORTANTE para el campo 'monto': extrae el valor NUMERICO puro, siempre en positivo (sin signo), sin simbolos ni comas. Ejemplo: '$1,234.56' -> '1234.56'. Ejemplo: '-$40.00' -> '40.00' (el signo negativo es solo de despliegue, no forma parte del monto real).\n\n"
        "SCORING: 0-20 = riesgo bajo | 21-50 = riesgo medio | 51-80 = riesgo alto | 81-100 = riesgo critico\n\n"
        "RIESGO: Solo puede ser BAJO, MEDIO, ALTO, CRITICO o INDETERMINADO.\n\n"
        "VALIDACIONES: Genera validaciones con categoria, nombre, status (ok|warn|fail|info) y detalle.\n\n"
        "RECOMENDACIONES accionables. Ejemplos:\n"
        "- Esperar acreditacion bancaria antes de entregar.\n"
        "- Solicitar comprobante completo con folio visible.\n"
        "- Confirmar con CEP de Banxico en banxico.org.mx/cep\n"
        "- No entregar producto hasta validacion bancaria.\n\n"
        "RESPUESTA: Devuelve EXCLUSIVAMENTE JSON valido, sin markdown, sin backticks, sin texto adicional.\n\n"
        '{"riesgo":"BAJO|MEDIO|ALTO|CRITICO|INDETERMINADO","score":0,"campos_extraidos":{'
        '"banco_origen":{"valor":null,"confianza":0.0},'
        '"banco_destino":{"valor":null,"confianza":0.0},'
        '"monto":{"valor":null,"confianza":0.0},'
        '"monto_texto":{"valor":null,"confianza":0.0},'
        '"fecha":{"valor":null,"confianza":0.0},'
        '"hora":{"valor":null,"confianza":0.0},'
        '"referencia":{"valor":null,"confianza":0.0},'
        '"clave_rastreo":{"valor":null,"confianza":0.0},'
        '"folio":{"valor":null,"confianza":0.0},'
        '"clabe_parcial":{"valor":null,"confianza":0.0},'
        '"nombre_receptor":{"valor":null,"confianza":0.0},'
        '"concepto":{"valor":null,"confianza":0.0}'
        '},"validaciones":[{"categoria":"estructural|visual|temporal|contextual|semantica","nombre":"string","status":"ok|warn|fail|info","detalle":"string"}],'
        '"resumen":"2-3 oraciones explicando el veredicto","recomendacion":"accion concreta y accionable"}'
    )


def extract_field_value(campo) -> str | None:
    if campo is None:
        return None
    if isinstance(campo, dict):
        return campo.get("valor")
    return str(campo) if campo else None


# ─────────────────────────────────────────────────────────────────────────────
# CEP BANXICO
# ─────────────────────────────────────────────────────────────────────────────

async def query_cep(clave: str, fecha_banxico: str):
    url = "https://www.banxico.org.mx/cep/go?i=1&t=&s=" + clave + "&d=" + fecha_banxico
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http:
        resp = await http.get(url)
    if resp.status_code != 200:
        return False, ""
    html = resp.text
    not_found = (
        "no se encontro" in html.lower() or
        "no existe" in html.lower() or
        len(html) < 500
    )
    return not not_found, html


async def verify_cep(clave_rastreo: str, referencia: str, fecha: str, monto: float,
                     banco_origen: str, banco_destino: str) -> dict:
    """
    Estados posibles de 'status':
      NO_EXISTE  -> no se encontro ninguna operacion en Banxico con esa clave
      EXISTE     -> se encontro la operacion Y el monto coincide (verificacion completa)
      PARCIAL    -> se encontro la operacion pero NO se pudo confirmar el monto
                    (CEP no expuso el monto en el HTML estatico, o el monto no coincide)
      ERROR      -> fallo la consulta (excepcion)
      TIMEOUT    -> Banxico no respondio a tiempo

    Item 1.6 (Observabilidad): cada rama registra su duracion y un evento de
    dominio en metrics_service bajo el namespace "cep" (distinto del
    namespace "xml" de cep_xml_auto_service.py -- este mide el scraping del
    HTML del CEP, no la descarga del XML oficial).
    """
    t_inicio = time.time()
    try:
        fecha_clean = re.sub(r"[^\d]", "", fecha)
        if len(fecha_clean) < 8:
            metrics_service.registrar_evento("cep", "cep_fecha_invalida")
            metrics_service.registrar_error("cep", duracion_ms=(time.time() - t_inicio) * 1000)
            return {"found": False, "status": "FECHA_INVALIDA", "confidence": 0,
                    "detalle": "No fue posible normalizar la fecha: " + fecha}
        fecha_banxico = fecha_clean[:8]

        claves_a_intentar = []
        if clave_rastreo:
            claves_a_intentar.append(("clave_rastreo", clean_clave_rastreo(clave_rastreo)))
        if referencia and referencia != clave_rastreo:
            claves_a_intentar.append(("referencia", referencia.strip()))

        found_html = None
        clave_usada = None
        tipo_clave_usada = None

        for tipo, clave in claves_a_intentar:
            encontrado, html = await query_cep(clave, fecha_banxico)
            if encontrado:
                found_html = html
                clave_usada = clave
                tipo_clave_usada = tipo
                break

        if not found_html:
            claves_intentadas = ", ".join(c for _, c in claves_a_intentar)
            metrics_service.registrar_evento("cep", "cep_no_existe")
            metrics_service.registrar_exito("cep", duracion_ms=(time.time() - t_inicio) * 1000)
            return {
                "found": False,
                "status": "NO_EXISTE",
                "confidence": 0,
                "detalle": "No se encontro la transferencia en CEP Banxico. Claves consultadas: " + claves_intentadas
            }

        # ── Extracción robusta del monto ──────────────────────────────────────
        montos_cep = extract_montos_from_html(found_html)
        monto_comprobante = normalize_monto_float(str(monto)) if monto > 0 else 0.0
        cep_sin_monto = len(montos_cep) == 0
        match_monto = None  # None=indeterminado | True=coincide | False=difiere

        if monto_comprobante > 0 and not cep_sin_monto:
            match_monto = montos_coinciden(monto_comprobante, montos_cep)

        montos_str = (
            ", ".join("$" + "{:,.2f}".format(m) for m in montos_cep)
            if montos_cep else None
        )

        # URL directa al CEP con datos pre-llenados
        cep_url = (
            "https://www.banxico.org.mx/cep/go?i=1&t=&s="
            + str(clave_usada) + "&d=" + fecha_banxico
        )

        # ── FIX 2: status y mensajes mas precisos forensicamente ───────────────
        # Antes: cuando no se podia leer el monto del HTML dinamico, se decia
        # "CONFIRMADA" con confidence 0.85. Eso es enganoso: existir en Banxico
        # no es lo mismo que estar verificada (monto/origen/destino). Ahora se
        # distingue EXISTE (verificacion completa con monto coincidente) de
        # PARCIAL (se localizo la operacion pero falta confirmar el monto).
        if match_monto is True:
            status = "EXISTE"
            confidence = 1.0
            detalle = (
                "Transferencia CONFIRMADA en CEP Banxico. "
                "Clave: " + str(clave_usada) + ". "
                "Monto verificado: $" + "{:,.2f}".format(monto_comprobante) + ". "
                "Esta transferencia existe en los registros oficiales de Banxico y el monto coincide."
            )
        elif match_monto is False:
            status = "PARCIAL"
            confidence = 0.5
            detalle = (
                "Se localizo una operacion en CEP Banxico (clave: " + str(clave_usada) + ") "
                "pero el monto NO coincide: comprobante=$" + "{:,.2f}".format(monto_comprobante)
                + " / CEP=" + str(montos_str) + ". "
                "Posible alteracion del monto. Verifica manualmente en: " + cep_url
            )
        elif monto_comprobante <= 0:
            status = "PARCIAL"
            confidence = 0.6
            detalle = (
                "Se localizo una operacion en CEP Banxico (clave: " + str(clave_usada) + "). "
                "No se detecto monto en el comprobante para comparar, por lo que la verificacion "
                "es PARCIAL. Revisa el monto directamente en: " + cep_url
            )
        else:
            # Operacion localizada, pero el HTML estatico de Banxico no expuso
            # el monto (requiere JS dinamico) -> no podemos confirmar coincidencia.
            status = "PARCIAL"
            confidence = 0.65
            detalle = (
                "Se localizo una operacion coincidente en CEP Banxico "
                "(clave: " + str(clave_usada) + ", fecha: " + fecha_banxico + "). "
                "No fue posible validar el monto automaticamente porque el CEP "
                "requiere carga dinamica para mostrarlo. Monto en comprobante: "
                "$" + "{:,.2f}".format(monto_comprobante) + ". "
                "Se recomienda confirmar manualmente en: " + cep_url
            )

        metrics_service.registrar_evento("cep", "cep_existe" if status == "EXISTE" else "cep_parcial")
        metrics_service.registrar_exito("cep", duracion_ms=(time.time() - t_inicio) * 1000)

        return {
            "found": True,
            "status": status,
            "confidence": confidence,
            "match_monto": match_monto,
            "cep_sin_monto": cep_sin_monto,
            "monto_comprobante": monto_comprobante,
            "montos_cep": montos_cep,
            "clave_usada": clave_usada,
            "tipo_clave": tipo_clave_usada,
            "cep_url": cep_url,
            "detalle": detalle,
        }

    except httpx.TimeoutException:
        metrics_service.registrar_evento("cep", "cep_timeout")
        metrics_service.registrar_error("cep", duracion_ms=(time.time() - t_inicio) * 1000, timeout=True)
        return {"found": False, "status": "TIMEOUT", "confidence": 0,
                "detalle": "Tiempo de espera agotado al consultar CEP de Banxico."}
    except Exception as e:
        metrics_service.registrar_evento("cep", "cep_error")
        metrics_service.registrar_error("cep", duracion_ms=(time.time() - t_inicio) * 1000)
        return {"found": False, "status": "ERROR", "confidence": 0,
                "detalle": "Error al consultar CEP: " + str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/analizar")
@limiter.limit("3/minute")
async def analizar(
    request: Request,
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form(""),
    fecha_pasada_confirmada: str = Form("false"),
    xml_cep: UploadFile | None = File(None),
):
    contenido = await file.read()
    t_inicio_analizar = time.time()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")
    fecha_confirmada = fecha_pasada_confirmada.lower() == "true"

    # ── Hash SHA-256 del comprobante ───────────────────────────────────────
    # Se calcula ANTES de enviar nada a Claude. Si DATABASE_URL no está
    # configurada todavía, esto degrada con gracia (ver hash_service.py):
    # se calcula y reporta el hash pero no hay detección de reutilización
    # entre peticiones distintas.
    # empresa_id usa DEFAULT_EMPRESA_ID mientras no exista autenticación
    # multiempresa real (ver database.py).
    hash_info = registrar_y_consultar_hash(contenido, empresa_id=DEFAULT_EMPRESA_ID)

    system_prompt = build_system_prompt(fecha_hoy, fecha_legible, banco_hint, clabe_hint, fecha_confirmada)

    if media_type == "application/pdf":
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de analisis."}
        ]
    else:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de analisis."}
        ]

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    raw = response.content[0].text.strip()

    match = re.search(r'\{[\s\S]*\}', raw)
    if not match:
        metrics_service.registrar_evento("analizar", "documento_no_reconocido")
        metrics_service.registrar_error("analizar", duracion_ms=(time.time() - t_inicio_analizar) * 1000)
        return {
            "riesgo": "INDETERMINADO",
            "score": 0,
            "campos_extraidos": {},
            "validaciones": [{
                "categoria": "contextual",
                "nombre": "Documento no reconocido",
                "status": "warn",
                "detalle": "El documento no parece ser un comprobante de transferencia bancaria."
            }],
            "resumen": "No fue posible analizar el documento. Sube un comprobante de transferencia bancaria valido.",
            "recomendacion": "Sube una imagen mas clara o un PDF del comprobante generado por tu banco."
        }

    result = json.loads(match.group(0))

    campos_raw = result.get("campos_extraidos", {})
    campos_planos = {}
    for key, val in campos_raw.items():
        campos_planos[key] = extract_field_value(val)

    banco_origen = campos_planos.get("banco_origen") or banco_hint or None
    iat_result = calculate_iat(campos_planos, banco_origen)

    # ── Columnas desnormalizadas para el dashboard ──────────────────────────
    # Se calculan aqui (independiente del bloque CEP, que solo corre bajo
    # ciertas condiciones) para que siempre esten disponibles al guardar la
    # auditoria, permitiendo filtros rapidos en /api/v1/dashboard/* sin abrir
    # el JSONB resultado.
    monto_detectado_general = normalize_monto_float(str(campos_planos.get("monto") or ""))
    if monto_detectado_general <= 0 and campos_planos.get("monto_texto"):
        monto_detectado_general = normalize_monto_float(str(campos_planos.get("monto_texto")))
    clabe_detectada_general = (
        (campos_planos.get("clabe_parcial") or "").replace(" ", "").replace("*", "").replace(".", "")
    )[:18] or None

    claude_score = result.get("score", 50)
    final_score = fuse_scores(claude_score, iat_result["iat_score"])
    result["score"] = final_score
    result["iat_score"] = iat_result["iat_score"]
    result["iat_metricas"] = iat_result["metricas"]

    iat_validaciones = iat_anomalias_to_validaciones(iat_result["anomalias"])
    result["validaciones"] = (result.get("validaciones") or []) + iat_validaciones

    # ── CLABE ingresada por el usuario ────────────────────────────────────────
    if len(clabe_hint) == 18:
        cv = validate_clabe(clabe_hint)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE ingresada - digito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                "CLABE valida. Banco: " + cv["bank"] + " (codigo " + cv["bank_code"] + ")"
                if cv["valid"] else "CLABE invalida: " + cv["reason"]
            ),
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"
        # Devolver resultado para que el frontend NO recalcule
        result["clabe_resultado"] = {
            "valid": cv["valid"],
            "bank": cv.get("bank", ""),
            "bank_code": cv.get("bank_code", ""),
            "reason": cv.get("reason", ""),
            "clabe": clabe_hint,
        }

    # ── CLABE visible en el comprobante ──────────────────────────────────────
    clabe_raw = (
        (campos_planos.get("clabe_parcial") or "")
        .replace(" ", "").replace("*", "").replace(".", "")
    )
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante - digito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                "CLABE valida. Banco: " + cv["bank"] + " (codigo " + cv["bank_code"] + ")"
                if cv["valid"] else "CLABE invalida: " + cv["reason"]
            ),
        }
        validaciones = result.get("validaciones", [])
        idx = next(
            (i for i, v in enumerate(validaciones)
             if "clabe" in v.get("nombre", "").lower()
             and "ingresada" not in v.get("nombre", "").lower()),
            -1,
        )
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"
        result["clabe_comprobante"] = {
            "valid": cv["valid"],
            "bank": cv.get("bank", ""),
            "bank_code": cv.get("bank_code", ""),
        }

    # ── Hash del documento: reutilización ─────────────────────────────────────
    # Criterio forense importante: el mismo archivo subido más de una vez NO es
    # prueba de fraude por sí solo (puede ser un reenvío legítimo, una segunda
    # consulta del mismo usuario, etc.). SHA-256 solo detecta "mismo archivo
    # exacto" — no detecta una captura recortada distinta ni un PDF regenerado
    # de la misma transferencia. Por eso esto entra como advertencia (warn) y
    # suma 10 puntos, nunca escala el riesgo a ALTO de forma automática. La
    # señal fuerte real vendrá del fingerprint transaccional (Fase 2).
    result["hash_documento"] = hash_info["hash_documento"]
    result["veces_visto"] = hash_info["veces_visto"]
    result["documento_reutilizado"] = hash_info["documento_reutilizado"]

    if hash_info["documento_reutilizado"]:
        veces = hash_info["veces_visto"]
        detalle_hash = (
            "Este comprobante exacto ya fue analizado anteriormente "
            + str(veces - 1) + " vez(es) (visto " + str(veces) + " veces en total"
            + (". Primer analisis: " + hash_info["primer_analisis"][:10] if hash_info.get("primer_analisis") else "")
            + "). Esto no confirma fraude por si solo: puede tratarse de un reenvio "
            "legitimo o una segunda consulta del mismo comprobante."
        )
        result["validaciones"].append({
            "categoria": "historial",
            "nombre": "Documento previamente analizado",
            "status": "warn",
            "detalle": detalle_hash,
        })
        final_score = final_score + 10

    # ── Detección de fecha pasada ─────────────────────────────────────────────
    fecha_campo = campos_planos.get("fecha") or ""
    es_pasada, dias_diferencia = fecha_es_pasada(fecha_campo)
    requiere_confirmacion_fecha = es_pasada and not fecha_confirmada and dias_diferencia > 0
    result["requiere_confirmacion_fecha"] = requiere_confirmacion_fecha
    result["dias_diferencia"] = dias_diferencia if es_pasada else 0

    if requiere_confirmacion_fecha:
        result["mensaje_confirmacion_fecha"] = (
            "El comprobante tiene fecha " + fecha_campo
            + " (" + str(dias_diferencia) + " dia(s) atras). "
            "Si estas validando una transferencia pasada, confirma para que el sistema "
            "no penalice la fecha y el analisis sea mas preciso."
        )

    # ── CEP de Banxico ────────────────────────────────────────────────────────
    clave_rastreo = campos_planos.get("clave_rastreo") or ""
    referencia = campos_planos.get("referencia") or ""
    monto_str = campos_planos.get("monto") or ""
    monto_texto_str = campos_planos.get("monto_texto") or ""
    fecha_str = campos_planos.get("fecha") or ""

    cep = None  # queda None si no hubo datos suficientes para intentar la consulta

    if (clave_rastreo or referencia) and fecha_str:
        monto_num = normalize_monto_float(str(monto_str)) if monto_str else 0.0
        if monto_num <= 0 and monto_texto_str:
            monto_num = normalize_monto_float(str(monto_texto_str))

        cep = await verify_cep(
            clave_rastreo=str(clave_rastreo),
            referencia=str(referencia),
            fecha=str(fecha_str),
            monto=monto_num,
            banco_origen=str(campos_planos.get("banco_origen") or ""),
            banco_destino=str(campos_planos.get("banco_destino") or ""),
        )

        # ── FIX 2 (cont.): badge del CEP ahora distingue PARCIAL de EXISTE ────
        # ok    -> EXISTE con monto confirmado
        # warn  -> PARCIAL (encontrada pero monto sin confirmar o no coincide)
        # info  -> NO_EXISTE / ERROR / TIMEOUT / FECHA_INVALIDA
        if cep.get("status") == "EXISTE":
            cep_status = "ok"
        elif cep.get("status") == "PARCIAL":
            cep_status = "warn"
        else:
            cep_status = "info"

        cep_entry = {
            "categoria": "cep",
            "nombre": "CEP Banxico - Verificacion SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP."),
        }
        if cep.get("cep_url"):
            cep_entry["cep_url"] = cep["cep_url"]
        result["validaciones"].append(cep_entry)
        result["cep_resultado"] = cep

        # Solo penalizar score legacy si el monto definitivamente no coincide
        if cep.get("found") and cep.get("match_monto") is False and monto_num > 0:
            final_score = max(final_score, 50)

    # ── Score y riesgo final (legacy, sin cambios de logica, solo clamping) ────
    # FIX: se detecto en produccion un score de 101.5 -- ocurria porque las
    # lineas "final_score = max(final_score, N)" de arriba no tienen techo
    # si final_score ya superaba 100 antes de esa linea (ej. fusion de
    # Claude+IAT+ajustes). Se mantiene la logica intacta, solo se agrega
    # clamping final a [0,100].
    final_score = max(0.0, min(100.0, final_score))
    result["score"] = round(final_score, 2)
    if final_score >= 81:
        result["riesgo"] = "CRITICO"
    elif final_score >= 51:
        result["riesgo"] = "ALTO"
    elif final_score >= 21:
        result["riesgo"] = "MEDIO"
    else:
        result["riesgo"] = "BAJO"

    result["campos_extraidos"] = campos_planos

    # ── Scoring v3: 4 dimensiones separadas ─────────────────────────────────────
    # confianza_documental / verificabilidad / contexto_temporal / estado_operacion.
    # No reemplazan a score/riesgo (arriba) -- son campos NUEVOS y adicionales.
    # Ver scoring_v3.py para el detalle de que esta anclado a Circular 14/2017 +
    # estados oficiales de consulta SPEI, y que es decision de producto.
    # ── Motor 1: Estado SPEI — fuente inicial desde el scraping del CEP HTML ──
    # La fuente puede ser actualizada a xml_oficial mas adelante en este mismo
    # endpoint, si el XML se descarga exitosamente. El estado SPEI nunca es
    # modificado por el Motor 2 (analisis documental de VerificaPago).
    estado_operacion = mapear_estado_cep_a_estado_operacion(
        status_cep=(cep.get("status") if cep else "NO_EXISTE"),
        found=bool(cep and cep.get("found")),
    )
    fuente_estado = NivelEvidencia.CEP_HTML if (cep and cep.get("found")) else NivelEvidencia.NO_DISPONIBLE

    contexto_temporal_result = evaluar_contexto_temporal(
        fecha_comprobante=campos_planos.get("fecha"),
        hora_comprobante=campos_planos.get("hora"),
        estado_operacion=estado_operacion,
    )

    verificabilidad_result = evaluar_verificabilidad(
        campos_planos=campos_planos,
        estado_operacion=estado_operacion,
        cep_resultado=cep,
    )

    # confianza_documental: inverso del score de riesgo documental de Claude.
    # Es la base del Motor 2 (integridad del comprobante), completamente
    # independiente del Motor 1 (estado SPEI).
    confianza_documental = max(0.0, min(100.0, 100.0 - claude_score))

    # ── Motor 2: Integridad documental — independiente del estado SPEI ─────────
    # Determina si el comprobante como documento tiene observaciones,
    # sin que eso afecte ni contradiga el estado oficial de Banxico.
    tiene_anomalias_altas = any(
        a.get("severidad") == "alta"
        for a in (iat_result.get("anomalias") or [])
    )
    integridad_comprobante = calcular_integridad_comprobante(
        confianza_documental=confianza_documental,
        tiene_anomalias_altas=tiene_anomalias_altas,
    )

    result["confianza_documental"] = confianza_documental
    result["verificabilidad"] = verificabilidad_result["score"]
    result["contexto_temporal"] = contexto_temporal_result["score"]

    # Motor 1 — campos SPEI (fuente: Banxico, nunca modificados por el Motor 2)
    result["estado_operacion"] = estado_operacion.value
    result["fuente_estado"] = fuente_estado
    result["nivel_evidencia"] = fuente_estado
    result["semaforo_spei"] = SEMAFORO_SPEI.get(estado_operacion, SEMAFORO_SPEI[EstadoOperacion.DESCONOCIDA])

    # Motor 2 — integridad documental (fuente: VerificaPago)
    result["integridad_comprobante"] = integridad_comprobante
    result["integridad_config"] = INTEGRIDAD_CONFIG.get(integridad_comprobante, {})

    result["contexto_operacional"] = None  # reservado para version futura (MonSPEI/incidentes)

    result["interpretacion"] = generar_interpretacion(
        confianza_documental=confianza_documental,
        verificabilidad=verificabilidad_result["score"],
        contexto_temporal=contexto_temporal_result["score"],
        estado_operacion=estado_operacion,
    )

    result["detalle_temporal"] = contexto_temporal_result["explicacion"]
    result["elementos_verificabilidad"] = verificabilidad_result["elementos_disponibles"]

    # ── XML oficial del CEP (Fase 2: manual + Fase 2-B: automatico) ─────────────
    # Prioridad: si el usuario adjunto el XML manualmente, se usa ese (no se
    # vuelve a consultar Banxico). Si no lo adjunto, se intenta descargarlo
    # automaticamente usando los datos que el OCR ya extrajo del comprobante
    # -- sin pedirle nada nuevo al usuario salvo que falte algun dato.
    #
    # La descarga automatica replica una secuencia de Banxico NO documentada
    # publicamente (GET / -> POST valida.do -> GET descarga.do), investigada
    # y confirmada en el chat: el campo de captcha que aparece en el HTML del
    # navegador no se valida del lado del servidor en valida.do. Aun asi, por
    # ser un endpoint no documentado, todo este flujo puede romperse sin
    # aviso si Banxico cambia su implementacion -- por eso degrada con gracia
    # en cualquier punto de fallo, sin afectar el resto del analisis.
    #
    # NO se valida la firma digital del XML localmente en ningun caso (manual
    # o automatico) -- esa via se investigo a fondo y se refuto con una
    # prueba criptografica real (ver scoring_v3.py / discusion del chat).
    xml_bytes_a_procesar = None
    origen_xml = None

    if xml_cep is not None:
        xml_bytes_a_procesar = await xml_cep.read()
        origen_xml = "manual"
    else:
        chequeo = datos_suficientes_para_consulta(campos_planos)
        if chequeo["suficiente"]:
            d = chequeo["datos"]
            descarga = await descargar_xml_cep_automatico(
                clave_o_referencia=d["clave_o_referencia"],
                fecha_ddmmyyyy=d["fecha"],
                banco_emisor_spei=d["banco_emisor"],
                banco_receptor_spei=d["banco_receptor"],
                cuenta=d["cuenta"],
                monto=d["monto"],
                hash_sha256=hash_info.get("hash_documento"),
            )
            if descarga["exito"]:
                xml_bytes_a_procesar = descarga["xml_bytes"]
                origen_xml = "automatico"
            else:
                result["cep_xml"] = {
                    "xml_proporcionado": False,
                    "intento_automatico": True,
                    "automatico_exitoso": False,
                    "razon": descarga["razon"],
                }
        else:
            result["cep_xml"] = {
                "xml_proporcionado": False,
                "intento_automatico": False,
                "datos_faltantes": chequeo["faltantes"],
            }

    if xml_bytes_a_procesar is not None:
        try:
            xml_datos = parsear_xml_cep(xml_bytes_a_procesar)
            comparacion = comparar_xml_contra_comprobante(xml_datos, campos_planos)
            result["cep_xml"] = construir_resultado_xml(xml_datos, comparacion)
            result["cep_xml"]["origen"] = origen_xml

            # ── Motor 1: actualizar estado SPEI desde el XML si tiene mayor jerarquia ──
            # El XML oficial es la fuente de mayor jerarquia disponible hoy.
            # Si el XML aporta un estado mas confiable que el que ya teniamos
            # (del scraping del CEP HTML), lo reemplaza. Esta es la unica forma
            # en que el estado SPEI puede cambiar: cuando una fuente de evidencia
            # de mayor nivel lo actualiza. Nunca puede ser cambiado por el Motor 2.
            nuevo_nivel = NivelEvidencia.XML_OFICIAL
            if evidencia_mas_alta(result.get("fuente_estado", NivelEvidencia.NO_DISPONIBLE), nuevo_nivel):
                estado_desde_xml = extraer_estado_de_xml(xml_datos)
                result["estado_operacion"] = estado_desde_xml.value
                result["fuente_estado"] = nuevo_nivel
                result["nivel_evidencia"] = nuevo_nivel
                result["semaforo_spei"] = SEMAFORO_SPEI.get(
                    estado_desde_xml, SEMAFORO_SPEI[EstadoOperacion.DESCONOCIDA]
                )
                # Actualizar tambien el contexto temporal y el semaforo categorico
                # con el nuevo estado de mayor certeza.
                contexto_temporal_result = evaluar_contexto_temporal(
                    fecha_comprobante=campos_planos.get("fecha"),
                    hora_comprobante=campos_planos.get("hora"),
                    estado_operacion=estado_desde_xml,
                )
                result["contexto_temporal"] = contexto_temporal_result["score"]
                result["detalle_temporal"] = contexto_temporal_result["explicacion"]

            # ── Motor 2: comparacion de campos (no afecta el estado SPEI) ──────────
            # Ver ROADMAP.md item 1.3: en vez de un mensaje agregado unico, se
            # genera una entrada de validacion POR CAMPO comparado, para que la
            # UI pueda mostrar el desglose (Monto coincide / Banco coincide /
            # etc.) en vez de un solo veredicto opaco. cep_xml_service.py ya
            # calcula esto en comparacion["comparaciones"] -- aqui solo se
            # traduce cada entrada a una validacion legible.
            NOMBRES_CAMPO_XML = {
                "monto": "Monto",
                "fecha": "Fecha",
                "clave_rastreo": "Clave de rastreo",
                "banco_destino": "Banco receptor",
                "cuenta_destino_ultimos_digitos": "Cuenta destino",
            }
            origen_xml_texto = "adjuntado" if origen_xml == "manual" else "obtenido automáticamente"

            for c in comparacion["comparaciones"]:
                nombre_campo = NOMBRES_CAMPO_XML.get(c["campo"], c["campo"])
                if c["coincide"] is True:
                    status = "ok"
                    detalle = f"{nombre_campo} coincide con el XML oficial del CEP ({origen_xml_texto})."
                elif c["coincide"] is False:
                    status = "fail"
                    detalle = (
                        f"{nombre_campo} NO coincide: comprobante='{c['valor_comprobante']}' "
                        f"/ XML oficial='{c['valor_xml']}'."
                    )
                else:
                    # coincide is None -- ej. fecha, formato variable entre bancos,
                    # se reporta como informativo, no como fallo ni acierto.
                    status = "info"
                    detalle = (
                        f"{nombre_campo} en el comprobante: '{c['valor_comprobante']}'. "
                        f"{nombre_campo} en el XML oficial: '{c['valor_xml']}'. "
                        "El formato varía entre bancos — revisa manualmente si es necesario."
                    )
                result["validaciones"].append({
                    "categoria": "cep_xml",
                    "nombre": nombre_campo,
                    "status": status,
                    "detalle": detalle,
                })

            if comparacion["discrepancias"] == 0 and comparacion["coincidencias"] >= 3:
                verificabilidad_result["score"] = min(100, verificabilidad_result["score"] + 10)
                result["verificabilidad"] = verificabilidad_result["score"]
                result["elementos_verificabilidad"].append(
                    f"XML oficial del CEP ({origen_xml_texto}) coincide con los datos del comprobante"
                )
        except XMLCepInvalido as e:
            result["cep_xml"] = {
                "xml_proporcionado": xml_cep is not None,
                "origen": origen_xml,
                "estructura_xml_valida": False,
                "error": str(e),
            }
        except Exception as e:
            logger.warning("Error al procesar XML del CEP: %s", e)
            result["cep_xml"] = {
                "xml_proporcionado": xml_cep is not None,
                "origen": origen_xml,
                "estructura_xml_valida": False,
                "error": "Error inesperado al procesar el archivo.",
            }

            # ── Evidencias (item 5.1, Etapa 5): hechos crudos, sin interpretar ────────
    # Paso intermedio hacia el Motor de Presentación completo (ver ROADMAP.md).
    # Mobile puede empezar a decidir sobre estos datos explícitos mientras se
    # estabiliza el objeto `presentation` -- no reemplaza los campos que ya
    # existen en el nivel superior de result (estado_operacion, etc.), los
    # agrupa para que el frontend no tenga que rearmar esta forma cada vez.
    cep_xml_data = result.get("cep_xml") or {}
    if cep_xml_data.get("xml_proporcionado"):
        xml_valido = cep_xml_data.get("estructura_xml_valida", False)
        xml_discrepancias = cep_xml_data.get("comparacion_campos", {}).get("discrepancias")
    else:
        # No es lo mismo "no se intento obtener XML" que "XML invalido" --
        # None distingue ambos casos en vez de forzar False.
        xml_valido = None
        xml_discrepancias = None
 
    result["evidencias"] = {
        "xml_valido": xml_valido,
        "xml_discrepancias": xml_discrepancias,
        "confianza_documental": confianza_documental,
        "verificabilidad": verificabilidad_result["score"],
        "contexto_temporal": contexto_temporal_result["score"],
        "hash_reutilizado": hash_info["documento_reutilizado"],
    }

    # ── Auditoría: guardar el análisis completo ────────────────────────────────
    # Si DATABASE_URL no está configurada, guardar_analisis() devuelve None
    # sin lanzar excepción y la respuesta se entrega igual al usuario.
    # empresa_id usa DEFAULT_EMPRESA_ID mientras no exista autenticación
    # multiempresa real (ver database.py).
    try:
        audit_id = guardar_analisis(
            hash_sha256=hash_info.get("hash_documento"),
            score_claude=claude_score,
            score_iat=iat_result["iat_score"],
            score_final=result["score"],
            riesgo=result["riesgo"],
            resultado=result,
            empresa_id=DEFAULT_EMPRESA_ID,
            archivo_nombre=file.filename,
            archivo_tipo=media_type,
            monto_detectado=monto_detectado_general if monto_detectado_general > 0 else None,
            banco_detectado=campos_planos.get("banco_origen") or banco_hint or None,
            clabe_detectada=clabe_detectada_general,
            estado_operacion=result.get("estado_operacion"),
            fuente_estado=result.get("fuente_estado"),
            nivel_evidencia=result.get("nivel_evidencia"),
            clave_rastreo=campos_planos.get("clave_rastreo") or None,
            referencia=campos_planos.get("referencia") or None,
        )
        if audit_id:
            result["audit_id"] = audit_id
    except Exception as e:
        logger.error("No fue posible guardar auditoria: %s", e)

    # ── Alert Engine: evaluar reglas de deteccion (item 3.3, Etapa 3) ────────
    # Ver DECISION_LOG.md, ADR "las alertas son eventos persistentes...".
    # Corre DESPUES de guardar el analisis -- nunca antes, y nunca modifica
    # el resultado que se le devuelve al usuario. Si el motor de alertas
    # falla, el analisis principal ya se completo y se devuelve igual.
    try:
        contexto_alertas = {
            "empresa_id": DEFAULT_EMPRESA_ID,
            "analisis_id": result.get("audit_id"),
            "hash_sha256": hash_info.get("hash_documento"),
            "veces_visto": hash_info.get("veces_visto"),
            "clabe_detectada": clabe_detectada_general,
            "clave_rastreo": campos_planos.get("clave_rastreo") or None,
            "banco_detectado": campos_planos.get("banco_origen") or banco_hint or None,
            "monto_detectado": monto_detectado_general if monto_detectado_general > 0 else None,
        }
        alert_engine.evaluar(contexto_alertas)
    except Exception as e:
        logger.warning("El Alert Engine fallo sin afectar el analisis: %s", e)


    metrics_service.registrar_exito("analizar", duracion_ms=(time.time() - t_inicio_analizar) * 1000)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# DASHBOARD DE AUDITORIA — /api/v1/dashboard/*
# ─────────────────────────────────────────────────────────────────────────────
# Rutas nuevas, versionadas desde el inicio bajo /api/v1/. El endpoint
# /analizar NO se toca ni se mueve aqui -- ya esta en produccion y conectado
# al frontend, y no aporta valor romperlo ahora (ver discusion en el chat).
#
# Todos los endpoints reciben empresa_id como query param opcional, con
# default DEFAULT_EMPRESA_ID. Esto permite que, cuando se active
# multiempresa real con autenticacion, el frontend solo necesite empezar a
# enviar el empresa_id correcto -- sin que estos endpoints cambien de forma.

dashboard_router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@dashboard_router.get("/stats")
def dashboard_stats(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
):
    return dashboard_service.obtener_stats(empresa_id=empresa_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


@dashboard_router.get("/analisis")
def dashboard_listar_analisis(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    riesgo: str | None = Query(default=None),
    estado_operacion: str | None = Query(default=None),
    hash_sha256: str | None = Query(default=None),
    banco: str | None = Query(default=None),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    q: str | None = Query(default=None, description="Búsqueda unificada: banco, clave de rastreo, referencia, CLABE o monto"),
):
    return dashboard_service.listar_analisis(
        empresa_id=empresa_id, limit=limit, offset=offset, riesgo=riesgo,
        estado_operacion=estado_operacion, hash_sha256=hash_sha256,
        banco=banco, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, q=q,
    )


@dashboard_router.get("/analisis/{analisis_id}")
def dashboard_detalle_analisis(
    analisis_id: str,
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
):
    detalle = dashboard_service.obtener_analisis_detalle(analisis_id=analisis_id, empresa_id=empresa_id)
    if detalle is None:
        raise HTTPException(status_code=404, detail="Analisis no encontrado")
    return detalle

@dashboard_router.get("/analisis/exportar")
def dashboard_exportar_analisis(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    riesgo: str | None = Query(default=None),
    estado_operacion: str | None = Query(default=None),
    hash_sha256: str | None = Query(default=None),
    banco: str | None = Query(default=None),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    q: str | None = Query(default=None),
):
    """
    Item 2.4 (ROADMAP.md, Etapa 2): exporta a CSV todos los análisis que
    coinciden con los filtros activos -- mismos parámetros que
    /api/v1/dashboard/analisis, pero sin paginación (hasta el límite de
    seguridad interno de exportar_analisis()). Devuelve exactamente lo
    que el usuario ve filtrado en el Historial, no solo la página cargada.
 
    Las etiquetas de estado_operacion se traducen a texto legible
    (Liquidada, En proceso, etc.) usando SEMAFORO_SPEI -- mismo mapeo que
    usa el resto del producto, para que el CSV hable el mismo idioma que
    la app.
    """
    items = dashboard_service.exportar_analisis(
        empresa_id=empresa_id, riesgo=riesgo, estado_operacion=estado_operacion,
        hash_sha256=hash_sha256, banco=banco, fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta, q=q,
    )
 
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Fecha", "Banco", "Monto", "Estado SPEI", "Riesgo documental",
        "Clave de rastreo", "Referencia", "Hash", "Veces analizado",
    ])
    for item in items:
        estado_enum = None
        try:
            estado_enum = EstadoOperacion(item["estado_operacion"]) if item["estado_operacion"] else None
        except ValueError:
            estado_enum = None
        etiqueta_estado = SEMAFORO_SPEI.get(estado_enum, {}).get("etiqueta", item["estado_operacion"] or "—") if estado_enum else "—"
 
        writer.writerow([
            item["fecha"],
            item["banco_detectado"],
            item["monto_detectado"] if item["monto_detectado"] is not None else "",
            etiqueta_estado,
            item["riesgo"],
            item["clave_rastreo"],
            item["referencia"],
            item["hash_sha256"],
            item["veces_visto"],
        ])
 
    buffer.seek(0)
    fecha_archivo = datetime.date.today().isoformat()
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=historial_verificapago_{fecha_archivo}.csv"},
    )

@dashboard_router.get("/hashes")
def dashboard_top_hashes(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    min_veces: int = Query(default=2),
    limit: int = Query(default=20, le=100),
):
    return dashboard_service.top_hashes_reutilizados(empresa_id=empresa_id, min_veces=min_veces, limit=limit)


@dashboard_router.get("/tendencia")
def dashboard_tendencia(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    dias: int = Query(default=30, le=365),
):
    return dashboard_service.tendencia_diaria(empresa_id=empresa_id, dias=dias)


@dashboard_router.get("/metricas/xml")
def dashboard_metricas_xml():
    """
    Métricas de la descarga automática del XML del CEP (item 1.6,
    Observabilidad, parcial): consultas, éxitos/fallos, cache hits/miss,
    reintentos, timeouts, duración. En memoria del proceso, no
    distribuidas ni persistentes -- ver metrics_service.py. Ruta anidada
    bajo /metricas/ a propósito: /metricas/ocr, /metricas/claude,
    /metricas/usuarios, etc. seguirán la misma estructura a futuro.
    """
    return metrics_service.obtener_metricas("xml")


@dashboard_router.get("/metricas/cep")
def dashboard_metricas_cep():
    """
    Métricas del scraping HTML del CEP (item 1.6) -- distinto de
    /metricas/xml, que mide la descarga del XML oficial. Este mide
    verify_cep(): tasa de éxito, eventos (cep_existe, cep_parcial,
    cep_no_existe, cep_timeout, cep_error), duración.
    """
    return metrics_service.obtener_metricas("cep")


@dashboard_router.get("/metricas/analizar")
def dashboard_metricas_analizar():
    """
    Métricas del endpoint /analizar completo (item 1.6): tiempo promedio de
    análisis de punta a punta (OCR + IAT + CEP + XML + persistencia), tasa
    de éxito, casos de documento no reconocido.
    """
    return metrics_service.obtener_metricas("analizar")


@dashboard_router.get("/metricas/scores-por-banco")
def dashboard_scores_por_banco(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    dias: int = Query(default=30, le=365),
    min_analisis: int = Query(default=1),
):
    """
    Item 1.6 (Observabilidad): distribución de scores de Claude Vision por
    banco detectado. A diferencia de /metricas/xml, /metricas/cep y
    /metricas/analizar (en memoria del proceso), esta consulta va contra
    la base de datos -- refleja el histórico completo, no solo lo ocurrido
    desde el último reinicio del servidor.
    """
    return dashboard_service.distribucion_scores_por_banco(
        empresa_id=empresa_id, dias=dias, min_analisis=min_analisis
    )


@dashboard_router.get("/alertas")
def dashboard_listar_alertas(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    estado: str | None = Query(default=None),
    severidad: str | None = Query(default=None),
    tipo_alerta: str | None = Query(default=None),
):
    """
    Item 3.4 (ROADMAP.md, Etapa 3): lista paginada de alertas generadas
    por el Alert Engine (item 3.3). Mismo patrón que /analisis: filtros
    opcionales, paginación con limit/offset.
    """
    return alerta_service.listar_alertas(
        empresa_id=empresa_id, limit=limit, offset=offset,
        estado=estado, severidad=severidad, tipo_alerta=tipo_alerta,
    )


@dashboard_router.patch("/alertas/{alerta_id}/estado")
def dashboard_cambiar_estado_alerta(
    alerta_id: str,
    nuevo_estado: str = Query(...),
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
):
    """
    Item 3.4: marca una alerta como REVISADA o DESCARTADA (o cualquier
    otro valor de estado -- no se restringe el flujo aquí, ver
    alerta_service.cambiar_estado_alerta()).
    """
    actualizado = alerta_service.cambiar_estado_alerta(
        alerta_id=alerta_id, nuevo_estado=nuevo_estado, empresa_id=empresa_id
    )
    if not actualizado:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"ok": True, "id": alerta_id, "estado": nuevo_estado}

@dashboard_router.get("/alertas/conteo")
def dashboard_conteo_alertas(empresa_id: str = Query(default=DEFAULT_EMPRESA_ID)):
    """
    Item 3.5: conteo de alertas para el badge inteligente de BottomNav.
    Separa el total de alertas NUEVA del subconjunto "notificable" (Motor
    de Prioridad, ver DECISION_LOG.md) -- el badge usa `notificables`.
    """
    return alerta_service.contar_alertas(empresa_id=empresa_id)

@dashboard_router.get("/monto-total")
def dashboard_monto_total(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
):
    """Item 4.1: monto total procesado en el periodo (KPI de volumen)."""
    return dashboard_service.obtener_monto_total_procesado(
        empresa_id=empresa_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
 
 
@dashboard_router.get("/bancos-frecuentes")
def dashboard_bancos_frecuentes(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
    limit: int = Query(default=5, le=20),
):
    """Item 4.1: top bancos por volumen de análisis (distinto de /metricas/scores-por-banco, que es por score)."""
    return dashboard_service.obtener_banco_mas_frecuente(
        empresa_id=empresa_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=limit
    )
 
 
@dashboard_router.get("/riesgo-por-periodo")
def dashboard_riesgo_por_periodo(
    empresa_id: str = Query(default=DEFAULT_EMPRESA_ID),
    fecha_desde: str | None = Query(default=None),
    fecha_hasta: str | None = Query(default=None),
):
    """Item 4.1: distribución por riesgo documental (Motor 2) y por estado_operacion (Motor 1) en el periodo."""
    return dashboard_service.obtener_riesgo_por_periodo(
        empresa_id=empresa_id, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta
    )
 
 
@dashboard_router.get("/alertas-agregadas")
def dashboard_alertas_agregadas(empresa_id: str = Query(default=DEFAULT_EMPRESA_ID)):
    """Item 4.1: conteo de alertas NUEVA por severidad y tipo."""
    return dashboard_service.obtener_alertas_agregadas(empresa_id=empresa_id)
 
 
@dashboard_router.get("/resumen-ejecutivo")
def dashboard_resumen_ejecutivo(empresa_id: str = Query(default=DEFAULT_EMPRESA_ID)):
    """
    Item 4.2 (Mobile Executive Summary): bundle de datos para la
    tarjeta resumen dentro de Perfil/Empresa -- una sola llamada.
    """
    return dashboard_service.obtener_resumen_ejecutivo(empresa_id=empresa_id)

@dashboard_router.get("/centro-operativo")
def dashboard_centro_operativo():
    """
    Item 5.5 (Etapa 5): bundle completo para el Centro Operativo
    (Desktop). Ver DESIGN_SYSTEM.md sección 10 para la estructura
    visual que consume esta respuesta.
    """
    return dashboard_service.obtener_centro_operativo()

app.include_router(dashboard_router)


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2", "modelo": MODEL_NAME}