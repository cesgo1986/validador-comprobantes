# ROADMAP.md — Plan de desarrollo de VerificaPago

**Versión del documento:** 0.11.0 · **Última actualización:** 02/07/2026

## Estado actual (post Sprint 0)

El núcleo del producto está funcionando en producción:

- ✅ OCR + análisis IA con Claude Vision
- ✅ Motor IAT (análisis estadístico propio)
- ✅ Scoring v3 con 4 dimensiones independientes
- ✅ 2 motores independientes: Estado SPEI + Integridad documental
- ✅ Jerarquía de evidencia: XML oficial > CEP HTML > análisis documental
- ✅ Descarga automática del XML del CEP desde Banxico
- ✅ Comparación XML vs. comprobante visual campo por campo
- ✅ Detección de reutilización de comprobantes (hash SHA-256)
- ✅ Flujo móvil de 6 pantallas (App Router Next.js)
- ✅ Backend multiempresa preparado (empresa_id en todas las tablas)
- ✅ Endpoints de dashboard (`/api/v1/dashboard/*`)
- ✅ Auditoría de análisis en base de datos (Supabase)
- ✅ Documentación técnica fundacional (`/docs`)

---

## Secuencia del roadmap (2026-07)

A partir de esta fecha, el desarrollo sigue una secuencia de Etapas en vez de Sprints etiquetados A-E de forma plana. Motivo y detalle completo en `DECISION_LOG.md` ("Cierre funcional del MVP Beta antes de escalar").

**Regla de secuencia:** no se inicia la Etapa 2 en serio hasta cerrar la Etapa 1. El contenido técnico de los Sprints B/C/D/E anteriores no se perdió — está reubicado dentro de esta secuencia.

```
Etapa 1 — Cierre funcional del MVP Beta   ⭐ (prioridad inmediata)
Etapa 2 — Historial real                   ⭐⭐⭐
Etapa 3 — Alertas inteligentes
Etapa 4 — Dashboard Empresa
Etapa 5 — Desktop (incluye Motor de Presentación)
Etapa 6 — Seguridad
Etapa 7 — Multiempresa real
```

---

## Etapa 1 — Cierre funcional del MVP Beta (Sprint A-Final)

**Objetivo:** que cualquier persona pueda entender el resultado en menos de 10 segundos.

Este es el hallazgo clave de la revisión de 2026-07: lo que falta en la Etapa 1 ya no es desarrollar funcionalidades nuevas — es terminar el **lenguaje** de VerificaPago. El sistema ya calcula todo lo que necesita calcular; lo que falta es que la persona que recibe el resultado entienda de inmediato qué significa y qué hacer con él, sin tener que interpretar un semáforo o un score. Por eso este cierre se trata como un sprint final de UX (**Sprint A-Final**), después del cual esta parte del producto se "congela" y toda la energía se mueve a capacidades empresariales.

> ⚠️ **Nota de estado (2026-07):** confirmado contra código real compartido (`app/resultado/page.tsx`, `app/resultado/detalle/page.tsx`). Ver detalle por ítem abajo.

### 1.1 — Estado SPEI protagonista + integridad separada ✅ (confirmado)
- Estado SPEI como semáforo principal de `/resultado`
- Integridad documental mostrada por separado, sin fusionarse con el estado SPEI
- Jerarquía de evidencia (XML oficial > CEP HTML > no disponible) reflejada en la UI

> ⚠️ **Orden de trabajo decidido (2026-07, refinado):** el Sprint A-Final sigue esta secuencia completa hasta cerrar el MVP Beta — no por funcionalidad, sino por **experiencia de decisión**: VerificaPago ya sabe analizar, consultar y comparar, pero todavía no explica su decisión de forma consistente.

```
1.1 ✅ Estado visual (cerrado)
   ↓
1.4  Diseñar el flujo de decisión explicable (la "gramática" de VerificaPago)
   ↓
1.2  Escribir los mensajes contextuales usando ese flujo
   ↓
1.3  Completar la evidencia XML (desglose campo a campo)
   ↓
1.5  Robustecer la arquitectura XML backend
   ↓
1.6  Observabilidad
   ↓
✅ MVP Beta cerrado
```

1.4 se diseña antes que 1.2 porque los mensajes contextuales dependen de la estructura que los va a contener — ver `DECISION_LOG.md`. 1.3 es independiente y puede avanzar en paralelo con 1.4/1.2, es trabajo de frontend puro sobre datos que el backend ya expone. 1.5 y 1.6 se quedan al final deliberadamente: son infraestructura, y el MVP Beta necesita cerrar primero la capa visible (ver `DECISION_LOG.md`, "Fase de Fundación").

