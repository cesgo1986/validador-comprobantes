# DECISION_LOG.md — Registro de decisiones

**Versión del documento:** 0.24.0 · **Última actualización:** 05/07/2026

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

## 2026-07 — 🏛️ ADR: todas las vistas de análisis (nuevo e histórico) reutilizan el mismo modelo de presentación y el mismo `AnalisisContext`

**Decisión:** toda pantalla que muestre un análisis de VerificaPago —recién ejecutado o histórico— debe consumir el mismo modelo de datos (`AnalisisContext`) y el mismo modelo de decisión (`MODELO_DECISION_EXPLICABLE.md`), independientemente de su origen. `app/historial/[id]/page.tsx` (ítem 2.3) hidrata `AnalisisContext` con el resultado obtenido de `GET /api/v1/dashboard/analisis/{id}` exactamente igual que `/resultado` lo hace tras un análisis en vivo — así, `/resultado/detalle` se reutiliza sin ninguna modificación ni bifurcación de lógica.

**Motivo:** sin esta regla, cada pantalla nueva que muestre un análisis (Dashboard Empresa, Desktop, futuras integraciones) corre el riesgo de reimplementar su propia versión del modelo de decisión — y si el Modelo de Decisión Explicable cambia en el futuro, habría que actualizar múltiples implementaciones en vez de una.

**Consecuencia:**
- Fuente única de verdad de "cómo se presenta un análisis": `AnalisisContext` + `mensajesContextuales.ts` + `MODELO_DECISION_EXPLICABLE.md`.
- **Deuda técnica reconocida — resuelta 2026-07, antes de Etapa 4:** `app/historial/[id]/page.tsx` duplicaba una porción significativa del JSX de `app/resultado/page.tsx` (semáforo, bloque "¿Qué significa esto?", panel de detalles expandible). Se extrajo a tres componentes compartidos en `app/components/resultado/`: `SemaforoSpei.tsx`, `QueSignificaEsto.tsx`, `DetalleExpandible.tsx` (más `app/lib/colores.ts` para las constantes de color, también duplicadas). Se resolvió justo antes de que existiera el tercer consumidor (Dashboard Empresa, Etapa 4), cumpliendo el compromiso registrado en esta misma entrada.

---

## 2026-07 — 🏛️ ADR: la divulgación progresiva es un principio transversal del producto

**Decisión:** la divulgación progresiva —ya aplicada en `/resultado` (Nivel 1 fijo: Resultado + Impacto; Nivel 2+ bajo demanda: integridad, evidencias, dimensiones, diagnóstico técnico)— se adopta formalmente como principio transversal, no exclusivo de esa pantalla. Todo módulo de VerificaPago (Historial, Dashboard Empresa, Alertas Inteligentes, Desktop, futuras APIs) debe presentar primero la información necesaria para una decisión inmediata, dejando el detalle técnico disponible bajo demanda.

**Motivo:** sin este principio explícito, cada módulo nuevo reinventa su propia jerarquía de información — el riesgo real detectado al diseñar Historial (una pantalla que mezclaba lista, estadísticas, filtros avanzados y estados de error todos al mismo peso visual, la misma saturación que ya se corrigió en `/resultado`).

**Consecuencia:**
- `app/historial/page.tsx` se rediseña: búsqueda simple + lista cronológica agrupada por día como Nivel 1; filtros avanzados (riesgo, fecha, hash) y "Resumen de actividad" colapsados por defecto como Nivel 2+.
- Cualquier pantalla nueva que se diseñe de aquí en adelante (Etapas 2-5) parte de esta regla por defecto, no como una decisión de diseño a discutir caso por caso.
- Se renombra "Estadísticas resumidas" a **"Resumen de actividad"** — lenguaje de producto, no de ingeniería, consistente con la decisión ya tomada de que VerificaPago habla el idioma del usuario (ver `PRODUCT_VISION.md`).

---

## 2026-07 — 🏛️ ADR: los campos usados para búsqueda, correlación o analítica deben existir como columnas desnormalizadas

**Decisión:** todo campo que vaya a usarse para búsqueda, filtros, estadísticas, correlación o reglas de negocio futuras debe existir como columna propia en la tabla `analisis`, además de permanecer íntegro dentro del JSONB `resultado`. Se generaliza el criterio ya aplicado con `estado_operacion`/`fuente_estado`/`nivel_evidencia` (ver ADR anterior) a una regla de arquitectura permanente, no solo a esa migración puntual.

**Aplicación inmediata (ítem 2.2, Etapa 2):** se agregan `clave_rastreo` y `referencia` (indexadas, para la búsqueda unificada del Historial) y se siembra `tipo_transferencia` (sin uso activo — hoy siempre `"SPEI"`, pero evita otra migración cuando VerificaPago soporte SPID/TEF/transferencias internas).

