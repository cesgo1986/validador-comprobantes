# DECISION_LOG.md — Registro de decisiones

**Versión del documento:** 0.11.0 · **Última actualización:** 02/07/2026

Registro de decisiones importantes tomadas durante el desarrollo de VerificaPago. No es un changelog de código — es el "por qué" detrás de las decisiones de arquitectura y producto. Cada entrada incluye la decisión, el motivo y las consecuencias para que puedan revisarse y cuestionarse en el futuro.

## Convenciones de captura (sesiones de trabajo)

Durante las sesiones de trabajo en Verificapago / Verificapago1.1, lo que amerita documentación se marca con uno de tres identificadores, para traerlo después a este chat (Arquitecto de Conocimiento):

- **📘 `#DOC-VP`** — documentación rutinaria: cualquier decisión, hallazgo o ajuste que valga la pena registrar, sin importar el tamaño.
- **🏛️ `#ADR-VP`** (Architecture Decision Record) — exclusivo para decisiones que cambian la arquitectura del sistema (ej. cambiar el origen de verdad de un dato, mover lógica entre capas, alterar la jerarquía de evidencia). Formato sugerido al marcarlas: *Decisión* / *Motivo* / *Impacto* / *Documentos afectados*.
- **🧪 `#LAB-VP`** — investigaciones o hallazgos experimentales que todavía no son (o nunca llegan a ser) una decisión oficial: experimentos con Banxico, investigación de certificados, pruebas con IA, benchmarks, ideas descartadas. Vive en `LABORATORIO.md`, no en este log — si la investigación termina en un cambio real al sistema, la decisión correspondiente sí se registra aquí (opcionalmente como `#ADR-VP`), referenciando la entrada de `LABORATORIO.md` para el detalle experimental.

Los tres se complementan, no se sustituyen entre sí: permiten distinguir de un vistazo qué fue documentación de avance normal, qué fue una decisión arquitectónica deliberada, y qué fue investigación/exploración sin convertirse (todavía) en decisión.

---

## 2026-06 — Separar Estado SPEI de Integridad Documental

**Decisión:** el resultado de VerificaPago se divide en dos dimensiones completamente independientes: Motor 1 (Estado SPEI, fuente Banxico) y Motor 2 (Integridad del comprobante, fuente VerificaPago).

**Motivo:** un comprobante puede estar visualmente alterado aunque la transferencia SPEI haya existido y se haya liquidado. Mezclar ambas señales en un solo score produce falsos positivos inaceptables — comprobantes reales de BBVA con un concepto "inusual" terminaban clasificados como ALTO RIESGO aunque Banxico confirmara la liquidación.

**Consecuencia:**
- Banxico responde por la operación. VerificaPago responde por el documento.
- El estado SPEI nunca puede ser degradado por el análisis documental, ni siquiera si el documento presenta señales graves de alteración.
- La combinación más importante a comunicarle al usuario es: `LIQUIDADA + Posible alteración` — el dinero llegó, pero el comprobante fue manipulado después.

---

## 2026-06 — No realizar validación criptográfica local del XML del CEP

**Decisión:** VerificaPago parsea el XML oficial del CEP y compara sus campos contra el comprobante visual, pero no valida la firma digital criptográfica del XML de forma local.

