# ROADMAP.md — Plan de desarrollo de VerificaPago

**Versión del documento:** 0.28.0 · **Última actualización:** 07/07/2026

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
1.4 ✅ Flujo de decisión explicable + jerarquía de divulgación progresiva (cerrado)
   ↓
1.2 ✅ Mensajes contextuales escritos usando ese flujo (cerrado — desplegados junto con 1.4)
   ↓
1.3 ✅ Comparación XML campo a campo (cerrado)
   ↓
1.5 ✅ Arquitectura XML backend: cache, métricas, reintentos (cerrado)
   ↓
1.6  Observabilidad
   ↓
✅ MVP Beta cerrado
```

1.4 se diseña antes que 1.2 porque los mensajes contextuales dependen de la estructura que los va a contener — ver `DECISION_LOG.md`. 1.3 es independiente y puede avanzar en paralelo con 1.4/1.2, es trabajo de frontend puro sobre datos que el backend ya expone. 1.5 y 1.6 se quedan al final deliberadamente: son infraestructura, y el MVP Beta necesita cerrar primero la capa visible (ver `DECISION_LOG.md`, "Fase de Fundación").

### 1.2 — Mensajes contextuales por estado SPEI ✅ (completado y desplegado)
No se encontró ningún componente que implemente el contenido extendido por estado (qué significa / qué hacer / tiempo esperado / casos comunes). `resultado/page.tsx` solo muestra la etiqueta y el diagnóstico general (`interpretacion`/`resumen`), no un mensaje específico por cada uno de los 9 estados.

**Criterio de cierre (2026-07):** no basta con mostrar el nombre del estado (ej. "En proceso"). El mensaje debe responder directamente la pregunta que el comercio realmente tiene: *¿entrego el producto o no?* Esa respuesta es trabajo de VerificaPago, no del CEP — el CEP solo informa el estado técnico, VerificaPago tiene que traducirlo a una recomendación de acción.

Cada uno de los 9 estados se redacta siguiendo el flujo de decisión completo (Resultado → Interpretación → Impacto → Recomendación inmediata *si aplica* → Evidencias), no como un texto suelto — ver `MODELO_DECISION_EXPLICABLE.md` para el modelo de 5 capas detrás de este flujo. Regla de fondo aplicada a los nueve: **nunca inducir al usuario a una acción cuando la evidencia todavía no lo permite.**

**Catálogo final (2026-07):**

**Acreditada** 🟢
- Interpretación: El banco receptor confirmó que los recursos fueron acreditados al beneficiario. Es la evidencia oficial de mayor certeza disponible.
- Impacto: Puedes considerar el pago confirmado y entregar el producto o servicio con confianza.
- Recomendación inmediata: *(no aplica)*
- Evidencias: ✓ CEP Banxico

**Liquidada** 🟢
- Interpretación: La operación fue liquidada correctamente en SPEI y forma parte del registro oficial de Banxico.
- Impacto: Puedes considerar el pago realizado. Es seguro continuar con la operación.
- Recomendación inmediata: *(no aplica)*
- Evidencias: ✓ XML oficial (o ✓ CEP, según el nivel de evidencia disponible)

**En proceso** 🟡
- Interpretación: La operación aún está siendo procesada por SPEI; todavía no hay confirmación de liquidación.
- Impacto: Espera unos minutos y vuelve a consultar antes de emitir un juicio sobre la operación. Si el comprobante presenta alta integridad documental, es una señal favorable, aunque todavía no constituye confirmación oficial.
- Recomendación inmediata: Esperar y volver a consultar.
- Evidencias: ✓ Consulta a Banxico en curso

**Devuelta** 🟠
- Interpretación: La operación existió, pero los recursos fueron devueltos al banco emisor.
- Impacto: No consideres el pago como realizado. Pide al comprador que verifique con su banco por qué se devolvió.
- Recomendación inmediata: Solicitar un nuevo comprobante.
- Evidencias: ✓ Estado SPEI confirmado

**En devolución** 🟠
- Interpretación: La devolución de esta operación está en curso — el proceso todavía no concluye.
- Impacto: No consideres el pago como realizado todavía. Espera a que el proceso de devolución termine.
- Recomendación inmediata: Esperar a que concluya la devolución.
- Evidencias: ✓ Estado SPEI confirmado

**Rechazada** 🔴
- Interpretación: SPEI rechazó la operación — la transferencia no se procesó.
- Impacto: No entregues el producto o servicio. Esta transferencia no ocurrió.
- Recomendación inmediata: *(no aplica — el Impacto ya es la acción)*
- Evidencias: ✓ Estado SPEI confirmado

**Cancelada** 🔴
- Interpretación: El banco emisor canceló la operación antes de que se liquidara.
- Impacto: No entregues el producto o servicio. La transferencia no se completó.
- Recomendación inmediata: *(no aplica — el Impacto ya es la acción)*
- Evidencias: ✓ Estado SPEI confirmado

**No liquidada** 🔴
- Interpretación: La operación no logró liquidarse dentro del proceso establecido por SPEI.
- Impacto: No consideres el pago como realizado. Solicita un comprobante actualizado o verifica directamente con el banco del comprador.
- Recomendación inmediata: *(no aplica — el Impacto ya incluye la acción)*
- Evidencias: ✓ Estado SPEI confirmado

**Desconocida (No verificado)** ⚪
- Interpretación: No fue posible obtener una confirmación oficial del estado de esta operación con Banxico. Esto puede deberse a datos insuficientes, indisponibilidad temporal del servicio o a que la operación aún no esté disponible para consulta.
- Impacto: La ausencia de confirmación oficial no implica que la transferencia sea falsa ni que sea válida. Antes de entregar un producto o servicio, considera la integridad del comprobante y, si el monto lo amerita, verifica directamente con el banco o espera una nueva consulta.
- Recomendación inmediata: Verificar nuevamente los datos del comprobante.
- Evidencias: solo integridad documental (sin evidencia SPEI)

Este es probablemente el estado que más aparecerá durante la Beta — es el que recibe más cuidado de redacción porque es donde más fácil es que alguien tome una mala decisión: ni afirma que la transferencia es falsa, ni que es válida, solo orienta.

### 1.3 — Comparación XML en la UI ✅ (completado y desplegado)
`main.py` ahora genera una entrada de `validaciones` (categoría `cep_xml`) por cada campo comparado — `monto`, `fecha`, `clave_rastreo`, `banco_destino`, `cuenta_destino_ultimos_digitos` — en vez del mensaje agregado único que había antes. `app/resultado/detalle/page.tsx` mapea `cep_xml` a "Comparación XML oficial (Banxico)" como grupo propio, justo después de `cep` en el orden de prioridad. El backend ya calculaba esto (`cep_xml.comparacion_campos.comparaciones`, ver `API.md`) — el cambio fue exclusivamente de presentación: desglosar en vez de agregar. El campo `fecha` se reporta como `status: "info"` (no ok/fail) porque su comparación es intencionalmente no concluyente por formato variable entre bancos (ver `cep_xml_service.py`).

### 1.4 — El flujo de decisión explicable (antes "Centro de Estado" / "Evidencia de la decisión" / "¿Cómo se llegó a este resultado?") ✅ (completado y desplegado)
Ver `DECISION_LOG.md`, entradas "'Evidencia de la decisión' se renombra a '¿Cómo se llegó a este resultado?'...", "Refinamiento: de las 4 preguntas al flujo de decisión de 5 pasos" y "🏛️ ADR: se formaliza la capa de Recomendación, distinta de Impacto" (2026-07). Es un **patrón visual reutilizable**, no una pantalla nueva, gobernado por una regla de producto: toda conclusión de VerificaPago debe poder justificarse con al menos una evidencia verificable, y nunca debe inducir a una acción cuando la evidencia todavía no lo permite.

**El componente ya no se piensa como una lista de datos que responde preguntas — se piensa como una conversación de 6 pasos**, porque el usuario no piensa en preguntas, piensa en "¿qué pasó?":

```
① Resultado                Liquidada
② Interpretación            La transferencia fue liquidada correctamente mediante SPEI.
③ Impacto                   Puedes considerar el pago realizado.
④ Recomendación inmediata   (solo si aplica — no en este caso)
⑤ Evidencias                ✓ Estado SPEI · ✓ XML · ✓ Datos · ⚠ Imagen
⑥ Detalle                   (el acordeón existente en /resultado/detalle — ver 1.3)
```

Esta secuencia es la forma de presentación del modelo de 5 capas definido en `MODELO_DECISION_EXPLICABLE.md` (Hechos → Interpretación → Impacto → Recomendación → Evidencia). Impacto y Recomendación son capas distintas, no un alias entre sí — ver el ADR referenciado arriba.

Extensible sin cambiar la UI: hoy ⑤ Evidencias enumera XML/OCR/IA, mañana puede sumar hash, historial, patrones, alertas o motor antifraude sin rediseñar el componente ni el flujo.

Se implementa embebido dentro de `/resultado` (extendiendo el bloque que ya existe para Motor 1 y Motor 2 en `resultado/page.tsx`), no como ruta nueva. Es el primer candidato a estandarizarse dentro del futuro objeto `presentation` del Motor de Presentación (Etapa 5) — la forma de datos objetivo para esa migración (`evidencias: [{tipo, resultado}]`) ya quedó anotada en `DECISION_LOG.md` como referencia de diseño, no como algo implementado hoy. Al definirse como flujo (no como pantalla), se convierte en la "gramática" de VerificaPago — se reutiliza igual en Historial, Dashboard Empresa, Desktop, Alertas Inteligentes y la futura API Enterprise, sin que cada uno reinvente cómo explicar una decisión.

**Estado del diseño (2026-07): completado, en producción.** El texto de los 9 estados está redactado y desplegado (ver catálogo en 1.2). La implementación en `resultado/page.tsx` incluyó además un rediseño de jerarquía no previsto originalmente en el diseño del flujo: el patrón de 6 pasos se organizó en **divulgación progresiva** — ① Resultado y ②③④ (Interpretación/Impacto/Recomendación) quedan siempre visibles como Nivel 1 (respuesta en ~5 segundos a "¿puedo entregar o no?"); ⑤ Evidencias, integridad documental, reutilización del documento, las 4 dimensiones y el diagnóstico técnico quedan detrás de un único botón "Ver detalles del análisis" (Nivel 2+), para no competir visualmente con la decisión principal. También se corrigió que el mensaje de integridad documental contextualice primero el estado SPEI favorable antes de mostrar una observación, para no inducir una lectura contraria a la conclusión real (ver `DECISION_LOG.md`, regla "nunca inducir a una acción cuando la evidencia no lo permite").

### 1.5 — Arquitectura XML backend ✅ (completado y desplegado)
Ver `DECISION_LOG.md`, ADR "Externalización de servicios transversales (Cache y Metrics)".

- **Reintentos con backoff:** progresión explícita (200ms, 500ms, 1000ms), máximo 3 intentos. Solo reintenta timeouts — errores 4xx/5xx no se reintentan. Vive en `cep_xml_auto_service.py`, es lógica específica de ese flujo HTTP.
- **Caché de resultado de consulta:** extraído a `services/cache_service.py` (genérico, `get`/`set`/`delete` con TTL), no vive dentro del XML Service. TTL de **30 minutos** — un comprobante ya analizado prácticamente nunca cambia, así que prioriza ahorrar llamadas a Banxico sobre "frescura" del dato. Consumido por hash SHA-256 del comprobante.
- **Métricas de descarga:** extraídas a `services/metrics_service.py` (genérico, namespaced por servicio), no vive dentro del XML Service. Registra consultas totales, éxitos/fallos, cache hits/miss, reintentos, timeouts, duración (promedio/mín/máx), y eventos de dominio (`xml_descargado`, `xml_no_encontrado`, `xml_con_error`).
- **Endpoint de métricas:** `GET /api/v1/dashboard/metricas/xml` — ruta anidada bajo `/metricas/` a propósito, para que `/metricas/ocr`, `/metricas/claude`, `/metricas/usuarios`, etc. sigan la misma estructura cuando existan.

**Por qué se separó en dos servicios en vez de implementarlo dentro de `cep_xml_auto_service.py`:** Historial, Dashboard Empresa, validación por QR/XML manual y el futuro Motor de Presentación (Etapa 5) también van a necesitar cachear y medir. Hacerlo genérico desde ahora evita terminar con `_METRICAS_OCR`, `_METRICAS_XML`, `_METRICAS_HISTORIAL` dispersas sin una interfaz común.

### 1.6 — Observabilidad ✅ (completado y desplegado)
- Porcentaje de XML descargados automáticamente vs. fallidos → `GET /api/v1/dashboard/metricas/xml` (1.5)
- Tiempo promedio de análisis completo → `GET /api/v1/dashboard/metricas/analizar`
- Causas más frecuentes de fallo en la descarga del XML → campo `eventos` de `/metricas/xml` (`xml_no_encontrado`, `xml_con_error`)
- OCR promedio y distribución de scores por banco → `GET /api/v1/dashboard/metricas/scores-por-banco` (consulta a base de datos, histórico completo; usa `score_claude` como señal de riesgo documental, no como confianza de OCR — ver nota en `dashboard_service.py`)
- Errores de scraping del CEP HTML → `GET /api/v1/dashboard/metricas/cep` (`cep_no_existe`, `cep_timeout`, `cep_error`, etc.)

## ✅ Etapa 1 — Cierre funcional del MVP Beta: COMPLETA (2026-07)

### Entregables de cierre de Etapa 1 (Sprint A-Final)
- ✅ Mensajes contextuales para los 9 estados SPEI, cada uno respondiendo "¿entrego o no?"
- ✅ Comparación XML campo a campo visible en la UI
- ✅ "¿Cómo se llegó a este resultado?" implementado como patrón visual embebido en `/resultado`, con jerarquía de divulgación progresiva
- ✅ Fuentes de validación refinadas
- ✅ Observabilidad básica (XML, CEP, análisis completo, scores por banco)
- ✅ Estados "Acreditada", "Liquidada", "En proceso", "Devuelta", "En devolución", "Rechazada", "Cancelada", "No liquidada" y "Desconocida" completamente diseñados (catálogo completo, ver ítem 1.2)
- 🟡 Casos de intermitencia del portal de Banxico (mantenimiento, caída temporal): cubiertos de forma general por el mensaje del estado `desconocida`, pero no se diseñó un tratamiento visual específico distinto para "Banxico no disponible ahora mismo" vs. "no se pudo determinar el estado" por otras razones. Ajuste menor, no bloqueante — candidato para revisar durante la Beta si se observa confusión real de usuarios.

Con esto cerrado, esta parte del producto se congela — no se vuelve a tocar `/resultado` salvo bugs — y el foco se mueve por completo a valor empresarial (Etapas 2-4).

---

## ✅ Etapa 2 — Historial real: COMPLETA (2026-07)

**Objetivo:** conectar el historial con datos reales y hacerlo buscable — el siguiente gran salto de utilidad, porque cambia el producto de "analizo un comprobante" a "analizo tendencias".

**Nota:** el backend ya está listo (`/api/v1/dashboard/analisis` existe). Falta principalmente el frontend.

Funcionalidades:
- Lista de análisis con filtros (fecha, banco, riesgo, hash)
- Búsqueda por clave de rastreo, monto, banco, cuenta
- Vista de detalle de un análisis histórico
- Exportación de historial
- Métricas agregadas visibles para el usuario, ej.: total de análisis, % exitosos, % rechazados, posibles alteraciones detectadas, documentos reutilizados, no encontrados

**2.1 — Lista con filtros ✅ (completado y desplegado, 2026-07):** diseño con divulgación progresiva (ver `DECISION_LOG.md`) — Nivel 1: búsqueda simple + lista cronológica agrupada por día, coloreada/etiquetada por `estado_operacion` (Motor 1, no `riesgo`). Nivel 2+: filtros avanzados (riesgo, fecha, hash) y "Resumen de actividad", colapsados por defecto. Incluyó migración de `estado_operacion`/`fuente_estado`/`nivel_evidencia` en la tabla `analisis` (ver ADR en `DECISION_LOG.md`). Nota: los análisis anteriores a la migración muestran `estado_operacion: null` — la columna se agregó vacía, sin backfill retroactivo del JSONB histórico. Pendiente evaluar si vale la pena un script de backfill más adelante; no bloquea el uso normal.

**2.2 — Búsqueda unificada ✅ (completado y desplegado, 2026-07):** la caja de búsqueda simple (Nivel 1) del Historial busca simultáneamente en banco, clave de rastreo, referencia, CLABE y (si el texto es numérico) monto — el usuario escribe una sola cosa, sin elegir en qué campo buscar (parámetro `q` en `GET /api/v1/dashboard/analisis`, ver `API.md`). Incluyó migración desnormalizando `clave_rastreo` y `referencia` (indexadas) y sembrando `tipo_transferencia` (sin uso activo, siempre `"SPEI"` hoy) — ver ADR de columnas desnormalizadas en `DECISION_LOG.md`. Misma limitación que 2.1: análisis anteriores a la migración no tienen `clave_rastreo`/`referencia` poblados, solo se pueden encontrar por banco o monto.

**2.4 — Exportación de historial ✅ (completado y desplegado, 2026-07):** `GET /api/v1/dashboard/analisis/exportar` — mismos filtros que `/analisis` (incluida la búsqueda unificada `q`), sin paginación, hasta 5000 filas. Reutiliza `_construir_filtros_analisis()` compartida con `listar_analisis()` (ver `dashboard_service.py`) para garantizar que la exportación coincide exactamente con lo que el usuario ve filtrado en pantalla — no una implementación de filtros separada que pudiera divergir. Etiquetas de estado SPEI traducidas a texto legible vía `SEMAFORO_SPEI` en el CSV. Botón "⬇ Exportar a CSV" agregado dentro del panel de filtros avanzados de `app/historial/page.tsx` (Nivel 2, no compite con la lista). Verificado funcionando end-to-end.

**2.3 — Vista de detalle de un análisis histórico ✅ (completado y desplegado, 2026-07):** `app/historial/[id]/page.tsx`, consume `GET /api/v1/dashboard/analisis/{id}`. Reutiliza `AnalisisContext` (ver ADR en `DECISION_LOG.md`) — hidrata el contexto con el resultado histórico para que "Ver validaciones completas" navegue a `/resultado/detalle` sin ninguna modificación en ese archivo. Incluye: badge "Análisis archivado" (cambia la expectativa del usuario — no espera que los datos cambien), ficha de auditoría (fecha, archivo, banco, monto, hash, nivel de evidencia, fuente del estado) antes del semáforo, espacio reservado "Actividad relacionada" (visión de Historial Inteligente, sin implementar), y nota de privacidad reencuadrada ("no se guarda la imagen" como decisión de diseño, no como limitación). Deliberadamente **sin** botón "Ver comprobante" — el sistema no persiste la imagen original del comprobante, solo el JSON del análisis.

**Refactor ✅ resuelto (2026-07, antes de Etapa 4):** `app/historial/[id]/page.tsx` duplicaba una porción significativa del JSX de `app/resultado/page.tsx`. Extraído a componentes compartidos en `app/components/resultado/`: `SemaforoSpei.tsx`, `QueSignificaEsto.tsx`, `DetalleExpandible.tsx` (+ `app/lib/colores.ts`). Resuelto antes de abrir Etapa 4 (Dashboard Empresa) — ver ADR en `DECISION_LOG.md`.

**Evolución futura — Historial Inteligente (visión, sin sprint asignado):** el Historial evolucionará hacia un Historial Inteligente capaz de identificar patrones por emisor, beneficiario, cuenta, CLABE, banco, dispositivo y comportamiento histórico — es decir, no buscar comprobantes, sino buscar comportamiento. Esta evolución se considerará cuando exista suficiente información estadística proveniente de la Beta. No es un compromiso de roadmap ni tiene fecha — queda anotada aquí para no perderse cuando llegue el momento de evaluarla. El espacio "Actividad relacionada" en `/historial/[id]` ya quedó reservado visualmente para cuando esto se implemente.

---

## ✅ Etapa 3 — Alertas inteligentes: COMPLETA (2026-07)

**Objetivo:** pasar de guardar información a detectarla activamente. Esto ya no es validación puntual, es inteligencia sobre el histórico. Depende de Etapa 2 (Historial real), ya cerrada, para tener la base de datos sobre la cual detectar patrones.

Ver `DECISION_LOG.md`, ADR "las alertas son eventos persistentes generados por un motor de reglas independiente" — decisión de fondo que ordena toda esta etapa: las alertas se implementan como un **Alert Engine** desacoplado que evalúa reglas después de guardar cada análisis, no como lógica dispersa dentro de los endpoints, y la tabla `alertas` registra **hechos** (`tipo_alerta`, `entidad_tipo`, `entidad_id`, `severidad`, `estado` + `metadata` JSONB), no interpretaciones ya resueltas.

**3.1 — Diseño del Alert Engine (arquitectura) ✅:** ver el ADR completo en `DECISION_LOG.md`. Flujo: `analizar()` → guardar análisis → `AlertEngine.evaluar()` → crear eventos. Estructura planeada:
```
alert_engine/
├── engine.py            -- orquesta: junta resultados de todas las reglas
├── regla_hash.py         -- reutilización del mismo hash
├── regla_clabe.py         -- CLABE receptora frecuente
├── regla_clave_rastreo.py
├── regla_dispositivo.py   -- futuro, sin dato disponible todavía
└── regla_banco.py         -- futuro
```
Cada regla es una función que recibe el análisis recién guardado y devuelve `[]` o una lista de alertas — agregar una regla nueva es agregar un archivo, no modificar el motor. Se siembra un tercer motor conceptual, el **Motor de Comportamiento** (ver `MOTOR_DECISIONES.md`), junto al Motor SPEI y el Motor Documental.

**3.2 — Tabla `alertas` ✅ (completado y desplegado, 2026-07):** migración de Alembic + `models/alerta.py` + `services/alerta_service.py` (capa de persistencia: crear, listar, cambiar estado). Deliberadamente **sin** las reglas de detección todavía — eso es 3.3, vive aparte en `alert_engine/` (aún no creado), para no mezclar "cómo se guarda una alerta" con "qué la dispara". `tipo_alerta`/`severidad`/`entidad_tipo`/`estado` son `String`, no `ENUM` de Postgres — la restricción de valores permitidos vive en el código, no en la base de datos, para que agregar un tipo de alerta nuevo sea agregar un archivo, no una migración.

**3.3 — Primeras reglas de detección ✅ (completado y desplegado, 2026-07):** `alert_engine/` completo — `engine.py` (orquestador), `regla_hash.py`, `regla_clabe.py`, `regla_clave_rastreo.py` (esta última revisada durante el diseño: solo compara banco, no monto — ver `LABORATORIO.md`). Se dispara desde `main.py` justo después de `guardar_analisis()`, nunca antes, y nunca modifica el resultado devuelto al usuario — si el motor de alertas falla, el análisis principal ya se completó. Umbrales de las 3 reglas documentados como hipótesis iniciales en `LABORATORIO.md` (`#LAB-VP`), sujetos a ajuste con datos reales de la Beta. Verificado en producción: análisis normales sin afectación, alertas creándose correctamente en la tabla.

