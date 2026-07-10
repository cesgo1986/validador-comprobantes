# CHANGELOG.md — Historial de versiones

**Versión del documento:** 0.24.8 · **Última actualización:** 07/07/2026

Formato: `[versión] — fecha — descripción`. Las versiones siguen Semantic Versioning: MAJOR.MINOR.PATCH.

---

## [0.24.8] — 2026-07 — Wireframe conceptual del Centro Operativo (V1, solo Nivel A) — DESIGN_SYSTEM.md sección 10

### Documentado (estructura, sin código)
- `DESIGN_SYSTEM.md`: nueva sección 10 — wireframe conceptual completo del Centro Operativo V1. Estado 🟢/🟠/🔴, hero stat (monto procesado), secundarios, "qué requiere atención" (Nivel 2, solo aparece lo que aplica), "tendencias" (Nivel 3, con la corrección de factibilidad de la sesión anterior). Cada bloque verificado contra el principio "responde una pregunta o provoca una acción". Nivel 4 (estratégico) explícitamente ausente en V1 — depende de datos de Nivel B que no existen todavía, no se muestra como sección vacía. Aclaración: el grid de 3 zonas de la sección 3 no aplica aquí (es para pantallas de un solo elemento) — el Centro Operativo usa solo Navigation + Workspace.
- `ROADMAP.md`: 5.5 actualizada con la referencia al wireframe. Pendiente real que queda: destinos exactos de los botones de acción, depende de 5.4.

---

## [0.24.7] — 2026-07 — Centro Operativo: modelo de datos de 3 niveles + principio de "acción, no KPI" (5.5 sigue congelada)

### Documentado (decisión de producto, sin código)
- `DECISION_LOG.md`, `ROADMAP.md`: principio de diseño permanente adoptado — "cada dato debe responder una pregunta de negocio o provocar una acción; si un widget no cambia ninguna decisión, no pertenece al Dashboard". Modelo de 3 niveles de datos: Nivel A (Motor de Verdad, sin captura de la empresa, corazón del Centro Operativo), Nivel B (datos enriquecidos opcionales — sucursales, clientes, % de cobros por otros canales, patrón Stripe/Shopify), Nivel C (integraciones ERP/POS, etapa aparte).
- **Autocorrección registrada:** una evaluación de factibilidad de esta misma sesión (marcar "banco con más incidencias" como no construible) resultó incorrecta — `Alerta.analisis_origen` ya permite esa agregación sin dato nuevo. Se corrige explícitamente en vez de dejarlo pasar.
- Confirmado: solo "tiempo de liberación" sigue genuinamente bloqueado (gap de 4.1, columna `duracion_ms`).

---

## [0.24.6] — 2026-07 — KPI principal del Centro Operativo resuelto (5.5 sigue congelada para código)

### Documentado (decisión de negocio, sin código)
- `DECISION_LOG.md`, `ROADMAP.md`: jerarquía de información definida — Nivel 1 (hero stat): monto total procesado. Nivel 2: volumen, % liquidados, alertas críticas. Historia de negocio primero, historia de control después. Cadencia de uso objetivo: varias veces al día — decisión de posicionamiento (Centro Operativo, no reporte), no solo de UX. No requiere WebSockets — `AggregationService` on-demand es suficiente para ese patrón de uso.
- Preguntas que siguen sin resolver antes de retomar 5.5: qué decisiones puede tomar el director sin abrir un comprobante individual, y el diseño visual concreto.

---

## [0.24.5] — 2026-07 — Corrección de alcance: "canal de cobro" (SPEI), no "canales de cobro" en plural

### Corregido (documentación)
- `PRODUCT_VISION.md`: se corrige una imprecisión que apareció en la síntesis de la sesión anterior — "habilitador de canales de cobro" (plural, genérico) sonaba a pasarela de pagos completa (Stripe/Conekta/Clip), una promesa mucho más grande de la que el producto sostiene. VerificaPago habilita **un canal específico — SPEI** — no canales de cobro en general. Eslogan de trabajo fijado: "Convierte SPEI en un canal de cobro confiable". Criterio de filtro para funcionalidades futuras actualizado para ser explícito en esto.

---

## [0.24.4] — 2026-07 — Propuesta de valor para empresas + hipótesis de evolución del producto (sin comprometer roadmap)

### Documentado (sin código, sin arquitectura, sin roadmap nuevo — deliberadamente)
- `PRODUCT_VISION.md`: nueva sección "Propuesta de valor para empresas" — el "Job To Be Done" del producto (no "validar comprobantes", sino "aceptar SPEI con la confianza de tarjeta, y crecer con eso"), con dos ángulos de venta (defensivo: elimina riesgo; ofensivo: habilita un canal de cobro adicional). Tabla de valor reordenada por resultado de negocio, no por módulo técnico. Criterio de filtro para funcionalidades futuras: "¿esto ayuda a que SPEI sea un canal de cobro más confiable y operativo?".
- `PRODUCT_VISION.md`: nueva sección "Hipótesis de evolución del producto" — Motor de Operaciones (conciliación automática vía identificador de operación en el campo concepto) y Niveles de confianza progresivos (comportamiento observado, no KYC), ambas capturadas como hipótesis sin comprometer arquitectura ni roadmap. Riesgo regulatorio de LFPDPPP identificado y sin resolver. Open Banking descartado explícitamente (cae bajo Ley Fintech, requeriría entidad regulada o agregador autorizado por CNBV — otro negocio, no una función más).

Sube a versión MINOR porque redefine el posicionamiento comercial del producto — no es un ajuste incremental, aunque no toque ni una línea de código.

---

## [0.24.3] — 2026-07 — 🏛️ ADR: se congela 5.5 (Dashboard Empresa Desktop) hasta definir el Centro Operativo VerificaPago

### Documentado
- `DECISION_LOG.md`: ADR — 5.5 congelada, no se construye ninguna pantalla de dashboard empresarial hasta responder qué vende VerificaPago Empresa (visibilidad/riesgo/control, no OCR/CEP/IA), cuál es el KPI principal, y qué decisiones debe poder tomar un director de operaciones sin abrir un comprobante individual. Hallazgo importante: buena parte del backend necesario (`AggregationService`, `alertas-agregadas`) ya existe — lo pendiente es la priorización de producto, no reconstruir backend.
- `ROADMAP.md`: 5.5 marcada como congelada con la razón explícita; se siembra "reglas de detección de velocidad/anomalía" en la etapa funcional futura (Alert Engine, no presentación).
- 5.3 y 5.4 **no se congelan** — continúan sin cambios, son reutilización de componentes ya construidos.

