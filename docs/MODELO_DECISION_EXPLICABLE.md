# MODELO_DECISION_EXPLICABLE.md — Cómo "piensa" VerificaPago

**Versión del documento:** 0.11.0 · **Última actualización:** 02/07/2026

*Documento de arquitectura de producto. Define el modelo mental detrás de cada resultado que VerificaPago presenta, independientemente de cuántos motores o algoritmos incorpore en el futuro. No describe pantallas — describe cómo VerificaPago razona.*

---

## Por qué existe este documento

VerificaPago ha evolucionado en tres etapas, sin que el equipo lo planeara explícitamente así:

1. **Un validador de comprobantes** — al inicio, respondía "¿este comprobante se ve real?"
2. **Un motor de análisis documental** — con los 2 motores independientes (Estado SPEI + Integridad documental) y las 4 dimensiones del scoring v3, empezó a responder preguntas más precisas con fuentes distintas.
3. **Un motor de decisión explicable** — hoy, el objetivo ya no es solo calcular un resultado correcto, sino que cualquier persona pueda entender *cómo* se llegó a ese resultado y *qué hacer* con él.

Ese último salto es el que este documento formaliza. Es sutil desde el código, pero enorme desde producto: cambia lo que VerificaPago promete.

---

## El modelo: 5 capas

Toda respuesta de VerificaPago se puede descomponer en cinco capas, en este orden estricto. Cada capa solo puede derivarse de la anterior — nunca al revés.

```
1. Hechos
      ↓
2. Interpretación
      ↓
3. Impacto
      ↓
4. Recomendación (solo cuando aplica)
      ↓
5. Evidencia (la explicación de cómo se llegó ahí)
```

**Nota de evolución (2026-07):** el modelo nació con 4 capas (Hechos → Interpretación → Recomendación → Evidencia). Al escribir el catálogo completo de mensajes contextuales de `ROADMAP.md` (ítem 1.2), se hizo evidente que "qué implica esto para mí" y "qué debo hacer ahora" son cosas distintas — la primera describe una consecuencia, la segunda es una acción concreta que no siempre existe. Esa distinción se formalizó separando Impacto de Recomendación. Ver `DECISION_LOG.md`.

### 1. Hechos — ¿qué sabe VerificaPago?

No son opiniones ni conclusiones. Son datos verificables, tal como llegan de sus fuentes.

Ejemplos:
- Estado SPEI: `Liquidada` — fuente: XML Banxico
- OCR: `97%` de confianza de extracción
- Imagen: sin señales de alteración detectadas
- Hash: no reutilizado
- Comparación XML: monto coincide, banco coincide, cuenta coincide, clave de rastreo coincide

Los hechos son independientes de las interpretaciones. Un hecho no cambia según cómo se decida presentarlo.

### 2. Interpretación — ¿qué concluye VerificaPago?

Aquí empieza la inteligencia del sistema: los hechos se combinan en una conclusión categórica.

Ejemplos: `integridad_comprobante` = `sin_observaciones` / `con_observaciones` / `posible_alteracion` (ver `MOTOR_DECISIONES.md`).

Una interpretación no es un dato — ya es una lectura de varios datos.

### 3. Impacto — ¿qué implica esto para mí?

Traduce la interpretación a una consecuencia concreta para el usuario, sin necesariamente decirle qué hacer todavía. Responde "¿qué significa este resultado en mi situación?", no "¿qué acción tomo ahora?".

Ejemplos:
- "Puedes considerar el pago confirmado y entregar el producto o servicio con confianza." (`acreditada`)
- "No consideres el pago como realizado. Pide al comprador que verifique con su banco por qué se devolvió." (`devuelta`)

Es el valor real del producto y el que más diferencia a VerificaPago de un simple validador: no basta con mostrar el estado técnico (ej. "En proceso"), el Impacto tiene que responder la pregunta real del comercio: *¿entrego o no?*

### 4. Recomendación — ¿qué debo hacer ahora? (capa opcional)

A diferencia de las otras cuatro capas, esta es **contextual**: aparece solo cuando hay una acción concreta e inmediata que agregar más allá de lo que ya dice el Impacto. Su ausencia también es información — significa que no hace falta ninguna acción adicional.

