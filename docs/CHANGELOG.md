# CHANGELOG.md — Historial de versiones

**Versión del documento:** 0.11.0 · **Última actualización:** 02/07/2026

Formato: `[versión] — fecha — descripción`. Las versiones siguen Semantic Versioning: MAJOR.MINOR.PATCH.

---

## [0.12.1] — 2026-07 — Código: flujo de decisión desplegado; fix de falso positivo BBVA (monto negativo)

### Desplegado en producción
- `app/resultado/page.tsx` y `app/resultado/mensajesContextuales.ts` (nuevo): implementación del flujo de decisión de 6 pasos (Impacto y Recomendación inmediata) sobre el catálogo de 1.2. Confirmado desplegado y funcionando en Vercel.

### Corregido (confirmado en producción)
- `main.py`, `build_system_prompt()`: falso positivo — BBVA muestra el monto con signo negativo en egresos (ej. `-$40.00`) como convención visual, no como alteración. El `system_prompt` no distinguía este caso y lo marcaba como "Monto negativo" (severidad alta). Se corrigió en tres puntos del prompt: regla de formatos válidos, regla de riesgo, e instrucción de extracción del campo `monto` (siempre en valor absoluto). Desplegado en Render y verificado contra el comprobante que originó el hallazgo. Ver `LABORATORIO.md`.

### Observado (para Sprint A-Final, sin resolver todavía)
- La pantalla `/resultado` en producción resultó saturada: integridad documental, reutilización del documento y el flujo de decisión compiten por atención con el mismo peso visual. Pendiente de rediseño de jerarquía (divulgación progresiva) — ver conversación en curso, aún sin decisión final registrada.

---

## [0.12.0] — 2026-07 — ADR: se formaliza la capa de Recomendación; catálogo final de los 9 mensajes contextuales

### Cambiado (arquitectura del modelo — MINOR por ser cambio de modelo, no patch)
- `MODELO_DECISION_EXPLICABLE.md`: el modelo pasa de 4 a 5 capas — se separa **Impacto** ("¿qué implica esto para mí?", siempre presente) de **Recomendación** ("¿qué hago ahora?", capa opcional). Estructura de presentación actualizada de 5 a 6 pasos (se agrega ④ Recomendación inmediata). Principios del modelo reescritos, incorporando explícitamente "nunca inducir al usuario a una acción cuando la evidencia todavía no lo permite".
- `DECISION_LOG.md`: registrado como 🏛️ `#ADR-VP` — motivo, impacto en el resto del producto (Historial, Dashboard, Alertas, Desktop, API Enterprise) y documentos afectados.

### Completado (texto, pendiente de código)
- `ROADMAP.md`, ítem 1.2: catálogo final de los 9 mensajes contextuales, con wording revisado (más precisos en `acreditada`, `liquidada`, `en_proceso`, `devuelta`, `no_liquidada`, `desconocida`) y el campo "Recomendación inmediata" agregado donde aplica (`en_proceso`, `devuelta`, `en_devolucion`, `desconocida`).
- `ROADMAP.md`, ítem 1.4: el diseño de texto queda completo; lo pendiente se reduce exclusivamente a la implementación en `resultado/page.tsx`.

---

## [0.11.2] — 2026-07 — Refinamiento: flujo de decisión de 5 pasos para 1.4

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: el componente "¿Cómo se llegó a este resultado?" se rediseña como flujo conversacional de 5 pasos (Resultado → Interpretación → Impacto → Evidencias → Detalle), en vez de una lista de datos que responde 4 preguntas.
- `MODELO_DECISION_EXPLICABLE.md`: sección "Estructura fija de presentación" actualizada, reconciliando el flujo de 5 pasos con el modelo de 4 capas — el flujo es la forma de presentación del modelo, no un modelo distinto.
- `ROADMAP.md`: ítem 1.4 actualizado con el flujo de 5 pasos; se agrega el diagrama de secuencia completo del Sprint A-Final (1.1 → 1.4 → 1.2 → 1.3 → 1.5 → 1.6 → MVP Beta cerrado); ejemplo de mensaje contextual (1.2) redactado siguiendo el flujo completo.

