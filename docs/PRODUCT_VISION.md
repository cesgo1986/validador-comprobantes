# PRODUCT_VISION.md — Visión estratégica de VerificaPago

**Versión del documento:** 0.28.7 · **Última actualización:** 07/07/2026

*Documento de producto, no técnico. Define qué es VerificaPago, hacia dónde va y qué no será nunca.*

---

## Qué es VerificaPago

VerificaPago es una plataforma de verificación de transferencias SPEI que responde dos preguntas independientes:

**¿Qué dice Banxico?** — La transferencia existió, fue liquidada, devuelta o no se encontró.
**¿Qué dice VerificaPago?** — El comprobante presentado es consistente, tiene observaciones o posibles alteraciones.

Son dos preguntas distintas con fuentes distintas. Nunca se mezclan. Esa separación es la identidad del producto.

---

## El problema que resuelve

En México, cualquier persona puede capturar pantalla de un comprobante de transferencia, editarlo con herramientas básicas y enviarlo como "prueba de pago". El receptor no tiene forma directa de verificarlo.

Los bancos no ofrecen esto. Banxico no tiene una herramienta orientada a comercios. El CEP existe pero requiere conocimiento técnico para consultarlo y no da contexto sobre la calidad del documento.

VerificaPago cierra esa brecha: cualquier comercio, freelancer o empresa puede subir un comprobante y obtener en segundos una respuesta respaldada por la fuente oficial (Banxico) más un análisis documental independiente.

---

## Qué nunca hará VerificaPago

- No confirmará pagos en nombre de ninguna institución financiera
- No reemplazará una consulta directa al banco emisor o receptor
- No validará firmas digitales que requieran acceso a infraestructura privada de Banxico
- No almacenará imágenes de comprobantes de forma permanente (solo el análisis)
- No tomará decisiones automáticas de aprobación o rechazo — le dará información al humano para que él decida
- No intentará ser una herramienta bancaria — es una herramienta para quienes reciben pagos bancarios

---

## Principios del producto

**1. Honestidad epistémica**
VerificaPago solo afirma lo que puede demostrar. Si no pudo consultar Banxico, dice "no verificado". No infla la confianza para parecer más capaz de lo que es.

**2. Dos motores, dos preguntas**
El estado SPEI (Motor 1, fuente: Banxico) nunca puede ser modificado por el análisis documental (Motor 2, fuente: VerificaPago). Un comprobante alterado no convierte una transferencia real en falsa.

**3. Degradación elegante**
Si falla la descarga del XML, el análisis continúa. Si falla el CEP, el OCR sigue corriendo. El usuario siempre obtiene el mejor resultado posible con la información disponible.

**4. Explicabilidad**
Cada resultado se explica. No un número opaco, sino: "La transferencia fue liquidada por SPEI. El comprobante presenta observaciones menores en el formato del folio." El comercio puede tomar una decisión informada.

VerificaPago nunca dice "créeme" — siempre dice "aquí está por qué llegué a esta conclusión". Este principio se materializa como **"¿Cómo se llegó a este resultado?"** (concepto conocido internamente durante su diseño como "Evidencia de la decisión"): un patrón visual reutilizable, no una pantalla aislada, que acompaña cada conclusión — estado SPEI, integridad documental, nivel de evidencia general — con su fuente explícita (XML oficial, CEP, OCR, IA, análisis visual, hash único, etc.), legible en unos cinco segundos. Rige una regla de producto: toda conclusión de VerificaPago debe poder justificarse con al menos una evidencia verificable. Al ser un patrón y no una pantalla, se replica igual en Mobile, Desktop, Dashboard y la futura API Enterprise, sin que cada cliente invente su propia forma de justificar un resultado. Ver `DECISION_LOG.md` ("'Evidencia de la decisión' se renombra a '¿Cómo se llegó a este resultado?' y se define su estructura").

**5. Arquitectura que respeta la fuente**
Banxico responde por la operación. VerificaPago responde por el documento. Esa línea nunca se cruza en el código ni en la interfaz.

**6. Una sola experiencia, múltiples presentaciones**
VerificaPago es un producto, no dos aplicaciones. Móvil define el producto — cualquier funcionalidad nueva se diseña primero ahí. Desktop nunca redefine la experiencia, solo aprovecha el espacio disponible para mostrar simultáneamente lo que en móvil vive detrás de divulgación progresiva. Ninguna funcionalidad nace exclusivamente para Desktop: si aporta valor, existe también en móvil, aunque sea detrás de un panel expandible. Ver `DECISION_LOG.md` ("una sola experiencia, múltiples presentaciones").

---

## Público objetivo

### Fase 1 — Comercios y freelancers (hoy)
Personas que reciben transferencias como pago antes de entregar un producto o servicio. Necesitan verificar rápidamente, desde su celular, si el comprobante que les enviaron es válido.

