# LABORATORIO.md — Investigaciones y hallazgos experimentales

**Versión del documento:** 0.23.0 · **Última actualización:** 05/07/2026

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

### 2026-07 — Laboratorio de breakpoints para Presentation Expansion (ítem 5.2, Etapa 5)

**Hallazgo previo, antes de definir cualquier rango:** `app/components/BottomNav.tsx` tiene `maxWidth: 480` hardcodeado — pero solo en el elemento `<nav>`, no en el contenido de las pantallas. `/resultado`, `/historial`, `/perfil` no tienen ningún contenedor con ancho máximo propio. Consecuencia real, hoy: si se abre la app en un navegador ancho (sin simular mobile), las tarjetas blancas de contenido se estiran de borde a borde mientras la barra de navegación inferior queda centrada en 480px — dos anchos distintos en la misma pantalla. Esto se corrige antes de introducir cualquier breakpoint nuevo, no después: se necesita un contenedor de ancho máximo compartido entre el contenido y la navegación, consistente en las 4 rangos.

**Rangos definidos** (mismo criterio propuesto originalmente por ChatGPT, adoptado sin cambios en los cortes):

| Rango | Nombre | Contenedor (ancho máximo, centrado) |
|---|---|---|
| < 768px | Mobile | 480px (comportamiento actual, sin cambios) |
| 768px – 1199px | Tablet | ~720px |
| 1200px – 1599px | Desktop | ~1140px |
| ≥ 1600px | Wide Desktop | ~1400px (no crece indefinidamente — más ancho que esto solo agrega aire a los costados, no paneles nuevos) |

**Comportamiento por pantalla y rango** — respondiendo, para cada uno: ¿qué paneles aparecen? ¿qué deja de ser colapsable? ¿qué se convierte en maestro-detalle?

**`/resultado`**
- Mobile / Tablet: igual que hoy — Nivel 1 fijo (`SemaforoSpei` + `QueSignificaEsto`), Nivel 2+ detrás del botón "Ver detalles del análisis" (`DetalleExpandible` colapsado). Tablet no alcanza el ancho cómodo para 2 columnas sin verse forzado.
- Desktop / Wide Desktop: 2 columnas simultáneas — Resultado (semáforo + interpretación) a la izquierda, Evidencias (`DetalleExpandible`, siempre expandido, sin el botón de toggle) a la derecha. Ítem 5.3.

**`/historial`**
- Mobile / Tablet: igual que hoy — lista con búsqueda/filtros, tocar una tarjeta navega a la ruta `/historial/[id]`. Tablet tampoco alcanza el ancho cómodo para maestro-detalle sin que el panel de detalle se vea comprimido.
- Desktop / Wide Desktop: maestro-detalle — lista a la izquierda (más angosta), detalle a la derecha, sin navegar a una ruta separada (la URL podría seguir cambiando vía query param o ruta anidada, a decidir en 5.4, pero visualmente ambos paneles coexisten). Ítem 5.4.

**`/perfil` (Executive Summary → Dashboard Empresa)**
- Mobile / Tablet: tarjeta única de resumen (comportamiento actual).
- Desktop / Wide Desktop: se expande a Dashboard Empresa completo — gráficas, tabla, filtros, exportación, drill-down — mismos endpoints de `AggregationService` (ítem 4.1), sin backend nuevo. Wide Desktop puede mostrar más series/columnas simultáneas que Desktop, sin agregar funcionalidad nueva. Ítem 5.5.

**Navegación — decisión nueva, no propuesta originalmente por ChatGPT:** `BottomNav` (5 íconos fijos abajo) se mantiene sin cambios en Mobile y Tablet — son dispositivos táctiles donde ese patrón es esperado. En Desktop y Wide Desktop, se reorganiza como barra lateral fija (izquierda), con los mismos 5 destinos y el mismo botón `+` — es una reorganización del mismo patrón (misma información, mismos destinos), no un rediseño, consistente con el ADR "una sola experiencia, múltiples presentaciones".

**Por qué se registra como `#LAB-VP` y no directamente como ADR:** son valores de diseño (anchos de contenedor, cortes de breakpoint) que probablemente se ajustarán una o dos veces al implementar 5.3-5.5 contra pantallas reales — no una decisión arquitectónica en el sentido de origen de datos o jerarquía de motores. Si algo de esto cambia sustancialmente durante la implementación, se actualiza esta misma entrada.

