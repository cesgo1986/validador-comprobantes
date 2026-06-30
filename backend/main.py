import json
import base64
import datetime
import re
import os
import httpx
from fastapi import FastAPI, UploadFile, File, Form, APIRouter, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import anthropic
from dotenv import load_dotenv
from iat import calculate_iat, fuse_scores, iat_anomalias_to_validaciones
from services.hash_service import registrar_y_consultar_hash
from services.auditoria_service import guardar_analisis
from services import dashboard_service
from database import init_db, DEFAULT_EMPRESA_ID
from services.cep_xml_service import parsear_xml_cep, comparar_xml_contra_comprobante, construir_resultado_xml, XMLCepInvalido
from services.cep_xml_auto_service import datos_suficientes_para_consulta, descargar_xml_cep_automatico
from scoring_v3 import (
    EstadoOperacion, mapear_estado_cep_a_estado_operacion,
    evaluar_contexto_temporal, evaluar_verificabilidad, generar_interpretacion,
)

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea las tablas (hashes_documentos, analisis) si no existen y si
# DATABASE_URL está configurada. Si no está configurada, init_db()
# devuelve False sin lanzar excepción — la app sigue funcionando, solo
# sin persistencia (ver database.py y hash_service.py para el detalle
# de cómo se degrada con gracia).
try:
    init_db()
except Exception as e:
    print("Aviso: no fue posible inicializar la base de datos:", e)

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
        "REGLAS SOBRE LO QUE SI DEBES MARCAR COMO RIESGO:\n"
        "- Fecha futura (posterior a hoy).\n"
        "- Monto en cero o negativo.\n"
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
        "IMPORTANTE para el campo 'monto': extrae el valor NUMERICO puro, sin simbolos ni comas. Ejemplo: '$1,234.56' -> '1234.56'.\n\n"
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
    """
    try:
        fecha_clean = re.sub(r"[^\d]", "", fecha)
        if len(fecha_clean) < 8:
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
        return {"found": False, "status": "TIMEOUT", "confidence": 0,
                "detalle": "Tiempo de espera agotado al consultar CEP de Banxico."}
    except Exception as e:
        return {"found": False, "status": "ERROR", "confidence": 0,
                "detalle": "Error al consultar CEP: " + str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINT PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form(""),
    fecha_pasada_confirmada: str = Form("false"),
    xml_cep: UploadFile | None = File(None),
):
    contenido = await file.read()
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
    estado_operacion = mapear_estado_cep_a_estado_operacion(
        status_cep=(cep.get("status") if cep else "NO_EXISTE"),
        found=bool(cep and cep.get("found")),
    )

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

    # confianza_documental reutiliza el score de Claude (analisis visual/OCR)
    # ya que esa es exactamente la pregunta que claude_score responde: ?se ve
    # autentico el documento? No incluye CEP ni tiempo, que es justo lo que
    # buscabamos separar. claude_score en el prompt actual es una escala de
    # RIESGO documental (0=riesgo bajo, 100=riesgo critico); confianza_documental
    # es su inverso, con clamping a [0,100] por si claude_score se desvia del
    # rango esperado (ver el bug de score>100 detectado en produccion).
    confianza_documental = max(0.0, min(100.0, 100.0 - claude_score))

    result["confianza_documental"] = confianza_documental
    result["verificabilidad"] = verificabilidad_result["score"]
    result["contexto_temporal"] = contexto_temporal_result["score"]
    result["estado_operacion"] = estado_operacion.value
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

            # Si el XML coincide con el comprobante en todos los campos
            # comparables, esto es evidencia adicional de verificabilidad
            # -- pero un boost moderado, no maximo, porque sigue sin ser
            # una validacion criptografica.
            if comparacion["discrepancias"] == 0 and comparacion["coincidencias"] >= 3:
                verificabilidad_result["score"] = min(100, verificabilidad_result["score"] + 10)
                result["verificabilidad"] = verificabilidad_result["score"]
                result["elementos_verificabilidad"].append(
                    f"XML oficial del CEP ({'adjuntado' if origen_xml == 'manual' else 'obtenido automaticamente'}) "
                    "coincide con los datos del comprobante"
                )
            elif comparacion["discrepancias"] > 0:
                # Discrepancia real entre el XML oficial y el comprobante
                # visual -- esto SI es una señal fuerte, agregada como
                # validacion explicita para que aparezca en el detalle.
                result["validaciones"].append({
                    "categoria": "cep_xml",
                    "nombre": "Discrepancia entre XML oficial y comprobante",
                    "status": "fail",
                    "detalle": (
                        f"Se encontraron {comparacion['discrepancias']} discrepancia(s) entre "
                        "el XML oficial del CEP y los datos visibles en el comprobante. "
                        "Esto es una señal relevante de posible alteración."
                    ),
                })
        except XMLCepInvalido as e:
            result["cep_xml"] = {
                "xml_proporcionado": xml_cep is not None,
                "origen": origen_xml,
                "estructura_xml_valida": False,
                "error": str(e),
            }
        except Exception as e:
            print("Aviso: error al procesar XML del CEP:", e)
            result["cep_xml"] = {
                "xml_proporcionado": xml_cep is not None,
                "origen": origen_xml,
                "estructura_xml_valida": False,
                "error": "Error inesperado al procesar el archivo.",
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
        )
        if audit_id:
            result["audit_id"] = audit_id
    except Exception as e:
        print("Aviso: no fue posible guardar auditoria:", e)

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
    hash_sha256: str | None = Query(default=None),
):
    return dashboard_service.listar_analisis(
        empresa_id=empresa_id, limit=limit, offset=offset, riesgo=riesgo, hash_sha256=hash_sha256
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


app.include_router(dashboard_router)


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2", "modelo": MODEL_NAME}