### 1.2 — Mensajes contextuales por estado SPEI (pendiente — se escribe después de 1.4)
No se encontró ningún componente que implemente el contenido extendido por estado (qué significa / qué hacer / tiempo esperado / casos comunes). `resultado/page.tsx` solo muestra la etiqueta y el diagnóstico general (`interpretacion`/`resumen`), no un mensaje específico por cada uno de los 9 estados.

**Criterio de cierre (2026-07):** no basta con mostrar el nombre del estado (ej. "En proceso"). El mensaje debe responder directamente la pregunta que el comercio realmente tiene: *¿entrego el producto o no?* Esa respuesta es trabajo de VerificaPago, no del CEP — el CEP solo informa el estado técnico, VerificaPago tiene que traducirlo a una recomendación de acción.

Cada uno de los 9 estados se redacta siguiendo el flujo de decisión de 1.4 (Resultado → Interpretación → Impacto → Evidencias), no como un texto suelto. Ejemplo (`en_proceso`):

```
Resultado:       En proceso
Interpretación:  La operación aún está siendo procesada por SPEI.
Impacto:         Espera unos minutos antes de considerar la transferencia como fallida.
Evidencias:      ✓ XML · ✓ CEP
```

### 1.3 — Comparación XML en la UI (parcialmente construido — incluido en Sprint A-Final)
`app/resultado/detalle/page.tsx` ya existe y agrupa `result.validaciones` por categoría (`cep`, `estructural`, `visual`, `temporal`, `contextual`, `semantica`, `reputacion`, `historial`) en acordeones colapsables con estado ok/warn/fail. Esto cubre "fuentes de validación refinadas" en términos generales, pero **no** es todavía el desglose campo a campo que pide este ítem — hoy la categoría `cep` se renderiza como los ítems que el backend meta en `validaciones` (según `API.md`, un único ítem "CEP Banxico - Verificación SPEI"), no como una lista campo por campo de `cep_xml.comparacion_campos`. Falta:
- ✓ Monto coincide
- ✓ Banco receptor coincide
- ✓ Cuenta destino coincide
- ✓ Clave de rastreo coincide
- ⚠ Discrepancias explícitas cuando existan (ej. "Banco destino diferente")

El backend ya calcula todo esto (`cep_xml.comparacion_campos.comparaciones`, ver `API.md`) — es trabajo puramente de frontend: mapear esos campos a entradas individuales dentro del grupo `cep`, o a una sección propia. Se prioriza en este sprint porque genera confianza inmediata y el costo de cerrarlo es bajo (el dato ya existe). Corresponde al paso ⑤ Detalle del flujo de decisión de 1.4.

### 1.4 — El flujo de decisión explicable (antes "Centro de Estado" / "Evidencia de la decisión" / "¿Cómo se llegó a este resultado?") — se diseña primero, antes que 1.2
Ver `DECISION_LOG.md`, entradas "'Evidencia de la decisión' se renombra a '¿Cómo se llegó a este resultado?'..." y "Refinamiento: de las 4 preguntas al flujo de decisión de 5 pasos" (2026-07). Es un **patrón visual reutilizable**, no una pantalla nueva, gobernado por una regla de producto: toda conclusión de VerificaPago debe poder justificarse con al menos una evidencia verificable.

**El componente ya no se piensa como una lista de datos que responde preguntas — se piensa como una conversación de 5 pasos**, porque el usuario no piensa en preguntas, piensa en "¿qué pasó?":

```
① Resultado         Liquidada
② Interpretación     La transferencia fue liquidada correctamente mediante SPEI.
③ Impacto            Puedes considerar el pago realizado.
④ Evidencias         ✓ Estado SPEI · ✓ XML · ✓ Datos · ⚠ Imagen
⑤ Detalle            (el acordeón existente en /resultado/detalle — ver 1.3)
```

Esta secuencia es la forma de presentación del modelo de 4 capas ya definido en `MODELO_DECISION_EXPLICABLE.md` (Hechos → Interpretación → Recomendación → Evidencia), con dos ajustes de diseño:
- **① Resultado** se hace explícito como primer paso, separado de la interpretación — es el dato categórico crudo (ej. "Liquidada"), no todavía una lectura de él.
- La capa que el modelo llama internamente "Recomendación" se etiqueta de cara al usuario como **③ Impacto** ("¿qué implica para mí?"), un lenguaje menos directivo que "qué debo hacer", pero que cumple la misma función: traducir la interpretación en algo accionable.

Extensible sin cambiar la UI: hoy ④ Evidencias enumera XML/OCR/IA, mañana puede sumar hash, historial, patrones, alertas o motor antifraude sin rediseñar el componente ni el flujo.

