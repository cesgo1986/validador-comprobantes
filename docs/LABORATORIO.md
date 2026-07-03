# LABORATORIO.md — Investigaciones y hallazgos experimentales

**Versión del documento:** 0.11.0 · **Última actualización:** 02/07/2026

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

---

## Investigaciones registradas

### 2026-07 — Falso positivo: BBVA muestra montos con signo negativo en egresos

**Qué se investigó:** por qué un comprobante legítimo de BBVA fue marcado con la validación "Monto negativo" (severidad alta, categoría estructural), a pesar de que la transferencia fue confirmada como liquidada por Banxico (estado SPEI correcto, sin discrepancias en el XML).

**Método:** revisión del comprobante real (imagen adjunta por el usuario) y del `system_prompt` que gobierna el análisis de Claude Vision en `main.py`.

**Resultado:** BBVA despliega el monto con signo negativo (ej. `-$40.00`) como convención visual para indicar que el dinero fue descontado de la cuenta (egreso) — no es una señal de alteración del documento. El `system_prompt` no distinguía este caso: la regla "Monto en cero o negativo" instruía a Claude a marcar como riesgo cualquier signo negativo, sin excepción.

**Consecuencia (decisión oficial derivada, confirmada en producción 2026-07):** se corrigió el `system_prompt` en `build_system_prompt()` (`main.py`) en tres puntos: (1) se agregó a las reglas de formatos válidos que algunos bancos muestran el monto con signo negativo para egresos y que esto no debe marcarse como riesgo; (2) se acotó la regla de "marcar como riesgo" para excluir el signo negativo consistente con esa convención; (3) se reforzó la instrucción de extracción del campo `monto` para que siempre se extraiga como valor absoluto (positivo). No se tocó lógica de backend — el problema vivía enteramente en el prompt, no en `normalize_monto_float()` ni en ninguna validación estructural de Python. Desplegado en Render y verificado contra el mismo comprobante de BBVA que originó el hallazgo: ya no marca "Monto negativo".

**Nota para crecimiento futuro:** este es el primer caso registrado de una convención de despliegue específica de un banco que generó un falso positivo. Si aparecen más casos de este tipo (otro banco con otra convención visual particular), vale la pena evaluar si conviene mantenerlos como reglas dentro del `system_prompt` (como aquí) o migrarlos a un catálogo de datos por banco — similar al patrón ya usado en `catalogo_bancos.json` para el flujo del CEP — en vez de seguir acumulando excepciones sueltas dentro del texto del prompt.

---

## Documentos relacionados

- `XML_CEP.md` — destino del detalle técnico de investigaciones ya cerradas sobre el CEP
- `DECISION_LOG.md` — destino de las decisiones oficiales derivadas de una investigación