**Motivo:** sin esta regla, cada etapa que necesite un identificador para buscar/filtrar/correlacionar (Alertas Inteligentes, Dashboard Empresa, Motor Antifraude, Analítica) descubre la falta de columna cuando ya la necesita con urgencia, y termina resolviéndolo con una consulta sobre JSONB (lenta, sin índice) o con una migración de emergencia. Es más barato decidirlo como regla general ahora que resolverlo caso por caso después.

**Consecuencia:**
- Antes de cerrar cualquier ítem futuro que introduzca un dato nuevo del análisis, la pregunta de diseño pasa a ser explícita: *¿este campo se va a buscar, filtrar, correlacionar o agregar en el futuro?* Si la respuesta es sí, se desnormaliza en la misma migración que lo introduce — no después.
- `services/dashboard_service.py`, `listar_analisis()`: nuevo parámetro `q` (búsqueda unificada) — combina `banco_detectado`, `clave_rastreo`, `referencia` y `clabe_detectada` con `OR` (coincidencia parcial), y compara contra `monto_detectado` si el texto es interpretable como número. El usuario escribe una sola cosa; el sistema decide dónde buscarla — mismo principio que ya rige el Modelo de Decisión Explicable (el usuario expresa intención, el sistema interpreta).
- `app/historial/page.tsx`: la caja de búsqueda simple (Nivel 1) pasa de "Buscar por banco..." a una búsqueda unificada ("🔎 Banco, clave de rastreo, cuenta o monto...").
- Documentos afectados: `ARQUITECTURA.md` (esquema de `analisis`), `API.md` (parámetro `q` en `/api/v1/dashboard/analisis`), `ROADMAP.md` (2.2).

---

## 2026-07 — 🏛️ ADR: se desnormaliza `estado_operacion`, `fuente_estado` y `nivel_evidencia` en la tabla `analisis`

**Decisión:** se agregan tres columnas desnormalizadas a la tabla `analisis` — `estado_operacion`, `fuente_estado` y `nivel_evidencia` — además de las ya existentes (`banco_detectado`, `monto_detectado`, `clabe_detectada`). Los tres campos ya se calculan durante el análisis (Motor 1 y `MODELO_DECISION_EXPLICABLE.md`) pero hoy solo viven dentro del JSONB `resultado`, sin columna propia.

**Motivo — se descarta explícitamente la alternativa más rápida:** se evaluó usar el campo legacy `riesgo` (Motor 2, documental) como color/protagonista de la lista de Historial, por ser lo único ya desnormalizado. Se rechaza: repetiría exactamente el error que la Etapa 1 corrigió — dejar que el análisis documental sea la señal protagonista en vez del estado SPEI confirmado (Motor 1). Habría sido incoherente con toda la arquitectura de 2 motores independientes ya documentada en `MOTOR_DECISIONES.md`.

**Por qué ahora y por qué los tres campos juntos:** Historial es el primer módulo que necesita `estado_operacion` fuera de `/resultado`, pero no será el último — Dashboard Empresa, Alertas Inteligentes, API Enterprise y Analítica/BI también van a necesitar consultarlo. Sin columna propia, cada uno terminaría leyendo y filtrando sobre JSONB — consultas más lentas, índices más complicados, SQL más difícil de mantener. Es la migración más barata posible ahora; se vuelve más cara cuantos más módulos dependan del JSONB directamente. `fuente_estado` y `nivel_evidencia` se agregan en la misma migración porque ya existen conceptualmente (jerarquía de evidencia, ver `MOTOR_DECISIONES.md`) y habilitan filtros futuros de alto valor sin otra migración — ej. "mostrar solo operaciones confirmadas por XML oficial", o estadísticas tipo "80% de los análisis fueron confirmados por XML".

**Consecuencia:**
- Nueva migración de Alembic agregando las 3 columnas a `analisis`.
- `models/analisis.py`, `services/auditoria_service.py` (función `guardar_analisis`) y la llamada correspondiente en `main.py` se actualizan para persistir los 3 campos — ya se calculan en el endpoint `/analizar`, no requiere lógica nueva, solo pasarlos a la capa de persistencia.
- `services/dashboard_service.py`: `listar_analisis()` se actualiza para devolver `estado_operacion` en vez de (o además de) `riesgo`, y `app/historial/page.tsx` colorea/etiqueta cada fila por `estado_operacion` (Motor 1), consistente con `/resultado`.
- Documentos afectados: `ARQUITECTURA.md` (esquema de `analisis`), `API.md` (forma de `/api/v1/dashboard/analisis` y `/analisis/{id}`).

---

## 2026-07 — 🏛️ ADR: las alertas son eventos persistentes generados por un motor de reglas independiente