---

## [0.11.1] — 2026-07 — Se declara concluida la Fase de Fundación

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: ADR de cierre de la Fase de Fundación de VerificaPago — arquitectura, visión, modelo de decisión, gobernanza documental y roadmap alcanzan estabilidad suficiente para priorizar funcionalidades sobre redefinir bases.
- `DECISION_LOG.md`: se adopta el hábito "No romper la arquitectura" — cuatro preguntas antes de desarrollar cualquier idea nueva (¿ya existe algo que lo resuelva? ¿pertenece a un documento existente? ¿rompe algún ADR? ¿afecta el Modelo de Decisión Explicable?).
- `DECISION_LOG.md`: se anota, sin adoptarla todavía formalmente en `PRODUCT.md`/`PRODUCT_VISION.md`, la definición emergente de VerificaPago como "motor de confianza para pagos por transferencia" — pendiente de decisión explícita.

---

## [0.11.0] — 2026-07 — Consolidación documental: README, versionado, referencias cruzadas y congelamiento de estructura

### Agregado
- `README.md`: índice maestro de `/docs` — estructura por categorías (Producto, Arquitectura, Decisiones, Evolución, Laboratorio), orden recomendado de lectura, tabla de convenciones de captura (incluye el marcador reservado 🎯 `#PDR-VP`, no activo todavía), y la política de versionado documental.

### Cambiado
- Los 12 documentos de `/docs` ahora incluyen un encabezado de versión (`Versión del documento` / `Última actualización`) y una sección final "Documentos relacionados" con referencias cruzadas explícitas — la documentación pasa de ser archivos aislados a una red navegable.

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: principio de gobernanza documental — una única fuente de verdad por pieza de conocimiento; las decisiones referencian investigaciones sin duplicarlas.
- `DECISION_LOG.md`: estructura documental congelada — no se crean documentos nuevos salvo dominio propio y reutilizable. Se posponen explícitamente `PRINCIPIOS_DE_PRODUCTO.md`, `BETA_PLAN.md`, `SEGURIDAD.md`, `HISTORIAL.md` hasta que exista superficie real.
- Se anota, sin activar, un cuarto marcador de captura reservado: 🎯 `#PDR-VP` (Product Decision Record).

Esta versión marca el cierre de la ronda de trabajo dedicada a `/docs` — de aquí en adelante, la documentación se actualiza solo ante eventos concretos (módulo nuevo, cambio de arquitectura, decisión importante, investigación relevante), no como tarea de expansión activa.

---

## [0.10.2] — 2026-07 — Tercer nivel de captura: LABORATORIO.md y #LAB-VP

### Agregado
- `LABORATORIO.md`: nuevo documento para investigaciones y hallazgos experimentales que todavía no son (o nunca llegan a ser) una decisión oficial — experimentos con Banxico, investigación de certificados, pruebas con IA, benchmarks, ideas descartadas. Se retroalimentó con la investigación criptográfica del sello digital del XML (ya documentada en `XML_CEP.md`), como primer ejemplo del formato.

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: sección de convenciones ampliada a tres marcadores — 📘 `#DOC-VP` (documentación rutinaria), 🏛️ `#ADR-VP` (decisión arquitectónica), 🧪 `#LAB-VP` (investigación/hallazgo experimental, vive en `LABORATORIO.md`).
- Regla de frontera entre ambos documentos: si una investigación termina en un cambio real al sistema, la decisión vive en `DECISION_LOG.md` y referencia la entrada experimental en `LABORATORIO.md` — no se duplica el detalle técnico entre ambos.

---

