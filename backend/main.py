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
        "FECHA ACTUAL: " + fecha_legible + " (" + fecha_hoy + ")." + banco_hint_text + clabe_hint_text + fecha_confirmada_text + "\n\n"
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
    try:
        fecha_clean = re.sub(r"[^\d]", "", fecha)
        if len(fecha_clean) < 8:
            return {"found": False, "status": "FECHA_INVALIDA", "confidence": 0,
                    "detalle": "No fue posible normalizar la fecha: " + fecha}
        fecha_banxico = fecha_clean[:8]

        claves_a_intentar = []
        if clave_rastreo:
            clave_limpia = clean_clave_rastreo(clave_rastreo)
            claves_a_intentar.append(("clave_rastreo", clave_limpia))
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

        monto_match_re = re.search(r"\$\s*([\d,]+\.?\d*)", found_html)
        match_monto = False
        if monto_match_re and monto > 0:
            monto_cep = round(float(monto_match_re.group(1).replace(",", "")), 2)
            monto_comp = round(monto, 2)
            # Tolerancia de 1 peso para cubrir diferencias de redondeo y formato
            match_monto = abs(monto_cep - monto_comp) < 1.0

        confidence = 1.0 if match_monto else 0.7
        monto_txt = "Monto coincide" if match_monto else "Monto no coincide con el comprobante"
        detalle = "Transferencia encontrada en CEP Banxico usando " + str(tipo_clave_usada) + " (" + str(clave_usada) + "). " + monto_txt

        return {
            "found": True,
            "status": "EXISTE",
            "confidence": confidence,
            "match_monto": match_monto,
            "clave_usada": clave_usada,
            "tipo_clave": tipo_clave_usada,
            "detalle": detalle
        }

    except httpx.TimeoutException:
        return {"found": False, "status": "TIMEOUT", "confidence": 0,
                "detalle": "Tiempo de espera agotado al consultar CEP de Banxico."}
    except Exception as e:
        return {"found": False, "status": "ERROR", "confidence": 0,
                "detalle": "Error al consultar CEP: " + str(e)}


@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form(""),
    fecha_pasada_confirmada: str = Form("false")
):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")
    fecha_confirmada = fecha_pasada_confirmada.lower() == "true"

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
        model="claude-sonnet-4-5",
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

    claude_score = result.get("score", 50)
    final_score = fuse_scores(claude_score, iat_result["iat_score"])
    result["score"] = final_score
    result["iat_score"] = iat_result["iat_score"]
    result["iat_metricas"] = iat_result["metricas"]

    iat_validaciones = iat_anomalias_to_validaciones(iat_result["anomalias"])
    result["validaciones"] = (result.get("validaciones") or []) + iat_validaciones

    if len(clabe_hint) == 18:
        cv = validate_clabe(clabe_hint)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE ingresada - digito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                "CLABE valida. Banco: " + cv["bank"] + " (codigo " + cv["bank_code"] + ")"
                if cv["valid"] else "CLABE invalida: " + cv["reason"]
            )
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    clabe_raw = (campos_planos.get("clabe_parcial") or "").replace(" ", "").replace("*", "").replace(".", "")
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante - digito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                "CLABE valida. Banco: " + cv["bank"] + " (codigo " + cv["bank_code"] + ")"
                if cv["valid"] else "CLABE invalida: " + cv["reason"]
            )
        }
        validaciones = result.get("validaciones", [])
        idx = next((i for i, v in enumerate(validaciones)
                    if "clabe" in v.get("nombre", "").lower() and "ingresada" not in v.get("nombre", "").lower()), -1)
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    clave_rastreo = campos_planos.get("clave_rastreo") or ""
    referencia = campos_planos.get("referencia") or ""
    monto_str = campos_planos.get("monto") or ""
    fecha_str = campos_planos.get("fecha") or ""

    if (clave_rastreo or referencia) and fecha_str:
        try:
            monto_num = float(re.sub(r"[^\d.]", "", str(monto_str).replace(",", ""))) if monto_str else 0.0
        except ValueError:
            monto_num = 0.0

        cep = await verify_cep(
            clave_rastreo=str(clave_rastreo),
            referencia=str(referencia),
            fecha=str(fecha_str),
            monto=monto_num,
            banco_origen=str(campos_planos.get("banco_origen") or ""),
            banco_destino=str(campos_planos.get("banco_destino") or "")
        )

        cep_status = "ok" if cep.get("confidence", 0) >= 1.0 else "warn" if cep.get("found") else "info"
        result["validaciones"].append({
            "categoria": "cep",
            "nombre": "CEP Banxico - Verificacion SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP.")
        })
        result["cep_resultado"] = cep

        if cep.get("found") and cep.get("confidence", 0) < 1.0:
            final_score = max(final_score, 50)

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