**3.4 — Pantalla `/alertas` ✅ (completado y desplegado, 2026-07):** `app/alertas/page.tsx` con divulgación progresiva — Nivel 1: solo alertas `NUEVA` por defecto (lo que necesita atención ahora), con acciones rápidas "Marcar como revisada"/"Descartar" por tarjeta. Nivel 2 (filtros): estado, severidad, tipo de alerta. Dos endpoints nuevos: `GET /api/v1/dashboard/alertas` y `PATCH /api/v1/dashboard/alertas/{id}/estado` (ver `API.md`). Etiquetas legibles por tipo de alerta y entidad — el usuario nunca ve el valor crudo del enum (`REUTILIZACION_HASH` se muestra como "Comprobante reutilizado").

**3.5 — Notificaciones y badge inteligente ✅ (completado y desplegado, 2026-07):** Motor de Prioridad implementado como filtro simple — `services/alerta_service.py`: `contar_alertas()` separa `total_nuevas` de `notificables` (severidad `MEDIA`+, ver `LABORATORIO.md` para el umbral como hipótesis). Nuevo endpoint `GET /api/v1/dashboard/alertas/conteo`. `BottomNav.tsx` reemplaza el badge hardcodeado en `3` por el conteo real (`notificables`), refrescado cada 60s mientras la app está abierta — no es tiempo real (WebSockets), es polling simple, suficiente para esta etapa. Verificado funcionando en producción.

