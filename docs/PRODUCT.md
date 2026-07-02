# VerificaPago — Definición del Producto

## Qué es VerificaPago

VerificaPago es una plataforma que ayuda a determinar si un comprobante bancario representa una operación SPEI auténtica, mediante la combinación de información oficial de Banxico con análisis documental basado en inteligencia artificial.

No es un detector de imágenes falsas.  
No es un validador de firmas digitales.  
Es un **motor de evaluación de evidencia de pago** que responde dos preguntas independientes:

1. **¿Cuál es el estado oficial de la transferencia según SPEI/Banxico?** (hecho verificable)
2. **¿Qué tan consistente y confiable es el comprobante presentado?** (análisis propio de VerificaPago)

Estas dos preguntas nunca se mezclan. Pueden tener respuestas distintas y ambas son válidas.

---

## El problema que resuelve

Cualquier persona puede capturar pantalla de un comprobante bancario, editarlo con herramientas básicas y enviarlo como "prueba de pago". El receptor no tiene forma directa de verificarlo sin acceso a los sistemas internos del banco o de Banxico.

VerificaPago cierra esa brecha consultando directamente la fuente oficial (Banxico vía CEP/XML) y complementando con análisis visual e IA sobre el documento presentado.

---

## Lo que VerificaPago NO es

- No confirma pagos en nombre de ninguna institución financiera
- No tiene acceso a sistemas internos bancarios
- No reemplaza una consulta directa al banco emisor o receptor
- No valida firmas digitales criptográficas del XML (ver `DECISION_LOG.md` — la infraestructura de firma pertenece a la IES privada de SPEI y no está disponible públicamente)

---

## Usuarios objetivo

**Versión móvil (actual):** personas y pequeñas empresas que reciben comprobantes de transferencia como pago y necesitan verificarlos de forma rápida antes de entregar un producto o servicio.

**Versión desktop (roadmap Sprint C):** empresas medianas que procesan volúmenes de comprobantes diariamente — marketplaces, financieras, despachos contables, inmobiliarias.

---

## Stack técnico

| Componente | Tecnología |
|---|---|
| Backend | FastAPI (Python) en Render |
| Frontend | Next.js 14 App Router en Vercel |
| Base de datos | Supabase (PostgreSQL) |
| OCR + análisis | Claude Vision API (claude-sonnet-4-5) |
| Migraciones | Alembic |
| Repositorio | GitHub (`cesgo1986/validador-comprobantes`) |

---

## Filosofía de diseño

**Honestidad epistémica:** VerificaPago solo afirma lo que puede demostrar. Si no pudo consultar Banxico, dice "no verificado", no "bajo riesgo". Si el documento tiene observaciones pero la transferencia existe, los reporta como dimensiones separadas, no las fusiona en un número opaco.

**Degradación graciosa:** cada capa del sistema puede fallar sin detener las demás. Si la descarga del XML falla, el análisis documental continúa. Si el CEP no está disponible, el OCR y el IAT siguen corriendo. El usuario siempre obtiene el mejor resultado posible con la información disponible.

**Dos motores independientes:** el estado SPEI (Motor 1, fuente Banxico) nunca puede ser modificado por el análisis documental (Motor 2, fuente VerificaPago). Ver `MOTOR_DECISIONES.md`.