## [0.10.1] — 2026-07 — Convención #ADR-VP y documento futuro PRINCIPIOS_DE_PRODUCTO.md

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: nueva sección de convenciones al inicio del documento — se adopta `#ADR-VP` (Architecture Decision Record) como marcador complementario a `#DOC-VP`, exclusivo para decisiones que cambian la arquitectura del sistema. Formato sugerido: Decisión / Motivo / Impacto / Documentos afectados.
- `MODELO_DECISION_EXPLICABLE.md`: sección práctica ampliada con las cuatro preguntas de diagnóstico para evaluar ideas nuevas antes de implementarlas (¿aporta hecho o interpreta?, ¿modifica recomendación o solo agrega evidencia?, ¿rompe algún principio?, ¿necesita documento nuevo o pertenece a uno existente?).
- `ROADMAP.md`: se anota `PRINCIPIOS_DE_PRODUCTO.md` como documento futuro pendiente — reglas innegociables de producto, formato "constitución" corta (1-2 páginas). Deliberadamente pospuesto hasta la entrada a Beta.

---

## [0.10.0] — 2026-07 — Nuevo documento fundacional: Modelo de decisión explicable

### Agregado
- `MODELO_DECISION_EXPLICABLE.md`: documento de arquitectura de producto que formaliza cómo "piensa" VerificaPago — el modelo de 4 capas (Hechos → Interpretación → Recomendación → Evidencia) y la estructura de presentación fija (Resultado → Recomendación → ¿Cómo se llegó a este resultado? → Ver detalles), aplicable a cualquier pantalla o cliente presente y futuro.

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: decisión de formalizar el modelo, con sus 5 principios (toda conclusión deriva de hechos verificables; hechos independientes de interpretaciones; recomendaciones derivan de interpretaciones; toda recomendación es trazable a evidencias; la interfaz nunca muestra una conclusión sin explicar cómo se obtuvo).
- `ROADMAP.md`: la sesión de diseño pendiente del ítem 1.4 se reformula como las 4 preguntas del modelo (qué hechos conoce, qué interpreta, qué recomienda, qué evidencia respalda la recomendación), no como diseño de pantalla.

Sube a versión MINOR (`0.9.x` → `0.10.0`) en vez de PATCH porque agrega un documento de arquitectura de producto — un hito estructural, no un ajuste incremental sobre trabajo ya registrado.

---

## [0.9.6] — 2026-07 — "Evidencia de la decisión" se renombra a "¿Cómo se llegó a este resultado?"; se fija estructura y orden de trabajo

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: renombre final del patrón (habla el idioma del usuario, no del ingeniero), estructura de referencia legible en ~5 segundos, y la regla de producto "toda conclusión debe poder justificarse con al menos una evidencia verificable".
- `DECISION_LOG.md`: se fija el orden de trabajo del Sprint A-Final — el componente (1.4) se diseña antes que los mensajes contextuales (1.2), porque el copy depende de la estructura que lo contiene. 1.3 se mantiene independiente y puede avanzar en paralelo.
- `DECISION_LOG.md`: se anota la forma de datos objetivo (`evidencias: [{tipo, resultado}]`) como preparación de diseño para el futuro Motor de Presentación — no implementada todavía.
- `PRODUCT_VISION.md` y `ROADMAP.md`: nombre del patrón actualizado en el principio de Explicabilidad y en el ítem 1.4 respectivamente.

---

## [0.9.5] — 2026-07 — "Centro de Estado" evoluciona a "Evidencia de la decisión"

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: el ítem 1.4 de la Etapa 1 deja de ser una pantalla ("Centro de Estado") y pasa a ser un patrón visual reutilizable ("Evidencia de la decisión") que acompaña cada conclusión (estado SPEI, integridad documental, nivel de evidencia) con su fuente explícita.
- `PRODUCT_VISION.md`: el principio de Explicabilidad se amplía para nombrar explícitamente este patrón como la materialización concreta de "VerificaPago nunca dice créeme, dice aquí está por qué".
- `ROADMAP.md`: Etapa 1 se renombra internamente como **Sprint A-Final**, con objetivo explícito ("que cualquier persona entienda el resultado en menos de 10 segundos"). Los ítems 1.2 y 1.3 se mantienen pendientes pero con criterio de cierre más preciso (1.2 debe responder "¿entrego o no?"; 1.3 es trabajo de frontend puro, el backend ya expone los datos). 1.4 se redefine como patrón, no pantalla.