**Consecuencia (decisión de diseño derivada, vigente para 5.3-5.5):**
- Antes de 5.3, se agrega un contenedor de ancho máximo compartido entre contenido y navegación (corrige el hallazgo inicial).
- Los 4 rangos y sus anchos de contenedor quedan fijos para toda la Etapa 5, salvo ajuste documentado aquí mismo.
- La conversión de `BottomNav` a barra lateral en Desktop/Wide Desktop queda decidida — se implementa en 5.3 (primer ítem que necesita el layout de escritorio).

---

### 2026-07 — Umbral del Motor de Prioridad (Evento vs. Notificación)

**Qué se decidió (sin experimento previo, criterio de arranque):** para el badge inteligente (ítem 3.5, Etapa 3), se definió que solo las alertas de severidad `MEDIA`, `ALTA` o `CRITICA` cuentan como "notificables" — `BAJA` se sigue registrando como evento (visible en la pantalla `/alertas` si el usuario filtra por ese estado), pero no incrementa el badge.

**Motivo:** el ejemplo del ADR original sigue aplicando — un hash reutilizado por segunda vez (`BAJA`, ver `regla_hash.py`) probablemente no amerita interrumpir al usuario; un hash reutilizado 5+ veces (`ALTA`) sí. Sin este corte, el badge terminaría contando cosas que no cambian ninguna decisión real, y se volvería ruido — exactamente lo que el ADR de separación Evento/Notificación buscaba evitar.

**Por qué se registra aquí y no como decisión definitiva:** el corte "MEDIA o superior" es arbitrario en el sentido de que no viene de datos — es la línea más razonable con la información disponible hoy. Si en la Beta se observa que las alertas `MEDIA` (hoy solo `CLABE_FRECUENTE`) generan demasiado ruido, o que hace falta un nivel intermedio, este es el lugar donde se documenta el ajuste.

**Consecuencia (decisión oficial derivada):** el conjunto vive como constante en código (`services/alerta_service.py`: `SEVERIDADES_NOTIFICABLES = {"MEDIA", "ALTA", "CRITICA"}`), no en base de datos — mismo criterio que los umbrales de las reglas de detección.

---

### 2026-07 — Umbrales iniciales de las reglas del Alert Engine (hipótesis, sujetas a ajuste con datos de la Beta)

**Qué se decidió (sin experimento previo, criterio de arranque):** los umbrales de las tres primeras reglas del Alert Engine (ítem 3.3, Etapa 3) se fijaron sin datos históricos reales — son un punto de partida razonable, no una conclusión validada.

- **Reutilización de hash:** severidad escala con `veces_visto` — 2ª vez = BAJA, 3-4 = MEDIA, 5+ = ALTA.
- **CLABE receptora frecuente:** 10 o más análisis con la misma CLABE en 30 días → alerta de severidad MEDIA. Umbral deliberadamente alto porque un negocio legítimo recibe pagos constantemente — se busca un salto de actividad, no el uso normal.
- **Clave de rastreo repetida:** severidad ALTA fija cuando la misma clave de rastreo aparece con **banco distinto**. La versión inicial también comparaba `monto_detectado`, pero se retiró esa comparación (ver revisión abajo) — quedó solo banco.

**Revisión (2026-07, mismo día):** se retiró la comparación por `monto_detectado` en la regla de clave de rastreo. Motivo: un monto distinto con la misma clave de rastreo es más probable que sea un error de OCR (Claude Vision leyendo mal un dígito) que evidencia real de fraude — mientras que un banco distinto con la misma clave es una contradicción estructural (la clave de rastreo codifica el banco emisor en su formato) mucho más difícil de explicar por error de lectura. Comparar solo banco reduce falsos positivos sin perder la señal que de verdad importa. Esta revisión ocurrió antes de desplegar la regla — no hubo datos reales de producción todavía que la motivaran, fue una corrección de diseño detectada en revisión.

**Por qué se registra aquí y no directamente como decisión definitiva:** estos números (10 apariciones, 30 días, los cortes de 2/3/5 para hash, y ahora "solo banco" para clave de rastreo) son exactamente el tipo de parámetro que se espera seguir ajustando en cuanto haya datos reales de la Beta. Cuando eso ocurra, la corrección se documenta como continuación de esta misma entrada, no como una investigación nueva.

