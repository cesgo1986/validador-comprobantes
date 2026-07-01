"""
services/cep_xml_auto_service.py

Replicacion del flujo de consulta y descarga del XML oficial del CEP
desde el portal de Banxico (banxico.org.mx/cep/).

Este modulo replica el comportamiento observado en el portal al momento
de su implementacion. Dicho comportamiento puede cambiar sin previo aviso
por parte de Banxico. Todos los parametros configurables (endpoints,
tipo de criterio, senales de exito) viven en catalogo_bancos.json, no
en este archivo, para poder ajustarlos sin modificar codigo.

La descarga del XML es una funcionalidad opcional que nunca detiene el
analisis principal. Cualquier fallo en cualquier paso se captura y se
reporta en el campo cep_xml del resultado, sin afectar el resto del
pipeline.

Nota sobre la firma digital del XML: no se valida localmente. La via
de validacion fue investigada con una prueba RSA pura (sello^e mod n)
y el bloque resultante no exhibio ninguna estructura de padding
reconocida (ni PKCS1v15 ni PSS). La llave privada que firma el XML
pertenece a la infraestructura interna de Banxico/SPEI y no esta
disponible publicamente.
"""
import json
import os
import re
import time
import datetime
from typing import Optional
import httpx

# ─────────────────────────────────────────────────────────────────────────────
# Configuracion — cargada desde JSON, no hardcodeada en el codigo
# ─────────────────────────────────────────────────────────────────────────────

_CATALOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "catalogo_bancos.json")
_CATALOGO_PATH = os.path.normpath(_CATALOGO_PATH)