Se implementa embebido dentro de `/resultado` (extendiendo el bloque que ya existe para Motor 1 y Motor 2 en `resultado/page.tsx`), no como ruta nueva. Es el primer candidato a estandarizarse dentro del futuro objeto `presentation` del Motor de Presentación (Etapa 5) — la forma de datos objetivo para esa migración (`evidencias: [{tipo, resultado}]`) ya quedó anotada en `DECISION_LOG.md` como referencia de diseño, no como algo implementado hoy. Al definirse como flujo (no como pantalla), se convierte en la "gramática" de VerificaPago — se reutiliza igual en Historial, Dashboard Empresa, Desktop, Alertas Inteligentes y la futura API Enterprise, sin que cada uno reinvente cómo explicar una decisión.

**Sesión de diseño pendiente (sin código):** ver `MODELO_DECISION_EXPLICABLE.md`. Se diseña respondiendo, en orden, los 5 pasos del flujo de decisión para cada uno de los 9 estados SPEI — no como preguntas aisladas, sino como la conversación completa: qué resultado se muestra, cómo se interpreta, qué impacto tiene para el usuario, qué evidencias lo respaldan, y qué detalle adicional queda disponible si quiere profundizar.

### 1.5 — Arquitectura XML backend (pendiente)
- Reintentos con backoff exponencial cuando `valida.do` falla por timeout
- Caché de resultado de consulta (evitar re-consultar Banxico si el mismo comprobante se analiza dos veces en minutos, usando el hash SHA-256)
- Métricas de descarga: porcentaje de éxito/fallo, tiempo promedio de respuesta

### 1.6 — Observabilidad (pendiente)
- Porcentaje de XML descargados automáticamente vs. fallidos
- Tiempo promedio de análisis completo
- Causas más frecuentes de fallo en la descarga del XML
- OCR promedio y distribución de scores por banco
- Errores de scraping del CEP HTML

### Entregables de cierre de Etapa 1 (Sprint A-Final)
- Mensajes contextuales para los 9 estados SPEI, cada uno respondiendo "¿entrego o no?"
- Comparación XML campo a campo visible en la UI
- "¿Cómo se llegó a este resultado?" implementado como patrón visual embebido en `/resultado`
- Fuentes de validación refinadas
- Casos de intermitencia de Banxico claramente explicados en la UI
- Estados "No encontrada", "En proceso", "Devuelta", "Rechazada" y "Cancelada" completamente diseñados

Con esto cerrado, esta parte del producto se congela — no se vuelve a tocar `/resultado` salvo bugs — y el foco se mueve por completo a valor empresarial (Etapas 2-4).

---

## Etapa 2 — Historial real ⭐⭐⭐

**Objetivo:** conectar el historial con datos reales y hacerlo buscable — el siguiente gran salto de utilidad, porque cambia el producto de "analizo un comprobante" a "analizo tendencias".

**Nota:** el backend ya está listo (`/api/v1/dashboard/analisis` existe). Falta principalmente el frontend.

Funcionalidades:
- Lista de análisis con filtros (fecha, banco, riesgo, hash)
- Búsqueda por clave de rastreo, monto, banco, cuenta
- Vista de detalle de un análisis histórico
- Exportación de historial
- Métricas agregadas visibles para el usuario, ej.: total de análisis, % exitosos, % rechazados, posibles alteraciones detectadas, documentos reutilizados, no encontrados

---

## Etapa 3 — Alertas inteligentes

**Objetivo:** pasar de guardar información a detectarla activamente. Esto ya no es validación puntual, es inteligencia sobre el histórico.

Ejemplos de alertas:
- Este mismo comprobante (hash) apareció nuevamente
- El mismo hash apareció hace N días
- Un cliente/cuenta acumula varios intentos fallidos en un periodo corto
- Varias cuentas distintas usando la misma imagen de comprobante

Depende de Etapa 2 (historial real) para tener la base de datos sobre la cual detectar patrones.

---

## Etapa 4 — Dashboard Empresa

**Objetivo:** cambiar de público — de "analizo una transferencia" a "analizo miles". Este es el salto a Enterprise.

Ejemplo de contenido del dashboard:
- Transferencias del día por estado (liquidadas, en proceso, devueltas)
- Monto total procesado
- Clientes con más incidencias
- Top bancos por volumen
- Tiempo promedio de validación

---

## Etapa 5 — Desktop

**Objetivo:** nueva experiencia para clientes empresariales que procesan volúmenes altos. Se ubica después de Historial, Alertas y Dashboard porque para este punto ya está claro exactamente qué información debe consumir.

**No es adaptar la UI móvil.** Es diseñar desde cero para pantallas grandes:
- Análisis de múltiples comprobantes simultáneos
- Vista de resultados en tabla con filtros
- Integración con el historial y dashboard
- Exportación de reportes
- Workflow de aprobación/rechazo por operador