**Decisión:** la Etapa 3 (Alertas Inteligentes) no se implementa como lógica dispersa dentro de los endpoints (`if hash_repetido: insertar_alerta(...)`), ni como una tabla que registra interpretaciones ya resueltas (`tipo`, `mensaje`, `severidad`). Se implementa como un **Alert Engine** independiente que evalúa reglas después de guardar cada análisis, y una tabla `alertas` que registra **hechos**, no interpretaciones.

**Flujo:** `analizar()` → guardar análisis → `AlertEngine.evaluar()` → crear eventos. El endpoint `/analizar` nunca contiene lógica de detección de patrones directamente — solo dispara la evaluación.

**Esquema de la tabla `alertas` (diseño, aún no implementado):**
```
id
tipo_alerta        -- REUTILIZACION_HASH, CLAVE_RASTREO_REPETIDA,
                      CUENTA_RECEPTORA_FRECUENTE, BANCO_RIESGO,
                      DISPOSITIVO_REPETIDO, ... (abierto a crecer)
severidad
entidad_tipo        -- HASH, CUENTA, CLABE, BANCO, DISPOSITIVO
entidad_id
analisis_origen
estado               -- NUEVA, REVISADA, DESCARTADA
metadata (JSONB)     -- detalle libre por tipo de alerta, sin tocar el esquema
created_at
updated_at
```

**Por qué `metadata` como JSONB en vez de columnas por tipo de alerta:** con `estado_operacion`/`clave_rastreo`/`referencia` ya se estableció que todo campo usado para buscar/filtrar/correlacionar debe desnormalizarse (ver ADR anterior) — pero eso aplica a identificadores estables de la operación, no a los detalles variables de cada tipo de alerta. Forzar una columna por cada dato que una alerta pudiera necesitar (cantidad de veces, lista de análisis relacionados, umbral usado) llevaría a una tabla con decenas de columnas casi siempre vacías conforme crezcan los tipos de alerta. El balance correcto: `tipo_alerta`, `entidad_tipo`, `entidad_id`, `severidad` y `estado` se desnormalizan porque se van a filtrar/agrupar constantemente; el detalle específico de cada tipo vive en `metadata`.

**Estructura del Alert Engine (diseño, aún no implementado):**
```
alert_engine/
├── engine.py          -- orquesta: junta los resultados de todas las reglas
├── regla_hash.py       -- reutilización del mismo hash
├── regla_clabe.py       -- CLABE receptora frecuente
├── regla_clave_rastreo.py
├── regla_dispositivo.py -- futuro, sin dato disponible todavía
└── regla_banco.py       -- futuro
```
Cada regla es una función que recibe el análisis recién guardado y devuelve `[]` o una lista de alertas. El motor solo agrega resultados — agregar una regla nueva es agregar un archivo, no modificar el motor.

**Separación Evento / Notificación:** no todo evento merece notificar al usuario. Un hash reutilizado por segunda vez es un evento; un hash reutilizado en 4 empresas distintas amerita notificación. Se introduce un **Motor de Prioridad** entre la generación de eventos y las notificaciones/badge, para que el badge de la app (hoy hardcodeado en `3`, ver `BottomNav.tsx`) no se convierta en ruido constante.

**Se siembra un tercer motor — Motor de Comportamiento:** junto al Motor SPEI (Banxico) y el Motor Documental (VerificaPago), se nombra un tercer motor conceptual que hoy solo cubre reglas simples (hash repetido, cuenta repetida, CLABE repetida) pero que a futuro podría evaluar horarios, frecuencia, dispositivos, redes entre empresas y patrones de fraude organizado — sin romper el esquema, porque vive en `metadata`.

**Consecuencia:**
- `ROADMAP.md`, Etapa 3, se reestructura en 3.1 (diseño del Alert Engine — este ADR) → 3.2 (tabla `alertas`) → 3.3 (primeras reglas: hash, cuenta, CLABE, clave de rastreo) → 3.4 (pantalla `/alertas`) → 3.5 (notificaciones y badge inteligente).
- `MOTOR_DECISIONES.md` se actualiza para nombrar el Motor de Comportamiento como tercer motor conceptual, sembrado sin implementación todavía.
- Las discusiones sobre umbrales de detección (¿cuántas veces es "frecuente"?) se registran como `#LAB-VP` en `LABORATORIO.md` conforme ocurran durante la Beta — son investigaciones que van a evolucionar con datos reales, no decisiones definitivas de hoy.

---

## 2026-07 — 🏛️ ADR: una sola experiencia, múltiples presentaciones

**Decisión:** VerificaPago es un solo producto con dos presentaciones (móvil y Desktop), no dos aplicaciones distintas. Reglas:

1. Existe un único flujo funcional.
2. Móvil define el producto — cualquier funcionalidad nueva se diseña primero para móvil.
3. Desktop nunca redefine la experiencia — solo aprovecha el espacio disponible para mostrar simultáneamente lo que en móvil está detrás de divulgación progresiva (ej. Resultado + Evidencias lado a lado, en vez de un botón "Ver detalles del análisis").
4. Ninguna funcionalidad nace exclusivamente para Desktop. Si aporta valor al producto, debe existir también en móvil, aunque sea detrás de un panel expandible o del botón `+` (ver ADR siguiente).

**Motivo:** sin esta regla, Etapa 5 (Desktop) corre el riesgo de convertirse en un producto paralelo con su propia lógica, su propia UX y — con el tiempo — su propio conjunto de bugs y decisiones que ya no coinciden con móvil. La pregunta al construir algo nuevo deja de ser *"¿cómo lo hacemos para Desktop?"* y pasa a ser *"¿cómo funciona el producto? ¿cómo se muestra en móvil? ¿cómo se expande en Desktop?"*.

**Consecuencia:**
- `ROADMAP.md`, Etapa 5: se corrige la descripción — decía *"No es adaptar la UI móvil, es diseñar desde cero para pantallas grandes"*, que contradice este ADR. Ahora dice lo contrario: Desktop parte de la app móvil ya construida y deja de esconder información, no rediseña.
- El botón `+` de `BottomNav` (hoy sin uso más allá de regresar al flujo de análisis) es el lugar donde progresivamente aparecerán funciones nuevas que en Desktop se conviertan en barra lateral — ver ADR de Etapa 4 para el primer caso concreto (resumen empresarial).
- Se agrega como principio en `PRODUCT_VISION.md`.

---

## 2026-07 — 🏛️ ADR: ningún dashboard consulta la base de datos o los motores directamente — todos pasan por `AggregationService`

**Decisión:** se introduce un cuarto consumidor del núcleo (junto a Motor SPEI, Motor Documental y Alert Engine): **Dashboard Empresa**. Se establece que ningún dashboard —el de Etapa 4, el de Desktop en Etapa 5, o cualquier futuro— calcula nada por su cuenta ni consulta la base de datos directamente. El flujo obligatorio es:

```
Dashboard → DashboardService → AggregationService → Motores
```

Nunca `Dashboard → SELECT ... → Base de datos` directo.

**Motivo:** sin esta capa, cada dashboard nuevo reimplementaría sus propias agregaciones (¿cuántos análisis hoy? ¿qué banco es más frecuente? ¿qué % terminó liquidado?), y el día que cambie una regla del Alert Engine o del Motor Documental, habría que actualizar cada dashboard por separado — exactamente el problema que ya se resolvió para Historial con `_construir_filtros_analisis()` compartida, pero a una escala mayor.

**`AggregationService` (nuevo, ítem 4.1 — Etapa 4), responsabilidad única:** responder preguntas agregadas sobre el estado del sistema — cuántos análisis hubo en un periodo, banco más frecuente, alertas críticas activas, tendencia semanal, % liquidado, % con alta confianza documental, etc. Es la única pieza autorizada a construir queries de agregación nuevas; `dashboard_service.py` pasa a ser un consumidor de `AggregationService`, no el lugar donde viven las queries agregadas nuevas.

**Estructura de Etapa 4 (reemplaza el desglose genérico anterior):**
- **4.1 — Backend empresarial completo (`AggregationService` + endpoints):** KPIs agregados, tendencias, distribución por bancos, riesgo por periodo, alertas agregadas, actividad por empresa. La API queda prácticamente definitiva — Desktop (Etapa 5) consume exactamente estos mismos endpoints, sin necesitar otros nuevos.
- **4.2 — Mobile Executive Summary:** no un dashboard completo en móvil — un resumen ejecutivo compacto (análisis de hoy, alertas nuevas, riesgo alto, % confirmadas), sin gráficas ni tablas ni filtros. Vive dentro de `Perfil`, que temporalmente se convierte en "Perfil / Empresa" (ver ADR siguiente).
- **4.3 — Desktop completo:** diferido a Etapa 5, donde ya existía. Consume `AggregationService` a través de los mismos endpoints de 4.1 — gráficas, tablas, filtros, exportación, drill-down viven ahí, no en Etapa 4.

**Consecuencia:**
- `ROADMAP.md`, Etapa 4, se reescribe con este desglose.
- `ARQUITECTURA.md` agrega `services/aggregation_service.py` (planeado) a la estructura del backend.

---

## 2026-07 — 🏛️ ADR: `Perfil` evoluciona temporalmente a "Perfil / Empresa"

**Decisión:** en vez de agregar un sexto ícono al `BottomNav` para el Executive Summary de Dashboard Empresa (ítem 4.2), se usa el espacio ya reservado en `Perfil` — hoy un placeholder sin implementar, destinado a convertirse en el panel de usuario cuando exista autenticación real (Etapa 6). Durante la Etapa 4, `Perfil` muestra datos de la empresa, el resumen ejecutivo y configuración básica; cuando llegue la autenticación multiempresa, ese mismo espacio evoluciona naturalmente al panel de usuario, sin romper la navegación ni haber construido algo que después haya que eliminar.