Ejemplos:
- `en_proceso` → "Esperar y volver a consultar."
- `devuelta` → "Solicitar un nuevo comprobante."
- `desconocida` → "Verificar nuevamente los datos del comprobante."
- `liquidada` → *(no aplica — el Impacto ya es autosuficiente, no hay una acción adicional que dar)*

Esta capa elimina una pregunta mental adicional que el usuario haría de todos modos: *"¿y ahora qué hago?"* — respondiéndola de forma explícita en vez de dejarla implícita en el tono del Impacto.

### 5. Evidencia — ¿cómo se llegó a esta conclusión?

Es el componente **"¿Cómo se llegó a este resultado?"** (ver `DECISION_LOG.md` y `ROADMAP.md`, ítem 1.4). Conecta el Impacto y la Recomendación de vuelta con los hechos e interpretaciones que los sustentan.

```
¿Cómo se llegó a este resultado?

✓ XML Banxico
✓ OCR
✓ IA
⚠ Documento con observaciones
```

---

## Estructura fija de presentación: el flujo de decisión

Toda pantalla o componente que muestre un resultado de VerificaPago sigue el mismo flujo, sin excepción. No se piensa como una lista de datos — se piensa como una conversación, porque el usuario no piensa en preguntas, piensa en *"¿qué pasó?"*:

```
① Resultado              Liquidada
② Interpretación          La transferencia fue liquidada correctamente mediante SPEI.
③ Impacto                 Puedes considerar el pago realizado.
④ Recomendación inmediata (solo si aplica) — ej. "Esperar y volver a consultar."
⑤ Evidencias              ✓ Estado SPEI · ✓ XML · ✓ Datos · ⚠ Imagen
⑥ Detalle                 (acordeón expandible con el desglose completo)
```

Este flujo de 6 pasos **es** el modelo de 5 capas de la sección anterior, expresado como experiencia de usuario en vez de como modelo de datos:

- **① Resultado** es la salida visible de la capa de Hechos (específicamente el hecho principal: el estado SPEI) — se muestra como paso explícito y separado, antes de interpretarlo.
- **② Interpretación**, **③ Impacto**, **④ Recomendación inmediata** y **⑤ Evidencias** corresponden 1:1 a las capas 2, 3, 4 y 5 del modelo. Ninguna es un alias de otra — Impacto y Recomendación son capas distintas (ver sección anterior).
- **④ Recomendación inmediata** hereda el carácter opcional de la capa 4: solo aparece cuando agrega una acción concreta más allá de lo que ya dice el Impacto.
- **⑥ Detalle** es el acordeón expandible (ya existente en `app/resultado/detalle/page.tsx`) para quien quiere profundizar más allá de lo que el flujo muestra por defecto. No es una capa de razonamiento nueva, es el mecanismo de profundidad opcional sobre la capa de Evidencia.

Esta estructura es lo que hace que la experiencia se sienta consistente sin importar qué combinación de hechos e interpretaciones haya detrás en un caso particular. Ver `ROADMAP.md`, ítem 1.2, para el catálogo completo aplicado a los 9 estados SPEI.

---

## Principios del modelo

1. **Toda conclusión debe derivarse de hechos verificables.** Ninguna interpretación, impacto o recomendación aparece sin que existan hechos que la sustenten.
2. **Los hechos son independientes de las interpretaciones.** Un hecho no se ajusta para que la interpretación se vea mejor o peor — la relación va siempre en un solo sentido: de hecho a interpretación, nunca al revés.
3. **El impacto deriva de la interpretación**, no directamente de los hechos crudos. **La recomendación, cuando existe, deriva del impacto** — es la acción concreta que se desprende de la consecuencia ya descrita, no una capa independiente.
4. **Nunca inducir al usuario a una acción cuando la evidencia todavía no lo permite.** Ni el Impacto ni la Recomendación afirman más certeza de la que los Hechos y la Interpretación realmente sostienen — la ausencia de confirmación se comunica como ausencia de confirmación, no como riesgo ni como validez.
5. **Toda conclusión debe ser trazable a sus evidencias.** Si no se puede explicar de dónde sale una interpretación, un impacto o una recomendación, esa conclusión no debería mostrarse.
6. **La interfaz nunca muestra una conclusión sin explicar cómo se obtuvo.** Ninguna pantalla presenta un resultado "pelón" — siempre acompañado, aunque sea de forma colapsada, de su evidencia.