**Nota de proceso:** las discusiones sobre umbrales de detección (¿cuántas veces es "frecuente"? ¿en cuántos días?) se registran como `#LAB-VP` en `LABORATORIO.md` conforme ocurran durante la Beta — son investigaciones que van a evolucionar con datos reales, no decisiones definitivas de hoy.

---

## ✅ Etapa 4 — Backend Empresarial + Executive Summary móvil: COMPLETA (2026-07)

**Objetivo:** cambiar de público — de "analizo una transferencia" a "analizo miles". Este es el salto a Enterprise. Ver `DECISION_LOG.md`, ADR "ningún dashboard consulta la base de datos o los motores directamente" — decisión de fondo que ordena toda esta etapa: se introduce `AggregationService` como cuarto consumidor del núcleo (junto a Motor SPEI, Motor Documental y Alert Engine), y **no** se construye un dashboard completo en móvil — ver ADR "una sola experiencia, múltiples presentaciones".

**4.1 — Backend empresarial completo ✅ (completado y desplegado, 2026-07):** `services/aggregation_service.py` (nuevo). Se movieron ahí, sin cambiar su lógica, las 4 agregaciones que ya existían en `dashboard_service.py` (`obtener_stats`, `tendencia_diaria`, `distribucion_scores_por_banco`, `top_hashes_reutilizados`) — `dashboard_service.py` ahora las expone como wrappers delgados, mismo nombre/firma, cero riesgo para los endpoints ya en producción. Se agregan 4 agregaciones nuevas: monto total procesado, banco más frecuente por volumen, riesgo por periodo (Motor 1 + Motor 2 por separado), y alertas agregadas. 5 endpoints nuevos: `/monto-total`, `/bancos-frecuentes`, `/riesgo-por-periodo`, `/alertas-agregadas`, `/resumen-ejecutivo` (este último para 4.2). Incluyó un fix real encontrado en el proceso: comparación de fechas contra `Analisis.fecha` (ver `CHANGELOG.md` v0.19.1) — afectaba también los filtros de fecha de Historial desde el ítem 2.1, sin haberse detectado hasta ahora.

