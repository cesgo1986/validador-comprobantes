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
        return {"valid": False, "reason": "Longitud incorrecta (debe ser 18 dígitos)"}
    if not clean.isdigit():
        return {"valid": False, "reason": "Contiene caracteres no numéricos"}
    weights = [3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7, 1, 3, 7]
    total = sum(int(clean[i]) * weights[i] for i in range(17))
    check = (10 - (total % 10)) % 10
    if check != int(clean[17]):
        return {"valid": False, "reason": "Dígito verificador incorrecto"}
    bank_code = clean[:3]
    bank = BANKS.get(bank_code, "Banco no reconocido")
    return {"valid": True, "bank": bank, "bank_code": bank_code}


def build_system_prompt(fecha_hoy: str, fecha_legible: str, banco_hint: str, clabe_hint: str) -> str:
    banco_hint_text = (
        f'\nBANCO EMISOR DECLARADO POR EL USUARIO: "{banco_hint}". '
        f'Úsalo como banco origen y valida coherencia con el documento.'
        if banco_hint.strip() else ""
    )
    clabe_hint_text = (
        f'\nCLABE INGRESADA POR USUARIO: {clabe_hint}. '
        f'Compara con la cuenta destino visible en el comprobante.'
        if len(clabe_hint) == 18 else
        f'\nCUENTA PARCIAL INGRESADA: {clabe_hint} ({len(clabe_hint)} dígitos).'
        if len(clabe_hint) > 0 else ""
    )

    return f"""Eres VerificaPago AI, un analista forense especializado en comprobantes de transferencia bancaria en México.

OBJETIVO:
Determinar el nivel de riesgo de fraude de un comprobante de pago mediante análisis documental, estructural, semántico, temporal y contextual.

FECHA ACTUAL: {fecha_legible} ({fecha_hoy}).{banco_hint_text}{clabe_hint_text}

REGLAS IMPORTANTES:
- NO confirmes que una transferencia ocurrió realmente.
- NO afirmes que el dinero fue recibido.
- Evalúa únicamente la evidencia presente en el comprobante.
- Los números ocultos con asteriscos (****1234) son NORMALES en México.
- El diseño visual NO es evidencia suficiente para identificar un banco.
- Identifica bancos ÚNICAMENTE por texto visible, nunca por colores o tipografía.
- Si un dato no puede determinarse con seguridad, devuelve null.

CRITERIOS DE ANÁLISIS:
1. ESTRUCTURAL: Consistencia de folios, referencias, montos, fechas, horas, campos obligatorios.
2. SEMÁNTICO: Coherencia entre texto y operación, banco y terminología, conceptos y formato.
3. TEMPORAL: Fechas futuras, fechas imposibles, horas imposibles, operaciones excesivamente antiguas.
4. VISUAL: Recortes sospechosos, campos truncados, elementos inconsistentes, calidad anormal, manipulaciones visibles.
5. CONTEXTUAL: Datos incompletos, inconsistencias entre origen y destino.

EXTRACCIÓN DE CAMPOS:
Extrae únicamente si son visibles. Para cada campo genera valor y confianza:
- 1.00 = completamente visible
- 0.80 = muy probable
- 0.60 = parcialmente visible
- 0.40 = incierto
- 0.20 = especulación mínima

SCORING:
0-20 = riesgo bajo | 21-50 = riesgo medio | 51-80 = riesgo alto | 81-100 = riesgo crítico

RIESGO: Solo puede ser BAJO, MEDIO, ALTO, CRITICO o INDETERMINADO.

VALIDACIONES: Genera validaciones con categoria, nombre, status (ok|warn|fail|info) y detalle.

RECOMENDACIONES accionables. Ejemplos:
- Esperar acreditación bancaria antes de entregar.
- Solicitar comprobante completo con folio visible.
- Confirmar con CEP de Banxico en banxico.org.mx/cep
- No entregar producto hasta validación bancaria.

RESPUESTA: Devuelve EXCLUSIVAMENTE JSON válido, sin markdown, sin backticks, sin texto adicional.

{{
  "riesgo": "BAJO|MEDIO|ALTO|CRITICO|INDETERMINADO",
  "score": 0-100,
  "campos_extraidos": {{
    "banco_origen":    {{"valor": null, "confianza": 0.0}},
    "banco_destino":   {{"valor": null, "confianza": 0.0}},
    "monto":           {{"valor": null, "confianza": 0.0}},
    "monto_texto":     {{"valor": null, "confianza": 0.0}},
    "fecha":           {{"valor": null, "confianza": 0.0}},
    "hora":            {{"valor": null, "confianza": 0.0}},
    "referencia":      {{"valor": null, "confianza": 0.0}},
    "clave_rastreo":   {{"valor": null, "confianza": 0.0}},
    "folio":           {{"valor": null, "confianza": 0.0}},
    "clabe_parcial":   {{"valor": null, "confianza": 0.0}},
    "nombre_receptor": {{"valor": null, "confianza": 0.0}},
    "concepto":        {{"valor": null, "confianza": 0.0}}
  }},
  "validaciones": [
    {{"categoria": "estructural|visual|temporal|contextual|semantica", "nombre": "string", "status": "ok|warn|fail|info", "detalle": "string"}}
  ],
  "resumen": "2-3 oraciones explicando el veredicto",
  "recomendacion": "acción concreta y accionable"
}}"""