---

## [0.9.4] — 2026-07 — Estado de Etapa 1 confirmado contra código real

### Documentado (sin cambios de código)
- `ROADMAP.md`: 1.1 (Estado SPEI protagonista + integridad separada) confirmado como completado, verificado contra `app/resultado/page.tsx`.
- `ROADMAP.md`: 1.3 (Detalle XML en la UI) reclasificado de "pendiente" a "parcialmente construido — no cumple el criterio original". `app/resultado/detalle/page.tsx` ya agrupa validaciones por categoría en acordeones, pero no desglosa `cep_xml.comparacion_campos` campo por campo como pide el criterio original.
- `ROADMAP.md`: 1.2 (mensajes contextuales por estado) y 1.4 (Centro de Estado) confirmados como no iniciados — sin código compartido que los implemente.

---

## [0.9.3] — 2026-07 — Roadmap reestructurado en Etapas secuenciales

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: decisión de cerrar funcionalmente el MVP Beta (Etapa 1) antes de iniciar desarrollos de escalabilidad — Dashboard, Alertas, Desktop y Seguridad se reordenan como consecuencia.
- `ROADMAP.md`: reestructurado de Sprints A-E (etiquetado plano) a una secuencia de Etapas 1-7: Cierre del MVP Beta → Historial real → Alertas inteligentes → Dashboard Empresa → Desktop (incluye Motor de Presentación) → Seguridad → Multiempresa real. Ningún contenido técnico de los Sprints anteriores se eliminó, solo se reubicó.
- `ROADMAP.md`: Seguridad (antes Sprint B, la segunda prioridad) pasa a Etapa 6, al final de la secuencia — ver justificación en `DECISION_LOG.md`.
- Se anota `BETA_PLAN.md` como documento de producto pendiente de redactar (objetivos del beta, KPIs, criterios de salida), sin crear el archivo todavía.
- Los ítems de la Etapa 1 (1.1 Estado SPEI protagonista + integridad separada) se marcan como "reportado como cerrado, pendiente confirmar" — no se dan por completados en la documentación hasta verificar contra el código en producción.

---

## [0.9.2] — 2026-07 — Decisión de arquitectura: lógica de presentación queda en frontend hasta el segundo consumidor

### Documentado (sin cambios de código)
- `DECISION_LOG.md`: regla de arquitectura — la lógica de presentación (colores, iconos, severidad) migra al backend solo cuando exista más de un consumidor real. Hoy permanece en el frontend para no acoplar la iteración visual al ciclo de release del backend.
- `DECISION_LOG.md`: se define el paso intermedio `evidencias` (hechos crudos que el backend expondrá) como preparación para el futuro objeto `presentation`, sin crear todavía un campo de severidad pre-interpretado como `severidad_integridad`.
- `ROADMAP.md`: Sprint C ahora incluye explícitamente el hito **Motor de Presentación** (C.1), no solo la UI de escritorio — es el punto en que Desktop se vuelve el segundo consumidor del backend y dispara la regla anterior.

---

## [0.9.1] — 2026-07 — Refinamiento del semáforo de integridad en /resultado

### Agregado
- `PRODUCT_VISION.md`: documento de visión estratégica (modelo de negocio, roadmap a 3 años, métricas), separado de `PRODUCT.md` (definición técnica del producto)

### Cambiado
- `app/resultado/page.tsx`: el color del indicador de integridad documental ya no viene 1:1 de `integridad_config.color`. El rojo se reserva para evidencia acumulada fuerte (`confianza_documental < 30` o discrepancia en el XML); el resto de los casos de riesgo se muestran en ámbar, para evitar que el usuario lea "🟢 Liquidada + 🔴 Posible alteración" como una contradicción. Ver `DECISION_LOG.md`.
- Subtexto explicativo bajo el indicador de integridad ajustado para ser consistente con el nuevo criterio de color.