**Consecuencia:** `BottomNav.tsx` no se modifica en su estructura de 5 elementos. `app/perfil/page.tsx` deja de ser un placeholder vacío en la Etapa 4.

---

## 2026-07 — 🏛️ ADR: núcleo funcional del MVP congelado — todo módulo nuevo consume los motores existentes

**Decisión:** se declara congelado el núcleo funcional del MVP — `/resultado`, `/historial` y `/alertas` (Motor SPEI, Motor Documental, Alert Engine, Modelo de Decisión Explicable, `AnalisisContext`). A partir de esta decisión, **ningún módulo nuevo puede implementar lógica propia de decisión** — Dashboard Empresa (Etapa 4), las APIs futuras y cualquier cliente (web, móvil, escritorio) deben consumir exactamente estos motores, no reimplementarlos.

"Congelado" significa: no se vuelve a tocar por gusto o mejora incremental. Sí se toca por bugs, performance o accesibilidad — igual que ya se hizo con el fix de BBVA (Etapa 1) o el fix del `onClick` faltante en Historial (Etapa 2).

**Motivo — revisión de coherencia arquitectónica antes de abrir Etapa 4 (2026-07), 6 puntos verificados contra el código real, no de memoria:**

1. **Independencia de los 3 motores — ✔ confirmado.** El Alert Engine solo *lee* datos ya producidos por Motor SPEI/Documental (vía columnas desnormalizadas), nunca los reinterpreta ni los modifica.
2. **¿Todo llega al Modelo de Decisión Explicable? — parcial, pendiente explícito.** El análisis en vivo y el histórico sí siguen el modelo completo (Hechos → Interpretación → Impacto → Recomendación → Evidencias). Alertas, en cambio, hoy es un sistema paralelo — no se integra todavía como "Evidencia" dentro de la vista de un análisis específico. Queda anotado como pendiente, no resuelto en este ADR.
3. **Duplicación de lógica — se encontró y se corrigió.** `historial/[id]/page.tsx` duplicaba JSX de `resultado/page.tsx`, exactamente la deuda técnica que quedó registrada al construir 2.3 con el compromiso de resolverla "antes del tercer consumidor". Se resolvió en esta misma sesión (ver entrada anterior de este log) — extracción a `app/components/resultado/`.
4. **Base de datos preparada para Empresa — parcial, y es lo esperado.** `empresa_id` ya está en `analisis`, `alertas`, `hashes_documentos`. `usuario_id` no está vinculado todavía (existe la tabla `usuarios`, sin FK en `analisis`/`alertas`) — correcto para esta etapa, porque no hay autenticación real (eso es Etapa 6). No bloquea Etapa 4 si el dashboard opera a nivel empresa, no por usuario individual.
5. **Documentación sincronizada — se encontró y se corrigió.** Los 12 documentos de `/docs` tenían el encabezado "Versión del documento" fijo en `0.11.0` desde su creación, sin actualizarse en cada versión, mientras `CHANGELOG.md` ya iba en `0.16.0`. Corregido — y se establece como práctica: de aquí en adelante, cada cambio a `docs/` debe actualizar el encabezado de versión del archivo tocado, no solo `CHANGELOG.md`.
6. **Congelamiento del MVP — decisión tomada en este ADR.** Ver arriba.