Casos de uso: ventas en línea, servicios profesionales, renta de inmuebles, compraventa de autos, servicios de construcción.

### Fase 2 — Empresas medianas (Fase B — Desktop)
Empresas que procesan decenas o cientos de comprobantes diarios. Necesitan una plataforma, no una app. Dashboard, historial, filtros, exportación, roles de usuario.

Casos de uso: marketplaces, financieras, despachos contables, inmobiliarias, cobranza.

### Fase 3 — Enterprise e integración (Fase D — API)
Empresas que necesitan integrar la verificación en sus propios sistemas. ERP, WooCommerce, Shopify, sistemas de facturación, plataformas de cobranza.

---

## Propuesta de valor para empresas (2026-07)

**El "Job To Be Done" del producto no es "validar comprobantes"** — es permitir que una empresa acepte transferencias SPEI con la misma confianza operativa con la que hoy acepta tarjeta, y **crezca** con eso, no solo se defienda con eso. Dos ángulos de venta distintos, complementarios, no un solo argumento:

- **Defensivo (elimina riesgo):** *"VerificaPago permite que las empresas adopten las transferencias SPEI como un método de cobro seguro, verificable y operativo, eliminando la incertidumbre, reduciendo el trabajo manual y acelerando la liberación de pedidos."*
- **Ofensivo (habilita crecimiento):** una empresa que solo acepta tarjeta o *contactless* está limitando su catálogo de formas de cobro — y por lo tanto sus ventas — no por decisión estratégica, sino porque no tiene manera de aceptar transferencias con confianza operativa. VerificaPago no solo quita el miedo a SPEI, habilita un canal de cobro adicional real. El primer ángulo lo compra un director de operaciones/riesgo; el segundo lo compra un director comercial o el CEO — la propuesta de valor completa necesita hablarle a ambos.

**Precisión de alcance (2026-07):** VerificaPago habilita **un canal específico — transferencias SPEI** — no "canales de cobro" en plural ni de forma genérica. No procesa tarjetas, no procesa OXXO, no compite con una pasarela de pagos completa (Stripe, Conekta, Clip). Esta precisión importa: prometer "habilitador de canales de cobro" sin más sería exactamente el tipo de expansión de alcance que este mismo documento ya frena en la sección de hipótesis de evolución (Open Banking, KYC) — cada promesa comercial debe sostenerse en lo que el producto realmente hace hoy.

**Eslogan de trabajo:** *"Convierte SPEI en un canal de cobro confiable"* — específico, defendible, sin prometer de más.

**Criterio de filtro para cualquier funcionalidad futura:** ¿esto hace que una empresa pueda adoptar **SPEI específicamente** con mayor confianza, eficiencia o escala? Si la respuesta es sí, pertenece a VerificaPago. Si no, puede ser una buena idea — para otro producto.

**Tabla de valor, ordenada por lo que compra la empresa (no por módulo técnico):**

| Resultado que compra la empresa | Cómo lo consigue VerificaPago | Estado |
|---|---|---|
| Aceptar SPEI como método de cobro oficial, sin miedo | Validación SPEI + evidencia oficial de Banxico + modelo de decisión explicable | ✅ |
| Vender más al ampliar su catálogo de formas de cobro | Confianza operativa consistente sobre el canal SPEI | ✅ (efecto indirecto del punto anterior) |
| Liberar pedidos más rápido | Automatización del análisis (segundos, no minutos) | ✅ |
| Reducir fraude | Motor Documental + Alert Engine | ✅ |
| Reducir trabajo manual en picos de volumen | OCR + IA + verificación automática | ✅ |
| Tener trazabilidad de cada operación | Historial con búsqueda unificada + auditoría | ✅ |
| Entender qué está pasando en su operación completa | `AggregationService` + Dashboard Empresa | 🟡 backend listo, pantalla congelada (ver `ROADMAP.md`, 5.5) |
| Conciliar pagos automáticamente contra lo que espera | Motor de Operaciones | 🔵 hipótesis, ver sección "Hipótesis de evolución del producto" |

(Criterio de filtro completo arriba, antes de la tabla — se aplica igual a esta lista: si una funcionalidad no ayuda a que SPEI específicamente sea más confiable, eficiente o escalable como canal de cobro, probablemente sea una distracción, sin importar qué tan interesante sea técnicamente.)

---

## Modelo de negocio

### Plan Gratuito
- N análisis por mes (a definir en beta)
- Historial básico (últimos 30 días)
- Sin XML automático

### Plan Pro (individual/PYME)
- Análisis ilimitados o volumen alto
- XML automático del CEP
- Historial completo con búsqueda
- Alertas de reutilización
- Descargar reportes PDF