---

## [0.9.0] — 2026-07 — Documentación fundacional y Sprint A en curso

### Agregado
- Carpeta `/docs` con documentación fundacional: PRODUCT, ARQUITECTURA, MOTOR_DECISIONES, XML_CEP, SCORING, ROADMAP, DECISION_LOG, API, CHANGELOG

### En progreso (Sprint A)
- Mensajes contextuales por estado SPEI en la UI
- Reintentos con backoff en la descarga automática del XML
- Métricas de observabilidad del motor

---

## [0.8.0] — 2026-06 — 2 motores independientes + descarga automática de XML

### Agregado
- **Motor 1 (Estado SPEI):** campo `estado_operacion` con jerarquía de evidencia: XML oficial > CEP HTML > no disponible. Nuevos campos: `fuente_estado`, `nivel_evidencia`, `semaforo_spei`.
- **Motor 2 (Integridad documental):** campo `integridad_comprobante` con 3 estados: `sin_observaciones` / `con_observaciones` / `posible_alteracion`. Nuevo campo `integridad_config`.
- **Descarga automática del XML del CEP:** el sistema consulta `banxico.org.mx/cep/valida.do` y descarga el XML oficial sin intervención del usuario, cuando dispone de clave de rastreo, bancos, cuenta y monto extraídos del comprobante.
- **Comparación XML vs. comprobante:** campo a campo (monto, clave de rastreo, banco destino, últimos dígitos de cuenta). Las discrepancias se reportan como validación `fail` explícita.
- Catálogo de bancos externalizado a `catalogo_bancos.json` (actualizable sin deploy)
- Trazabilidad HTTP: cada petición a Banxico registra URL, método, status, tiempo, headers y cookies

### Cambiado
- Los parámetros del flujo CEP (`tipoCriterio`, señales de éxito, timeouts) ahora viven en `catalogo_bancos.json`, no hardcodeados
- La detección de éxito de `valida.do` usa capas (Content-Type + URL final + señales configurables) en vez de un string de clase CSS frágil
- Comentarios del código reemplazados de "confirmado experimentalmente" a lenguaje neutral: "comportamiento observado al momento de implementar este módulo"

### Investigado y documentado (no implementado por limitaciones técnicas)
- Validación criptográfica local del XML: prueba RSA pura `sello^e mod n` no produjo padding reconocible. La IES privada de Banxico/SPEI no es pública. Ver `DECISION_LOG.md`.

---

## [0.7.0] — 2026-06 — Flujo móvil multipantalla + semáforo categórico

### Agregado
- 6 pantallas navegables con App Router de Next.js: upload → analizando → resultado → detalle → comprobante
- Bottom navigation fija (Inicio, Historial, Alertas, Perfil)
- `AnalisisContext` para compartir el estado del análisis entre pantallas sin localStorage
- Semáforo categórico en `/resultado`: Verificado / Consistente / Revisar / Riesgo alto — derivado por reglas, no por fórmula
- Diagnóstico en prosa colapsable (reemplaza al veredicto numérico único como protagonista)
- Soporte para upload opcional del XML del CEP (comparación manual de campos)
- Fix: clamping del score a [0, 100] — se detectó un score de 101.5 en producción

### Cambiado
- `page.tsx` migrado de una sola página larga (con todos los estados) a rutas separadas

---

## [0.6.0] — 2026-06 — Scoring v3: 4 dimensiones separadas

### Agregado
- `scoring_v3.py`: módulo separado con 4 dimensiones independientes
- `confianza_documental` (0-100): inverso del claude_score de riesgo visual
- `verificabilidad` (0-100): qué tan corroborable es la operación externamente
- `contexto_temporal` (0-100): ancla Circular 14/2017 art.19a (30s/5s de Banxico)
- `estado_operacion` (categórico): mapeado a los 8 estados reales de SPEI
- `interpretacion`: texto en prosa que explica las 4 dimensiones sin fusionarlas en un número
- Regla temporal: penalización de verificabilidad solo cuando `estado_operacion = desconocida`