**Gaps identificados y deliberadamente no resueltos en este corte:** "tiempo promedio de validación" requeriría una columna nueva (`duracion_ms`) en `analisis` — hoy solo existe como promedio en memoria del proceso (`metrics_service`), no histórico ni por periodo; no se implementa para no exponer un número que parezca histórico sin serlo. "Actividad por empresa" (comparar varias empresas) no tiene sentido real hasta que exista autenticación multiempresa (Etapa 6).

**4.2 — Mobile Executive Summary ✅ (completado y desplegado, 2026-07):** `app/perfil/page.tsx` reemplaza el placeholder — tarjeta "Resumen de hoy" (análisis, alertas nuevas, riesgo alto, % confirmadas), consumiendo `GET /api/v1/dashboard/resumen-ejecutivo`. Sin gráficas, sin tablas, sin filtros. Deliberadamente **sin** datos de la empresa (nombre, plan) — no existe todavía un endpoint que los expongan; se agrega cuando exista, no se inventa un valor fijo. El resto de `Perfil` (gestión de datos, preferencias, seguridad, suscripción) sigue como placeholder hasta Etapa 6. Verificado funcionando en producción.

**4.3 — Desktop completo:** diferido formalmente a Etapa 5, donde ya existía como ítem propio — no se implementa en Etapa 4 (ver ADR "una sola experiencia, múltiples presentaciones"). Consume `AggregationService` a través de los mismos endpoints de 4.1 — gráficas, tablas, filtros, exportación, drill-down viven ahí, no aquí.

