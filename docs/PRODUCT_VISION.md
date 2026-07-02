# PRODUCT_VISION.md — Visión estratégica de VerificaPago

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

**5. Arquitectura que respeta la fuente**  
Banxico responde por la operación. VerificaPago responde por el documento. Esa línea nunca se cruza en el código ni en la interfaz.

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