### Principio de diseño formalizado
- "Ausencia de evidencia ≠ evidencia de fraude" — la verificabilidad baja no infla el score de riesgo
- Los 4 scores son independientes y no se promedian entre sí

---

## [0.5.0] — 2026-06 — Backend multiempresa + dashboard

### Agregado
- Esquema multiempresa: tablas `empresas`, `usuarios`, `analisis`, `hashes_documentos`
- `UNIQUE(empresa_id, hash_sha256)` para aislamiento por empresa
- `DEFAULT_EMPRESA_ID` mientras no existe autenticación multiempresa real
- Endpoints de dashboard: `/api/v1/dashboard/stats`, `/analisis`, `/analisis/{id}`, `/hashes`, `/tendencia`
- Columnas desnormalizadas en `analisis`: `banco_detectado`, `monto_detectado`, `clabe_detectada` para filtros rápidos sin abrir el JSONB
- `services/dashboard_service.py` con todos los queries del dashboard
- Migración Alembic inicial: `ade15461db9e_esquema_multiempresa_inicial.py`

### Cambiado
- `database.py` ahora exporta `DEFAULT_EMPRESA_ID`
- `hash_service.py` y `auditoria_service.py` actualizados para recibir `empresa_id`
- Comando de start en Render: `alembic upgrade head && uvicorn main:app...`

---

## [0.4.0] — 2026-06 — CEP Banxico + descarga de XML automática (investigación)

### Agregado
- Integración con `banxico.org.mx/cep/`: scraping del CEP para verificar estado SPEI
- `verify_cep()`: consulta asíncrona con httpx, manejo de timeout y errores
- Tres estados de CEP: `EXISTE` (monto coincide) / `PARCIAL` (encontrado, monto sin confirmar) / `NO_EXISTE`
- `cep_xml_service.py`: parseo del XML del CEP y comparación de campos

### Investigado
- Flujo completo del portal `banxico.org.mx/cep/` capturado con DevTools
- Descubrimiento: el campo `captcha` en `valida.do` no se valida del lado del servidor
- Hallazgo: la descarga del XML requiere cuenta beneficiaria + monto (no solo clave de rastreo + fecha)

---

## [0.3.0] — 2026-05 — Hash SHA-256 + auditoría

### Agregado
- `hash_service.py`: SHA-256 del comprobante antes del análisis, detección de reutilización
- `auditoria_service.py`: persistencia del análisis completo en base de datos
- `hash_documento.py`: modelo SQLAlchemy con `UNIQUE(empresa_id, hash_sha256)`
- Respuesta incluye `hash_documento`, `veces_visto`, `documento_reutilizado`, `audit_id`

### Seguridad
- Incidente de exposición accidental de credenciales en git — resuelto con `git filter-repo` y rotación de API keys

---

## [0.2.0] — 2026-05 — Validación de CLABE + IAT

### Agregado
- Validación de checksum de CLABE (algoritmo oficial con ponderadores CNBV)
- Identificación de banco emisor desde CLABE
- Motor IAT (Índice de Autenticidad Transaccional): análisis estadístico de entropía, longitud de campos, secuencias anómalas
- Fusión de scores: `0.7 * claude_score + 0.3 * iat_score`

---

## [0.1.0] — 2026-04 — MVP inicial

### Agregado
- Upload de comprobante (PNG, JPG, PDF)
- OCR con Claude Vision API (claude-sonnet-4-5)
- Extracción de campos: banco, monto, fecha, hora, clave de rastreo, referencia, folio, CLABE, concepto
- Score de riesgo visual (0-100)
- Frontend Next.js con una sola pantalla
- Backend FastAPI en Render
- Base de datos Supabase (PostgreSQL)

---

## Documentos relacionados

- `DECISION_LOG.md` — el detalle completo de cada decisión resumida aquí
- `ROADMAP.md` — el plan que estos cambios van cerrando