Esta regla de producto ya existía de forma más acotada en la entrada de `DECISION_LOG.md` sobre "¿Cómo se llegó a este resultado?" ("toda conclusión debe poder justificarse con al menos una evidencia verificable") — este documento la generaliza a las cuatro capas completas del modelo.

---

## Por qué este modelo escala sin complicar la interfaz

El componente de evidencia no muestra **módulos** del sistema. Muestra **evidencias**. Esa distinción es la que permite que VerificaPago crezca sin que la interfaz se vuelva más compleja.

Hoy el sistema tiene dos fuentes de hechos: Estado SPEI e Integridad documental. En el futuro podría incorporar, por ejemplo:

- Historial del emisor
- Historial del beneficiario
- Patrón de pagos
- Frecuencia de operación
- Score de riesgo por cuenta/CLABE
- Motor antifraude

Cada una de esas futuras fuentes entra al modelo exactamente en la capa 1 (Hechos), alimenta una interpretación en la capa 2, y aparece como una línea más en el componente de evidencia de la capa 5 — **sin rediseñar la interfaz ni la estructura de presentación.** El usuario sigue viendo "Resultado → Interpretación → Impacto → Recomendación → Evidencias → Detalle", sin importar cuántas fuentes de evidencia haya detrás.

Esta es una nota de diseño para el futuro, no un compromiso de roadmap — ninguna de estas fuentes está planeada para construirse todavía (ver `ROADMAP.md`).

---

## Cómo se usa este documento en la práctica

Cuando aparezca una idea nueva — y van a aparecer muchas — antes de implementarla se responden cuatro preguntas de diagnóstico, en este orden:

1. **¿Esta idea aporta un nuevo hecho, o interpreta hechos existentes?** Si es un hecho nuevo, entra en la capa 1 como una evidencia más. Si reinterpreta hechos que ya existen, es un cambio en la capa 2.
2. **¿Modifica el impacto o la recomendación, o solo agrega evidencia?** Cambiar qué implica un resultado (capa 3) o qué acción se recomienda (capa 4) tiene más peso que agregar una línea más al componente de evidencia (capa 5).
3. **¿Rompe alguno de los principios de este documento?** Revisar contra los seis principios de la sección anterior antes de construir.
4. **¿Necesita un documento nuevo, o pertenece a uno existente?** No toda idea justifica un archivo nuevo en `docs/` — la mayoría de las veces la respuesta correcta es una entrada en `DECISION_LOG.md` o un ajuste a `MOTOR_DECISIONES.md`/`SCORING.md`/`ROADMAP.md`. Un documento nuevo se justifica solo cuando la idea define una capa de conocimiento distinta a las que ya existen (ver `PRODUCT_VISION.md` y `MODELO_DECISION_EXPLICABLE.md` como ejemplos de cuándo sí ameritó uno nuevo).

Estas cuatro preguntas son las que mantienen el crecimiento del producto ordenado — no evitan que el producto crezca, evitan que crezca sin disciplina.

Adicionalmente, antes de agregar cualquier fuente nueva de información al sistema (un motor nuevo, una integración nueva, una señal nueva), la pregunta de diseño de fondo sigue siendo: *¿en qué capa entra esto?*

- ¿Es un hecho nuevo? → se agrega a la capa 1, se expone como una evidencia más.
- ¿Cambia cómo se interpreta un hecho existente? → se ajusta la capa 2, documentado en `MOTOR_DECISIONES.md` o `SCORING.md`.
- ¿Cambia qué implica el resultado para el usuario, o qué se le recomienda hacer? → se ajusta la capa 3 (Impacto) o la capa 4 (Recomendación), documentado en el catálogo de mensajes contextuales (ver `ROADMAP.md`, ítem 1.2).

Si una propuesta no encaja claramente en ninguna capa, o intenta saltarse una (por ejemplo, una recomendación sin interpretación que la sustente), es señal de que rompe el modelo y debe reconsiderarse antes de implementarse.

---

## Documentos relacionados

- `MOTOR_DECISIONES.md` — la fuente de las capas 1 y 2 (Hechos e Interpretación)
- `SCORING.md` — el cálculo detrás de los hechos e interpretaciones
- `ROADMAP.md` — dónde se aplica este modelo (ítems 1.2 y 1.4 de la Etapa 1)
- `DECISION_LOG.md` (ver "Modelo de decisión explicable")