---

## [0.24.2] — 2026-07 — DESIGN_SYSTEM.md (14º documento); BottomNav.tsx renombrado a NavigationShell.tsx; pausa de diseño antes de seguir 5.3

### Documentado
- `DESIGN_SYSTEM.md` (nuevo, 14º documento de `/docs`): lenguaje visual único de VerificaPago — filosofía, jerarquía lineal (Mobile) vs. exploratoria (Desktop), grid de 3 zonas, espaciados (principio, sin tokens fijos todavía), componentes base (reutilizar, no reimplementar), color, `NavigationShell`, animaciones (escudo exclusivo de Mobile), y una sección explícita de preguntas abiertas sin resolver (imagen del comprobante en Desktop, contenido de la zona de Context sin imagen, espaciados concretos, reducción de cajas, animación de Desktop).
- `README.md`: estructura documental actualizada — 14 documentos, no 13. El principio de "no crear documentos nuevos salvo dominio propio y reutilizable" se mantiene; lo que cambia es que ya se aplicó una vez más (como con `MODELO_DECISION_EXPLICABLE.md` y `LABORATORIO.md` en su momento).
- `DECISION_LOG.md`: ADR — "no se diseña Desktop, se diseña el lenguaje visual definitivo de VerificaPago". Se rechazan 4 elementos de un mockup de referencia por romper decisiones ya tomadas (imagen de comprobante histórico, workflow de aprobación, navegación con destinos inexistentes, datos de usuario/facturación) y se rescata la filosofía de 3 zonas + "menos cajas, más aire". Se registra el nuevo flujo de trabajo para presentación: `ROADMAP → DESIGN_SYSTEM.md → Wireframes/Mockups → Validación → Código`.
- `ARQUITECTURA.md`, `ROADMAP.md`: `BottomNav.tsx` renombrado a `NavigationShell.tsx` en las referencias de trabajo pendiente (5.3) — las menciones históricas de sesiones ya cerradas se dejan como `BottomNav`, porque ese era el nombre correcto en su momento.

### Agregado (código pendiente de aplicar y desplegar — reemplaza el código de la sesión anterior, todavía no desplegado)
- `app/components/NavigationShell.tsx` (renombrado de `BottomNav.tsx`, contenido funcional sin cambios respecto a la versión anterior — solo el nombre y los comentarios).
- `app/layout.tsx`: import actualizado a `NavigationShell`.

Sube a versión MINOR porque agrega un documento nuevo a la estructura congelada y registra una decisión de arquitectura permanente sobre el lenguaje visual del producto.

---

## [0.24.1] — 2026-07 — Etapa 5, 5.3: BottomNav → sidebar en Desktop/Wide Desktop — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `app/globals.css`: nuevas clases `.vp-nav`, `.vp-nav-item`, `.vp-nav-label`, `.vp-nav-plus-wrapper`, `.vp-content-area`, `.vp-page-padding` — el posicionamiento de la navegación (barra abajo vs. sidebar a la izquierda) se movió de estilos inline a clases CSS, porque un estilo inline siempre gana sobre una regla de `@media`.
- `app/layout.tsx`: envuelve el contenido en `.vp-content-area` (se corre a la derecha del sidebar en Desktop+) y `.vp-page-padding` (el padding para la barra inferior solo aplica en Mobile/Tablet).
- `app/components/BottomNav.tsx`: usa las clases nuevas en vez de estilos inline para posición/eje/bordes — colores, iconos y badge siguen inline (no cambian con el breakpoint).

### Documentado
- `ARQUITECTURA.md`, `ROADMAP.md`: actualizados.

---

## [0.24.0] — 2026-07 — 🏛️ ADR: Tailwind no se adopta; globals.css como Design System incremental

### Documentado
- `DECISION_LOG.md`: ADR — Tailwind permanece instalado (scaffold del proyecto, v4) pero no se adopta como sistema de estilos, por consistencia arquitectónica, no por limitación técnica. `globals.css` se refuerza como Design System incremental.
- `ROADMAP.md`: nota de la decisión agregada al ítem 5.2.

### Agregado (código pendiente de aplicar y desplegar)
- `app/globals.css`: se agrega `--vp-sidebar-width` (280px, para la conversión de `BottomNav` a sidebar) y `--vp-desktop-breakpoint` (1200px, referencia para JS — con nota explícita de que las variables CSS no funcionan dentro de la condición de un `@media`, los 4 rangos siguen como números literales).

Sube a versión MINOR porque registra una decisión de arquitectura permanente sobre el sistema de estilos de todo el proyecto, no un ajuste incremental.

---

## [0.23.2] — 2026-07 — Base del contenedor responsive desplegada y verificada; hallazgo: Tailwind ya está instalado

### Desplegado en producción
- `app/globals.css`, `app/layout.tsx`, `app/components/BottomNav.tsx`: verificado en escritorio ancho — el contenedor crece más allá de 480px según el ancho real de la ventana, sin afectar la vista móvil.

### Corregido (al aplicar el cambio)
- `app/globals.css` **ya existía** (scaffold de `create-next-app`, con `@import "tailwindcss"` — Tailwind v4 instalado y configurado, nunca usado hasta ahora). No se reemplazó el archivo — se le agregaron las reglas nuevas al final, conservando el contenido original completo. Corregido también en `ARQUITECTURA.md`.

### Decisión pendiente de confirmar
- Con Tailwind disponible, hay que decidir si el resto de la Etapa 5 (sidebar, layouts de 2 columnas) se construye con estilos inline + variables CSS (consistente con el 100% del código existente) o aprovechando las clases responsive de Tailwind (más simple de escribir, pero introduce un segundo patrón de estilos). Sin resolver todavía.

---

## [0.23.1] — 2026-07 — Etapa 5, 5.3 (en curso): base del contenedor responsive — código listo, pendiente de deploy