def extract_field_value(campo) -> str | None:
    """Extrae el valor de un campo que puede ser string o dict con 'valor'."""
    if campo is None:
        return None
    if isinstance(campo, dict):
        return campo.get("valor")
    return str(campo) if campo else None


def clean_clave_rastreo(clave: str) -> str:
    """
    Limpia la clave de rastreo:
    - Elimina espacios
    - Elimina caracteres no alfanuméricos al final (ej: 'I', 'l', 'O')
    - Corrige confusiones comunes de OCR: I→1, l→1, O→0
    """
    clave = clave.strip()
    # Corregir OCR al final: I o l sueltos al final → 1, O → 0
    clave = re.sub(r'[Il]


@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form("")
):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")

    system_prompt = build_system_prompt(fecha_hoy, fecha_legible, banco_hint, clabe_hint)

    if media_type == "application/pdf":
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]
    else:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    raw = response.content[0].text.strip()

    # Extraer JSON aunque venga con texto adicional
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
            "resumen": "No fue posible analizar el documento. Sube un comprobante de transferencia bancaria válido.",
            "recomendacion": "Sube una imagen más clara o un PDF del comprobante generado por tu banco."
        }

    result = json.loads(match.group(0))

    # ── Normalizar campos_extraidos al formato plano para el IAT ──
    campos_raw = result.get("campos_extraidos", {})
    campos_planos = {}
    for key, val in campos_raw.items():
        campos_planos[key] = extract_field_value(val)

    # ── Motor IAT ──────────────────────────────────────────────
    banco_origen = campos_planos.get("banco_origen") or banco_hint or None
    iat_result = calculate_iat(campos_planos, banco_origen)

    # Fusionar scores
    claude_score = result.get("score", 50)
    final_score = fuse_scores(claude_score, iat_result["iat_score"])
    result["score"] = final_score
    result["iat_score"] = iat_result["iat_score"]
    result["iat_metricas"] = iat_result["metricas"]

    # Agregar validaciones IAT
    iat_validaciones = iat_anomalias_to_validaciones(iat_result["anomalias"])
    result["validaciones"] = (result.get("validaciones") or []) + iat_validaciones

    # ── Validación CLABE ingresada por usuario ─────────────────
    if len(clabe_hint) == 18:
        cv = validate_clabe(clabe_hint)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE ingresada — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CLABE extraída por OCR ──────────────────────
    clabe_raw = (campos_planos.get("clabe_parcial") or "").replace(" ", "").replace("*", "").replace("•", "")
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        validaciones = result.get("validaciones", [])
        idx = next((i for i, v in enumerate(validaciones) if "clabe" in v.get("nombre", "").lower() and "ingresada" not in v.get("nombre", "").lower()), -1)
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CEP Banxico ─────────────────────────────────
    clave_rastreo = campos_planos.get("clave_rastreo") or campos_planos.get("referencia")
    monto_str = campos_planos.get("monto") or ""
    fecha_str = campos_planos.get("fecha") or ""

    if clave_rastreo and fecha_str:
        try:
            monto_num = float(re.sub(r"[^\d.]", "", str(monto_str).replace(",", ""))) if monto_str else 0.0
        except ValueError:
            monto_num = 0.0

        cep = await verify_cep(
            clave_rastreo=str(clave_rastreo),
            referencia=str(campos_planos.get("referencia") or ""),
            fecha=str(fecha_str),
            monto=monto_num,
            banco_origen=campos_planos.get("banco_origen"),
            banco_destino=campos_planos.get("banco_destino")
        )

        cep_status = "ok" if cep.get("confidence", 0) >= 1.0 else "warn" if cep.get("found") else "info"
        result["validaciones"].append({
            "categoria": "cep",
            "nombre": "CEP Banxico — Verificación SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP.")
        })
        result["cep_resultado"] = cep

        if cep.get("found") and cep.get("confidence", 0) < 1.0:
            final_score = max(final_score, 50)

    # ── Score y riesgo final ───────────────────────────────────
    result["score"] = round(final_score, 2)
    if final_score >= 81:
        result["riesgo"] = "CRITICO"
    elif final_score >= 51:
        result["riesgo"] = "ALTO"
    elif final_score >= 21:
        result["riesgo"] = "MEDIO"
    else:
        result["riesgo"] = "BAJO"

    # Normalizar campos_extraidos a formato plano para el frontend
    result["campos_extraidos"] = campos_planos

    return result


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2"}
, '1', clave)
    clave = re.sub(r'O


@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form("")
):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")

    system_prompt = build_system_prompt(fecha_hoy, fecha_legible, banco_hint, clabe_hint)

    if media_type == "application/pdf":
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]
    else:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    raw = response.content[0].text.strip()

    # Extraer JSON aunque venga con texto adicional
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
            "resumen": "No fue posible analizar el documento. Sube un comprobante de transferencia bancaria válido.",
            "recomendacion": "Sube una imagen más clara o un PDF del comprobante generado por tu banco."
        }

    result = json.loads(match.group(0))

    # ── Normalizar campos_extraidos al formato plano para el IAT ──
    campos_raw = result.get("campos_extraidos", {})
    campos_planos = {}
    for key, val in campos_raw.items():
        campos_planos[key] = extract_field_value(val)

    # ── Motor IAT ──────────────────────────────────────────────
    banco_origen = campos_planos.get("banco_origen") or banco_hint or None
    iat_result = calculate_iat(campos_planos, banco_origen)

    # Fusionar scores
    claude_score = result.get("score", 50)
    final_score = fuse_scores(claude_score, iat_result["iat_score"])
    result["score"] = final_score
    result["iat_score"] = iat_result["iat_score"]
    result["iat_metricas"] = iat_result["metricas"]

    # Agregar validaciones IAT
    iat_validaciones = iat_anomalias_to_validaciones(iat_result["anomalias"])
    result["validaciones"] = (result.get("validaciones") or []) + iat_validaciones

    # ── Validación CLABE ingresada por usuario ─────────────────
    if len(clabe_hint) == 18:
        cv = validate_clabe(clabe_hint)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE ingresada — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CLABE extraída por OCR ──────────────────────
    clabe_raw = (campos_planos.get("clabe_parcial") or "").replace(" ", "").replace("*", "").replace("•", "")
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        validaciones = result.get("validaciones", [])
        idx = next((i for i, v in enumerate(validaciones) if "clabe" in v.get("nombre", "").lower() and "ingresada" not in v.get("nombre", "").lower()), -1)
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CEP Banxico ─────────────────────────────────
    clave_rastreo = campos_planos.get("clave_rastreo") or campos_planos.get("referencia")
    monto_str = campos_planos.get("monto") or ""
    fecha_str = campos_planos.get("fecha") or ""

    if clave_rastreo and fecha_str:
        try:
            monto_num = float(re.sub(r"[^\d.]", "", str(monto_str).replace(",", ""))) if monto_str else 0.0
        except ValueError:
            monto_num = 0.0

        cep = await verify_cep(
            clave_rastreo=str(clave_rastreo),
            fecha=str(fecha_str),
            monto=monto_num,
            banco_origen=campos_planos.get("banco_origen"),
            banco_destino=campos_planos.get("banco_destino")
        )

        cep_status = "ok" if cep.get("confidence", 0) >= 1.0 else "warn" if cep.get("found") else "info"
        result["validaciones"].append({
            "categoria": "cep",
            "nombre": "CEP Banxico — Verificación SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP.")
        })
        result["cep_resultado"] = cep

        if cep.get("found") and cep.get("confidence", 0) < 1.0:
            final_score = max(final_score, 50)

    # ── Score y riesgo final ───────────────────────────────────
    result["score"] = round(final_score, 2)
    if final_score >= 81:
        result["riesgo"] = "CRITICO"
    elif final_score >= 51:
        result["riesgo"] = "ALTO"
    elif final_score >= 21:
        result["riesgo"] = "MEDIO"
    else:
        result["riesgo"] = "BAJO"

    # Normalizar campos_extraidos a formato plano para el frontend
    result["campos_extraidos"] = campos_planos

    return result


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2"}
, '0', clave)
    # Eliminar cualquier carácter no alfanumérico restante al final
    clave = re.sub(r'[^a-zA-Z0-9]+


@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form("")
):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")

    system_prompt = build_system_prompt(fecha_hoy, fecha_legible, banco_hint, clabe_hint)

    if media_type == "application/pdf":
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]
    else:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    raw = response.content[0].text.strip()

    # Extraer JSON aunque venga con texto adicional
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
            "resumen": "No fue posible analizar el documento. Sube un comprobante de transferencia bancaria válido.",
            "recomendacion": "Sube una imagen más clara o un PDF del comprobante generado por tu banco."
        }

    result = json.loads(match.group(0))

    # ── Normalizar campos_extraidos al formato plano para el IAT ──
    campos_raw = result.get("campos_extraidos", {})
    campos_planos = {}
    for key, val in campos_raw.items():
        campos_planos[key] = extract_field_value(val)

    # ── Motor IAT ──────────────────────────────────────────────
    banco_origen = campos_planos.get("banco_origen") or banco_hint or None
    iat_result = calculate_iat(campos_planos, banco_origen)

    # Fusionar scores
    claude_score = result.get("score", 50)
    final_score = fuse_scores(claude_score, iat_result["iat_score"])
    result["score"] = final_score
    result["iat_score"] = iat_result["iat_score"]
    result["iat_metricas"] = iat_result["metricas"]

    # Agregar validaciones IAT
    iat_validaciones = iat_anomalias_to_validaciones(iat_result["anomalias"])
    result["validaciones"] = (result.get("validaciones") or []) + iat_validaciones

    # ── Validación CLABE ingresada por usuario ─────────────────
    if len(clabe_hint) == 18:
        cv = validate_clabe(clabe_hint)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE ingresada — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CLABE extraída por OCR ──────────────────────
    clabe_raw = (campos_planos.get("clabe_parcial") or "").replace(" ", "").replace("*", "").replace("•", "")
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        validaciones = result.get("validaciones", [])
        idx = next((i for i, v in enumerate(validaciones) if "clabe" in v.get("nombre", "").lower() and "ingresada" not in v.get("nombre", "").lower()), -1)
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CEP Banxico ─────────────────────────────────
    clave_rastreo = campos_planos.get("clave_rastreo") or campos_planos.get("referencia")
    monto_str = campos_planos.get("monto") or ""
    fecha_str = campos_planos.get("fecha") or ""

    if clave_rastreo and fecha_str:
        try:
            monto_num = float(re.sub(r"[^\d.]", "", str(monto_str).replace(",", ""))) if monto_str else 0.0
        except ValueError:
            monto_num = 0.0

        cep = await verify_cep(
            clave_rastreo=str(clave_rastreo),
            fecha=str(fecha_str),
            monto=monto_num,
            banco_origen=campos_planos.get("banco_origen"),
            banco_destino=campos_planos.get("banco_destino")
        )

        cep_status = "ok" if cep.get("confidence", 0) >= 1.0 else "warn" if cep.get("found") else "info"
        result["validaciones"].append({
            "categoria": "cep",
            "nombre": "CEP Banxico — Verificación SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP.")
        })
        result["cep_resultado"] = cep

        if cep.get("found") and cep.get("confidence", 0) < 1.0:
            final_score = max(final_score, 50)

    # ── Score y riesgo final ───────────────────────────────────
    result["score"] = round(final_score, 2)
    if final_score >= 81:
        result["riesgo"] = "CRITICO"
    elif final_score >= 51:
        result["riesgo"] = "ALTO"
    elif final_score >= 21:
        result["riesgo"] = "MEDIO"
    else:
        result["riesgo"] = "BAJO"

    # Normalizar campos_extraidos a formato plano para el frontend
    result["campos_extraidos"] = campos_planos

    return result


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2"}
, '', clave)
    return clave