---

## ✅ Etapa 5 — Presentation Expansion (antes "Desktop"): COMPLETA (2026-07)

**Objetivo:** desplegar en pantallas anchas lo que ya existe, no rediseñar. Ver `DECISION_LOG.md`, ADR "Desktop = Responsive Web" — es el mismo frontend Next.js respondiendo a breakpoints, no una aplicación separada (se descartó explícitamente Electron/Tauri).

**Corrección (2026-07):** esta sección decía *"No es adaptar la UI móvil. Es diseñar desde cero para pantallas grandes"* — eso contradecía el ADR "una sola experiencia, múltiples presentaciones". Es exactamente lo contrario: Desktop **sí es** la misma app móvil, aprovechando el espacio disponible para dejar de esconder detrás de divulgación progresiva lo que en móvil vive detrás de un botón expandible.

**Retirado de esta etapa (2026-07):** "Análisis de múltiples comprobantes simultáneos" (Batch Analysis) y "Workflow de aprobación/rechazo por operador" — ver ADR en `DECISION_LOG.md`. Ninguno de los dos es presentación; son capacidades de producto que, por el ADR de una sola experiencia, deberían existir también en móvil. Quedan sembrados como candidatos de una etapa funcional futura, sin número ni fecha — junto con colaboración, permisos y equipos.

**5.1 — Motor de Presentación ✅ (paso intermedio completado y desplegado, 2026-07):** se agrega `result["evidencias"]` en `main.py` — hechos crudos (`xml_valido`, `xml_discrepancias`, `confianza_documental`, `verificabilidad`, `contexto_temporal`, `hash_reutilizado`), sin interpretar todavía. Es el paso intermedio, no el objeto `presentation` completo — ese queda para cuando Desktop (5.3+) exista de verdad y se pueda diseñar `presentation` sabiendo qué necesita cada consumidor. De paso, se limpió un cast forzado (`as unknown as {...}`) en `DetalleExpandible.tsx` que accedía a `cep_xml.comparacion_campos.discrepancias` manualmente — la ruta resultó ser correcta (se verificó contra `cep_xml_service.py`), pero ahora usa `result.evidencias.xml_discrepancias` sin cast ni la precedencia de operadores confusa que tenía antes (`?? 0 > 0`). Verificado en producción: `/resultado` e `/historial/[id]` se ven idénticos a como estaban antes del cambio.

