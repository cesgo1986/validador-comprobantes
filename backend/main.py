import json
import base64
import datetime
import re
import os
import httpx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import anthropic
from dotenv import load_dotenv
from iat import calculate_iat, fuse_scores, iat_anomalias_to_validaciones

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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

# Headers que simulan navegador real — Banxico bloquea requests sin User-Agent
CEP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
    "Referer": "https://www.banxico.org.mx/cep/",
}


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


def clean_clave_rastreo(clave: str) -> str:
    return clave.strip()


def normalize_monto_float(monto_str: str) -> float:
    """
    Convierte cualquier representacion de monto a float.
    Soporta: $1,234.56 / $1.234,56 / 1234.56 / MXN 1234.56 / 1 234.56 / 45,01
    """
    if not monto_str:
        return 0.0
    s = str(monto_str)
    # Quitar simbolos de moneda
    s = re.sub(r'(?i)(mxn|usd|pesos?|mx|\$)', '', s).strip()
    # Europeo: 1.234,56
    if re.search(r'\d\.\d{3},\d{1,2}$', s):
        s = s.replace('.', '').replace(',', '.')
    # Miles con coma, decimal con punto: 1,234.56 o 1,234
    elif re.search(r'\d,\d{3}\.', s) or re.search(r'\d,\d{3}$', s):
        s = s.replace(',', '')
    # Coma decimal simple: 45,01
    elif re.search(r'^\d+,\d{1,2}$', s):
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
    Extrae todos los montos del HTML/texto del CEP de Banxico.
    Cubre: inputs de formulario, tablas, texto plano, formatos MXN/$, europeo.
    """
    montos = set()

    # 1. Inputs con name/id de monto (formulario CEP — el más confiable)
    for pat in [
        r'(?i)<input[^>]*name=["\'][^"\']*(?:monto|importe|amount|valor|total)[^"\']*["\'][^>]*value=["\']([^"\']+)["\']',
        r'(?i)<input[^>]*value=["\']([^"\']+)["\'][^>]*name=["\'][^"\']*(?:monto|importe|amount|valor|total)[^"\']*["\']',
    ]:
        for m in re.finditer(pat, html):
            v = normalize_monto_float(m.group(1))
            if 0 < v < 1_000_000:
                montos.add(v)

    # 2. Celda de tabla: etiqueta de monto + valor en siguiente TD
    for m in re.finditer(
        r'(?i)(?:monto|importe|cantidad|amount|total|valor)[^<]{0,40}</td>\s*<td[^>]*>\s*\$?\s*([\d][\d\s,\.]*)',
        html
    ):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000:
            montos.add(v)

    # 3. Patron $ seguido de numero
    for m in re.finditer(r'\$\s*([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000:
            montos.add(v)

    # 4. MXN prefijo/sufijo
    for pat in [
        r'(?i)mxn\s*([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)\s*mxn',
    ]:
        for m in re.finditer(pat, html):
            v = normalize_monto_float(m.group(1))
            if 0 < v < 1_000_000:
                montos.add(v)

    # 5. Palabras clave con : o espacio
    for pat in [
        r'(?i)importe[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)\bmonto[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)cantidad[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)\btotal[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)amount[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
        r'(?i)\bvalor[:\s]+([\d]{1,3}(?:,\d{3})*(?:\.\d{1,2})?)',
    ]:
        for m in re.finditer(pat, html):
            v = normalize_monto_float(m.group(1))
            if 0 < v < 1_000_000:
                montos.add(v)

    # 6. TD con numero solo (excluir IDs/CLABEs largas)
    for m in re.finditer(r'<td[^>]*>\s*([\d]{1,7}(?:[.,]\d{1,2})?)\s*</td>', html):
        raw = m.group(1)
        if len(re.sub(r'[^\d]', '', raw)) <= 9:
            v = normalize_monto_float(raw)
            if 0 < v < 1_000_000:
                montos.add(v)

    # 7. Formato europeo en TD: 45,01 o 1.234,56
    for m in re.finditer(r'<td[^>]*>\s*(\d{1,3}(?:\.\d{3})*,\d{2})\s*</td>', html):
        v = normalize_monto_float(m.group(1))
        if 0 < v < 1_000_000:
            montos.add(v)

    # 8. Cualquier numero con exactamente 2 decimales (fuera de URLs/IDs)
    for m in re.finditer(r'(?<![/\d\-])([\d]{1,7}\.\d{2})(?!\d)', html):
        raw = m.group(1)
        if len(raw.replace('.', '')) <= 9:
            v = normalize_monto_float(raw)
            if 0 < v < 1_000_000:
                montos.add(v)

    return sorted(montos)


def montos_coinciden(monto_comprobante: float, montos_cep: list, tolerancia: float = 1.0) -> bool:
    if monto_comprobante <= 0:
        return False
    return any(abs(m - monto_comprobante) <= tolerancia for m in montos_cep)


def fecha_es_pasada(fecha_str: str) -> tuple:
    """
    Retorna (es_pasada: bool, dias_diferencia: int).
    es_pasada=True si el comprobante tiene mas de 0 dias respecto a hoy.
    """
    if not fecha_str:
        return False, 0
    formatos = [
        "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y",
        "%Y/%m/%d", "%d/%b/%Y", "%d/%b/%y",
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
    fecha_norm = fecha_str.lower()
    for es, en in meses.items():
        fecha_norm = fecha_norm.replace(es, en)
    for fmt in formatos:
        try:
            dt = datetime.datetime.strptime(fecha_norm.strip(), fmt)
            hoy = datetime.date.today()
            dias = (hoy - dt.date()).days
            return dias > 0, dias
        except ValueError:
            continue
    return False, 0


def build_system_prompt(
    fecha_hoy: str,
    fecha_legible: str,
    banco_hint: str,
    clabe_hint: str,
    fecha_confirmada: bool = False,
) -> str:
    banco_hint_text = ""
    if banco_hint.strip():
        banco_hint_text = '\nBANCO EMISOR DECLARADO POR EL USUARIO: "' + banco_hint + '". Usalo como banco origen.'

    clabe_hint_text = ""
    if len(clabe_hint) == 18:
        clabe_hint_text = "\nCLABE INGRESADA POR USUARIO: " + clabe_hint + ". Compara con la cuenta destino visible en el comprobante."
    elif len(clabe_hint) > 0:
        clabe_hint_text = "\nCUENTA PARCIAL INGRESADA: " + clabe_hint + " (" + str(len(clabe_hint)) + " digitos)."

    fecha_confirmada_text = (
        "\nIMPORTANTE: El usuario ha CONFIRMADO que este comprobante es de una fecha pasada y lo valida de forma retroactiva. "
        "NO marques la fecha como sospechosa. Analiza el resto del comprobante normalmente.\n"
        if fecha_confirmada else ""
    )

    return (
        "Eres VerificaPago AI, un analista forense especializado en comprobantes de transferencia bancaria en Mexico.\n\n"
        "OBJETIVO:\n"
        "Determinar el nivel de riesgo de fraude de un comprobante de pago mediante analisis documental, estructural, semantico, temporal y contextual.\n\n"
        "FECHA ACTUAL DEL SISTEMA: " + fecha_legible + " (" + fecha_hoy + "). "
        "ESTA ES LA FECHA REAL Y CORRECTA. El año actual es " + fecha_hoy[:4] + ". "
        "Usa esta fecha para todas las validaciones temporales."
        + banco_hint_text + clabe_hint_text + fecha_confirmada_text + "\n\n"
        "REGLAS IMPORTANTES:\n"
        "- NO confirmes que una transferencia ocurrio realmente.\n"
        "- NO afirmes que el dinero fue recibido.\n"
        "- Evalua unicamente la evidencia presente en el comprobante.\n"
        "- Si un dato no puede determinarse con seguridad, devuelve null.\n\n"
        "REGLAS SOBRE FORMATOS VALIDOS EN MEXICO:\n"
        "- Numeros de cuenta ocultos con asteriscos (****1234), puntos (•4023) o cualquier mascara son NORMALES.\n"
        "- El diseno visual NO identifica un banco. Usa SOLO el texto visible.\n"
        "- La clave de rastreo SPEI puede ser alfanumerica y terminar en letra (ej: 260608077756961262I, MBAN010026061500901361189). Longitudes 16-25 son VALIDAS.\n"
        "- Claves de rastreo solo numericas tambien son VALIDAS.\n"
        "- La diferencia de segundos entre aceptacion y liquidacion es NORMAL en SPEI.\n"
        "- Comprobantes con fechas pasadas son NORMALES. Solo marca como sospechoso si la fecha es FUTURA.\n"
        "- La leyenda 'Datos no verificados por esta institucion' es ESTANDAR en SPEI. NO es senal de fraude.\n"
        "- El concepto puede ser cualquier texto libre o estar ausente. NO es indicador de riesgo.\n"
        "- NO inferas inconsistencia entre tipo de cuenta origen y concepto.\n"
        "- Capturas recortadas son NORMALES.\n"
        "- Nombres como 'Switch Banamex', 'Nomina', 'Debito' con digitos parciales son FORMATOS VALIDOS.\n"
        "- Un asterisco al final de un nombre es formato valido de algunas apps bancarias.\n\n"
        "LO QUE SI ES RIESGO:\n"
        "- Fecha futura (posterior a hoy).\n"
        "- Monto en cero o negativo.\n"
        "- Campos criticos completamente ausentes (monto, fecha, banco).\n"
        "- Evidencia visual de edicion: pixelacion localizada, fuentes mixtas, elementos pegados.\n"
        "- Referencias o folios con valores genericos (000000, 123456, 111111).\n\n"
        "LO QUE NO ES RIESGO:\n"
        "- Horario de la transferencia: SPEI opera 24/7. Madrugada, fin de semana son VALIDOS.\n"
        "- Montos bajos: no existe minimo en SPEI.\n"
        "- Concepto libre: tacos, renta, reverso, devolucion, etc.\n\n"
        "CRITERIOS DE ANALISIS:\n"
        "1. ESTRUCTURAL: Folios, referencias, montos, fechas, campos obligatorios.\n"
        "2. SEMANTICO: Coherencia entre texto, banco y operacion.\n"
        "3. TEMPORAL: Fechas futuras o imposibles.\n"
        "4. VISUAL: Manipulaciones visibles, calidad anormal.\n"
        "5. CONTEXTUAL: Datos incompletos, inconsistencias origen/destino.\n\n"
        "EXTRACCION DE CAMPOS:\n"
        "Extrae solo si son visibles. Confianza: 1.00=visible | 0.80=muy probable | 0.60=parcial | 0.40=incierto | 0.20=especulacion\n\n"
        "IMPORTANTE: Para el campo 'monto' devuelve el valor NUMERICO PURO sin simbolos ni comas. Ej: si dice '$1,234.56' devuelve '1234.56'.\n\n"
        "SCORING: 0-20=bajo | 21-50=medio | 51-80=alto | 81-100=critico\n\n"
        "RIESGO: Solo puede ser BAJO, MEDIO, ALTO, CRITICO o INDETERMINADO.\n\n"
        "RESPUESTA: Devuelve EXCLUSIVAMENTE JSON valido, sin markdown, sin backticks.\n\n"
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
# CEP DE BANXICO — Estrategia dual: HTML + PDF
# El HTML del CEP usa JavaScript para renderizar datos, httpx solo ve el esqueleto.
# Solución: intentar primero con el endpoint HTML (con headers de navegador real),
# y si el monto no se extrae, intentar con el endpoint de descarga PDF/XML.
# ─────────────────────────────────────────────────────────────────────────────

async def query_cep_html(clave: str, fecha_banxico: str) -> tuple:
    """Consulta la página HTML del CEP. Retorna (encontrado, html)."""
    url = "https://www.banxico.org.mx/cep/go?i=1&t=&s=" + clave + "&d=" + fecha_banxico
    try:
        async with httpx.AsyncClient(
            timeout=12.0,
            follow_redirects=True,
            headers=CEP_HEADERS,
        ) as http:
            resp = await http.get(url)
        if resp.status_code != 200:
            return False, ""
        html = resp.text
        not_found = (
            "no se encontro" in html.lower()
            or "no existe" in html.lower()
            or len(html) < 500
        )
        return not not_found, html
    except Exception:
        return False, ""


async def query_cep_pdf(clave: str, fecha_banxico: str) -> str:
    """
    Intenta descargar el comprobante PDF/XML del CEP de Banxico.
    El PDF contiene el monto en texto plano, extraible con regex.
    URL: https://www.banxico.org.mx/cep/descarga.do?formato=PDF&...
    """
    url = (
        "https://www.banxico.org.mx/cep/descarga.do"
        "?formato=PDF&tipoConsulta=1&fecha=" + fecha_banxico
        + "&criterio=" + clave
    )
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=CEP_HEADERS,
        ) as http:
            resp = await http.get(url)
        if resp.status_code != 200:
            return ""
        # El PDF puede contener el monto en texto (muchos PDFs de Banxico son text-based)
        # Intentamos leerlo como texto — si es binario puro no dará nada útil
        try:
            return resp.text
        except Exception:
            return ""
    except Exception:
        return ""


async def verify_cep(
    clave_rastreo: str,
    referencia: str,
    fecha: str,
    monto: float,
    banco_origen: str,
    banco_destino: str,
) -> dict:
    try:
        # Normalizar fecha a formato AAAAMMDD que usa Banxico
        fecha_clean = re.sub(r"[^\d]", "", fecha)
        if len(fecha_clean) < 8:
            return {
                "found": False,
                "status": "FECHA_INVALIDA",
                "confidence": 0,
                "detalle": "No fue posible normalizar la fecha: " + fecha,
            }
        # Banxico espera AAAAMMDD
        if len(fecha_clean) == 8 and fecha_clean[:4].isdigit():
            fecha_banxico = fecha_clean  # ya en AAAAMMDD
        elif len(fecha_clean) == 8:
            # Puede ser DDMMAAAA, convertir
            fecha_banxico = fecha_clean[4:8] + fecha_clean[2:4] + fecha_clean[:2]
        else:
            fecha_banxico = fecha_clean[:8]

        # Claves a intentar en orden
        claves_a_intentar = []
        if clave_rastreo:
            claves_a_intentar.append(("clave_rastreo", clean_clave_rastreo(clave_rastreo)))
        if referencia and referencia != clave_rastreo:
            claves_a_intentar.append(("referencia", referencia.strip()))

        found_html = ""
        clave_usada = None
        tipo_clave_usada = None

        for tipo, clave in claves_a_intentar:
            encontrado, html = await query_cep_html(clave, fecha_banxico)
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
                "detalle": "No se encontro la transferencia en CEP Banxico. Claves consultadas: " + claves_intentadas,
            }

        # ── Paso 1: extraer monto del HTML ────────────────────────────────────
        montos_cep = extract_montos_from_html(found_html)
        monto_comprobante = monto if monto > 0 else 0.0

        # ── Paso 2: si el HTML no tiene monto (JS dinámico), intentar PDF ─────
        pdf_intentado = False
        if not montos_cep and clave_usada:
            pdf_intentado = True
            pdf_text = await query_cep_pdf(clave_usada, fecha_banxico)
            if pdf_text:
                montos_cep = extract_montos_from_html(pdf_text)

        # ── Paso 3: evaluar coincidencia ──────────────────────────────────────
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

        # ── Paso 4: mensajes claros por escenario ─────────────────────────────
        if match_monto is True:
            confidence = 1.0
            detalle = (
                "Transferencia CONFIRMADA en CEP Banxico. "
                "Clave: " + str(clave_usada) + ". "
                "Monto verificado: $" + "{:,.2f}".format(monto_comprobante) + ". "
                "Esta transferencia existe en los registros oficiales de Banxico."
            )
        elif match_monto is False:
            confidence = 0.5
            detalle = (
                "Transferencia encontrada en CEP Banxico (clave: " + str(clave_usada) + ") "
                "pero el monto no coincide: comprobante=$" + "{:,.2f}".format(monto_comprobante)
                + " / CEP=" + str(montos_str) + ". "
                "Posible alteracion del monto. Verifica en: " + cep_url
            )
        elif monto_comprobante <= 0:
            confidence = 0.8
            detalle = (
                "Transferencia encontrada en CEP Banxico (clave: " + str(clave_usada) + "). "
                "No se detectó monto en el comprobante para comparar. "
                "Verifica el monto directamente en: " + cep_url
            )
        else:
            # Transferencia confirmada; monto no accesible via HTML estatico (JS dinamico)
            confidence = 0.85
            detalle = (
                "Transferencia CONFIRMADA en Banxico "
                "(clave: " + str(clave_usada) + ", fecha: " + fecha_banxico + "). "
                "Monto en comprobante: $" + "{:,.2f}".format(monto_comprobante) + ". "
                "El CEP de Banxico requiere navegador para mostrar el monto exacto. "
                "Confirma el monto en: " + cep_url
            )

        return {
            "found": True,
            "status": "EXISTE",
            "confidence": confidence,
            "match_monto": match_monto,
            "cep_sin_monto": cep_sin_monto,
            "pdf_intentado": pdf_intentado,
            "monto_comprobante": monto_comprobante,
            "montos_cep": montos_cep,
            "clave_usada": clave_usada,
            "tipo_clave": tipo_clave_usada,
            "cep_url": cep_url,
            "detalle": detalle,
        }

    except httpx.TimeoutException:
        return {
            "found": False,
            "status": "TIMEOUT",
            "confidence": 0,
            "detalle": "Tiempo de espera agotado al consultar CEP de Banxico.",
        }
    except Exception as e:
        return {
            "found": False,
            "status": "ERROR",
            "confidence": 0,
            "detalle": "Error al consultar CEP: " + str(e),
        }


@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form(""),
    fecha_pasada_confirmada: str = Form("false"),
):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")
    fecha_confirmada = fecha_pasada_confirmada.lower() == "true"

    system_prompt = build_system_prompt(
        fecha_hoy, fecha_legible, banco_hint, clabe_hint, fecha_confirmada
    )

    if media_type == "application/pdf":
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de analisis."},
        ]
    else:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de analisis."},
        ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
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
                "detalle": "El documento no parece ser un comprobante de transferencia bancaria.",
            }],
            "resumen": "No fue posible analizar el documento.",
            "recomendacion": "Sube una imagen mas clara o un PDF del comprobante generado por tu banco.",
        }

    result = json.loads(match.group(0))

    campos_raw = result.get("campos_extraidos", {})
    campos_planos = {}
    for key, val in campos_raw.items():
        campos_planos[key] = extract_field_value(val)

    # ── Detectar si el comprobante es de fecha pasada ─────────────────────────
    fecha_campo = campos_planos.get("fecha") or ""
    es_pasada, dias_diferencia = fecha_es_pasada(fecha_campo)
    # Solo mostrar banner si la fecha es pasada, no fue confirmada aun, y es > 0 dias
    requiere_confirmacion_fecha = es_pasada and not fecha_confirmada and dias_diferencia > 0
    result["requiere_confirmacion_fecha"] = requiere_confirmacion_fecha
    result["dias_diferencia"] = dias_diferencia if es_pasada else 0

    if requiere_confirmacion_fecha:
        result["mensaje_confirmacion_fecha"] = (
            "Este comprobante tiene fecha del "
            + fecha_campo
            + " (" + str(dias_diferencia) + " dia(s) atras). "
            "Si es una transferencia pasada que deseas validar retroactivamente, "
            "confirma para analizarla sin penalizar la fecha."
        )

    # ── IAT ───────────────────────────────────────────────────────────────────
    banco_origen = campos_planos.get("banco_origen") or banco_hint or None
    iat_result = calculate_iat(campos_planos, banco_origen)

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
                if cv["valid"]
                else "CLABE invalida: " + cv["reason"]
            ),
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── CLABE visible en el comprobante ───────────────────────────────────────
    clabe_raw = (
        (campos_planos.get("clabe_parcial") or "")
        .replace(" ", "")
        .replace("*", "")
        .replace(".", "")
    )
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante - digito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                "CLABE valida. Banco: " + cv["bank"] + " (codigo " + cv["bank_code"] + ")"
                if cv["valid"]
                else "CLABE invalida: " + cv["reason"]
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

    # ── CEP de Banxico ────────────────────────────────────────────────────────
    clave_rastreo = campos_planos.get("clave_rastreo") or ""
    referencia = campos_planos.get("referencia") or ""
    monto_str = campos_planos.get("monto") or ""
    monto_texto_str = campos_planos.get("monto_texto") or ""
    fecha_str = campos_planos.get("fecha") or ""

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

        # Status del badge CEP
        if cep.get("found"):
            if cep.get("match_monto") is True:
                cep_status = "ok"           # encontrado + monto verificado
            elif cep.get("cep_sin_monto") or cep.get("match_monto") is None:
                cep_status = "warn"         # encontrado, monto no verificable por JS
            else:
                cep_status = "warn"         # encontrado, monto no coincide
        else:
            cep_status = "info"             # no encontrado (puede ser timing, no fraude)

        cep_entry = {
            "categoria": "cep",
            "nombre": "CEP Banxico - Verificacion SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP."),
        }
        # Incluir URL directa si está disponible — el frontend puede mostrarlo como botón
        if cep.get("cep_url"):
            cep_entry["cep_url"] = cep["cep_url"]
        result["validaciones"].append(cep_entry)
        result["cep_resultado"] = cep

        # Solo subir score si el monto DEFINITIVAMENTE no coincide
        if cep.get("found") and cep.get("match_monto") is False and monto_num > 0:
            final_score = max(final_score, 50)

    # ── Score y riesgo final ──────────────────────────────────────────────────
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

    return result


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2"}