Desktop cambia el mercado: pasa de "analizo un comprobante" a "analizo 500 comprobantes diarios".

### 5.1 — Motor de Presentación (backend)

Desktop es el segundo consumidor real del backend (después de Mobile). Por la regla de arquitectura fijada en `DECISION_LOG.md` ("Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores"), este es el momento de mover la lógica de colores/iconos/niveles de severidad — hoy vive solo en `app/resultado/page.tsx` — a un objeto `presentation` calculado por el backend:

```json
{
  "presentation": {
    "integridad": { "nivel": "warning", "texto": "Con observaciones" },
    "spei": { "nivel": "success", "texto": "Liquidada" }
  }
}
```

Antes de este sprint, el paso intermedio es exponer `evidencias` (hechos crudos: `xml_valido`, `xml_discrepancias`, `confianza_documental`, `verificabilidad`, `contexto_temporal`, `hash_reutilizado`) para que Mobile decida sobre datos explícitos mientras se estabiliza la UX — ver `DECISION_LOG.md`.

Sin este motor, Mobile y Desktop terminarían con dos implementaciones distintas del mismo criterio de severidad, con alto riesgo de divergir silenciosamente.

---

## Etapa 6 — Seguridad

**Objetivo:** hacer el sistema seguro para escalar a usuarios reales. Se mueve al final de la secuencia deliberadamente — ver `DECISION_LOG.md` — porque buena parte de esta superficie cambiará de forma conforme se definan Historial, Alertas y Dashboard.

- JWT / autenticación real (hoy no existe — `DEFAULT_EMPRESA_ID` para todos)
- Rate limiting por IP y por cuenta
- Eliminación automática de imágenes tras el análisis (no almacenar comprobantes en disco)
- API Keys para acceso B2B
- Auditoría de acceso (quién consultó qué y cuándo)
- Sanitización de inputs (validación de tipos de archivo más estricta)
- OAuth, encriptación adicional, observabilidad tipo SIEM, políticas de retención y borrado automático de logs

---

## Etapa 7 — Multiempresa real

**Objetivo:** activar la arquitectura multiempresa que ya existe en el esquema de datos. Comparte superficie con Etapa 6 (autenticación) — se evalúa si conviene fusionarlas al llegar a ese punto.

- Autenticación por empresa (JWT con empresa_id)
- Invitación de usuarios
- Aislamiento de datos entre empresas (el `UNIQUE(empresa_id, hash_sha256)` ya existe)
- Gestión de sucursales y permisos
- Facturación por créditos o por volumen
- API Keys por empresa para integración B2B

---

## Producto (no código) — pendiente de iniciar

**`BETA_PLAN.md` (nuevo documento, aún no redactado):** objetivos del beta, número de usuarios, qué se quiere medir y qué no, KPIs, criterios para salir de beta, mecanismo de reporte de errores, métricas a observar. Se activa cuando el proyecto empiece a invitar empresas reales — ver `DECISION_LOG.md`.

**`PRINCIPIOS_DE_PRODUCTO.md` (nuevo documento, aún no redactado — deliberadamente pospuesto hasta Beta):** documento corto (1-2 páginas), no técnico, con reglas innegociables del producto — ej. "el estado SPEI nunca será alterado por inferencias", "toda recomendación debe ser explicable", "las fuentes oficiales prevalecen sobre las inferencias", "el usuario siempre debe entender el resultado en menos de 10 segundos", "la confianza se construye mostrando evidencias, no ocultando complejidad". Funciona como una "constitución" del producto: cada función nueva debería poder responder una sola pregunta — ¿respeta los principios de VerificaPago? Se pospone intencionalmente hasta la entrada a Beta, cuando haya suficiente superficie de producto real para que esas reglas se prueben contra decisiones concretas en vez de quedar como aspiración abstracta.

---

## Roadmap B2B futuro (no comprometido)

- **CEP por lotes:** `banxico.org.mx/cep-scl/` — ya investigado y documentado, viable para volúmenes altos
- **Integración Open Finance:** cuando la regulación mexicana avance
- **Módulo de contexto operativo:** consulta de estado de SPEI y conectividad de participantes vía MonSPEI (sin API pública hoy, requiere scraping del portal o acuerdo con Banxico)
- **Motor de reputación:** scoring por CLABE/cuenta basado en historial de análisis propios

---

## Documentos relacionados

- `DECISION_LOG.md` — el porqué detrás de la secuencia de Etapas
- `MODELO_DECISION_EXPLICABLE.md` — el marco que guía el diseño del ítem 1.4
- `CHANGELOG.md` — el registro versión por versión de estos cambios