**Consecuencia:**
- Toda funcionalidad de Etapa 4 (Dashboard Empresa) en adelante debe justificar, antes de escribir código, en qué motor existente se apoya — no puede calcular su propia versión de "estado", "integridad" o "alerta".
- La integración de Alertas al Modelo de Decisión Explicable (hallazgo #2) queda como decisión pendiente explícita — se revisará cuando Dashboard Empresa o Alertas evolucionen lo suficiente para necesitarla, no se fuerza ahora.
- A partir de esta versión, actualizar el encabezado "Versión del documento" de cada archivo de `/docs` que se modifique es parte del flujo de trabajo, no un paso opcional.

---

## 2026-07 — 🏛️ ADR: Tailwind permanece instalado pero no se adopta como sistema de estilos

**Decisión:** Tailwind CSS (ya instalado en el scaffold del proyecto — `@import "tailwindcss"` en `globals.css`, Tailwind v4) permanece como dependencia, pero no se adopta como sistema de estilos mientras la arquitectura de estilos inline + variables CSS (`globals.css` como Design System incremental) siga satisfaciendo las necesidades del producto. No es una limitación técnica ni un descuido — es una decisión consciente de consistencia arquitectónica.

**Motivo:** el 100% del proyecto (Etapas 1-4, y el inicio de Etapa 5) usa estilos inline. Introducir Tailwind justo al comenzar el Motor de Presentación (Etapa 5) crearía dos idiomas de estilos convivientes sin necesidad real — cada componente nuevo generaría la pregunta "¿esto va en Tailwind o en `style={{}}`?", y el Motor de Presentación (que debería ser independiente de cómo se pinta la interfaz) no se beneficia de ese cambio.

**Consecuencia:**
- `globals.css` se refuerza como **Design System incremental** del proyecto — variables CSS que los componentes inline consumen vía `var(--token)`, empezando por lo que ya se necesita (`--vp-container-width`, y ahora `--vp-sidebar-width`), no por una tokenización especulativa de todo el sistema de un solo golpe.
- Spacing, radios de borde y elevaciones **no se tokenizan todavía** — los valores actuales en los componentes existentes no son consistentes entre sí (12px/14px/16px/20px de radio, según el componente), y forzar una tokenización ahora significaría inventar una convención nueva sin adopción real, o refactorizar componentes ya estables sin necesidad funcional. Se tokenizan progresivamente conforme se construyan o toquen componentes nuevos, no retroactivamente.
- Esta decisión se revisa si algún día Tailwind (u otra herramienta) resuelve un problema real que los estilos inline + variables no puedan resolver razonablemente — no antes.

---

## 2026-07 — 🏛️ ADR: Desktop = Responsive Web (no Electron/Tauri)

**Decisión:** Etapa 5 se construye como el mismo frontend Next.js respondiendo a breakpoints anchos — no como una aplicación de escritorio empaquetada (Electron, Tauri).

**Motivo:** coherente con el ADR "una sola experiencia, múltiples presentaciones" — una app empaquetada por separado ya no es una presentación distinta del mismo producto, es otra aplicación, con su propio pipeline de build, instaladores, actualizaciones y diferencias por sistema operativo, sin beneficio real para esta etapa. Los componentes ya construidos (`SemaforoSpei`, `QueSignificaEsto`, `DetalleExpandible`, etc.) no necesitan reimplementarse — solo reorganizarse con CSS/breakpoints.

**Revisión:** esta decisión se reconsidera únicamente si en el futuro se vuelven requisitos centrales del producto: modo offline, integración con hardware, o funciones nativas del sistema operativo. Hoy sería complejidad sin beneficio.

**Consecuencia:** `ROADMAP.md`, Etapa 5, renombrada a "Presentation Expansion".

---

## 2026-07 — 🏛️ ADR: Etapa 5 se redefine como presentación pura; Batch Analysis y Workflow se retiran

**Decisión:** Etapa 5 se enfoca exclusivamente en presentación (5.1 Motor de Presentación → 5.5 Dashboard Empresa Desktop). El análisis de múltiples comprobantes simultáneos (Batch Analysis) y el workflow de aprobación/rechazo por operador, propuestos originalmente como parte de Desktop, se retiran de esta etapa.

**Motivo:** ninguno de los dos es "presentación en pantalla ancha" — son capacidades de producto que, por el ADR de una sola experiencia, deberían existir también en móvil. Mezclarlos con una etapa dedicada a presentación diluye el enfoque de ambas.

**Consecuencia:** `ROADMAP.md` registra Batch Analysis, Workflow de aprobación, y (a futuro) colaboración/permisos/equipos como candidatos de una etapa funcional posterior, sembrada sin número ni fecha, probablemente después de Etapa 7.

---

## 2026-07 — 🏛️ ADR: evaluación de preparación para escala — evolución incremental, sin reescritura

**Decisión:** se documenta formalmente la primera "Architecture Readiness Review" del proyecto (ver `ARQUITECTURA.md`, sección "Evaluación de preparación para escala"). Conclusión: la arquitectura actual no requiere reescritura para escalar — requiere evolución incremental de piezas específicas, cada una activable sin cambiar el diseño alrededor.

**Corrección a dos supuestos iniciales de la discusión (con ChatGPT) que motivó esta revisión:**
- No es una arquitectura de "servicios independientes escalables horizontalmente" todavía — es un **monolito modular** (Motor SPEI, Motor Documental, Alert Engine, `AggregationService` como módulos de Python dentro de un solo proceso de Render). Es la arquitectura correcta para este tamaño; la separación en servicios desplegables por separado no está hecha ni es necesaria hoy.
- El riesgo de "¿dónde vivirán las imágenes al escalar?" no aplica — las imágenes de comprobantes nunca se persisten (ver Etapa 2, `historial/[id]/page.tsx`, nota de privacidad). No hay archivos que migrar a almacenamiento externo porque no hay archivos guardados.

**Riesgos reales identificados, con plan de evolución (ninguno bloquea Etapa 5):**
1. **Servicios en memoria no distribuidos** — `cache_service.py` y `metrics_service.py` guardan estado en la memoria del proceso; con más de una instancia de Render, cada una tendría su propio cache/métricas, inconsistentes entre sí. Evolución: migrar a Redis sin cambiar la interfaz de cada servicio.
2. **Descarga de XML/CEP síncrona** — cada `/analizar` consulta a Banxico dentro de la misma petición HTTP; a volumen alto, Banxico (no VerificaPago) se vuelve el cuello de botella. Evolución: cola de trabajos (RabbitMQ/Redis Queue) + workers.
3. **Sin autenticación real** — `DEFAULT_EMPRESA_ID` hardcodeado en cada endpoint, nada verifica la identidad de quien llama. Ya cubierto en `ROADMAP.md`, Etapa 6/7.
4. **CORS abierto** — `allow_origins=["*"]` en `main.py`. Evolución: restringir a los dominios reales antes de producción con empresas externas.
5. **Logging no estructurado** — errores registrados con `print(...)`, no con un logger centralizado. Evolución: `logging` estándar + agregación de logs.
6. **Costo económico no modelado** — cada análisis cuesta una llamada a Claude Vision, costo lineal con el volumen; sin modelo de costo unitario todavía. Es decisión de producto/pricing, no solo de infraestructura.
7. **Backups y recuperación ante desastres** — no verificados explícitamente (Supabase probablemente tiene backups por defecto, pero no está confirmado ni documentado).

**Motivo de fondo:** con 4 etapas completas y crecimiento sostenido, valía la pena confirmar antes de seguir invirtiendo en funcionalidades que no se estaba acumulando deuda técnica que forzara una migración costosa más adelante. La respuesta es que no — cada evolución identificada cambia un proveedor o una pieza interna (memoria → Redis, síncrono → cola, `print` → logger), no el modelo de datos ni la arquitectura de motores.

**Nota de alcance:** esta evaluación es una revisión de arquitectura basada en el código existente, no una auditoría de penetración ni una prueba de carga formal. Ambas valen la pena por separado cuando el proyecto se acerque a clientes empresariales reales.

**Consecuencia:** no se bloquea Etapa 5. Los hallazgos con hogar natural en seguridad (autenticación, rate limiting) ya estaban en `ROADMAP.md` Etapa 6; los puramente de infraestructura (cola, cache/métricas distribuidas, CORS, logging, costos, backups) se agregan ahí también — Etapa 6 ya funcionaba como el "bucket" de hardening pre-producción, no solo de seguridad estricta en sentido puro.

---

## 2026-07 — 🏛️ ADR: cierre del núcleo funcional de VerificaPago

**Decisión:** se declara concluido el núcleo funcional de VerificaPago. A partir de este punto, las nuevas funcionalidades deben construirse **reutilizando** los motores existentes — Motor SPEI, Motor Documental, Modelo de Decisión Explicable, Historial y el futuro Motor de Presentación — en vez de crear lógica paralela.

**Motivo:** con la Etapa 1 (experiencia de resultados) y la Etapa 2 (Historial real) cerradas y verificadas en producción, el proyecto ya tiene los bloques fundamentales que el resto del roadmap va a consumir: dos motores independientes con jerarquía de evidencia clara, un modelo de 5 capas para explicar cualquier decisión, un `AnalisisContext` reutilizable entre pantallas, y datos históricos desnormalizados y buscables. Esto marca un cambio de enfoque genuino: de **construir funcionalidades aisladas** a **expandir capacidades sobre una arquitectura consolidada**.

**Consecuencia:**
- Antes de escribir código para cualquier ítem de Etapa 3 en adelante, la pregunta de diseño por defecto es: *¿esto ya existe en alguno de los motores actuales, o reutiliza `AnalisisContext`/`MODELO_DECISION_EXPLICABLE.md`, antes de construir algo nuevo desde cero?*
- Este ADR es simbólico tanto como técnico — funciona como el punto de referencia al que se puede volver cuando, dentro de meses, alguien pregunte "¿por qué el proyecto ya no se siente como un MVP?".

---

## 2026-07 — 🏛️ ADR: se elimina la visualización del campo `recomendacion` legacy por contradecir el estado SPEI confirmado

**Decisión:** se elimina de `app/resultado/detalle/page.tsx` el bloque que mostraba `result.recomendacion` (etiquetado siempre como "Recomendación: Revisar manualmente"). El campo sigue existiendo en la respuesta del backend por compatibilidad, pero ya no se muestra en ninguna pantalla.

**Motivo:** `result.recomendacion` es un campo que Claude Vision genera como parte de su análisis inicial del comprobante — **antes** de que el backend consulte a Banxico y determine el estado SPEI final. Se detectó un caso real: una transferencia con estado SPEI `Liquidada` (confirmado vía CEP) mostraba, en `/resultado`, el mensaje correcto ("Puedes considerar el pago realizado"), pero en `/resultado/detalle` mostraba simultáneamente "Revisar manualmente... No entregar producto o servicio hasta confirmar que los fondos fueron efectivamente acreditados" — una recomendación generada sin conocimiento del resultado que el propio sistema ya había confirmado.

Esto viola dos principios ya establecidos:
- **Independencia de los 2 motores** (`MOTOR_DECISIONES.md`): el Motor 2 (documental) no debe poder emitir una instrucción que contradiga al Motor 1 (SPEI, fuente Banxico) ya confirmado.
- **"Nunca inducir al usuario a una acción cuando la evidencia todavía no lo permite"** (`MODELO_DECISION_EXPLICABLE.md`, principio 4): aquí ocurría el caso inverso — se inducía a *no actuar* (no entregar) cuando la evidencia sí lo permitía.

**Por qué no se corrige el texto en vez de eliminarlo:** el flujo de decisión de 1.4 (`Interpretación → Impacto → Recomendación inmediata`, ver `ROADMAP.md` ítem 1.2) ya resuelve exactamente esta necesidad — y lo hace correctamente, porque se calcula *después* de conocer el estado SPEI final. El campo legacy quedó huérfano cuando se construyó ese flujo, mostrando una recomendación redundante y, en casos como este, directamente contradictoria. No había necesidad de mantener dos fuentes de "qué hacer" en la misma app.

**Consecuencia:**
- `app/resultado/detalle/page.tsx` ya no renderiza `result.recomendacion`.
- El campo se mantiene en el backend (`main.py`, dentro del JSON que devuelve Claude) sin consumidor activo — candidato a eliminarse del `system_prompt` en una limpieza futura, no urgente porque no causa daño si nadie lo muestra.
- Antes de agregar cualquier mensaje de "qué hacer" en el futuro (Historial, Dashboard, Alertas), la fuente única debe ser el flujo de decisión de 1.4 (`mensajesContextuales.ts`), nunca un campo generado por el análisis documental de forma aislada.

---

## 2026-07 — 🏛️ ADR: externalización de servicios transversales (Cache y Metrics)

**Decisión:** el caché y las métricas dejan de vivir dentro de `cep_xml_auto_service.py` (donde surgió la necesidad, ítem 1.5) y se extraen a dos servicios propios y genéricos: `services/cache_service.py` (interfaz `get`/`set`/`delete`, con TTL por entrada) y `services/metrics_service.py` (`registrar_evento`, `registrar_exito`, `registrar_error`, `registrar_reintento`, `registrar_cache_hit`, `registrar_cache_miss`, `obtener_metricas`), namespaced por servicio (ej. `"xml"`).

**Motivo:** el caché y las métricas de descarga del XML no son necesidades exclusivas de ese flujo — Historial, Dashboard Empresa, validación por QR, XML manual, OCR, o el propio Motor de Presentación (Etapa 5) van a necesitar cachear resultados y medir su desempeño de la misma forma. Implementarlo dentro de `cep_xml_auto_service.py` habría significado, en unos meses, `_METRICAS_OCR`, `_METRICAS_XML`, `_METRICAS_HISTORIAL` dispersas en archivos distintos sin una interfaz común — exactamente el tipo de acoplamiento que el proyecto ha evitado desde la Fase de Fundación (servicios especializados con responsabilidad única).

**Impacto:**
- Reduce el acoplamiento: `cep_xml_auto_service.py` vuelve a ocuparse solo de hablar con Banxico (más los reintentos con backoff, que sí son lógica específica de ese flujo HTTP).
- Facilita una futura migración a Redis (cache) o Prometheus/Grafana (métricas) — el cambio queda contenido en un solo archivo por servicio, sin tocar a ningún consumidor.
- Mantiene la arquitectura modular ya establecida: `XML Service → Cache Service → Metrics Service → Banxico`, en vez de que el XML Service cargue con caché, métricas, reintentos y la llamada a Banxico todo junto.
- El endpoint de métricas se expone bajo `/api/v1/dashboard/metricas/xml`, anticipando que existirán `/metricas/ocr`, `/metricas/claude`, `/metricas/usuarios`, etc. bajo la misma estructura — no como una ruta suelta (`/xml-metricas`).
- El TTL del caché se fija en 30 minutos (no 5): un comprobante ya analizado prácticamente nunca cambia, así que el TTL prioriza ahorrar llamadas a Banxico y reducir riesgo de rate limit por encima de "frescura" del dato, que aquí no aporta valor real.
- El backoff entre reintentos usa una progresión explícita (200ms, 500ms, 1000ms) en vez de una fórmula exponencial pura, con un máximo de 3 intentos — Banxico normalmente responde en segundos, insistir más allá de eso no tiene sentido.

**Documentos afectados:** `ARQUITECTURA.md` (agrega `cache_service.py` y `metrics_service.py` a la estructura de `services/`), `ROADMAP.md` (ítem 1.5).

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