### Plan Empresa
- Todo lo de Pro
- Múltiples usuarios y sucursales
- Dashboard ejecutivo
- API REST con API Key
- Aislamiento completo de datos por empresa
- SLA de disponibilidad
- Soporte prioritario

### Plan Enterprise / Integraciones
- SDK
- Webhooks
- Integración con ERP (Odoo, SAP, Oracle)
- Integración con ecommerce (WooCommerce, Shopify)
- Volumen personalizado
- Contrato y factura

---

## Roadmap a 3 años

### 2026 — Consolidación y beta
**Q3 2026**
- Sprint A completo: mensajes contextuales, reintentos XML, observabilidad
- Sprint B: seguridad (JWT, API Keys, rate limiting, eliminación de imágenes)
- Beta privado con primeros comercios reales

**Q4 2026**
- Sprint C: versión Desktop diseñada desde cero
- Historial con datos reales y búsqueda
- Primer dashboard empresarial
- Lanzamiento público de la versión móvil

### 2027 — Crecimiento y plataforma
**Q1-Q2 2027**
- Sprint D: historial completo, alertas reales, dashboard avanzado
- Sprint E: multiempresa real (JWT por empresa, facturación, permisos)
- API pública documentada
- Página web y landing de conversión
- Onboarding guiado para nuevos comercios

**Q3-Q4 2027**
- Primeras integraciones (WooCommerce, Shopify)
- Motor de reputación por CLABE/cuenta
- CEP por lotes para B2B
- Primeros clientes Enterprise

### 2028 — Escalamiento
- SDK para iOS y Android
- Integraciones con ERP (Odoo, SAP)
- API para participantes del sistema bancario
- Expansión a otros casos de uso (SPID, CoDi)
- Posible expansión regional (otros países con sistemas de pago similares)

---

## Hipótesis de evolución del producto (sin comprometer roadmap ni arquitectura)

**Qué es esta sección:** ideas estratégicas grandes, capturadas para no perderlas, pero deliberadamente **sin** tablas, sin arquitectura, sin endpoints, sin ítems de roadmap. Se registran aquí — no como documento propio — porque `PRODUCT_VISION.md` existe exactamente para "hacia dónde puede evolucionar VerificaPago", no para comprometer qué se construye a continuación. Pasar de esta sección a una etapa real de `ROADMAP.md` requiere una validación de negocio explícita primero, no ocurre automáticamente por estar escrito aquí.

**2026-07 — Motor de Operaciones (hipótesis):** surgió de una discusión sobre conciliación — hoy VerificaPago siempre llega *después* del pago (transferencia → comprobante → validación). La hipótesis es que exista una identidad de operación que viva *antes* del pago también: una empresa genera una solicitud de cobro con un identificador (ej. `VP-H7A2QX`), el cliente lo incluye en el concepto de su transferencia (campo que VerificaPago ya extrae, tanto por OCR como del XML oficial de Banxico), y el sistema concilia automáticamente en vez de que la empresa tenga que adivinar a quién corresponde cada depósito. El estado de una operación evolucionaría: Esperada → Pagada → Validada → Conciliada → Liberada → Auditada.

**2026-07 — Niveles de confianza progresivos (hipótesis, ligada a la anterior):** en vez de un modelo de "identidad validada" (que implicaría KYC — INE, biometría, listas negras, regulación AML, un costo de cumplimiento que no encaja en el producto actual), la hipótesis es construir confianza por **comportamiento observado**, no por identidad verificada: cliente habitual, cuenta habitual, banco habitual, montos habituales. Tres niveles posibles sin comprometer ninguno: (0) hoy — validación de comprobante individual; (1) empresa registrada genera solicitudes de cobro con token; (2) el sistema reconoce relaciones recurrentes cliente↔cuenta↔empresa sin necesitar saber quién es la persona.

**2026-07 — OCR desacoplado de Claude (hipótesis):** hoy Claude Vision hace dos trabajos distintos en una sola llamada — extraer campos (OCR) y razonar sobre manipulación/fraude (juicio forense). Solo el segundo requiere IA de verdad; el primero es un problema resuelto por motores de OCR existentes (PaddleOCR, Google Vision OCR, AWS Textract, etc.) a una fracción del costo. La hipótesis: introducir una interfaz `OCRProvider` (`extract(imagen) -> campos_estructurados`), con `ClaudeOCR` como implementación actual y un proveedor barato como alternativa — el resto del sistema (Motor SPEI, Alert Engine) no se entera del cambio, porque ya consume `campos_extraidos` sin importar quién los generó. Claude pasaría de ser "el motor" a ser "el experto al que se consulta cuando los demás motores no llegan a una conclusión suficientemente confiable" (cuando hay incertidumbre, faltan campos críticos, o los otros motores detectan inconsistencia) — no en el 100% de los análisis.