async def query_cep(clave: str, fecha_banxico: str) -> tuple[bool, str]:
    """Realiza una consulta individual al CEP de Banxico."""
    url = f"https://www.banxico.org.mx/cep/go?i=1&t=&s={clave}&d={fecha_banxico}"
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as http:
        resp = await http.get(url)
    if resp.status_code != 200:
        return False, ""
    html = resp.text
    not_found = (
        "no se encontró" in html.lower() or
        "no existe" in html.lower() or
        len(html) < 500
    )
    return not not_found, html


async def verify_cep(clave_rastreo: str, referencia: str | None, fecha: str, monto: float,
                     banco_origen: str | None, banco_destino: str | None) -> dict:
    """
    Consulta el CEP de Banxico.
    Intenta primero con clave_rastreo, luego con referencia como fallback.
    """
    try:
        # Normalizar fecha al formato YYYYMMDD
        fecha_clean = re.sub(r"[^\d]", "", fecha)
        if len(fecha_clean) < 8:
            return {"found": False, "status": "FECHA_INVALIDA", "confidence": 0,
                    "detalle": f"No fue posible normalizar la fecha: {fecha}"}
        fecha_banxico = fecha_clean[:8]

        # Intentos en orden: clave_rastreo limpia → referencia
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
                "detalle": f"No se encontró la transferencia en CEP Banxico. Claves consultadas: {claves_intentadas}"
            }

        # Extraer monto del CEP
        monto_match = re.search(r"\$\s*([\d,]+\.?\d*)", found_html)
        match_monto = False
        if monto_match and monto > 0:
            monto_cep = float(monto_match.group(1).replace(",", ""))
            match_monto = abs(monto_cep - monto) < 0.01

        confidence = 1.0 if match_monto else 0.7

        detalle = (
            f"Transferencia encontrada en CEP Banxico usando {tipo_clave_usada} ({clave_usada}). "
            f"{'Monto coincide ✓' if match_monto else 'Monto no coincide con el comprobante ⚠'}"
        )

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
                "detalle": f"Error al consultar CEP: {str(e)}"}


