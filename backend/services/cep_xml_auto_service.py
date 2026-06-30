"""
services/cep_xml_auto_service.py — Descarga automática del XML del CEP (Fase 2-B).

Investigado y validado a fondo en el chat antes de construirse: el endpoint
valida.do de banxico.org.mx/cep/ NO valida el campo de captcha del lado del
servidor (confirmado con una peticion de prueba real, mandada desde Render,
que el servidor proceso sin pedir el campo). El captcha que aparece en el
HTML del navegador es del lado del cliente (oculto/mostrado por JS segun
condiciones de sesion que no controla esta consulta) -- no es una barrera
real para una peticion HTTP directa bien formada.

Flujo replicado (capturado con DevTools de un flujo real en banxico.org.mx):
  1. GET  /cep/                              -> obtiene cookies de sesion
  2. POST /cep/valida.do  (con los datos)     -> valida la operacion
  3. GET  /cep/descarga.do?formato=XML        -> descarga el XML, misma sesion

Esto es scraping de un endpoint NO documentado publicamente -- puede
romperse sin aviso si Banxico cambia su HTML/flujo. Por eso TODO este
modulo degrada con gracia: cualquier fallo simplemente significa "no se
pudo obtener el XML automaticamente", nunca interrumpe el analisis
principal del comprobante.
"""
import re
import datetime
import httpx

CEP_BASE_URL = "https://www.banxico.org.mx/cep/"

# Codigo SPEI = "40" + codigo CLABE de 3 digitos (confirmado empiricamente:
# BBVA CLABE=002 -> SPEI=40012, AZTECA CLABE=127 -> SPEI=40127).
BANKS_CLABE_A_SPEI = {
    "002": "40012", "006": "40006", "009": "40009", "012": "40012",
    "014": "40014", "021": "40021", "030": "40030", "036": "40036",
    "037": "40037", "044": "40044", "058": "40058", "059": "40059",
    "062": "40062", "072": "40072", "127": "40127", "128": "40128",
    "130": "40130", "137": "40137", "145": "40145", "147": "40147",
    "600": "40600", "601": "40601", "646": "40646", "706": "40706",
    "722": "40722", "723": "40723", "728": "40728", "741": "40741",
    "748": "40748",
}

# Nombres tal como el OCR/Claude suelen extraerlos -> codigo CLABE de 3
# digitos. Reutiliza el mismo catalogo de nombres que ya usa main.py
# (BANKS invertido), mapeado a texto en mayusculas sin acentos para
# comparacion tolerante.
NOMBRES_A_CLABE = {
    "BBVA": "002", "BANCOMEXT": "006", "BANOBRAS": "009", "HSBC": "012",
    "SANTANDER": "014", "BAJIO": "030", "INBURSA": "036", "MULTIVA": "037",
    "SCOTIABANK": "044", "BANREGIO": "058", "INVEX": "059", "AFIRME": "062",
    "BANORTE": "072", "AZTECA": "127", "AUTOFIN": "128", "COMPARTAMOS": "130",
    "BANCOPPEL": "137", "BANJERCITO": "145", "BANKAOOL": "147",
    "MONEXCB": "600", "GBM": "601", "STP": "646", "ARCUS": "706",
    "MERCADO PAGO": "722", "CUENCA": "723", "SPIN BY OXXO": "728",
    "KLAR": "741", "BINEO": "748",
}


def nombre_banco_a_codigo_spei(nombre_banco: str) -> str | None:
    """Traduce un nombre de banco (tal como lo extrae el OCR) a su codigo SPEI de 5 digitos."""
    if not nombre_banco:
        return None
    nombre_norm = nombre_banco.strip().upper()
    for nombre_catalogo, clabe in NOMBRES_A_CLABE.items():
        if nombre_catalogo in nombre_norm or nombre_norm in nombre_catalogo:
            return BANKS_CLABE_A_SPEI.get(clabe)
    return None


def _normalizar_fecha_ddmmyyyy(fecha_str: str) -> str | None:
    """valida.do espera la fecha en formato DD-MM-YYYY. Reutiliza los mismos
    formatos que ya soporta el resto del sistema (ver iat.parse_date)."""
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


def _normalizar_monto_para_consulta(monto) -> str | None:
    if monto is None:
        return None
    try:
        valor = float(str(monto).replace(",", "").replace("$", ""))
        if valor <= 0:
            return None
        # Banxico espera el monto sin separador de miles, con punto decimal.
        return f"{valor:.2f}".rstrip("0").rstrip(".") if valor == int(valor) else f"{valor:.2f}"
    except (ValueError, TypeError):
        return None