**Consecuencia (decisión oficial derivada):** los umbrales viven como constantes en cada archivo de regla (`alert_engine/regla_clabe.py`: `UMBRAL_APARICIONES = 10`, `VENTANA_DIAS = 30`) — no en base de datos ni configuración externa todavía. Si durante la Beta se ajustan con frecuencia, vale la pena evaluar moverlos a `catalogo_bancos.json` o una tabla de configuración, siguiendo el mismo patrón ya usado para los parámetros del flujo CEP.

---

### 2026-07 — Falso positivo: BBVA muestra montos con signo negativo en egresos

**Qué se investigó:** por qué un comprobante legítimo de BBVA fue marcado con la validación "Monto negativo" (severidad alta, categoría estructural), a pesar de que la transferencia fue confirmada como liquidada por Banxico (estado SPEI correcto, sin discrepancias en el XML).

**Método:** revisión del comprobante real (imagen adjunta por el usuario) y del `system_prompt` que gobierna el análisis de Claude Vision en `main.py`.

**Resultado:** BBVA despliega el monto con signo negativo (ej. `-$40.00`) como convención visual para indicar que el dinero fue descontado de la cuenta (egreso) — no es una señal de alteración del documento. El `system_prompt` no distinguía este caso: la regla "Monto en cero o negativo" instruía a Claude a marcar como riesgo cualquier signo negativo, sin excepción.

**Consecuencia (decisión oficial derivada, confirmada en producción 2026-07):** se corrigió el `system_prompt` en `build_system_prompt()` (`main.py`) en tres puntos: (1) se agregó a las reglas de formatos válidos que algunos bancos muestran el monto con signo negativo para egresos y que esto no debe marcarse como riesgo; (2) se acotó la regla de "marcar como riesgo" para excluir el signo negativo consistente con esa convención; (3) se reforzó la instrucción de extracción del campo `monto` para que siempre se extraiga como valor absoluto (positivo). No se tocó lógica de backend — el problema vivía enteramente en el prompt, no en `normalize_monto_float()` ni en ninguna validación estructural de Python. Desplegado en Render y verificado contra el mismo comprobante de BBVA que originó el hallazgo: ya no marca "Monto negativo".

**Nota para crecimiento futuro:** este es el primer caso registrado de una convención de despliegue específica de un banco que generó un falso positivo. Si aparecen más casos de este tipo (otro banco con otra convención visual particular), vale la pena evaluar si conviene mantenerlos como reglas dentro del `system_prompt` (como aquí) o migrarlos a un catálogo de datos por banco — similar al patrón ya usado en `catalogo_bancos.json` para el flujo del CEP — en vez de seguir acumulando excepciones sueltas dentro del texto del prompt.

---

### 2026-06 — Validación criptográfica del sello digital del XML del CEP

**Qué se investigó:** si el certificado del SAT cuyo número de serie coincide textualmente con el que referencia el XML del CEP era, en efecto, la llave que firmó ese XML.

**Método:** operación RSA inversa pura (`sello^e mod n`) sobre el sello digital del XML, usando el módulo y exponente del certificado FIEL descargado del portal de recuperación de certificados del SAT.

**Resultado:** el bloque de 256 bytes resultante no exhibió ninguna estructura de padding reconocida (ni PKCS#1 v1.5 ni RSASSA-PSS) — el certificado del SAT no es la llave que firmó el XML. La llave privada real pertenece a la infraestructura interna de Banxico/SPEI (IES) y no está disponible públicamente.

**Consecuencia (decisión oficial derivada):** VerificaPago no realiza validación criptográfica local del XML — ver `DECISION_LOG.md`, entrada "No realizar validación criptográfica local del XML del CEP". El detalle técnico completo de la investigación (estructura del XML, hipótesis, código de la prueba) vive en `XML_CEP.md`, sección "Investigación criptográfica del sello digital" — no se duplica aquí, esta entrada solo indexa que la investigación existe y dónde está.

---

*Nuevas investigaciones se agregan arriba de esta línea a medida que ocurren, con fecha, qué se investigó, método, resultado y — si aplica — la decisión oficial derivada y dónde vive.*

---

## Documentos relacionados

- `XML_CEP.md` — destino del detalle técnico de investigaciones ya cerradas sobre el CEP
- `DECISION_LOG.md` — destino de las decisiones oficiales derivadas de una investigación
- `MOTOR_DECISIONES.md` — Motor de Comportamiento, fuente de las alertas cuyos umbrales se documentan aquí