@app.post("/analizar")
async def analizar(
    file: UploadFile = File(...),
    banco_hint: str = Form(""),
    clabe_hint: str = Form("")
):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()
    fecha_legible = datetime.datetime.now().strftime("%A %d de %B de %Y")

    system_prompt = build_system_prompt(fecha_hoy, fecha_legible, banco_hint, clabe_hint)

    if media_type == "application/pdf":
        user_content = [
            {"type": "document", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]
    else:
        user_content = [
            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
            {"type": "text", "text": "Analiza este comprobante de transferencia bancaria y devuelve el JSON de análisis."}
        ]

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}]
    )

    raw = response.content[0].text.strip()

    # Extraer JSON aunque venga con texto adicional
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
            "resumen": "No fue posible analizar el documento. Sube un comprobante de transferencia bancaria válido.",
            "recomendacion": "Sube una imagen más clara o un PDF del comprobante generado por tu banco."
        }

    result = json.loads(match.group(0))

    # ── Normalizar campos_extraidos al formato plano para el IAT ──
    campos_raw = result.get("campos_extraidos", {})
    campos_planos = {}
    for key, val in campos_raw.items():
        campos_planos[key] = extract_field_value(val)

    # ── Motor IAT ──────────────────────────────────────────────
    banco_origen = campos_planos.get("banco_origen") or banco_hint or None
    iat_result = calculate_iat(campos_planos, banco_origen)

    # Fusionar scores
    claude_score = result.get("score", 50)
    final_score = fuse_scores(claude_score, iat_result["iat_score"])
    result["score"] = final_score
    result["iat_score"] = iat_result["iat_score"]
    result["iat_metricas"] = iat_result["metricas"]

    # Agregar validaciones IAT
    iat_validaciones = iat_anomalias_to_validaciones(iat_result["anomalias"])
    result["validaciones"] = (result.get("validaciones") or []) + iat_validaciones

    # ── Validación CLABE ingresada por usuario ─────────────────
    if len(clabe_hint) == 18:
        cv = validate_clabe(clabe_hint)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE ingresada — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        result["validaciones"].insert(0, entry)
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CLABE extraída por OCR ──────────────────────
    clabe_raw = (campos_planos.get("clabe_parcial") or "").replace(" ", "").replace("*", "").replace("•", "")
    if len(clabe_raw) == 18 and clabe_raw.isdigit():
        cv = validate_clabe(clabe_raw)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE en comprobante — dígito verificador",
            "status": "ok" if cv["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {cv["bank"]} (código {cv["bank_code"]})'
                if cv["valid"] else f'CLABE inválida: {cv["reason"]}'
            )
        }
        validaciones = result.get("validaciones", [])
        idx = next((i for i, v in enumerate(validaciones) if "clabe" in v.get("nombre", "").lower() and "ingresada" not in v.get("nombre", "").lower()), -1)
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not cv["valid"]:
            final_score = max(final_score, 70)
            result["riesgo"] = "ALTO"

    # ── Validación CEP Banxico ─────────────────────────────────
    clave_rastreo = campos_planos.get("clave_rastreo") or campos_planos.get("referencia")
    monto_str = campos_planos.get("monto") or ""
    fecha_str = campos_planos.get("fecha") or ""

    if clave_rastreo and fecha_str:
        try:
            monto_num = float(re.sub(r"[^\d.]", "", str(monto_str).replace(",", ""))) if monto_str else 0.0
        except ValueError:
            monto_num = 0.0

        cep = await verify_cep(
            clave_rastreo=str(clave_rastreo),
            fecha=str(fecha_str),
            monto=monto_num,
            banco_origen=campos_planos.get("banco_origen"),
            banco_destino=campos_planos.get("banco_destino")
        )

        cep_status = "ok" if cep.get("confidence", 0) >= 1.0 else "warn" if cep.get("found") else "info"
        result["validaciones"].append({
            "categoria": "cep",
            "nombre": "CEP Banxico — Verificación SPEI",
            "status": cep_status,
            "detalle": cep.get("detalle", "No fue posible consultar el CEP.")
        })
        result["cep_resultado"] = cep

        if cep.get("found") and cep.get("confidence", 0) < 1.0:
            final_score = max(final_score, 50)

    # ── Score y riesgo final ───────────────────────────────────
    result["score"] = round(final_score, 2)
    if final_score >= 81:
        result["riesgo"] = "CRITICO"
    elif final_score >= 51:
        result["riesgo"] = "ALTO"
    elif final_score >= 21:
        result["riesgo"] = "MEDIO"
    else:
        result["riesgo"] = "BAJO"

    # Normalizar campos_extraidos a formato plano para el frontend
    result["campos_extraidos"] = campos_planos

    return result


@app.get("/")
def root():
    return {"status": "ok", "servicio": "VerificaPago API v2"}