**Motivo:** se realizó una prueba criptográfica real (operación RSA pura: `sello^e mod n`) con el certificado cuyo número de serie coincide con el que el XML referencia, descargado del portal del SAT. El bloque resultante no exhibió ninguna estructura de padding reconocida (ni PKCS#1 v1.5 ni RSASSA-PSS). Conclusión: ese certificado del SAT no es la llave que firmó el XML. La llave privada real pertenece a la infraestructura interna de Banxico/SPEI (IES) y no está disponible públicamente.

**Consecuencia:**
- La validación de firma oficial solo puede obtenerse a través del validador web de Banxico (`banxico.org.mx/validador-cep-spei/`).
- VerificaPago redirige al usuario a esa herramienta cuando necesita la validación criptográfica formal.
- El comentario en el código (`cep_xml_auto_service.py`) dice explícitamente: "este comportamiento puede cambiar sin previo aviso" — no "confirmado experimentalmente", para mantener un tono neutral y mantenible.

---

## 2026-06 — Jerarquía de fuentes de evidencia SPEI

**Decisión:** se establece una jerarquía formal de fuentes, implementada como `NivelEvidencia` en `scoring_v3.py`:

```
XML oficial de Banxico  (nivel máximo)
        ↓
CEP HTML / scraping     (nivel alto)
        ↓
Análisis documental     (nivel menor)
        ↓
No disponible           (sin evidencia externa)
```

Una fuente de nivel superior puede actualizar el estado SPEI. Una fuente de nivel inferior nunca puede hacerlo.

**Motivo:** garantiza que cuando el sistema obtiene el XML oficial, ese dato siempre prevalece sobre cualquier inferencia previa del scraping del CEP HTML, sin necesidad de lógica condicional compleja dispersa en el código.

**Consecuencia:** el campo `nivel_evidencia` en la respuesta del API le indica al frontend (y a cualquier consumidor futuro del API) exactamente qué tan confiable es el estado SPEI reportado.

---

## 2026-06 — Parámetros de valida.do externalizados a JSON

**Decisión:** `tipoCriterio`, `tipoConsulta`, señales de éxito del HTML, content-types válidos y catálogo de bancos viven en `catalogo_bancos.json`, no hardcodeados en el código Python.

**Motivo:** el endpoint `valida.do` de Banxico no está documentado públicamente. Sus parámetros y el HTML de respuesta pueden cambiar sin aviso. Un string hardcodeado como `"boton-descarga-xml"` rompería silenciosamente la descarga automática del XML si Banxico cambia el nombre de esa clase CSS.

**Consecuencia:** cuando Banxico cambia algo del portal, se actualiza el JSON sin necesidad de un deploy de código. El historial de Git del JSON documenta exactamente cuándo y qué cambió en el comportamiento del portal.

---

## 2026-06 — El captcha del portal CEP no se valida del lado del servidor

**Decisión:** la descarga automática del XML manda el campo `captcha` vacío en el POST a `valida.do`.

**Motivo:** investigación empírica con una instalación de prueba en Render (`banxico-test.onrender.com`): el servidor respondió con éxito (`varHideCaptcha=true` en el HTML) sin que se resolviera ningún captcha. El campo captcha existe en el HTML del formulario, pero la lógica del servidor no lo valida para este flujo específico al momento de implementar este módulo.

**Consecuencia:** este comportamiento puede cambiar. Si Banxico activa la validación del captcha, la descarga automática fallará y el sistema degradará a "no fue posible obtener el XML automáticamente", sin interrumpir el análisis principal. La traza registrada en cada petición (`traza` en la respuesta) permitirá detectar este cambio rápidamente.

---

## 2026-06 — Score legacy mantenido para compatibilidad del frontend

**Decisión:** los campos `score` y `riesgo` siguen existiendo en la respuesta del API aunque el motor v3 usa dimensiones independientes.

**Motivo:** el frontend tenía `GaugeCircle` y lógica de colores basada en `score`/`riesgo`. Eliminarlos hubiera roto producción. Se mantienen calculados a partir de las nuevas dimensiones como un campo de compatibilidad.

**Consecuencia:** en una versión futura, cuando el frontend esté completamente migrado a los 2 motores, estos campos legacy pueden eliminarse del API sin afectar la lógica del motor.

---

## 2026-07 — Modelo de decisión explicable (Explainable Decision Model)

**Decisión:** se formaliza el modelo mental detrás de cada resultado que VerificaPago presenta, como documento fundacional independiente: `MODELO_DECISION_EXPLICABLE.md`. El modelo define cuatro capas estrictas — **Hechos → Interpretación → Recomendación → Evidencia** — y una estructura de presentación fija (**Resultado → Recomendación → ¿Cómo se llegó a este resultado? → Ver detalles**) que aplica a cualquier pantalla o cliente que muestre un resultado.

**Motivo:** el proyecto evolucionó, sin que se planeara así explícitamente, de validador de comprobantes → motor de análisis documental (2 motores independientes + scoring v3) → motor de decisión explicable (el objetivo ya no es solo calcular bien, es que cualquier persona entienda cómo se llegó al resultado y qué hacer con él). Ese salto necesitaba quedar nombrado y con reglas propias, no disperso entre `MOTOR_DECISIONES.md` (que describe el cálculo) y las decisiones puntuales de UI ya registradas (semáforo de integridad, "¿Cómo se llegó a este resultado?").

**Principios fijados (ver el documento completo para el desarrollo de cada uno):**
1. Toda conclusión debe derivarse de hechos verificables.
2. Los hechos son independientes de las interpretaciones.
3. Las recomendaciones derivan de las interpretaciones, no de los hechos crudos directamente.
4. Toda recomendación debe ser trazable a sus evidencias.
5. La interfaz nunca muestra una conclusión sin explicar cómo se obtuvo.

**Consecuencia:**
- El componente "¿Cómo se llegó a este resultado?" (capa 4) deja de ser solo una pieza de UI aislada — es la manifestación visible de un modelo completo de cuatro capas que también gobierna cómo se escriben los mensajes contextuales (capa 3, ítem 1.2 de `ROADMAP.md`) y cómo se documentan futuras interpretaciones (capa 2, en `MOTOR_DECISIONES.md`/`SCORING.md`).
- Se deja documentado (no planeado como roadmap, es nota de diseño a futuro) que fuentes de evidencia adicionales — historial del emisor/beneficiario, patrón de pagos, frecuencia, riesgo por cuenta, motor antifraude — entran al modelo sin rediseñar la interfaz: cada una es una evidencia más en la capa 4, no un módulo nuevo de UI.
- Antes de agregar cualquier fuente de información nueva al sistema, el criterio de diseño pasa a ser explícito: identificar en qué capa entra (hecho, interpretación o recomendación) antes de implementarla. Ver la sección "Cómo se usa este documento en la práctica" en `MODELO_DECISION_EXPLICABLE.md`.
- La próxima sesión de diseño del componente 1.4 se enmarca dentro de este modelo — ya no se diseña como pantalla, se diseña respondiendo las cuatro preguntas del modelo (qué hechos conoce, qué interpreta, qué recomienda, qué evidencia respalda la recomendación). Ver `ROADMAP.md`.

---

## 2026-07 — "Evidencia de la decisión" se renombra a "¿Cómo se llegó a este resultado?" y se define su estructura

**Decisión:** el patrón definido en la entrada anterior ("Evidencia de la decisión") se renombra a **"¿Cómo se llegó a este resultado?"**, y se fija su estructura y una regla de producto que lo gobierna, antes de escribir cualquier código o copy.

**Regla de producto:** *toda conclusión de VerificaPago debe poder justificarse con al menos una evidencia verificable.* Ninguna etiqueta (estado SPEI, integridad documental, nivel de evidencia) se muestra sin que el componente pueda enumerar de dónde sale.

**Motivo del renombre:** "Evidencia de la decisión" habla el idioma de quien construye el producto. Un comerciante, cajero o analista no piensa "muéstrame la evidencia de la decisión" — piensa "¿por qué me salió este resultado?". El nombre del componente debe hablar el idioma de quien lo usa, no el del equipo de ingeniería.

**Estructura de referencia (legible en ~5 segundos, no es un bloque grande):**

```
¿Cómo se llegó a este resultado?

Estado SPEI
✓ XML oficial de Banxico

Integridad documental
✓ OCR
✓ Inteligencia Artificial
⚠ Análisis visual

Nivel de evidencia
Muy alto

Ver detalles →
```

**Por qué esta estructura y no otra:** es deliberadamente extensible sin cambiar la UI. Hoy enumera XML, OCR e IA; el día que se agreguen hash, historial, patrones, alertas o un motor antifraude, esos ítems se agregan a la misma lista sin rediseñar el componente.

**Orden de trabajo decidido para Sprint A-Final:** se diseña primero este componente (modelo y estructura, sin código todavía) y **después** se escriben los mensajes contextuales de 1.2 — no al revés. Motivo: los mensajes de 1.2 dependen de la estructura que los va a contener; si se escriben primero, es muy probable que haya que reescribirlos en cuanto se decida qué evidencias mostrarse y cómo. Con el patrón definido primero, cada mensaje de 1.2 ya sabe de qué evidencia proviene (ejemplo: estado `liquidada` → mensaje "La transferencia fue liquidada correctamente por SPEI" → evidencia `✓ XML Banxico`), y 1.2 se vuelve, en buena medida, trabajo de redacción sobre una estructura ya resuelta.

**Preparación explícita para el Motor de Presentación (Etapa 5):** esta estructura anticipa que el backend, en el futuro, solo debería enviar hechos — el frontend decide cómo renderizarlos. Forma de referencia para esa migración futura (no implementada todavía, es solo el objetivo de diseño):

```json
{
  "estado_spei": "LIQUIDADA",
  "fuente_estado": "xml",
  "integridad": "OBSERVACIONES",
  "evidencias": [
    { "tipo": "xml", "resultado": "ok" },
    { "tipo": "ocr", "resultado": "ok" },
    { "tipo": "visual", "resultado": "warning" }
  ]
}
```

**Consecuencia:**
- Antes de escribir código para el Sprint A-Final, se dedica una sesión exclusivamente a diseñar este componente — se trata como un elemento característico de VerificaPago, al mismo nivel que el semáforo de SPEI.
- `ROADMAP.md` actualiza el nombre de 1.4 y fija el orden de trabajo: diseño del componente primero, luego 1.2.
- `PRODUCT_VISION.md` actualiza el nombre del patrón en el principio de Explicabilidad.

---

## 2026-07 — Evolución del concepto "Centro de Estado" a "Evidencia de la decisión"

**Decisión:** el concepto inicialmente denominado "Centro de Estado" (ítem 1.4 de la Etapa 1, ver `ROADMAP.md`) evoluciona a **"Evidencia de la decisión"**. Deja de planearse como una pantalla nueva y pasa a ser un **patrón visual reutilizable**: para cada conclusión que VerificaPago presenta (estado SPEI, integridad documental, nivel de evidencia general), se muestra explícitamente de dónde sale esa conclusión.

Ejemplo de forma:

```
Estado SPEI: Liquidada
Fuente: ✓ XML oficial Banxico

Integridad documental: Con observaciones
Fuente: ✓ OCR · ✓ IA · ✓ Comparación visual

Nivel de evidencia: Muy alto
Porque: ✓ XML oficial · ✓ CEP · ✓ Hash único · ✓ Consistencia documental
```

**Motivo:** la filosofía de VerificaPago no es únicamente emitir un resultado, es explicar de forma transparente las fuentes que lo sustentan — VerificaPago nunca dice "créeme", dice "aquí está por qué llegué a esta conclusión" (ver `PRODUCT_VISION.md`, principio de Explicabilidad). "Centro de Estado" sonaba a una pantalla más del flujo; "Evidencia de la decisión" nombra lo que realmente es: la trazabilidad de cada conclusión hasta su origen.

**Consecuencia:**
- Al ser un patrón, no una pantalla, se vuelve reutilizable entre Mobile, Desktop, Dashboard y la futura API Enterprise — todos los consumidores explican sus resultados de la misma forma, en vez de que cada cliente invente su propia manera de mostrar "por qué".
- Este patrón es candidato natural a vivir dentro del futuro objeto `presentation` del Motor de Presentación (ver la entrada "Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores" y Etapa 5 en `ROADMAP.md`) — cuando exista el segundo consumidor real, "Evidencia de la decisión" es de los primeros candidatos a estandarizarse ahí.
- `ROADMAP.md`, ítem 1.4, se renombra de "Centro de Estado" a "Evidencia de la decisión" y se redefine como patrón visual embebido en `/resultado`, no como pantalla independiente.
- `PRODUCT_VISION.md` incorpora este concepto como parte explícita del principio de Explicabilidad, para que la próxima persona que lea el documento entienda que no es solo una idea de UX, es una decisión de identidad de producto que debe sostenerse en el tiempo.

---

## 2026-07 — Cierre funcional del MVP Beta antes de escalar

**Decisión:** antes de iniciar desarrollos orientados a escalabilidad (Dashboard Empresa, Desktop, Motor de Presentación, arquitectura Enterprise), el proyecto completa primero el cierre funcional del MVP Beta: la experiencia completa de resultados — Centro de Estado SPEI, mensajes contextuales por estado, visualización de evidencia XML y explicación de las fuentes de validación.

**Motivo:** crecer en varias direcciones a la vez (seguir ajustando la pantalla de resultados mientras se construye historial, alertas y dashboard) diluye el foco y deja funcionalidades empresariales construidas sobre un flujo de usuario todavía incompleto. Terminar un flujo excelente primero, y ampliar el producto después, es la secuencia que da mejores resultados.

**Consecuencia:**
- `ROADMAP.md` se reorganiza en una secuencia de Etapas que reemplaza la numeración plana de Sprints A-E: Etapa 1 (cierre del MVP Beta) → Etapa 2 (Historial real) → Etapa 3 (Alertas inteligentes) → Etapa 4 (Dashboard Empresa) → Etapa 5 (Desktop, incluye el Motor de Presentación) → Etapa 6 (Seguridad). El contenido técnico de los Sprints anteriores no se pierde — se reubica dentro de esta secuencia.
- **Seguridad (antes Sprint B) se mueve al final de la secuencia**, no porque deje de importar, sino porque JWT, API Keys, rate limiting y auditoría van a cambiar de forma conforme se definan Historial, Alertas y Dashboard — implementarla antes sería construir sobre superficies que todavía se van a mover.
- Se planea un nuevo documento, `BETA_PLAN.md` (pendiente de redactar): objetivos del beta, número de usuarios, KPIs, criterios para salir de beta, mecanismo de reporte de errores y métricas a observar. Es documento de producto, no técnico — se activa cuando el proyecto empiece a invitar empresas reales.
- No se marca ningún ítem de la Etapa 1 como completado en `ROADMAP.md` hasta confirmar contra el estado real del código en producción — ver nota en la entrada de `ROADMAP.md` correspondiente.

---

## 2026-07 — Semáforo de integridad documental: el rojo se reserva para evidencia acumulada fuerte

**Decisión:** en la pantalla `/resultado`, el color del indicador de integridad documental (Motor 2) ya no se mapea 1:1 desde `integridad_config.color`. Se agrega una regla de frontend: el color rojo solo se muestra cuando hay evidencia acumulada fuerte — `confianza_documental < 30` **o** el XML oficial reporta discrepancias de campo. El caso `integridad_config.color = "rojo"` sin esas condiciones (o `"naranja"`) se muestra en ámbar, no en rojo.

**Motivo:** un usuario que ve simultáneamente "🟢 Liquidada" (Motor 1) y "🔴 Posible alteración" (Motor 2) tiende a leer la combinación como contradictoria y concluye erróneamente que la transferencia no ocurrió, aunque Banxico ya la haya confirmado. Esto es el mismo problema de falsos positivos que motivó separar los dos motores (ver entrada de 2026-06 "Separar Estado SPEI de Integridad Documental"), pero manifestado en la capa de presentación en vez de en el cálculo del score.

**Consecuencia:**
- El backend no cambia — `scoring_v3.py` sigue calculando `integridad_comprobante` y `integridad_config` exactamente igual.
- La reinterpretación de color vive solo en `app/resultado/page.tsx`, como una decisión de UX, no de scoring. Si se necesita este mismo criterio en otra pantalla (ej. `/resultado/detalle` o el dashboard desktop de Sprint C), debe replicarse explícitamente ahí — no es automático.
- El subtexto explicativo bajo el indicador de integridad también se ajusta según `esCasoExtremo`, para que el texto sea consistente con el color mostrado.
- **Resuelto (2026-07):** se decidió no subir esta lógica al backend todavía. Ver la entrada siguiente, "Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores", que fija el criterio general para este caso y para futuros similares.

---

## 2026-07 — Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores

**Decisión:** por ahora, la lógica que decide cómo se presenta un resultado al usuario (colores, iconos, umbrales de severidad, prioridad visual) permanece en el frontend, incluso cuando esa lógica interpreta datos que vienen del backend (ej. el criterio de "evidencia acumulada fuerte" de la entrada anterior). Se fija una regla explícita para saber cuándo debe dejar de ser así:

> Toda regla de presentación utilizada por más de un cliente (Mobile, Desktop, Dashboard, API pública) debe migrar al backend como un motor de presentación compartido. Mientras exista un único consumidor, la lógica visual puede permanecer en el frontend para facilitar la iteración del producto.

**Motivo:** la experiencia visual de `/resultado` todavía está en ajuste activo — posición del bloque, tamaño, color y prioridad visual ya cambiaron varias veces y es previsible que cambien más antes de estabilizarse. Si la severidad se sube al backend ahora mismo, cada ajuste visual implica tocar API, pruebas y despliegue del backend por un cambio que es puramente de presentación. Hoy solo existe un consumidor (Mobile), así que no hay todavía un problema de lógica duplicada que resolver — solo el costo de acoplar iteración visual a un ciclo de release más pesado.

**Paso intermedio (no es el motor de presentación, es preparación para él):** en vez de exponer un campo ya interpretado como `severidad_integridad`, el backend expondrá los **hechos crudos** que hoy se usan para decidir el color, agrupados como `evidencias`:

```json
{
  "evidencias": {
    "xml_valido": true,
    "xml_discrepancias": 0,
    "confianza_documental": 85,
    "verificabilidad": 90,
    "contexto_temporal": 100,
    "hash_reutilizado": false
  }
}
```

El frontend sigue decidiendo verde/ámbar/rojo a partir de esto. La diferencia es que la decisión se toma sobre datos explícitos y nombrados, no sobre una combinación de campos legacy (`confianza_documental`, `cep_xml.comparacion_campos.discrepancias`) leídos de forma ad hoc como hoy.

**Consecuencia:**
- No se crea `severidad_integridad` ni ningún campo de severidad pre-interpretado en esta etapa.
- El hito de "mover la lógica de presentación al backend" queda formalmente atado a Sprint C, y no como una tarea aislada — porque Sprint C es cuando aparece el segundo consumidor real (Desktop). El roadmap de Sprint C se actualiza para incluir un **Motor de Presentación**, no solo la UI de escritorio (ver `ROADMAP.md`).
- Cuando ese motor se construya, la forma esperada de la respuesta no es un campo suelto por dimensión, sino un objeto `presentation` con nivel + texto ya resueltos por el backend, consumible igual por Mobile, Desktop, Dashboard y API pública:

```json
{
  "presentation": {
    "integridad": { "nivel": "warning", "texto": "Con observaciones" },
    "spei": { "nivel": "success", "texto": "Liquidada" }
  }
}
```

- Regla de disparo para revisar esta decisión: en cuanto exista un segundo consumidor real del backend (no un prototipo — un cliente en desarrollo activo), esta decisión debe revisitarse antes de construir ese segundo cliente, no después.

---

## 2026-06 — Arquitectura multiempresa desde el inicio

**Decisión:** el esquema de base de datos incluye `empresa_id` en todas las tablas desde la primera migración, aunque la autenticación multiempresa real no existe todavía.

**Motivo:** agregar `empresa_id` a una tabla con datos existentes en producción es costoso y riesgoso. Hacerlo desde el inicio con un `DEFAULT_EMPRESA_ID` es barato y preserva la opción de activar multiempresa en el futuro sin migraciones destructivas.

**Consecuencia:** todos los endpoints del dashboard ya aceptan `empresa_id` como parámetro. Cuando se implemente autenticación real, los endpoints no necesitan cambiar — solo el frontend necesita empezar a enviar el `empresa_id` correcto.

---

## 2026-07 — 🏛️ ADR: se formaliza la capa de Recomendación, distinta de Impacto, en el Modelo de Decisión Explicable

**Decisión:** el Modelo de Decisión Explicable pasa de 4 a 5 capas. La capa que antes se llamaba "Recomendación" se divide en dos capas distintas y secuenciales:

```
1. Hechos → 2. Interpretación → 3. Impacto → 4. Recomendación (solo si aplica) → 5. Evidencia
```

- **Impacto** (capa 3): traduce la interpretación a una consecuencia concreta para el usuario — "¿qué implica esto para mí?". Siempre está presente.
- **Recomendación** (capa 4): una acción explícita e inmediata, solo cuando agrega algo más allá del Impacto — "¿qué hago ahora?". Es opcional; su ausencia también es información (no hace falta ninguna acción adicional).

**Motivo:** al escribir el catálogo completo de los 9 mensajes contextuales (`ROADMAP.md`, ítem 1.2), quedó claro que "qué implica esto" y "qué debo hacer" son preguntas distintas que antes se estaban resolviendo en un solo campo. Casos como `en_proceso` ("esperar y volver a consultar"), `devuelta` ("solicitar un nuevo comprobante") o `desconocida` ("verificar nuevamente los datos") tienen una acción concreta que dar, mientras que `liquidada` o `acreditada` no la necesitan — el Impacto ya es autosuficiente. Forzar una "Recomendación" en todos los casos generaba relleno; no tenerla nunca dejaba una pregunta sin responder exactamente cuando más importaba.

**Impacto de esta decisión en el proyecto:** al ser una capa del modelo (no solo texto), esta distinción se replica consistentemente en Historial, Dashboard Empresa, Alertas Inteligentes, Desktop y la futura API Enterprise — todos podrán responder "qué implica" y, cuando aplique, "qué hacer" de la misma forma, en vez de que cada superficie decida por su cuenta si mezclar ambas cosas.

**Documentos afectados:**
- `MODELO_DECISION_EXPLICABLE.md` — modelo actualizado de 4 a 5 capas; estructura de presentación actualizada de 5 a 6 pasos (se agrega ④ Recomendación inmediata); principios del modelo reescritos, incorporando explícitamente la regla *"nunca inducir al usuario a una acción cuando la evidencia todavía no lo permite"*.
- `ROADMAP.md` — catálogo de los 9 mensajes contextuales (ítem 1.2) reescrito con el wording final revisado (más preciso en `acreditada`, `liquidada`, `en_proceso`, `devuelta`, `no_liquidada`, `desconocida`) y el campo "Recomendación inmediata" añadido donde aplica.

---

## 2026-07 — Refinamiento: de las 4 preguntas al flujo de decisión de 5 pasos

**Decisión:** el componente "¿Cómo se llegó a este resultado?" se rediseña de una lista de datos que responde preguntas a un **flujo de decisión conversacional de 5 pasos**: ① Resultado → ② Interpretación → ③ Impacto → ④ Evidencias → ⑤ Detalle.

**Motivo:** el usuario no piensa en preguntas ("¿qué evidencia hay?"), piensa en "¿qué pasó?". Estructurar el componente como una secuencia narrativa en vez de una lista de datos funciona mejor psicológicamente y es más fácil de redactar de forma consistente entre los 9 estados SPEI.

**Relación con el modelo de 4 capas (`MODELO_DECISION_EXPLICABLE.md`):** este flujo no reemplaza el modelo de Hechos → Interpretación → Recomendación → Evidencia, es su forma de presentación al usuario, con dos ajustes:
- Se separa explícitamente **① Resultado** (el dato categórico crudo, ej. "Liquidada") como primer paso, antes de interpretarlo.
- La capa que el modelo llama internamente "Recomendación" se etiqueta de cara al usuario como **③ Impacto** — lenguaje menos directivo ("¿qué implica esto para mí?" en vez de "qué debo hacer"), misma función.
- **⑤ Detalle** se agrega como el mecanismo de profundidad opcional (el acordeón ya existente en `/resultado/detalle`), no es una capa de razonamiento nueva.

**Consecuencia:**
- `MODELO_DECISION_EXPLICABLE.md` y `ROADMAP.md` (ítem 1.4) se actualizan con el flujo de 5 pasos como estructura de referencia.
- Los mensajes contextuales de 1.2 se redactan siguiendo este flujo completo por cada estado, no como un texto suelto — ejemplo (`en_proceso`): Resultado "En proceso" → Interpretación "La operación aún está siendo procesada por SPEI" → Impacto "Espera unos minutos antes de considerar la transferencia como fallida" → Evidencias "✓ XML · ✓ CEP".
- Se reafirma que, al ser un flujo (no una pantalla), es la "gramática" de VerificaPago — se reutiliza igual en Historial, Dashboard Empresa, Desktop, Alertas Inteligentes y la futura API Enterprise.

---

## 2026-07 — Se declara concluida la Fase de Fundación de VerificaPago

**Decisión:** se declara concluida la Fase de Fundación de VerificaPago. No porque el proyecto esté terminado, sino porque la arquitectura, la visión de producto, el modelo de decisión, la gobernanza documental y el roadmap alcanzaron un nivel de estabilidad suficiente para que el desarrollo futuro se enfoque prioritariamente en construir funcionalidades, no en redefinir las bases del sistema.

**Motivo:** con `/docs` en v0.11.0 (estructura congelada, versionado, referencias cruzadas) y con el Modelo de Decisión Explicable formalizado, el proyecto dejó de necesitar sesiones dedicadas a diseñar sus fundamentos. El riesgo ya no es "falta base", es "dejar de construir sobre lo que ya está bien definido".

**Impacto:** a partir de esta decisión:
- Toda nueva documentación surge como **consecuencia** de cambios funcionales, decisiones de arquitectura o investigaciones — no como actividad propia. El flujo pasa a ser: se desarrolla una funcionalidad → se prueba → si amerita documentación, se marca `#DOC-VP` / `#ADR-VP` / `#LAB-VP` → se actualiza únicamente el documento afectado.
- No se abren nuevas fases de documentación general salvo que exista un cambio estratégico real del producto.
- Se adopta como hábito de trabajo la regla **"No romper la arquitectura"**: antes de desarrollar cualquier idea nueva, responder cuatro preguntas — ¿ya existe algo que resuelva esto? ¿pertenece a un documento existente? ¿rompe algún ADR? ¿afecta el Modelo de Decisión Explicable? Si las cuatro respuestas son "no", se procede. Esta regla complementa (no sustituye) las cuatro preguntas de diagnóstico ya definidas en `MODELO_DECISION_EXPLICABLE.md` para decidir en qué capa entra una idea — esa se enfoca en el modelo de decisión del producto; esta se enfoca en si la idea rompe algo que ya existe, a nivel de todo el proyecto.

**Observación registrada, sin cambio de documento todavía:** durante esta fase, la definición de VerificaPago evolucionó de forma orgánica — de "validador de comprobantes" a "motor de análisis documental" y ahora se describe informalmente como *"un motor de confianza para pagos por transferencia"*, o de forma aún más condensada: *VerificaPago convierte evidencia técnica compleja en una decisión comprensible para cualquier persona.* Esta frase no sustituye todavía la definición formal en `PRODUCT.md` ni `PRODUCT_VISION.md` — queda anotada aquí como observación de hacia dónde apunta la identidad del producto, pendiente de una decisión explícita si se quiere adoptar como definición oficial.

---

## 2026-07 — Principio de gobernanza documental: una única fuente de verdad por pieza de conocimiento

**Decisión:** cada pieza de conocimiento del proyecto tiene una única fuente de verdad. Las decisiones (`DECISION_LOG.md`) referencian investigaciones (`LABORATORIO.md`), pero no las duplican; los documentos especializados profundizan en su propio dominio, y el resto de los documentos solo enlaza o resume cuando hace falta, en vez de repetir el contenido.

**Motivo:** es la generalización formal de una regla que ya se venía aplicando de facto (ej. la entrada de `XML_CEP.md` sobre la investigación criptográfica del sello digital no se duplicó al crear `LABORATORIO.md`, solo se indexó). Sin esta regla explícita, el riesgo con 12 documentos y creciendo es que el mismo hecho técnico termine descrito de tres formas ligeramente distintas en tres archivos, y que nadie sepa cuál es la vigente cuando algo cambie.

**Consecuencia:**
- Cada documento nuevo o actualizado debe preguntarse, antes de escribir contenido: ¿esto ya vive en otro documento? Si sí, se referencia, no se repite.
- Se agrega una sección "Documentos relacionados" al final de cada archivo de `/docs`, con referencias explícitas a los documentos con los que tiene relación de contenido — ver `README.md` para el mapa completo.

---

## 2026-07 — Estructura documental congelada

**Decisión:** no se crean documentos nuevos en `/docs` salvo que representen un dominio propio y reutilizable — el mismo criterio que ya se aplicó al crear `MODELO_DECISION_EXPLICABLE.md` y `LABORATORIO.md`. Toda funcionalidad nueva se integra primero a la estructura documental existente (una sección nueva, una entrada de decisión, una entrada de investigación) antes de considerar un archivo nuevo.

**Motivo:** con 12 documentos ya en su lugar, el riesgo deja de ser "falta documentación" y pasa a ser "la documentación crece de forma desordenada" — el escenario clásico de terminar con `XML2.md`, `XML_FINAL.md`, `XML_V2.md` porque nadie se detuvo a decidir si algo merecía un archivo nuevo o una sección dentro de uno existente.

**Consecuencia:**
- `README.md` documenta esta regla como parte de la política de mantenimiento de `/docs`.
- `MODELO_DECISION_EXPLICABLE.md` ya tenía una pregunta de diagnóstico equivalente ("¿necesita un documento nuevo, o pertenece a uno existente?") — esta decisión la eleva de criterio de diseño de producto a regla de gobernanza documental explícita.
- Documentos explícitamente pospuestos y no creados en esta ronda, por no tener superficie real todavía: `PRINCIPIOS_DE_PRODUCTO.md`, `BETA_PLAN.md`, `SEGURIDAD.md`, `HISTORIAL.md`. Se seguirán postergando hasta que el módulo correspondiente exista de verdad.
- Queda anotado, sin activar, un cuarto marcador de captura: 🎯 `#PDR-VP` (Product Decision Record), para decisiones de producto que no son arquitectura ni investigación (renombrar un concepto, reordenar el roadmap, mover un entregable entre etapas). No se activa hasta que la necesidad de distinguirlo de `#DOC-VP` se vuelva recurrente en la práctica — ver `README.md`.
- A partir de esta versión, `/docs` deja de tratarse como una tarea de expansión activa y pasa a actualizarse solo ante eventos concretos: módulo nuevo, cambio de arquitectura, decisión importante, o investigación relevante — es decir, exclusivamente a través de los tres marcadores activos.

---

## Documentos relacionados

- Referenciado por prácticamente todos los documentos de `/docs` — es el registro central del "por qué".
- `LABORATORIO.md` — destino de las investigaciones que respaldan algunas decisiones marcadas aquí.
- `README.md` — mapa completo de convenciones y estructura documental.
- `MODELO_DECISION_EXPLICABLE.md`, `MOTOR_DECISIONES.md`, `ROADMAP.md` — documentos cuyas decisiones más recientes están detalladas en este log.