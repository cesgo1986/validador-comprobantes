# XML_CEP.md — Comprobante Electrónico de Pago de Banxico

Documentación técnica de todo lo investigado sobre el CEP de Banxico, incluyendo hallazgos empíricos, limitaciones y decisiones de diseño. Esta información fue reconstruida mediante investigación directa del portal, capturas de DevTools y pruebas criptográficas reales.

---

## Qué es el CEP

El Comprobante Electrónico de Pago (CEP) es el documento oficial que Banxico genera para confirmar que una transferencia SPEI fue procesada. Es la fuente de verdad más confiable disponible públicamente para verificar si una operación SPEI existió.

Portal: `banxico.org.mx/cep/`  
Validador oficial: `banxico.org.mx/validador-cep-spei/`  
CEP por lotes (B2B): `banxico.org.mx/cep-scl/`

---

## Estructura del XML oficial

El XML descargado del portal tiene esta estructura (confirmada con un archivo real):

```xml
<SPEI_Tercero
  FechaOperacion="2026-06-17"
  Hora="00:15:14"
  ClaveSPEI="40127"
  sello="b68NL+DD2yZE64/..."       <!-- 344 caracteres base64 = 256 bytes = RSA-2048 -->
  numeroCertificado="00001000000518750173"
  cadenaCDA="||1|17062026|..."      <!-- cadena original de la operación -->
  claveRastreo="MBAN01002606170065727438">
  <Beneficiario
    BancoReceptor="AZTECA"
    Nombre="..."
    TipoCuenta="3"
    Cuenta="4027665005017331"
    RFC="..."
    Concepto="..."
    MontoPago="20" />
  <Ordenante
    BancoEmisor="BBVA MEXICO"
    Nombre="..."
    TipoCuenta="40"
    Cuenta="012180015926940231"
    RFC="..." />
</SPEI_Tercero>
```

---

## Flujo de descarga automatizada

Replicación del comportamiento del portal `banxico.org.mx/cep/` capturado con DevTools (Chrome, pestaña Network, filtro Fetch/XHR):

### Paso 1 — Sesión inicial
```
GET https://www.banxico.org.mx/cep/
→ 200 OK
→ Set-Cookie: JSESSIONID=...; Hex49615001=...; TS012f422b=...; TS604574e3027=...
```

### Paso 2 — Validar la operación
```
POST https://www.banxico.org.mx/cep/valida.do
Content-Type: application/x-www-form-urlencoded

tipoCriterio=T
fecha=24-06-2026
criterio=MBAN01002606240057113860
emisor=40012
receptor=40127
cuenta=4027665005017331
receptorParticipante=0
monto=40
captcha=
tipoConsulta=1

→ 200 OK
→ HTML con botones de descarga (PDF, XML, ZIP)
   y <input type="hidden" name="varHideCaptcha" value="true"/>
```

### Paso 3 — Descargar el XML
```
GET https://www.banxico.org.mx/cep/descarga.do?formato=XML
(mismas cookies de la sesión)
→ 200 OK
→ Content-Type: application/xml
→ Body: <?xml version="1.0"?><SPEI_Tercero ...>
```

### Sobre el captcha

El campo `captcha` existe en el HTML del formulario visible al usuario, pero el servidor **no lo valida** en el endpoint `valida.do` al momento de implementar este módulo. Esto se confirmó empíricamente enviando el campo vacío desde infraestructura de Render (IP de datacenter, no IP residencial) y obteniendo una respuesta exitosa. El comportamiento puede cambiar sin previo aviso.

### Códigos SPEI de bancos

Los códigos de instituciones que acepta `valida.do` siguen el formato `"40"` + código CLABE de 3 dígitos:
- BBVA: `40012` (CLABE 002 → no, CLABE 012)
- AZTECA: `40127`
- BANORTE: `40072`
- STP: `40646`

El catálogo completo vive en `backend/catalogo_bancos.json` y puede actualizarse sin cambios de código.

---

## Detección de éxito (por capas)

Para saber si `valida.do` encontró la operación, se usa una detección en capas (de más a menos robusta):

1. **La URL final redirige a `descarga.do`** — exito garantizado
2. **Content-Type de la respuesta es `application/xml`** — Banxico entregó el XML directamente
3. **El body contiene alguna señal del JSON** (ej. `"descarga.do"`, `"boton-descarga"`) — configurable en `catalogo_bancos.json`

Nunca se hardcodea un string específico de clase CSS como `"boton-descarga-xml"` — ese tipo de dependencia se rompe cuando Banxico actualiza su frontend.

---

## Investigación criptográfica del sello digital

### Contexto

El XML del CEP contiene tres campos criptográficos:
- `numeroCertificado`: identificador del certificado usado para firmar
- `cadenaCDA`: cadena original de la operación (632 caracteres)
- `sello`: firma digital en base64 (344 caracteres = 256 bytes = RSA-2048)

### Hipótesis investigada

El número de certificado `00001000000518750173`, interpretado como ASCII de un valor hexadecimal, coincide con un certificado descargable del portal de recuperación de certificados del SAT (`portalsat.plataforma.sat.gob.mx`). El certificado encontrado es de tipo **FIEL**, perteneciente a una persona física, emitido por la Autoridad Certificadora del SAT con algoritmo `sha256RSA`.

### Prueba criptográfica realizada

Se ejecutó la operación RSA inversa pura:

```python
sello_int = int.from_bytes(base64.b64decode(sello_b64), byteorder='big')
resultado_int = pow(sello_int, e, n)  # e=65537, n=módulo de 2048 bits
resultado_bytes = resultado_int.to_bytes(256, byteorder='big')
```

**Resultado:** el bloque de 256 bytes no exhibe ninguna estructura de padding reconocida:
- No empieza con `0x00 0x01 0xFF...` (PKCS#1 v1.5)
- No termina con `0xBC` (RSASSA-PSS)
- No contiene ningún `DigestInfo` ASN.1 con OID de SHA-256

**Conclusión:** el certificado del SAT con ese número de serie no es la llave que firmó este XML. El número de serie del XML es un identificador que coincide textualmente con uno del SAT, pero la llave privada que firmó el CEP pertenece a la infraestructura interna de Banxico/SPEI (IES) y no está disponible públicamente.

### Consecuencia de diseño

VerificaPago no realiza validación criptográfica local del XML. Para obtener la validación oficial de firma, el usuario debe usar el validador web de Banxico: `banxico.org.mx/validador-cep-spei/`. Este validador acepta solo XMLs descargados directamente del portal de Banxico — un XML generado a partir de convertir un PDF no es aceptado.

---

## Limitaciones conocidas

1. **Endpoint no documentado:** `valida.do` y `descarga.do` no son APIs públicas documentadas. Pueden cambiar sin aviso.
2. **Dependencia de sesión:** la descarga del XML requiere mantener cookies activas entre los 3 pasos del flujo (GET sesión → POST valida → GET descarga). Si el servidor invalida la sesión entre pasos, el flujo falla.
3. **Sin validación de firma:** ver sección anterior.
4. **CEP disponible solo para SPEI:** no aplica para transferencias SPID (dólares) ni para pagos CoDi.
5. **Disponibilidad del portal:** el portal de Banxico puede estar en mantenimiento o degradado. La trazabilidad implementada (`traza` en la respuesta) registra tiempos, status codes y headers para facilitar el diagnóstico cuando esto ocurra.