```json
{
  "presentation": {
    "integridad": { "nivel": "warning", "texto": "Con observaciones" },
    "spei": { "nivel": "success", "texto": "Liquidada" }
  }
}
```

Sin este motor, Mobile y Desktop terminarían con dos implementaciones distintas del mismo criterio de severidad, con alto riesgo de divergir silenciosamente. El objeto `presentation` completo (arriba) queda para cuando Desktop exista de verdad — `evidencias` es el paso de hoy.

**5.2 — Responsive Foundation ✅ (diseño completo, 2026-07, sin código todavía):** laboratorio de breakpoints completo — ver `LABORATORIO.md`. 4 rangos (Mobile <768px, Tablet 768-1199px, Desktop 1200-1599px, Wide Desktop ≥1600px), cada uno con ancho de contenedor y comportamiento definido para `/resultado`, `/historial` y `/perfil`. **Corrección (misma sesión):** el hallazgo original sobre una inconsistencia entre el ancho de `BottomNav` y el del contenido era incorrecto — `app/layout.tsx` ya envuelve el contenido en el mismo ancho máximo (480px). El trabajo real de 5.3 es hacer que ese ancho responda a los 4 rangos vía CSS, no corregir una inconsistencia que no existía. También queda decidida la conversión de `BottomNav` a barra lateral en Desktop/Wide Desktop.

**Decisión de estilos (2026-07):** ver `DECISION_LOG.md`, ADR "Tailwind permanece instalado pero no se adopta como sistema de estilos" — `globals.css` (que ya existía desde el scaffold del proyecto, con Tailwind instalado sin usar) se refuerza como **Design System incremental**: variables CSS que los componentes inline consumen vía `var(--token)`, empezando por `--vp-container-width` y `--vp-sidebar-width`. Spacing/radios/elevaciones no se tokenizan todavía — se hace progresivamente, no retroactivamente sobre componentes ya estables.

**5.3 — `/resultado` en pantalla ancha ✅ (completado y desplegado, 2026-07):** Resultado + Evidencias visibles simultáneamente (dos columnas), sin el botón "Ver detalles del análisis" — mismos componentes de `app/components/resultado/`, sin reimplementar. Sub-pasos:
- ✅ **Base del contenedor responsive** (desplegado y verificado).
- ✅ **Conversión de `NavigationShell` a barra lateral en Desktop/Wide Desktop** (desplegado y verificado).
- ✅ **Layout de 2 columnas en `/resultado`** (desplegado y verificado): `app/components/resultado/DetalleExpandible.tsx` con el prop `siempreAbierto`; `app/globals.css` con `.vp-resultado-grid` y `.vp-detalle-forzar-desktop`; `app/resultado/page.tsx` reestructurado. **Alcance deliberado: solo `/resultado`** — `historial/[id]/page.tsx` no se toca, su tratamiento en Desktop se decide en 5.4.

**Dos bugs reales encontrados y corregidos durante el despliegue de este ítem** (ambos por el mismo patrón: un estilo inline nunca cede ante una clase CSS sin `!important`):
1. `app/layout.tsx` quedó desplegado con el import viejo (`BottomNav` en vez de `NavigationShell`) de una sesión anterior — rompía el build por completo (`module-not-found`). Corregido reemplazando el archivo.
2. La regla que debía **ocultar** el botón de toggle en Desktop (`.vp-detalle-forzar-desktop .vp-detalle-toggle-btn { display: none; }`) le faltaba `!important` — el botón tiene `display: "flex"` inline (para centrar su contenido), así que la regla sin `!important` nunca podía ganarle. Se corrigió agregando `!important`, igual que ya se había hecho correctamente para la regla que fuerza visible el contenido.
- ⏳ Layout de 2 columnas en `/resultado` (Resultado + Evidencias simultáneas) — pendiente.

**5.4 — `/historial` en pantalla ancha ✅ (completado y desplegado, 2026-07):** patrón maestro-detalle — lista y detalle simultáneos, sin navegar a `/historial/[id]` como ruta separada. Primera vez en Etapa 5 que se necesita detectar el ancho de pantalla en JS (no solo CSS): navegar de ruta vs. seleccionar inline es una decisión de *comportamiento*, no de estilo. La decisión se toma **dentro del clic** (`window.matchMedia`), nunca durante el renderizado — evita cualquier riesgo de mismatch de hidratación de Next.js, porque el HTML inicial es idéntico en servidor y cliente.

Se extrajo `app/components/historial/HistorialDetalleContenido.tsx` (nuevo) — todo el cuerpo visual que antes vivía completo dentro de `historial/[id]/page.tsx` (badge, ficha de auditoría, `SemaforoSpei`, `QueSignificaEsto`, `DetalleExpandible`, botones, nota de privacidad), parametrizado por `onVolver`/`onVerValidaciones` porque su comportamiento difiere entre los 2 consumidores. `historial/[id]/page.tsx` quedó mucho más corto — solo hace el fetch y usa el componente compartido; sigue existiendo tal cual para Mobile/Tablet. `app/historial/page.tsx` agrega estado de selección (`idSeleccionado`, `detalleSeleccionado`) y la columna derecha, oculta por completo en Mobile/Tablet vía `.vp-historial-detalle-panel` (no solo por no setearse el estado — se oculta explícitamente, para no depender de esa coincidencia). Verificado en producción: móvil sin cambios, selección múltiple funcionando en escritorio, "Ver validaciones completas" funcionando desde el panel inline.

**Descongelada (2026-07):** con el KPI principal, la jerarquía de decisión, el modelo de 3 niveles, y el wireframe conceptual ya resueltos (ver `DECISION_LOG.md` y `DESIGN_SYSTEM.md` sección 10), se retoma el desarrollo de código. Ver progreso del backend abajo.