def datos_suficientes_para_consulta(campos_planos: dict) -> dict:
    """
    Revisa si hay suficiente informacion (extraida del comprobante) para
    intentar la consulta automatica del XML, sin pedir nada al usuario.
    Devuelve que falta, si algo falta.
    """
    clave_o_referencia = campos_planos.get("clave_rastreo") or campos_planos.get("referencia")
    fecha = _normalizar_fecha_ddmmyyyy(campos_planos.get("fecha") or "")
    banco_emisor = nombre_banco_a_codigo_spei(campos_planos.get("banco_origen") or "")
    banco_receptor = nombre_banco_a_codigo_spei(campos_planos.get("banco_destino") or "")
    cuenta = (campos_planos.get("clabe_parcial") or "").replace("*", "").replace(" ", "")
    monto = _normalizar_monto_para_consulta(campos_planos.get("monto") or campos_planos.get("monto_texto"))

    faltantes = []
    if not clave_o_referencia:
        faltantes.append("clave_rastreo_o_referencia")
    if not fecha:
        faltantes.append("fecha")
    if not banco_emisor:
        faltantes.append("banco_emisor")
    if not banco_receptor:
        faltantes.append("banco_receptor")
    if not cuenta or len(cuenta) < 4:
        faltantes.append("cuenta_destino")
    if not monto:
        faltantes.append("monto")

    return {
        "suficiente": len(faltantes) == 0,
        "faltantes": faltantes,
        "datos": {
            "clave_o_referencia": clave_o_referencia,
            "fecha": fecha,
            "banco_emisor": banco_emisor,
            "banco_receptor": banco_receptor,
            "cuenta": cuenta,
            "monto": monto,
        },
    }


async def descargar_xml_cep_automatico(
    clave_o_referencia: str,
    fecha_ddmmyyyy: str,
    banco_emisor_spei: str,
    banco_receptor_spei: str,
    cuenta: str,
    monto: str,
) -> dict:
    """
    Replica la secuencia GET / -> POST valida.do -> GET descarga.do?formato=XML
    capturada con DevTools de un flujo real. Devuelve:
      {"exito": True, "xml_bytes": b"..."}
    o
      {"exito": False, "razon": "..."}
    Nunca lanza excepcion -- cualquier fallo se captura y se reporta como
    "exito": False, para que el analisis principal nunca se vea afectado.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Paso 1: sesion inicial
            resp_inicial = await client.get(CEP_BASE_URL)
            if resp_inicial.status_code != 200:
                return {"exito": False, "razon": f"No se pudo iniciar sesion (status {resp_inicial.status_code})"}

            # Paso 2: validar la consulta
            payload = {
                "tipoCriterio": "T",  # T = clave de rastreo / referencia (confirmado en el payload real capturado)
                "fecha": fecha_ddmmyyyy,
                "criterio": clave_o_referencia,
                "emisor": banco_emisor_spei,
                "receptor": banco_receptor_spei,
                "cuenta": cuenta,
                "receptorParticipante": "0",
                "monto": monto,
                "captcha": "",  # confirmado: no se valida del lado del servidor
                "tipoConsulta": "1",
            }
            resp_valida = await client.post(CEP_BASE_URL + "valida.do", data=payload)
            if resp_valida.status_code != 200:
                return {"exito": False, "razon": f"La consulta no fue aceptada (status {resp_valida.status_code})"}

            if "boton-descarga-xml" not in resp_valida.text:
                # La consulta no genero el modal de descarga -- la operacion
                # no se encontro con esos datos, o hubo un error de negocio
                # (ej. "No existe un tipo de criterio" si algun campo viene mal).
                mensaje_error = "No fue posible localizar la operacion con los datos proporcionados."
                m = re.search(r'<p[^>]*>\s*([^<]+?)\s*</p>', resp_valida.text)
                if m:
                    mensaje_error = m.group(1).strip()
                return {"exito": False, "razon": mensaje_error}

            # Paso 3: descargar el XML, misma sesion (cookies ya en el client)
            resp_xml = await client.get(CEP_BASE_URL + "descarga.do", params={"formato": "XML"})
            if resp_xml.status_code != 200:
                return {"exito": False, "razon": f"No se pudo descargar el XML (status {resp_xml.status_code})"}

            xml_bytes = resp_xml.content
            if not xml_bytes or b"<SPEI_Tercero" not in xml_bytes:
                return {"exito": False, "razon": "La respuesta no tiene la estructura esperada de un XML de CEP."}

            return {"exito": True, "xml_bytes": xml_bytes}

    except httpx.TimeoutException:
        return {"exito": False, "razon": "Tiempo de espera agotado al consultar Banxico."}
    except Exception as e:
        return {"exito": False, "razon": f"Error inesperado: {type(e).__name__}: {e}"}