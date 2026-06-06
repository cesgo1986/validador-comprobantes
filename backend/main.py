import json
import base64
import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import anthropic
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción reemplaza con tu dominio de Vercel
    allow_methods=["*"],
    allow_headers=["*"],
)

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

def build_system_prompt(fecha_hoy: str, banco_hint: str) -> str:
    banco_hint_text = (
        f'\nBANCO EMISOR DECLARADO POR EL USUARIO: "{banco_hint}". '
        f'Usa este dato como banco origen. Valida si el diseño y elementos del comprobante son consistentes con ese banco.'
        if banco_hint.strip() else ""
    )

    return f"""Eres un sistema experto en análisis forense de comprobantes de transferencia bancaria SPEI de México.

FECHA ACTUAL DEL SISTEMA: {fecha_hoy}. Usa esta fecha como referencia para validar si una transferencia es futura o demasiado antigua. NO asumas ninguna otra fecha.
{banco_hint_text}

CONTEXTO IMPORTANTE SOBRE COMPROBANTES:
- El comprobante puede provenir de cualquier canal válido: app del banco, correo de confirmación, captura de pantalla, PDF generado por el banco o notificación. Todos son válidos siempre que sean de una transferencia real.
- Los bancos mexicanos actualmente OCULTAN la CLABE o número de cuenta completos por seguridad. Solo muestran los últimos 4-6 dígitos (ej: "****1234"). Esto es NORMAL y no es señal de alteración.
- Para identificar el banco emisor y receptor, usa ÚNICAMENTE el texto explícito visible en el documento. NUNCA inferas el banco por colores, tipografía o diseño visual. Si no hay texto identificatorio claro, indica "No identificado".

Tu tarea es analizar el comprobante y devolver ÚNICAMENTE un JSON válido (sin backticks ni markdown) con esta estructura exacta:

{{
  "riesgo": "BAJO" | "MEDIO" | "ALTO" | "INDETERMINADO",
  "score": número 0-100,
  "campos_extraidos": {{
    "banco_origen": "string o null",
    "banco_destino": "string o null",
    "monto": "string o null",
    "monto_texto": "string o null",
    "fecha": "string o null",
    "hora": "string o null",
    "referencia": "string o null",
    "folio": "string o null",
    "clabe_parcial": "string con los dígitos visibles o null",
    "nombre_receptor": "string o null",
    "concepto": "string o null"
  }},
  "validaciones": [
    {{
      "categoria": "estructural" | "visual" | "contextual" | "temporal" | "semantica" | "reputacion",
      "nombre": "string corto",
      "status": "ok" | "warn" | "fail" | "info",
      "detalle": "string explicativo"
    }}
  ],
  "resumen": "string de 2-3 oraciones explicando el veredicto",
  "recomendacion": "string con acción concreta para el receptor"
}}

VALIDACIONES OBLIGATORIAS:

ESTRUCTURALES:
- Si CLABE aparece parcial, analiza si la terminación es consistente con el banco declarado. NO marques error por ocultación parcial.
- Si CLABE completa visible: valida dígito verificador y código CNBV.
- Estructura de referencia SPEI (longitud, formato numérico).
- Presencia de folio o número de operación.

VISUALES:
- Tipografía consistente dentro del documento.
- Señales de edición: pixelación localizada, bordes irregulares, diferencias de compresión en zonas de monto o fecha.
- Presencia de elementos de autenticidad: sello, marca de agua, código de verificación.

CONTEXTUALES:
- Presencia de campos obligatorios SPEI (monto, fecha, referencia, banco origen, banco destino).
- Coherencia del layout con comprobantes reales del banco identificado por texto.
- Formato reconocible de institución financiera mexicana.

TEMPORALES:
- Fecha válida vs fecha actual {fecha_hoy}: no futura, no mayor a 90 días para uso comercial.
- Hora en rango razonable para operaciones SPEI.
- Día hábil bancario (SPEI no opera domingos 22:00-00:00 ni mantenimientos).

SEMÁNTICAS:
- Coherencia monto numérico vs texto (si ambos aparecen).
- Banco en CLABE vs banco declarado en texto (si CLABE completa visible).
- Monto redondo exacto en cantidades altas: señalar como informativo.

REPUTACIÓN / INTELIGENCIA:
- Señales de template genérico no bancario.
- Elementos inusuales para México (moneda distinta a MXN sin justificación).
- Número de referencia con longitud atípica.

Si el documento NO es un comprobante de transferencia bancaria, establece riesgo INDETERMINADO.
Responde SOLO con el JSON, sin texto adicional."""


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


@app.post("/analizar")
async def analizar(file: UploadFile = File(...), banco_hint: str = Form("")):
    contenido = await file.read()
    b64 = base64.b64encode(contenido).decode()
    media_type = file.content_type
    fecha_hoy = datetime.date.today().isoformat()

    system_prompt = build_system_prompt(fecha_hoy, banco_hint)

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

    text = response.content[0].text.replace("```json", "").replace("```", "").strip()
    result = json.loads(text)

    # Validación local de CLABE si está completa
    clabe_raw = (result.get("campos_extraidos") or {}).get("clabe_parcial", "") or ""
    clabe_clean = clabe_raw.replace(" ", "").replace("*", "").replace("•", "")
    if len(clabe_clean) == 18 and clabe_clean.isdigit():
        clabe_result = validate_clabe(clabe_clean)
        entry = {
            "categoria": "estructural",
            "nombre": "CLABE — dígito verificador",
            "status": "ok" if clabe_result["valid"] else "fail",
            "detalle": (
                f'CLABE válida. Banco: {clabe_result["bank"]} (código {clabe_result["bank_code"]})'
                if clabe_result["valid"]
                else f'CLABE inválida: {clabe_result["reason"]}'
            )
        }
        validaciones = result.get("validaciones", [])
        idx = next((i for i, v in enumerate(validaciones) if "clabe" in v.get("nombre", "").lower()), -1)
        if idx >= 0:
            validaciones[idx] = entry
        else:
            validaciones.insert(0, entry)
        result["validaciones"] = validaciones
        if not clabe_result["valid"]:
            result["score"] = max(result.get("score", 0), 70)
            result["riesgo"] = "ALTO"

    return result


@app.get("/")
def root():
    return {"status": "ok", "servicio": "Validador de Comprobantes API"}