**5.5 — ✅ COMPLETA (2026-07) — KPI principal, modelo de datos, backend y frontend:** ver `DECISION_LOG.md`, ADR "se congela 5.5". **Resuelto:** hero stat = monto total procesado; secundarios = volumen, % liquidados, alertas críticas. Historia de negocio primero, historia de control después. Cadencia objetivo: varias veces al día — `AggregationService` on-demand es suficiente, no requiere WebSockets. **Modelo de 3 niveles de datos** (Nivel A: Motor de Verdad, sin captura de la empresa — es el corazón del Centro Operativo; Nivel B: datos enriquecidos opcionales — sucursales, clientes, % de cobros por otros canales; Nivel C: integraciones ERP/POS, etapa aparte). **Principio de diseño permanente:** cada dato debe responder una pregunta de negocio o provocar una acción — si un widget no cambia ninguna decisión, no pertenece al Dashboard. **Corrección de factibilidad:** "banco con más incidencias" y comparaciones contra periodo anterior ("+23% vs. ayer") sí son construibles con `AggregationService` + agregaciones nuevas pequeñas sobre datos existentes (`Alerta.analisis_origen` ya permite cruzar alertas con banco) — no requieren dato nuevo. Solo "tiempo de liberación" sigue bloqueado por el gap ya conocido de 4.1 (columna `duracion_ms` no construida). **Todavía sin resolver:** qué decisiones exactas toma el director sin abrir un comprobante individual, y el diseño visual concreto (`DESIGN_SYSTEM.md` + wireframes) — **wireframe conceptual de V1 ya escrito** (`DESIGN_SYSTEM.md`, sección 10: estado 🟢/🟠/🔴, hero stat, "qué requiere atención", "tendencias" — solo Nivel A, sin Nivel 4/estratégico todavía). Pendiente: destinos exactos de cada botón de acción (¿navega con filtro preaplicado, o abre panel lateral?), depende de cómo termine 5.4.

**Backend ✅ (completado y desplegado, verificado en producción, 2026-07):** `services/aggregation_service.py` — 3 agregaciones nuevas (`calcular_banco_mayor_incidencia`, `calcular_comparacion_volumen`, `calcular_comparacion_alertas`), ninguna requiere dato nuevo, todas cruzan relaciones/columnas que ya existen. `services/dashboard_service.py` — `obtener_centro_operativo()`, bundle completo calcado del wireframe de `DESIGN_SYSTEM.md` sección 10. `main.py` — endpoint `GET /api/v1/dashboard/centro-operativo`. Fix real encontrado en la primera prueba: `banco_mayor_incidencia` filtraba por la fecha del análisis en vez de la fecha de la alerta, escondiendo riesgo activo acumulado en días sin análisis nuevos — corregido, verificado con datos reales.

**Frontend ✅ (completado, desplegado y verificado en producción, 2026-07):** `app/components/perfil/CentroOperativo.tsx` (puramente presentacional, recibe `datos` por prop) — estructura calcada del wireframe de `DESIGN_SYSTEM.md` sección 10 (estado 🟢/🟠/🔴, hero stat, "qué requiere atención", "tendencias"; ningún bloque aparece si no hay nada real que decir). `app/perfil/page.tsx` hace **una sola llamada** a `/centro-operativo` y reparte el mismo objeto a ambas presentaciones vía `.vp-mobile-only`/`.vp-desktop-only` — ver `DECISION_LOG.md`, ADR "una sola llamada al backend para Mobile y Desktop" (corrección de arquitectura hecha antes de desplegar). Botones de acción navegan a `/alertas` o `/historial` (sin filtro preaplicado todavía — mejora futura, no bloqueante). Verificado: móvil sin cambios, Centro Operativo completo en escritorio, una sola petición de red confirmada.

**Con esto, 5.5 queda completa — Etapa 5 (Presentation Expansion) completa: 5.1 ✅ 5.2 ✅ 5.3 ✅ 5.4 ✅ 5.5 ✅.**

---

## Etapa 6 — Seguridad e infraestructura para escala

**Objetivo:** hacer el sistema seguro y capaz de crecer a usuarios reales. Se mueve al final de la secuencia deliberadamente — ver `DECISION_LOG.md` — porque buena parte de esta superficie cambiará de forma conforme se definan Historial, Alertas y Dashboard.

**Reorganizada en capas (2026-07)** — ver `DECISION_LOG.md`, ADR "Etapa 6 reorganizada en capas; se siembra el Identity Engine". Cada capa responde una pregunta distinta, en el orden en que hace falta responderla — ya no es una lista plana de ítems sueltos.

**Nota (2026-07):** "eliminación automática de imágenes tras el análisis" ya está, en la práctica, satisfecho por diseño desde Etapa 2 — el sistema nunca persiste la imagen del comprobante en disco, se procesa en memoria y se descarta (ver `historial/[id]/page.tsx`, nota de privacidad). Este ítem se conserva en 6.1 como verificación pendiente (confirmar que ningún mecanismo interno de FastAPI/Starlette esté dejando archivos temporales sin limpiar), no como funcionalidad por construir desde cero.

### 6.1 — Hardening

Todo lo que mejora la seguridad sin cambiar el comportamiento del producto. Sin dependencias entre sí, se puede desplegar en cualquier momento.

- CORS restringido — hoy `allow_origins=["*"]` en `main.py`; restringir a los dominios reales antes de producción con empresas externas
- Headers de seguridad (HSTS, X-Frame-Options, CSP, etc.)
- Logging estructurado — hoy los errores se registran con `print(...)`, migrar a `logging` estándar + agregación de logs
- Confirmar política de backups de Supabase — no verificado explícitamente hasta ahora
- Verificar eliminación de imágenes (ver nota arriba)
- Auditoría de variables de entorno y secretos (nada hardcodeado, gestión correcta)
- **Rate limiting por IP** — no requiere identidad, solo la dirección de origen
- **Registro de eventos de seguridad sin identidad** (intentos de login fallidos, rate limiting activado, errores 500) — distinto de la auditoría de acciones de 6.3, esto no requiere saber "quién", solo "qué pasó"

### 6.2 — Identity Layer

Deliberadamente nombrada "Identity Layer" y no "login" — sirve a futuro para Portal Web, API, app móvil e integraciones, no solo para un formulario de inicio de sesión. Es la capa de la que dependen casi todas las demás.

- JWT con `empresa_id` y `usuario_id`
- Invitación de usuarios
- Recuperación de contraseña
- Sesiones
- Refresh tokens
- **Identity Engine** (sembrado, ver `DECISION_LOG.md`): quinto motor transversal del sistema, junto a Motor SPEI, Motor Documental, Alert Engine y `AggregationService`. Se diseña aquí, no antes.