### Corregido (documentación)
- `LABORATORIO.md`, `ROADMAP.md`: se corrige un hallazgo falso de la entrada anterior (v0.23.0) — al ver `app/layout.tsx` completo, resultó que el contenido **ya** compartía el mismo ancho máximo (480px) que `BottomNav`, no había ninguna inconsistencia que corregir. El trabajo real es hacer que ese ancho responda a los 4 rangos, no corregir un bug que no existía.

### Agregado (código pendiente de aplicar y desplegar)
- `app/globals.css` (nuevo): variable `--vp-container-width` con los 4 rangos vía `@media`, clase `.vp-container`.
- `app/layout.tsx`: usa `.vp-container` en vez de `maxWidth: 480` fijo.
- `app/components/BottomNav.tsx`: usa `.vp-container` en vez de `maxWidth: 480` fijo — layout y nav ahora comparten una sola fuente de verdad, no pueden desincronizarse entre sí.

### Pendiente (mismo ítem 5.3)
- Conversión de `BottomNav` a barra lateral en Desktop/Wide Desktop.
- Layout de 2 columnas en `/resultado`.

---

## [0.23.0] — 2026-07 — Etapa 5, 5.2: laboratorio de breakpoints completo (Responsive Foundation)

### Documentado (sin código todavía)
- `LABORATORIO.md`: laboratorio completo de breakpoints — 4 rangos (Mobile/Tablet/Desktop/Wide Desktop), ancho de contenedor por rango, comportamiento definido para `/resultado`, `/historial`, `/perfil`. Hallazgo real: el contenido de las pantallas no tiene ancho máximo propio hoy, solo `BottomNav` (480px) — corrección necesaria antes de 5.3. Decisión de navegación: `BottomNav` se convierte en barra lateral en Desktop/Wide Desktop, sin cambios en Mobile/Tablet.
- `ROADMAP.md`: ítem 5.2 marcado como diseño completo — 5.3 ya puede empezar con las reglas definidas.

---

## [0.22.1] — 2026-07 — 5.1 cerrado: objeto evidencias desplegado, sin regresión visual

### Desplegado en producción
- `main.py`, `app/context/AnalisisContext.tsx`, `app/components/resultado/DetalleExpandible.tsx`: verificado — `/resultado` e `/historial/[id]` se ven idénticos a como estaban antes del cambio.

### Cerrado
- `ROADMAP.md`: ítem **5.1** (paso intermedio del Motor de Presentación) pasa a ✅.

---

## [0.22.0] — 2026-07 — Etapa 5, 5.1: objeto `evidencias` (paso intermedio del Motor de Presentación) — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `main.py`: nuevo bloque `result["evidencias"]` — hechos crudos sin interpretar (`xml_valido`, `xml_discrepancias`, `confianza_documental`, `verificabilidad`, `contexto_temporal`, `hash_reutilizado`), construido después del procesamiento del XML para capturar los valores finales.
- `app/context/AnalisisContext.tsx`: nueva interfaz `Evidencias`, agregada como campo opcional a `Resultado`.

### Corregido
- `app/components/resultado/DetalleExpandible.tsx`: se elimina un cast forzado (`as unknown as {...}`) que accedía a `cep_xml.comparacion_campos.discrepancias` manualmente — verificado contra `cep_xml_service.py` que la ruta era correcta, pero ahora usa `result.evidencias.xml_discrepancias` sin cast. De paso se corrige la precedencia de operadores confusa `?? 0 > 0` (se evaluaba como `?? (0 > 0)`, no como "usa 0 si falta, luego compara" — funcionaba por coincidencia con los valores reales, pero no decía lo que parecía decir).

### Documentado
- `API.md`: nueva sección `evidencias` en "Campos del resultado por categoría".
- `ROADMAP.md`: ítem 5.1 actualizado.

---

## [0.21.1] — 2026-07 — Vigilancia a futuro + ritual de Architecture Review