**Plan de validación, en 3 fases — ninguna comprometida todavía:**
1. Construir la capa `OCRProvider` con un motor existente, sin tocar el flujo de producción.
2. Correr OCR + Claude en paralelo durante semanas, comparando qué tanto coinciden — esto da el dato real que hoy no existe: qué % de casos el OCR barato resuelve solo, y en cuáles Claude sigue siendo necesario.
3. Solo si la Fase 2 confirma que la coincidencia es suficientemente alta, cambiar el flujo de producción para que Claude intervenga solo cuando el OCR tenga baja confianza o el resto de los motores detecte inconsistencia.

**Por qué no se construye ahora:** el problema que resuelve (costo a escala) todavía no ha ocurrido — el proyecto no tiene volumen de producción real que lo urja. Comprometer la Fase 3 sin los datos de la Fase 2 repetiría el mismo error que ya se evitó con la conciliación por token: diseñar antes de confirmar que el dato base (qué tan bien lee un OCR barato comprobantes de ~30 bancos mexicanos distintos) es confiable.

**Optimización relacionada, sí construible ahora, sin esperar a la capa OCR — ver `ROADMAP.md` próximo ítem de 6.1 o etapa aparte:** cachear el juicio forense de Claude (campos extraídos, score de riesgo visual) cuando el hash del archivo coincide exacto (`hash_service.py` ya detecta esto, hoy sin aprovecharse) — pero **siempre volver a consultar CEP/XML en Banxico** sin importar si el archivo ya se vio, porque el Estado SPEI puede cambiar entre una subida y otra aunque el archivo sea idéntico. Cachear la respuesta completa sin este matiz arriesgaría mostrar un estado desactualizado — justo lo opuesto a la propuesta de valor del producto.

**Riesgo regulatorio identificado, sin resolver:** correlacionar identidad de cliente + cuenta bancaria + comportamiento **a través de múltiples empresas distintas** ya es procesamiento de datos personales financieros bajo la LFPDPPP (Ley Federal de Protección de Datos Personales en Posesión de los Particulares), incluso sin hacer KYC. Cualquier diseño real de esto necesita opinión legal explícita antes de construirse — no es un supuesto que el equipo de producto pueda resolver por su cuenta.

**Explícitamente descartado, no solo pospuesto:** integración vía Open Banking (leer directamente las apps bancarias de los usuarios) — en México cae bajo la Ley Fintech, requeriría convertirse en entidad regulada o asociarse con un agregador ya autorizado por la CNBV (ej. Belvo, Finerio Connect, Prometeo). Es una empresa distinta, con una licencia distinta — no una función más de VerificaPago. Ver `DECISION_LOG.md` si esta discusión se retoma alguna vez, para no reabrir el mismo análisis desde cero.

---

## Métricas que importan

### Métricas de producto (usuario)
- Tiempo promedio desde upload hasta resultado (meta: < 10 segundos)
- Porcentaje de análisis con XML exitoso
- Porcentaje de análisis donde el estado SPEI fue determinado (vs. "no verificado")
- Net Promoter Score de comercios

### Métricas de negocio
- Análisis por usuario por mes (indicador de adopción y hábito)
- Conversión de gratuito a pago
- Retención mensual
- Análisis por tipo de banco (entender el mercado)

### Métricas de motor
- Porcentaje de XML descargados automáticamente
- Tasa de falsos positivos reportados por usuarios
- Score promedio de confianza documental por banco
- Tiempo de respuesta del backend (percentil 95)

---

## Lo que distingue a VerificaPago

La mayoría de las herramientas de detección de fraude responden una pregunta: **¿el documento parece falso?**

VerificaPago responde dos: **¿qué dice la fuente oficial? y ¿qué tan confiable es el documento?**

Esa separación, que parece sutil, cambia completamente el tipo de decisiones que el usuario puede tomar:

- "La transferencia está liquidada, pero el comprobante tiene observaciones" → entregó, pero investiga el comprobante
- "El comprobante se ve perfecto, pero SPEI no lo encontró" → espera antes de entregar
- "La transferencia está liquidada y el comprobante coincide con el XML" → máxima certeza disponible hoy

Eso es lo que hace a VerificaPago defendible frente a copias: la filosofía está en la arquitectura, no solo en la interfaz.

---

## Documentos relacionados

- `PRODUCT.md` — definición técnica/producto complementaria
- `MODELO_DECISION_EXPLICABLE.md` — el principio de Explicabilidad se desarrolla ahí a fondo
- `DECISION_LOG.md` — decisiones que materializan esta visión
- `ROADMAP.md` — el plan concreto para llegar a esta visión