### 6.3 — Access Control Layer

Depende de 6.2 — una vez que sabemos quién eres, qué puedes hacer.

- Roles y permisos, RBAC
- **Rate limiting por cuenta** — distinto del rate limiting por IP de 6.1, este sí requiere saber a qué cuenta pertenece la petición
- API Keys por empresa para integración B2B
- **Auditoría de acciones real** ("qué usuario hizo qué, cuándo") — distinta del registro de eventos de seguridad de 6.1, esta sí requiere identidad

### 6.4 — Data Protection

Todo lo relacionado con proteger la información que entra al sistema. Independiente de 6.2/6.3, se puede hacer en paralelo.

- Sanitización de inputs
- Validación de tipos de archivo más estricta
- **Límite de tamaño de subida y protección contra uploads maliciosos** (hallazgo de la Architecture Readiness Review, sin conectar a un ítem concreto hasta esta reorganización)
- Antivirus (sembrado, sin fecha)
- Encriptación donde aplique

### 6.5 — Scale Layer

Requiere decisiones de proveedor de infraestructura, mayor esfuerzo que las capas anteriores. Hallazgos de la Architecture Readiness Review.

- **Cola de trabajos para consultas a Banxico** — hoy la descarga del XML/CEP es síncrona dentro de `/analizar`; a volumen alto, Banxico se vuelve el cuello de botella. Requiere cola (RabbitMQ/Redis Queue) + workers
- **Cache y métricas distribuidas** — `cache_service.py` y `metrics_service.py` viven en memoria del proceso; si Render corre más de una instancia, cada una tiene su propio estado. Migrar a Redis sin cambiar la interfaz de cada servicio
- Procesamiento asíncrono en general

### 6.6 — Business Readiness

Sin código — es un ejercicio de producto/finanzas, independiente de todo lo anterior, puede correr en paralelo con cualquier capa.

- **Modelo de costo unitario** — cada análisis cuesta una llamada a Claude Vision; modelar el costo antes de definir planes B2B por volumen
- Margen, pricing
- Consumo de Claude/Banxico, proyección financiera

**Diferido, sin fecha:** OAuth, observabilidad tipo SIEM, políticas de retención avanzada de logs — sin urgencia real hoy, sembrados desde la Architecture Readiness Review.

---

## Etapa 7 — Organización Empresarial

**Objetivo (redefinido 2026-07, ver `DECISION_LOG.md`):** ya no es "autenticación" — eso se fusionó en Etapa 6.2. Etapa 7 responde "¿cómo administras una empresa completa?", una pregunta distinta a "¿quién eres?" (Etapa 6), y no tiene sentido sin que 6.2 exista primero.

- Sucursales y departamentos
- Permisos avanzados y equipos
- Créditos y licencias
- Facturación por créditos o por volumen
- Consumo y administración empresarial
- Aislamiento de datos entre empresas (el `UNIQUE(empresa_id, hash_sha256)` ya existe en el esquema)

---

---

---

## Vigilancia a futuro (sin fecha, sin compromiso — revisar en cada Architecture Review)

Ninguno de estos 5 puntos requiere código hoy. Se sembraron en la revisión de escalabilidad posterior a Etapa 4 para no reinventarlos cuando aparezcan — cada uno se activa cuando la señal de negocio lo justifique, no antes.

- **Costo por análisis.** Hoy es el riesgo #1 de crecimiento (más que infraestructura): cada análisis implica OCR + Claude Vision + Banxico + XML + comparaciones + Alert Engine + persistencia, y cada paso tiene costo. Necesita un indicador de costo unitario antes de Beta — ver también Etapa 6, "Modelo de costo unitario".
- **Telemetría de negocio**, distinta de las métricas técnicas que ya existen (`metrics_service.py`: duración/éxito de XML/CEP/análisis). Candidatos: costo promedio por análisis, análisis abandonados, empresas activas, alertas falsas vs. confirmadas, consultas CEP fallidas.
- **Feature Flags.** No hacen falta todavía (una sola empresa activa hoy), pero se anticipan necesarios en cuanto existan varias empresas con necesidades distintas — para no terminar con lógica condicional por cliente repartida por el código.
- **Versionado de reglas del Alert Engine.** Si una regla de `alert_engine/` cambia sus umbrales o su lógica en el futuro, las alertas ya generadas quedan sin forma de saber con qué versión de la regla se generaron — dificultando reconstruir por qué se disparó una alerta antigua. Posible solución futura: registrar la versión de la regla en el `metadata` JSONB de cada alerta (la columna ya existe y está diseñada para esto, ver `DECISION_LOG.md`).
- **Abstracción del proveedor de IA de visión.** Hoy el análisis documental depende directamente de Claude Vision (`anthropic` SDK, llamado directo desde `main.py`). No se abstrae ahora, pero vale la pena tenerlo en mente si algún día conviene poder cambiar de proveedor sin tocar el resto del sistema.

## Etapa futura (sembrada, sin número ni fecha) — Capacidades avanzadas de operación

Retirada de Etapa 5 en 2026-07 (ver `DECISION_LOG.md`) porque ninguno de estos ítems es presentación — son capacidades de producto que, por el ADR de una sola experiencia, deben existir también en móvil, no solo en Desktop:
- Análisis de múltiples comprobantes simultáneos (Batch Analysis)
- Workflow de aprobación/rechazo por operador
- Colaboración entre usuarios de la misma empresa
- Permisos y equipos
- Aprobaciones multinivel
- **Reglas de detección de velocidad/anomalía** (sembrado 2026-07, surgido de la sesión de Centro Operativo): misma CLABE recibiendo múltiples pagos en poco tiempo más allá del umbral ya cubierto por `CLABE_FRECUENTE`, montos atípicos respecto al historial de una cuenta específica (ej. una cuenta que nunca superó $20,000 recibe $180,000). Son reglas nuevas del Alert Engine, no presentación — si son valiosas, alimentan Alertas en móvil también, no exclusivas del Centro Operativo de escritorio.

No tiene número de etapa todavía — se abre cuando el producto lo necesite, probablemente después de Etapa 7 (Multiempresa real), ya que varias de estas capacidades (permisos, equipos) dependen de que exista autenticación multiempresa real.

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