### Documentado (sin código, sin decisión de arquitectura — sembradas para no reinventarlas)
- `ROADMAP.md`: nueva sección "Vigilancia a futuro" — costo por análisis (riesgo #1 de crecimiento), telemetría de negocio (distinta de las métricas técnicas ya existentes), Feature Flags, versionado de reglas del Alert Engine, abstracción del proveedor de IA de visión.
- `README.md`: se documenta el ritual de Architecture Review al cierre de cada etapa — no es un marcador nuevo (se mantiene la estructura de 13 documentos y 3 marcadores activos congelada); solo genera documentación si surge una decisión permanente, que ahí sí se registra como `#ADR-VP`.

---

## [0.21.0] — 2026-07 — Architecture Readiness Review; Etapa 5 redefinida como "Presentation Expansion"

### Documentado (sin código todavía)
- `DECISION_LOG.md`: 🏛️ ADR — Desktop = Responsive Web, se descarta Electron/Tauri explícitamente.
- `DECISION_LOG.md`: 🏛️ ADR — Etapa 5 se redefine como presentación pura (5.1-5.5); Batch Analysis y Workflow de aprobación se retiran, sembrados como etapa funcional futura sin número ni fecha.
- `DECISION_LOG.md`: 🏛️ ADR — primera Architecture Readiness Review del proyecto. Conclusión: no requiere reescritura, requiere evolución incremental. Se corrigen 2 supuestos (no es "servicios independientes escalables horizontalmente" todavía — es monolito modular; no hay archivos que migrar — nunca se persisten imágenes). 7 riesgos reales identificados con plan de evolución, ninguno bloqueante.
- `ARQUITECTURA.md`: nueva sección "Evaluación de preparación para escala", con tabla de riesgos/evolución.
- `ROADMAP.md`: Etapa 5 reescrita (5.1-5.5, sin batch/workflow); Etapa 6 ampliada con los hallazgos de infraestructura (cola para Banxico, cache/métricas distribuidas, CORS, logging, costos, backups); nueva sección "Etapa futura (sembrada)" para Batch/Workflow/colaboración.
- `LABORATORIO.md`: sembrado el laboratorio de breakpoints pendiente (ítem 5.2).

Sube a versión MINOR porque redefine una etapa completa del roadmap y documenta la primera revisión formal de arquitectura del proyecto, no un ajuste incremental.

---

## [0.20.0] — 2026-07 — ✅ Etapa 4 (Backend Empresarial + Executive Summary móvil) completa

### Desplegado en producción
- `app/perfil/page.tsx`: Executive Summary verificado funcionando.

### Cerrado
- `ROADMAP.md`: ítems **4.1** y **4.2** pasan a ✅. **4.3** (Desktop completo) queda formalmente diferido a Etapa 5, tal como se decidió en el ADR "una sola experiencia, múltiples presentaciones". Con esto, **la Etapa 4 completa queda cerrada**.

Sube a versión MINOR porque marca el cierre de una etapa completa del roadmap, mismo criterio que las Etapas 1, 2 y 3.

---

## [0.19.2] — 2026-07 — Etapa 4, 4.2: Mobile Executive Summary — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `app/perfil/page.tsx`: reemplaza el placeholder — tarjeta "Resumen de hoy" consumiendo `/resumen-ejecutivo`. Sin gráficas, sin tablas, sin filtros — ver ADR "una sola experiencia, múltiples presentaciones". Deliberadamente sin datos de la empresa (no existe endpoint todavía).

### Documentado
- `ARQUITECTURA.md`, `ROADMAP.md`: actualizados.

---

## [0.19.1] — 2026-07 — Fix: comparación de fechas contra Analisis.fecha (bug real, encontrado al construir 4.2)

### Corregido (pendiente de deploy)
- `services/aggregation_service.py`: nuevo helper `_parsear_fecha()` — convierte `fecha_desde`/`fecha_hasta` (string) a `date` antes de comparar contra `Analisis.fecha` (TIMESTAMP). Sin esto, SQLAlchemy tipaba el parámetro como `VARCHAR` y Postgres rechazaba la comparación (`UndefinedFunction: operator does not exist: timestamp >= character varying`) — error real encontrado en producción al probar `/resumen-ejecutivo`.
- Mismo fix aplicado a `services/dashboard_service.py` (`_construir_filtros_analisis()`) — el mismo patrón ya existía ahí desde el ítem 2.1 (filtro de fecha del Historial) y el ítem 2.4 (exportación), probablemente sin dispararse de forma visible hasta ahora.
- Segundo fix, más sutil, en el mismo commit: `fecha_hasta` con `<=` excluía registros del mismo día después de la medianoche (comparación de timestamp contra fecha pura a las 00:00:00). Corregido a "antes del día siguiente" para incluir el día completo — afecta también a Historial y Exportar.

Este bug no rompía nada visible en Historial hasta ahora porque nadie forzó el filtro de fecha con suficiente consistencia para notar el error 500 (o los resultados incompletos por el bug de "día completo"). Se descubrió al construir el ítem 4.2 porque es el primer código que llama a estas funciones con fechas reales garantizadas, no opcionales.

---

## [0.19.0] — 2026-07 — Etapa 4, 4.1: AggregationService + backend empresarial — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `services/aggregation_service.py` (nuevo): única pieza autorizada a construir queries agregadas. Incluye las 4 agregaciones movidas desde `dashboard_service.py` (sin cambio de lógica) más 4 nuevas: monto total procesado, banco más frecuente por volumen, riesgo por periodo (Motor 1 + Motor 2 separados), alertas agregadas.
- `services/dashboard_service.py`: reescrito — las 4 funciones de agregación existentes ahora son wrappers delgados hacia `aggregation_service` (mismo nombre/firma, cero riesgo para endpoints en producción); se agregan wrappers nuevos + `obtener_resumen_ejecutivo()` (ítem 4.2, compone `AggregationService` + `alerta_service`).
- `main.py`: 5 endpoints nuevos — `/monto-total`, `/bancos-frecuentes`, `/riesgo-por-periodo`, `/alertas-agregadas`, `/resumen-ejecutivo`.

### Documentado
- `API.md`, `ARQUITECTURA.md`, `ROADMAP.md`: actualizados. Se documentan explícitamente 2 gaps no resueltos en este corte: "tiempo promedio de validación" (requeriría columna nueva en `analisis`) y "actividad por empresa" (sin sentido real hasta Etapa 6).

---

## [0.18.0] — 2026-07 — Etapa 4 redefinida: AggregationService + Executive Summary móvil; principio "una sola experiencia, múltiples presentaciones"

### Documentado (sin código todavía)
- `DECISION_LOG.md`: 🏛️ ADR — "una sola experiencia, múltiples presentaciones": móvil define el producto, Desktop solo expande, nada exclusivo de Desktop.
- `DECISION_LOG.md`: 🏛️ ADR — ningún dashboard consulta la base de datos o los motores directamente; se introduce `AggregationService` (cuarto consumidor del núcleo) como única pieza autorizada a construir queries agregadas.
- `DECISION_LOG.md`: 🏛️ ADR — `Perfil` evoluciona temporalmente a "Perfil / Empresa" para el Executive Summary, sin agregar un sexto ícono a `BottomNav`.
- `PRODUCT_VISION.md`: nuevo principio #6, "Una sola experiencia, múltiples presentaciones".
- `ROADMAP.md`: Etapa 4 reescrita — 4.1 (`AggregationService` + backend empresarial completo), 4.2 (Mobile Executive Summary vía Perfil), 4.3 (Desktop completo, diferido a Etapa 5). Etapa 5 corregida: se retira la frase "no es adaptar la UI móvil, es diseñar desde cero" — contradecía el ADR de una sola experiencia.

Sube a versión MINOR porque redefine la estructura de una etapa completa del roadmap y establece un principio de producto permanente, no un ajuste incremental.

---

## [0.17.0] — 2026-07 — 🏛️ ADR: núcleo funcional del MVP congelado

### Documentado
- `DECISION_LOG.md`: se declara congelado el núcleo funcional (`/resultado`, `/historial`, `/alertas` — Motor SPEI, Motor Documental, Alert Engine, Modelo de Decisión Explicable, `AnalisisContext`). Ningún módulo nuevo (Dashboard Empresa, APIs futuras, cualquier cliente) puede implementar lógica propia de decisión — debe consumir estos motores.
- Registrada la revisión de coherencia arquitectónica de 6 puntos que motivó este ADR, con hallazgos reales (duplicación de JSX ya resuelta, desfase de versión en documentos ya corregido) y pendientes explícitos (integración de Alertas al Modelo de Decisión Explicable, aún sin resolver — no se fuerza).
- Se establece como práctica: cada cambio a `docs/` actualiza el encabezado "Versión del documento" del archivo tocado, no solo `CHANGELOG.md`.

Sube a versión MINOR porque marca el cierre formal de una fase de madurez del proyecto (núcleo congelado), no un ajuste incremental — mismo criterio que el cierre de la Fase de Fundación y del núcleo funcional previos.

---

## [0.16.2] — 2026-07 — Refactor de componentes compartidos desplegado y verificado

### Desplegado en producción
- `app/lib/colores.ts`, `app/components/resultado/*.tsx`, `app/resultado/page.tsx`, `app/historial/[id]/page.tsx`: desplegados sin regresión visual. `/resultado` e `/historial/[id]` se ven idénticos a la versión pre-refactor. Alertas e Historial siguen generándose correctamente.

---

## [0.16.1] — 2026-07 — Refactor: componentes compartidos entre /resultado y /historial/[id], previo a Etapa 4

### Agregado (código pendiente de aplicar y desplegar)
- `app/lib/colores.ts` (nuevo): paleta compartida (`TEAL`, `GREEN`, `ORANGE`, `RED`, `GRAY`), antes duplicada como constantes locales en cada archivo.
- `app/components/resultado/SemaforoSpei.tsx` (nuevo): Nivel 1 — semáforo SPEI.
- `app/components/resultado/QueSignificaEsto.tsx` (nuevo): Nivel 1 — Interpretación + Impacto + Recomendación.
- `app/components/resultado/DetalleExpandible.tsx` (nuevo): Nivel 2+ — integridad, evidencias, dimensiones, diagnóstico técnico. Recibe `avisoReutilizacion` y `extra` como props para las diferencias entre consumidores.

### Cambiado
- `app/resultado/page.tsx`: reescrito para consumir los componentes compartidos — ya no duplica el bloque central.
- `app/historial/[id]/page.tsx`: reescrito para consumir los componentes compartidos.

### Documentado
- `DECISION_LOG.md`: la deuda técnica reconocida al construir 2.3 se marca como **resuelta**, antes del tercer consumidor (Dashboard Empresa, Etapa 4), cumpliendo el compromiso registrado en su momento.
- `ROADMAP.md`, `ARQUITECTURA.md`: actualizados con la estructura nueva.

Este refactor fue producto de una auto-revisión de arquitectura antes de abrir Etapa 4 (6 puntos de coherencia: independencia de motores, integración al Modelo de Decisión Explicable, duplicación de lógica, preparación de BD para multiempresa, sincronía de documentación, y nivel de congelamiento del MVP). También se corrigió en esa revisión un desfase real: los 12 documentos de `/docs` tenían el encabezado "Versión del documento" desactualizado (`0.11.0` fijo desde su creación, sin actualizarse en cada versión) — se sincronizaron todos a `0.16.0`.

---

## [0.16.0] — 2026-07 — ✅ Etapa 3 (Alertas Inteligentes) completa

### Desplegado en producción
- `services/alerta_service.py`, `main.py`: Motor de Prioridad y endpoint de conteo, verificados funcionando.
- `app/components/BottomNav.tsx`: badge inteligente verificado — ya no hardcodeado.

### Cerrado
- `ROADMAP.md`: ítem **3.5** pasa a ✅. Con esto, **la Etapa 3 completa queda cerrada** — los 5 ítems (3.1 a 3.5) están en producción y verificados.

Sube a versión MINOR (no PATCH) porque marca el cierre de una etapa completa del roadmap, mismo criterio aplicado al cerrar las Etapas 1 y 2.

---

## [0.15.7] — 2026-07 — Etapa 3, 3.5: badge inteligente — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `services/alerta_service.py`: `contar_alertas()` — Motor de Prioridad, separa alertas `NUEVA` totales de las "notificables" (severidad `MEDIA`+).
- `main.py`: nuevo endpoint `GET /api/v1/dashboard/alertas/conteo`.
- `app/components/BottomNav.tsx`: badge de "Alertas" ya no hardcodeado en `3` — se conecta al conteo real, con polling cada 60s.

### Documentado
- `LABORATORIO.md`: umbral de severidades "notificables" (`MEDIA`+) registrado como `#LAB-VP`.
- `API.md`, `ARQUITECTURA.md`, `ROADMAP.md`: actualizados.

---

## [0.15.6] — 2026-07 — 3.4 cerrado: pantalla /alertas desplegada

### Desplegado en producción
- `main.py`: endpoints de alertas desplegados sin errores (corregido el import faltante de `alerta_service` detectado por Pylance antes del deploy).
- `app/alertas/page.tsx`: desplegado, reemplaza el placeholder.

### Cerrado
- `ROADMAP.md`: ítem **3.4** de la Etapa 3 pasa a ✅.

---

## [0.15.5] — 2026-07 — Etapa 3, 3.4: pantalla /alertas — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `main.py`: `GET /api/v1/dashboard/alertas` (listado paginado con filtros) y `PATCH /api/v1/dashboard/alertas/{id}/estado` (marcar revisada/descartada).
- `app/alertas/page.tsx`: reemplaza el placeholder. Divulgación progresiva — Nivel 1 muestra solo alertas `NUEVA` por defecto, con acciones rápidas por tarjeta; Nivel 2 (filtros) permite ver revisadas/descartadas y filtrar por severidad/tipo. Etiquetas legibles por tipo de alerta y entidad.

### Documentado
- `API.md`: los 2 endpoints nuevos documentados.
- `ARQUITECTURA.md`, `ROADMAP.md`: actualizados.

---

## [0.15.4] — 2026-07 — 3.3 cerrado: primeras reglas del Alert Engine desplegadas

### Desplegado en producción
- `alert_engine/` completo, verificado: análisis normales sin afectación, alertas creándose correctamente en la tabla `alertas`.

### Cerrado
- `ROADMAP.md`: ítem **3.3** de la Etapa 3 pasa a ✅.

---

## [0.15.3] — 2026-07 — Etapa 3, 3.3: primeras reglas del Alert Engine — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `alert_engine/engine.py` (nuevo): orquestador — ejecuta reglas activas, persiste alertas, degrada con gracia si una regla falla.
- `alert_engine/regla_hash.py` (nuevo): reutilización de hash, severidad escalada por `veces_visto` (2=BAJA, 3-4=MEDIA, 5+=ALTA).
- `alert_engine/regla_clabe.py` (nuevo): CLABE receptora frecuente (≥10 apariciones en 30 días, severidad MEDIA).
- `alert_engine/regla_clave_rastreo.py` (nuevo): clave de rastreo repetida con banco o monto distinto (severidad ALTA fija).
- `main.py`: dispara `alert_engine.evaluar()` después de `guardar_analisis()`, envuelto en try/except para no afectar el análisis principal si falla.

### Documentado
- `LABORATORIO.md`: los 3 umbrales registrados como `#LAB-VP` — hipótesis iniciales sin datos históricos, sujetas a ajuste durante la Beta.
- `ROADMAP.md`: ítem 3.3 detallado.

---

## [0.15.2] — 2026-07 — 3.2 cerrado: tabla alertas desplegada

### Desplegado en producción
- Migración de Alembic aplicada en Render: tabla `alertas` creada con sus 6 índices.
- `models/alerta.py`, `services/alerta_service.py` disponibles, sin consumidores todavía (esperado — 3.3 es lo que los va a usar).

### Cerrado
- `ROADMAP.md`: ítem **3.2** de la Etapa 3 pasa a ✅.

---

## [0.15.1] — 2026-07 — Etapa 3, 3.2: tabla alertas (persistencia) — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar — incluye migración de base de datos)
- Nueva migración de Alembic: tabla `alertas` completa (`tipo_alerta`, `severidad`, `entidad_tipo`, `entidad_id`, `analisis_origen`, `estado`, `metadata` JSONB), con índices en los campos que se van a filtrar/agrupar.
- `models/alerta.py` (nuevo): modelo `Alerta`. Sin `back_populates` deliberadamente, para no requerir tocar `models/empresa.py` ni `models/analisis.py`.
- `services/alerta_service.py` (nuevo): `crear_alerta()`, `listar_alertas()`, `cambiar_estado_alerta()` — solo persistencia, sin lógica de detección (eso es 3.3, en `alert_engine/`, todavía sin crear).

### Documentado
- `ARQUITECTURA.md`: `models/alerta.py`, `services/alerta_service.py` y el futuro `alert_engine/` (planeado) agregados a la estructura del backend.
- `ROADMAP.md`: ítem 3.2 detallado.

---

## [0.15.0] — 2026-07 — Cierre del núcleo funcional; Etapa 3 (Alertas Inteligentes) en marcha: diseño del Alert Engine

### Documentado (sin código todavía)
- `DECISION_LOG.md`: 🏛️ ADR — se declara concluido el núcleo funcional de VerificaPago (Motor SPEI, Motor Documental, Modelo de Decisión Explicable, Historial). Las funcionalidades nuevas reutilizan estos motores en vez de crear lógica paralela.
- `DECISION_LOG.md`: 🏛️ ADR — las alertas se implementan como eventos persistentes (tabla `alertas`, hechos no interpretaciones) generados por un Alert Engine desacoplado (reglas independientes, cada una un archivo). Se separan explícitamente Evento y Notificación mediante un Motor de Prioridad. Se siembra un tercer motor conceptual: el Motor de Comportamiento.
- `MOTOR_DECISIONES.md`: nueva sección sobre el Motor de Comportamiento, sembrado sin implementar.
- `ROADMAP.md`: Etapa 3 reestructurada en 3.1 (diseño del Alert Engine, completado en este ADR) → 3.2 (tabla `alertas`) → 3.3 (primeras reglas) → 3.4 (pantalla `/alertas`) → 3.5 (notificaciones y badge inteligente).

Sube a versión MINOR porque introduce un ADR de arquitectura fundacional para toda la capa inteligente del producto (Alertas, y a futuro Dashboard Empresa y Motor Antifraude), no un ajuste incremental.

---

## [0.14.0] — 2026-07 — ✅ Etapa 2 (Historial real) completa

### Desplegado en producción
- `main.py`, `services/dashboard_service.py`: endpoint de exportación CSV verificado funcionando end-to-end.
- `app/historial/page.tsx`: botón "⬇ Exportar a CSV" verificado.

### Cerrado
- `ROADMAP.md`: ítem **2.4** pasa a ✅. Con esto, **la Etapa 2 completa queda cerrada** — los 5 ítems (2.1 a 2.5) están en producción y verificados.

Sube a versión MINOR (no PATCH) porque marca el cierre de una etapa completa del roadmap, mismo criterio aplicado al cerrar la Etapa 1 (`0.13.0`).

---

## [0.13.9] — 2026-07 — Etapa 2, 2.4: exportación de historial a CSV — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `services/dashboard_service.py`: refactor — filtros de `listar_analisis()` extraídos a `_construir_filtros_analisis()`, compartida con la nueva `exportar_analisis()` (sin paginación, hasta 5000 filas) para garantizar que la exportación coincide exactamente con los filtros activos en pantalla.
- `main.py`: nuevo endpoint `GET /api/v1/dashboard/analisis/exportar`, genera CSV con `Content-Disposition: attachment`, etiquetas de estado SPEI traducidas vía `SEMAFORO_SPEI`.
- `app/historial/page.tsx`: botón "⬇ Exportar a CSV" dentro del panel de filtros avanzados (Nivel 2).

### Documentado
- `API.md`: nuevo endpoint documentado.
- `ROADMAP.md`: ítem 2.4 detallado.

---

## [0.13.8] — 2026-07 — 2.2 cerrado: búsqueda unificada desplegada y verificada

### Desplegado en producción
- Migración de Alembic aplicada en Render (`clave_rastreo`, `referencia`, `tipo_transferencia` en `analisis`).
- `app/historial/page.tsx`: búsqueda unificada verificada funcionando, tanto desde la app como directo contra `GET /api/v1/dashboard/analisis?q=...`.

### Cerrado
- `ROADMAP.md`: ítem **2.2** de la Etapa 2 pasa a ✅. Misma nota que 2.1: análisis previos a la migración no tienen `clave_rastreo`/`referencia` poblados — solo se encuentran por banco o monto.

---

## [0.13.7] — 2026-07 — Etapa 2, 2.2: búsqueda unificada + ADR de columnas desnormalizadas — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar — incluye migración de base de datos)
- Nueva migración de Alembic: `clave_rastreo`, `referencia` (indexadas) y `tipo_transferencia` (sembrada, sin uso activo) en `analisis`.
- `models/analisis.py`, `services/auditoria_service.py`, `main.py`: actualizados para persistir los 3 campos nuevos.
- `services/dashboard_service.py`: `listar_analisis()` con parámetro `q` de búsqueda unificada (banco, clave de rastreo, referencia, CLABE, y monto si el texto es numérico); `obtener_analisis_detalle()` incluye los campos nuevos.
- `main.py`: endpoint `/api/v1/dashboard/analisis` con el parámetro `q`.
- `app/historial/page.tsx`: caja de búsqueda simple pasa de "Buscar por banco..." a búsqueda unificada.

### Documentado
- `DECISION_LOG.md`: 🏛️ ADR — los campos usados para búsqueda/correlación/analítica deben existir como columnas desnormalizadas, como regla general (no solo para esta migración).
- `ARQUITECTURA.md`, `API.md`: esquema y forma de `/api/v1/dashboard/analisis` actualizados.

---

## [0.13.6] — 2026-07 — 2.3 cerrado: vista de detalle histórico desplegada, fix de navegación

### Desplegado en producción
- `app/historial/[id]/page.tsx`: vista de detalle de análisis histórico, verificada funcionando (badge, ficha de auditoría, reutilización de `/resultado/detalle`).
- `app/historial/page.tsx`: fix — el `onClick` de navegación a `/historial/[id]` no había quedado aplicado en el primer despliegue (el archivo se subió sin los cambios pendientes de guardar). Corregido reemplazando el archivo completo.

### Cerrado
- `ROADMAP.md`: ítem **2.3** de la Etapa 2 pasa a ✅.

---

## [0.13.5] — 2026-07 — Etapa 2, 2.3: vista de detalle histórico — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `app/historial/[id]/page.tsx` (nuevo): vista de detalle de un análisis histórico. Hidrata `AnalisisContext` con el resultado obtenido de `GET /api/v1/dashboard/analisis/{id}`, reutilizando `/resultado/detalle` sin modificarlo. Incluye badge "Análisis archivado", ficha de auditoría antes del semáforo, espacio reservado "Actividad relacionada", y nota de privacidad reencuadrada.
- `app/historial/page.tsx`: tarjetas de la lista ahora navegan a `/historial/[id]` al tocarlas.

### Documentado
- `DECISION_LOG.md`: 🏛️ ADR — todas las vistas de análisis (nuevo e histórico) reutilizan el mismo modelo de presentación y el mismo `AnalisisContext`. Incluye deuda técnica reconocida: `historial/[id]/page.tsx` duplica JSX de `resultado/page.tsx`, refactor pendiente antes del tercer consumidor (Dashboard Empresa).
- `ARQUITECTURA.md`: rutas `historial/page.tsx`, `historial/[id]/page.tsx` y `lib/estadoSpei.ts` actualizadas (ya no placeholders).
- `ROADMAP.md`: ítem 2.3 detallado; refactor pendiente registrado explícitamente como deuda técnica no bloqueante.

---

## [0.13.4] — 2026-07 — 2.1 cerrado: Historial desplegado con divulgación progresiva

### Desplegado en producción
- Migración de Alembic aplicada en Render (`estado_operacion`, `fuente_estado`, `nivel_evidencia` en `analisis`).
- `app/lib/estadoSpei.ts` y `app/historial/page.tsx` desplegados en Vercel — Historial funcional, verificado con análisis reales mostrando el semáforo SPEI como protagonista.

### Cerrado
- `ROADMAP.md`: ítem **2.1** (Etapa 2) pasa a ✅. Nota registrada: análisis previos a la migración muestran `estado_operacion: null` (sin backfill retroactivo) — no bloqueante.

---

## [0.13.3] — 2026-07 — Etapa 2, 2.1: desnormalización de Estado SPEI + Historial con divulgación progresiva — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar — incluye migración de base de datos)
- Nueva migración de Alembic: `estado_operacion`, `fuente_estado`, `nivel_evidencia` como columnas desnormalizadas en `analisis` (índice en `estado_operacion`).
- `models/analisis.py`, `services/auditoria_service.py`, `main.py`: actualizados para persistir los 3 campos nuevos (ya se calculaban en `/analizar`, sin lógica de extracción nueva).
- `services/dashboard_service.py`: `listar_analisis()` y `obtener_analisis_detalle()` devuelven `estado_operacion`/`fuente_estado`/`nivel_evidencia`; `listar_analisis()` agrega filtro `estado_operacion` y `veces_visto` (vía join con `hashes_documentos`).
- `main.py`: endpoint `/api/v1/dashboard/analisis` con el filtro `estado_operacion` nuevo.
- `app/lib/estadoSpei.ts` (nuevo): espejo en frontend de `SEMAFORO_SPEI` (backend), única fuente de verdad para pintar el estado SPEI fuera de `/resultado`.
- `app/historial/page.tsx`: reescrito con divulgación progresiva (ver ADR) — Nivel 1: búsqueda simple + lista cronológica agrupada por día, coloreada/etiquetada por `estado_operacion` (Motor 1); Nivel 2+: filtros avanzados (riesgo documental, fecha, hash) y "Resumen de actividad", colapsados por defecto.

### Documentado
- `ARQUITECTURA.md`, `API.md`: esquema de `analisis` y forma de `/api/v1/dashboard/analisis` actualizados con los campos nuevos.

---

## [0.13.2] — 2026-07 — Etapa 2 en marcha: 2.1 (Historial, lista con filtros) — código listo, pendiente de deploy

### Agregado (código pendiente de aplicar y desplegar)
- `app/historial/page.tsx`: implementación completa de la lista de análisis — estadísticas resumidas (total, hoy, reutilizados), filtros por riesgo/banco/rango de fechas, paginación ("cargar más"), estados vacío/error.
- `services/dashboard_service.py`: `listar_analisis()` extendida con filtros `banco` (búsqueda parcial) y `fecha_desde`/`fecha_hasta` — antes solo soportaba `riesgo` y `hash_sha256`.
- `main.py`: endpoint `GET /api/v1/dashboard/analisis` extendido con los mismos filtros nuevos.

### Corregido
- `API.md`: el campo de fecha en `/api/v1/dashboard/analisis` se documentaba como `created_at`; el código real (`dashboard_service.py`) siempre devolvió `fecha`. Se corrige la documentación para que coincida con el código, no al revés.
- `API.md`: se agregan los 4 endpoints de métricas de la Etapa 1 (`/metricas/xml`, `/metricas/cep`, `/metricas/analizar`, `/metricas/scores-por-banco`) que quedaron implementados en producción pero nunca documentados aquí.

---

## [0.13.1] — 2026-07 — Fix: recomendación legacy contradecía el estado SPEI confirmado

### Corregido (pendiente de deploy)
- `app/resultado/detalle/page.tsx`: se elimina el bloque "Recomendación: Revisar manualmente", que mostraba `result.recomendacion` (generado por Claude Vision antes de conocer el estado SPEI final). Caso detectado: transferencia `Liquidada` confirmada, mientras este bloque instruía "no entregar hasta confirmar acreditación" — contradicción directa entre motores.

### Documentado
- `DECISION_LOG.md`: 🏛️ ADR completo — motivo, por qué se elimina en vez de corregirse el texto, y consecuencia (el flujo de decisión de 1.4 es ahora la única fuente de "qué hacer").

---

## [0.13.0] — 2026-07 — ✅ Etapa 1 (MVP Beta, experiencia de resultados) completa

### Desplegado en producción
- `main.py`: `verify_cep()` y el endpoint `/analizar` instrumentados con `metrics_service` (namespaces `"cep"` y `"analizar"`).
- `services/dashboard_service.py`: nueva función `distribucion_scores_por_banco()`.
- Tres endpoints nuevos: `GET /api/v1/dashboard/metricas/cep`, `GET /api/v1/dashboard/metricas/analizar`, `GET /api/v1/dashboard/metricas/scores-por-banco`.

### Cerrado
- `ROADMAP.md`: ítem **1.6** (Observabilidad) pasa a ✅. Con esto, **la Etapa 1 completa queda cerrada** — los 6 ítems (1.1 a 1.6) están en producción.

Sube a versión MINOR (no PATCH) porque marca el cierre de una etapa completa del roadmap, no un ajuste incremental. A partir de esta versión, `/resultado` se congela salvo bugs, y el desarrollo se mueve a la Etapa 2 (Historial real).

---

## [0.12.5] — 2026-07 — 1.5 cerrado: cache, métricas y reintentos desplegados

### Desplegado en producción
- `services/cache_service.py` y `services/metrics_service.py` (nuevos, genéricos, reutilizables por cualquier componente futuro).
- `services/cep_xml_auto_service.py`: reintentos con backoff (200ms/500ms, máx. 3 intentos) en los 3 pasos del flujo CEP; consume `cache_service` (TTL 30 min, por hash SHA-256) y `metrics_service` (namespace `"xml"`) en vez de mantener estado propio.
- `main.py`: nuevo endpoint `GET /api/v1/dashboard/metricas/xml`.

### Cerrado
- `ROADMAP.md`: ítem **1.5** de la Etapa 1 pasa a ✅ completado y desplegado. Con esto, todos los ítems de la Etapa 1 están cerrados salvo **1.6 (Observabilidad)** — el último pendiente para cerrar el MVP Beta.

---

## [0.12.4] — 2026-07 — ADR: externalización de Cache y Metrics como servicios transversales

### Documentado (código pendiente de aplicar y desplegar)
- `DECISION_LOG.md`: 🏛️ ADR — caché y métricas se extraen de `cep_xml_auto_service.py` a `services/cache_service.py` y `services/metrics_service.py`, genéricos y reutilizables por cualquier componente futuro (Historial, Dashboard, OCR, QR, Motor de Presentación). Motivo, impacto y documentos afectados registrados en la entrada completa.
- `ARQUITECTURA.md`: estructura de `services/` actualizada con los dos servicios nuevos.
- `ROADMAP.md`, ítem 1.5: alcance ajustado — reintentos con backoff (200ms/500ms, máx. 3 intentos), TTL de caché en 30 minutos (no 5), endpoint de métricas bajo `/api/v1/dashboard/metricas/xml` (namespace preparado para `/metricas/ocr`, `/metricas/claude`, etc. a futuro).

---

## [0.12.3] — 2026-07 — 1.3 cerrado: desglose campo a campo de la comparación XML

### Desplegado en producción
- `main.py`: la comparación XML vs. comprobante ahora genera una entrada de `validaciones` individual por campo (`monto`, `fecha`, `clave_rastreo`, `banco_destino`, `cuenta_destino_ultimos_digitos`), categoría `cep_xml`, en vez de un mensaje agregado único.
- `app/resultado/detalle/page.tsx`: nueva categoría `cep_xml` mapeada a "Comparación XML oficial (Banxico)", ordenada justo después de `cep`.

### Cerrado
- `ROADMAP.md`: ítem **1.3** de la Etapa 1 pasa a ✅ completado y desplegado. Con esto, 1.1, 1.2, 1.3 y 1.4 de la Etapa 1 quedan cerrados — solo faltan 1.5 (arquitectura XML backend) y 1.6 (observabilidad) para cerrar el MVP Beta.

---

## [0.12.2] — 2026-07 — 1.2 y 1.4 cerrados: flujo de decisión + jerarquía de divulgación progresiva en producción

### Desplegado en producción
- `app/resultado/page.tsx`: rediseño de jerarquía de información. Nivel 1 (fijo, ~5 seg): ① Resultado + ②③④ "¿Qué significa esto?" (Interpretación/Impacto/Recomendación inmediata) — responde únicamente "¿puedo entregar o no?". Nivel 2+ (expandible bajo demanda, un solo botón "Ver detalles del análisis"): integridad documental, reutilización del documento, evidencias, las 4 dimensiones, diagnóstico técnico.
- Corrección de redacción: el mensaje de integridad documental ahora contextualiza primero el estado SPEI favorable ("La operación sí fue validada por Banxico...") antes de mostrar una observación, para no inducir una lectura contraria a la conclusión real cuando SPEI e integridad documental discrepan.

### Cerrado
- `ROADMAP.md`: ítems **1.2** (catálogo de 9 mensajes contextuales) y **1.4** (flujo de decisión explicable) de la Etapa 1 pasan a ✅ completados y desplegados.

### Documentado (sin cambios adicionales de código)
- `ROADMAP.md`: la secuencia del Sprint A-Final se actualiza — quedan pendientes únicamente 1.3 (evidencia XML campo a campo), 1.5 (arquitectura XML backend) y 1.6 (observabilidad) para cerrar el MVP Beta.

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