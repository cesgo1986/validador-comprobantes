"""
services/cep_xml_service.py — Soporte para el XML oficial del CEP (Fase 2).

Alcance deliberadamente acotado, despues de la investigacion criptografica
documentada en el chat: este modulo NO valida la firma digital del XML.
Esa via se intento (certificado del SAT con el numero de serie referenciado
en el XML) y se refuto experimentalmente con una prueba RSA pura -- el
bloque resultante de sello^e mod n no tiene ninguna estructura de padding
reconocible (ni PKCS1v15 ni PSS), lo que demuestra que ese certificado no
firmo este XML. La llave real vive en infraestructura interna de Banxico/
SPEI, accesible solo a participantes del sistema -- no a terceros.

Lo que SI hace este modulo, con etiquetas honestas:
  1. Parsea el XML oficial (estructura, no PDF convertido).
  2. Compara campo por campo contra lo que el OCR/Claude extrajo de la imagen.
  3. Reporta el numero de certificado como dato presente en el XML, SIN
     afirmar que se validó criptográficamente.
  4. Deja explícito que la validacion de firma real solo puede confirmarse
     a traves del validador oficial de Banxico (banxico.org.mx/validador-cep-spei/),
     no localmente.
"""
import xml.etree.ElementTree as ET
from typing import Optional


class XMLCepInvalido(Exception):
    """El archivo subido no tiene la estructura esperada de un CEP de Banxico."""
    pass


def parsear_xml_cep(contenido_xml: bytes) -> dict:
    """
    Parsea el XML oficial del CEP (estructura SPEI_Tercero con hijos
    Ordenante/Beneficiario, confirmada contra un XML real descargado de
    banxico.org.mx/cep/ desde un dispositivo movil).

    Lanza XMLCepInvalido si la estructura no coincide -- por ejemplo, si
    alguien sube un XML que no es de Banxico, o un XML reconstruido a mano
    a partir de un PDF (que segun lo confirmado experimentalmente, carece
    de la estructura/firma real y el validador oficial de Banxico tampoco
    lo acepta).
    """
    try:
        root = ET.fromstring(contenido_xml)
    except ET.ParseError as e:
        raise XMLCepInvalido(f"El archivo no es un XML valido: {e}")

    if root.tag not in ("SPEI_Tercero", "SPEIPrimero", "SPEI_Primero"):
        raise XMLCepInvalido(
            f"La raiz del XML es '{root.tag}', no coincide con la estructura "
            "esperada de un CEP de Banxico (SPEI_Tercero)."
        )

    attrs = root.attrib
    ordenante = root.find("Ordenante")
    beneficiario = root.find("Beneficiario")

    if ordenante is None or beneficiario is None:
        raise XMLCepInvalido("El XML no contiene los nodos Ordenante y Beneficiario esperados.")

    return {
        "fecha_operacion": attrs.get("FechaOperacion"),
        "hora": attrs.get("Hora"),
        "clave_spei": attrs.get("ClaveSPEI"),
        "clave_rastreo": attrs.get("claveRastreo"),
        "numero_certificado": attrs.get("numeroCertificado"),
        "sello_presente": bool(attrs.get("sello")),
        "cadena_original_presente": bool(attrs.get("cadenaCDA")),

        "ordenante_banco": ordenante.attrib.get("BancoEmisor"),
        "ordenante_nombre": ordenante.attrib.get("Nombre"),
        "ordenante_cuenta": ordenante.attrib.get("Cuenta"),
        "ordenante_rfc": ordenante.attrib.get("RFC"),

        "beneficiario_banco": beneficiario.attrib.get("BancoReceptor"),
        "beneficiario_nombre": beneficiario.attrib.get("Nombre"),
        "beneficiario_cuenta": beneficiario.attrib.get("Cuenta"),
        "beneficiario_rfc": beneficiario.attrib.get("RFC"),
        "beneficiario_concepto": beneficiario.attrib.get("Concepto"),
        "monto_pago": beneficiario.attrib.get("MontoPago"),
    }


def _normalizar_monto(valor) -> Optional[float]:
    if valor is None:
        return None
    try:
        return round(float(str(valor).replace(",", "").replace("$", "")), 2)
    except ValueError:
        return None


def _normalizar_texto(valor) -> str:
    if not valor:
        return ""
    return str(valor).strip().upper()


def _ultimos_n(valor: str, n: int) -> str:
    v = "".join(ch for ch in str(valor) if ch.isdigit())
    return v[-n:] if len(v) >= n else v


