# LABORATORIO.md — Investigaciones y hallazgos experimentales

Registro de experimentos, investigaciones técnicas, benchmarks e ideas descartadas de VerificaPago. **No es un registro de decisiones** — es el espacio para todo lo que se investigó, se probó o se descartó, tenga o no tenga una decisión oficial asociada todavía.

## Por qué existe este documento, separado de DECISION_LOG.md

`DECISION_LOG.md` registra decisiones ya tomadas: qué se decidió, por qué y qué consecuencias tuvo. Mezclar ahí las investigaciones que llevaron a esa decisión —o, peor, las que no llevaron a ninguna— diluye el propósito del log de decisiones y hace más difícil encontrar "qué se decidió" entre "qué se probó".

`LABORATORIO.md` es el lugar para:
- Experimentos técnicos (ej. pruebas contra endpoints no documentados de Banxico)
- Investigación sobre certificados, criptografía, protocolos
- Pruebas con modelos de IA (prompts, comparaciones, benchmarks)
- Ideas evaluadas y descartadas, con el motivo del descarte
- Hallazgos técnicos que no requirieron una decisión formal, pero que vale la pena que el equipo no vuelva a investigar desde cero

**Regla simple:** si el resultado de la investigación cambió cómo funciona o se construye VerificaPago, la decisión correspondiente vive en `DECISION_LOG.md` (opcionalmente marcada `#ADR-VP` si fue arquitectónica) y puede referenciar la entrada de este documento para el detalle experimental. Si la investigación no cambió nada — confirmó una hipótesis, la descartó, o quedó abierta — vive únicamente aquí.

## Convención de captura

Durante las sesiones de trabajo, estas investigaciones se marcan con `🧪 #LAB-VP` para traerlas a este chat (Arquitecto de Conocimiento). Junto con `📘 #DOC-VP` (documentación rutinaria) y `🏛️ #ADR-VP` (decisión arquitectónica), forman las tres categorías de captura de VerificaPago — ver `DECISION_LOG.md` para el detalle completo de las tres.

---

## Investigaciones registradas

### 2026-06 — Validación criptográfica del sello digital del XML del CEP

**Qué se investigó:** si el certificado del SAT cuyo número de serie coincide textualmente con el que referencia el XML del CEP era, en efecto, la llave que firmó ese XML.

**Método:** operación RSA inversa pura (`sello^e mod n`) sobre el sello digital del XML, usando el módulo y exponente del certificado FIEL descargado del portal de recuperación de certificados del SAT.

**Resultado:** el bloque de 256 bytes resultante no exhibió ninguna estructura de padding reconocida (ni PKCS#1 v1.5 ni RSASSA-PSS) — el certificado del SAT no es la llave que firmó el XML. La llave privada real pertenece a la infraestructura interna de Banxico/SPEI (IES) y no está disponible públicamente.

**Consecuencia (decisión oficial derivada):** VerificaPago no realiza validación criptográfica local del XML — ver `DECISION_LOG.md`, entrada "No realizar validación criptográfica local del XML del CEP". El detalle técnico completo de la investigación (estructura del XML, hipótesis, código de la prueba) vive en `XML_CEP.md`, sección "Investigación criptográfica del sello digital" — no se duplica aquí, esta entrada solo indexa que la investigación existe y dónde está.

---

*Nuevas investigaciones se agregan arriba de esta línea a medida que ocurren, con fecha, qué se investigó, método, resultado y — si aplica — la decisión oficial derivada y dónde vive.*