def _cargar_catalogo() -> dict:
    try:
        with open(_CATALOGO_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        return {}

_catalogo = _cargar_catalogo()
_cep_cfg = _catalogo.get("cep_flujo", {})
_bancos = _catalogo.get("bancos", {})

# Construir indices de busqueda rapida: nombre/alias -> codigo_spei
_nombre_a_spei: dict[str, str] = {}
for _clabe, _banco in _bancos.items():
    _codigo_spei = _banco.get("codigo_spei", "")
    if not _codigo_spei:
        continue
    for _nombre in [_banco.get("nombre", "")] + _banco.get("aliases", []):
        if _nombre:
            _nombre_a_spei[_nombre.upper()] = _codigo_spei


def nombre_banco_a_codigo_spei(nombre_banco: str) -> Optional[str]:
    """
    Traduce un nombre de banco (tal como lo extrae el OCR) a su codigo
    SPEI, buscando coincidencias exactas y parciales en el catalogo.
    Si el catalogo no tiene una coincidencia, devuelve None sin fallar.
    """
    if not nombre_banco:
        return None
    nombre_norm = nombre_banco.strip().upper()
    if nombre_norm in _nombre_a_spei:
        return _nombre_a_spei[nombre_norm]
    for nombre_catalogo, codigo in _nombre_a_spei.items():
        if nombre_catalogo in nombre_norm or nombre_norm in nombre_catalogo:
            return codigo
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Normalizacion de datos de entrada
# ─────────────────────────────────────────────────────────────────────────────

def _normalizar_fecha_ddmmyyyy(fecha_str: str) -> Optional[str]:
    if not fecha_str:
        return None
    formatos = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y/%m/%d"]
    for fmt in formatos:
        try:
            dt = datetime.datetime.strptime(fecha_str.strip(), fmt)
            return dt.strftime("%d-%m-%Y")
        except ValueError:
            continue
    return None


def _normalizar_monto(monto) -> Optional[str]:
    if monto is None:
        return None
    try:
        valor = float(str(monto).replace(",", "").replace("$", "").strip())
        if valor <= 0:
            return None
        return str(int(valor)) if valor == int(valor) else f"{valor:.2f}"
    except (ValueError, TypeError):
        return None


def datos_suficientes_para_consulta(campos_planos: dict) -> dict:
    clave = campos_planos.get("clave_rastreo") or campos_planos.get("referencia")
    fecha = _normalizar_fecha_ddmmyyyy(campos_planos.get("fecha") or "")
    emisor = nombre_banco_a_codigo_spei(campos_planos.get("banco_origen") or "")
    receptor = nombre_banco_a_codigo_spei(campos_planos.get("banco_destino") or "")
    cuenta = re.sub(r"[^\d]", "", campos_planos.get("clabe_parcial") or "")
    monto = _normalizar_monto(
        campos_planos.get("monto") or campos_planos.get("monto_texto")
    )

    faltantes = [
        campo for campo, valor in [
            ("clave_rastreo_o_referencia", clave),
            ("fecha", fecha),
            ("banco_emisor", emisor),
            ("banco_receptor", receptor),
            ("cuenta_destino", cuenta if len(cuenta) >= 4 else None),
            ("monto", monto),
        ] if not valor
    ]

    return {
        "suficiente": len(faltantes) == 0,
        "faltantes": faltantes,
        "datos": {
            "clave_o_referencia": clave,
            "fecha": fecha,
            "banco_emisor": emisor,
            "banco_receptor": receptor,
            "cuenta": cuenta,
            "monto": monto,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Trazabilidad — registro de cada peticion HTTP para facilitar diagnostico
# cuando el comportamiento del portal cambie.
# ─────────────────────────────────────────────────────────────────────────────

def _registrar_peticion(
    metodo: str,
    url: str,
    response: httpx.Response,
    duracion_ms: float,
) -> dict:
    """
    Registra metadatos de una peticion HTTP. No incluye el body completo
    (puede ser grande), solo las senales de diagnostico utiles.
    """
    return {
        "ts": datetime.datetime.utcnow().isoformat(),
        "metodo": metodo,
        "url": url,
        "status": response.status_code,
        "duracion_ms": round(duracion_ms, 1),
        "content_type": response.headers.get("content-type", ""),
        "content_length": response.headers.get("content-length"),
        "redirect_url": str(response.url) if str(response.url) != url else None,
        "cookies_recibidas": list(response.cookies.keys()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Deteccion de exito — sin depender del HTML
# ─────────────────────────────────────────────────────────────────────────────

def _valida_exitoso(response: httpx.Response) -> bool:
    """
    Determina si la respuesta de valida.do indica que la operacion existe
    y el portal esta listo para entregar el XML.

    Estrategia de deteccion por capas (de mas a menos robusto):
    1. La URL final (despues de redirects) apunta a descarga.do -> exito seguro.
    2. El Content-Type de la respuesta es application/xml -> el portal entrego
       el XML directamente sin un paso intermedio (posible en algunos flujos).
    3. El body contiene alguna de las senales de exito definidas en el catalogo
       (lista configurable en catalogo_bancos.json, no hardcodeada aqui).
    4. Si el body contiene algun patron de error conocido -> fallo explicito.

    Esta jerarquia hace que el codigo sea mas resistente a cambios en el
    HTML del portal: si manana Banxico cambia 'boton-descarga-xml' por
    otro nombre de clase, la deteccion por Content-Type/redirect sigue
    funcionando y la senal HTML puede actualizarse en el JSON sin tocar
    codigo.
    """
    # Capa 1: redirect a descarga.do
    url_final = str(response.url).lower()
    if "descarga.do" in url_final:
        return True

    # Capa 2: content-type indica XML directo
    ct = response.headers.get("content-type", "").lower()
    tipos_validos = _cep_cfg.get("content_types_xml_validos", [])
    if any(t in ct for t in tipos_validos):
        return True

    # Capa 3: senales en el body (configurables en JSON, no hardcodeadas)
    body = response.text
    senales = _cep_cfg.get("senales_exito_valida", [])
    if any(senal in body for senal in senales):
        return True

    return False


def _xml_valido(response: httpx.Response) -> bool:
    """
    Verifica que la respuesta de descarga.do sea realmente un XML del CEP
    y no una pagina de error. Basado en Content-Type y estructura del body,
    no en nombres de clases HTML.
    """
    ct = response.headers.get("content-type", "").lower()
    tipos_validos = _cep_cfg.get("content_types_xml_validos", [])
    content = response.content

    if any(t in ct for t in tipos_validos):
        return True
    if content.startswith(b"<?xml") or b"<SPEI_Tercero" in content:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Descarga automatica del XML
# ─────────────────────────────────────────────────────────────────────────────

async def descargar_xml_cep_automatico(
    clave_o_referencia: str,
    fecha_ddmmyyyy: str,
    banco_emisor_spei: str,
    banco_receptor_spei: str,
    cuenta: str,
    monto: str,
) -> dict:
    """
    Replica la secuencia de consulta del portal CEP:
      1. GET  /cep/           -> sesion inicial (cookies)
      2. POST /cep/valida.do  -> consulta la operacion
      3. GET  /cep/descarga.do?formato=XML -> descarga el XML

    Devuelve:
      {"exito": True, "xml_bytes": b"...", "traza": [...]}
    o:
      {"exito": False, "razon": "...", "traza": [...]}

    La traza incluye metadatos de cada peticion HTTP para facilitar el
    diagnostico cuando el comportamiento del portal cambie.
    """
    traza = []
    url_base = _cep_cfg.get("url_base", "https://www.banxico.org.mx/cep/")
    endpoint_valida = _cep_cfg.get("endpoint_valida", "valida.do")
    endpoint_descarga = _cep_cfg.get("endpoint_descarga", "descarga.do")
    tipo_criterio = _cep_cfg.get("tipo_criterio_clave_rastreo", "T")
    tipo_consulta = _cep_cfg.get("tipo_consulta_default", "1")
    receptor_participante = _cep_cfg.get("receptor_participante_default", "0")
    captcha_valor = _cep_cfg.get("campo_captcha_valor", "")
    timeout = _cep_cfg.get("timeout_segundos", 15)

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        }

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers) as client:

            # Paso 1: sesion inicial
            t0 = time.time()
            resp1 = await client.get(url_base)
            traza.append(_registrar_peticion("GET", url_base, resp1, (time.time()-t0)*1000))
            if resp1.status_code != 200:
                return {"exito": False, "razon": f"No se pudo iniciar sesion (status {resp1.status_code})", "traza": traza}

            # Paso 2: validar la operacion
            payload = {
                "tipoCriterio": tipo_criterio,
                "fecha": fecha_ddmmyyyy,
                "criterio": clave_o_referencia,
                "emisor": banco_emisor_spei,
                "receptor": banco_receptor_spei,
                "cuenta": cuenta,
                "receptorParticipante": receptor_participante,
                "monto": monto,
                "captcha": captcha_valor,
                "tipoConsulta": tipo_consulta,
            }
            url_valida = url_base + endpoint_valida
            t0 = time.time()
            resp2 = await client.post(url_valida, data=payload)
            traza.append(_registrar_peticion("POST", url_valida, resp2, (time.time()-t0)*1000))
            if resp2.status_code != 200:
                return {"exito": False, "razon": f"La consulta no fue aceptada (status {resp2.status_code})", "traza": traza}

            if not _valida_exitoso(resp2):
                # Extraer el mensaje de error del body si existe
                razon = "No fue posible localizar la operacion con los datos proporcionados."
                m = re.search(r'<p[^>]*>\s*([^<]{5,}?)\s*</p>', resp2.text)
                if m:
                    razon = m.group(1).strip()
                return {"exito": False, "razon": razon, "traza": traza}

            # Paso 3: descargar el XML
            url_descarga = url_base + endpoint_descarga
            t0 = time.time()
            resp3 = await client.get(url_descarga, params={"formato": "XML"})
            traza.append(_registrar_peticion("GET", url_descarga, resp3, (time.time()-t0)*1000))
            if resp3.status_code != 200:
                return {"exito": False, "razon": f"No se pudo descargar el XML (status {resp3.status_code})", "traza": traza}

            if not _xml_valido(resp3):
                return {"exito": False, "razon": "La respuesta no tiene estructura de XML del CEP.", "traza": traza}

            return {"exito": True, "xml_bytes": resp3.content, "traza": traza}

    except httpx.TimeoutException:
        return {"exito": False, "razon": "Tiempo de espera agotado al consultar Banxico.", "traza": traza}
    except Exception as e:
        return {"exito": False, "razon": f"Error inesperado: {type(e).__name__}: {e}", "traza": traza}