def comparar_xml_contra_comprobante(xml_datos: dict, campos_planos: dict) -> dict:
    """
    Compara cada campo relevante del XML oficial contra lo que el OCR/
    Claude extrajo de la imagen del comprobante. Cada comparacion se
    reporta de forma independiente -- no se fusiona en un solo booleano,
    porque distintos bancos exponen distintos campos en su comprobante
    visual (algunos no muestran CLABE completa, por ejemplo), y mezclar
    eso con "coincide/no coincide" perderia esa distincion.
    """
    comparaciones = []

    monto_xml = _normalizar_monto(xml_datos.get("monto_pago"))
    monto_comprobante = _normalizar_monto(campos_planos.get("monto"))
    if monto_xml is not None and monto_comprobante is not None:
        coincide = abs(monto_xml - monto_comprobante) < 0.01
        comparaciones.append({
            "campo": "monto",
            "valor_xml": monto_xml,
            "valor_comprobante": monto_comprobante,
            "coincide": coincide,
        })

    fecha_xml = xml_datos.get("fecha_operacion")
    fecha_comprobante = campos_planos.get("fecha")
    if fecha_xml and fecha_comprobante:
        # Comparacion superficial -- los formatos de fecha varian mucho
        # entre bancos (DD/MM/YYYY vs YYYY-MM-DD); se reportan ambos
        # valores para que el usuario juzgue, en vez de normalizar de
        # forma fragil y arriesgar falsos negativos.
        comparaciones.append({
            "campo": "fecha",
            "valor_xml": fecha_xml,
            "valor_comprobante": fecha_comprobante,
            "coincide": None,  # requiere revision manual por formato variable
        })

    clave_rastreo_xml = _normalizar_texto(xml_datos.get("clave_rastreo"))
    clave_rastreo_comprobante = _normalizar_texto(campos_planos.get("clave_rastreo"))
    if clave_rastreo_xml and clave_rastreo_comprobante:
        comparaciones.append({
            "campo": "clave_rastreo",
            "valor_xml": clave_rastreo_xml,
            "valor_comprobante": clave_rastreo_comprobante,
            "coincide": clave_rastreo_xml == clave_rastreo_comprobante,
        })

    banco_destino_xml = _normalizar_texto(xml_datos.get("beneficiario_banco"))
    banco_destino_comprobante = _normalizar_texto(campos_planos.get("banco_destino"))
    if banco_destino_xml and banco_destino_comprobante:
        # Comparacion por contiene, no igualdad exacta: el comprobante
        # puede decir "BANXICO" o "AZTECA" mientras el XML dice el nombre
        # completo de la institucion.
        coincide = banco_destino_xml in banco_destino_comprobante or banco_destino_comprobante in banco_destino_xml
        comparaciones.append({
            "campo": "banco_destino",
            "valor_xml": banco_destino_xml,
            "valor_comprobante": banco_destino_comprobante,
            "coincide": coincide,
        })

    cuenta_xml = xml_datos.get("beneficiario_cuenta")
    clabe_comprobante = campos_planos.get("clabe_parcial")
    if cuenta_xml and clabe_comprobante:
        # El comprobante casi siempre enmascara la cuenta (****1234) --
        # comparamos solo los ultimos digitos visibles.
        ultimos_comprobante = _ultimos_n(clabe_comprobante, 4)
        ultimos_xml = _ultimos_n(cuenta_xml, 4)
        if ultimos_comprobante:
            comparaciones.append({
                "campo": "cuenta_destino_ultimos_digitos",
                "valor_xml": ultimos_xml,
                "valor_comprobante": ultimos_comprobante,
                "coincide": ultimos_xml == ultimos_comprobante,
            })

    total = len(comparaciones)
    coincidencias = sum(1 for c in comparaciones if c["coincide"] is True)
    discrepancias = sum(1 for c in comparaciones if c["coincide"] is False)

    return {
        "comparaciones": comparaciones,
        "total_campos_comparados": total,
        "coincidencias": coincidencias,
        "discrepancias": discrepancias,
    }


def construir_resultado_xml(xml_datos: dict, comparacion: dict) -> dict:
    """
    Construye el bloque de resultado para insertar en la respuesta del
    analisis. Las etiquetas siguen exactamente la Capa 2 corregida
    discutida en el chat: se reporta SOLO lo que es verificable
    (presencia del numero de certificado, estructura del XML, comparacion
    de campos) sin afirmar una validacion criptografica que no se realizo.
    """
    return {
        "xml_proporcionado": True,
        "clave_rastreo": xml_datos.get("clave_rastreo"),
        "numero_certificado_presente": xml_datos.get("numero_certificado"),
        "estructura_xml_valida": True,
        "comparacion_campos": comparacion,
        "nota_validacion_criptografica": (
            "El XML contiene un numero de certificado y un sello digital, pero "
            "VerificaPago no realiza validacion criptografica local de la firma: "
            "esa verificacion depende de la infraestructura interna de Banxico/SPEI, "
            "accesible solo a participantes del sistema. Para una validacion "
            "criptografica oficial, usa el validador de Banxico: "
            "https://www.banxico.org.mx/validador-cep-spei/"
        ),
    }