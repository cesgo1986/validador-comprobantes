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

## El modelo: 4 capas

Toda respuesta de VerificaPago se puede descomponer en cuatro capas, en este orden estricto. Cada capa solo puede derivarse de la anterior — nunca al revés.

```
1. Hechos
      ↓
2. Interpretación
      ↓
3. Recomendación
      ↓
4. Evidencia (la explicación de cómo se llegó ahí)
```

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

### 3. Recomendación — ¿qué debería hacer el usuario?

Este es el valor real del producto y el que más diferencia a VerificaPago de un simple validador. No basta con mostrar el estado técnico (ej. "En proceso"); la recomendación debe responder la pregunta real del comercio: *¿entrego o no?*

Ejemplos:
- "Espere unos minutos antes de entregar el producto."
- "Puede continuar con la operación."
- "Revise el comprobante antes de aceptar el pago."

Este es el lenguaje que el usuario recuerda — no el score, no el semáforo.

### 4. Evidencia — ¿cómo se llegó a esta recomendación?

Es el componente **"¿Cómo se llegó a este resultado?"** (ver `DECISION_LOG.md` y `ROADMAP.md`, ítem 1.4). Conecta la recomendación de vuelta con los hechos e interpretaciones que la sustentan.

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
① Resultado         Liquidada
② Interpretación     La transferencia fue liquidada correctamente mediante SPEI.
③ Impacto            Puedes considerar el pago realizado.
④ Evidencias         ✓ Estado SPEI · ✓ XML · ✓ Datos · ⚠ Imagen
⑤ Detalle            (acordeón expandible con el desglose completo)
```

Este flujo de 5 pasos **es** el modelo de 4 capas de la sección anterior, expresado como experiencia de usuario en vez de como modelo de datos — con dos matices de diseño:

- **① Resultado** se muestra como paso explícito y separado, antes de interpretarlo — es el dato categórico crudo (ej. "Liquidada"), no todavía una lectura de él. En el modelo de 4 capas, es la salida visible de la capa de Hechos (específicamente el hecho principal: el estado SPEI).
- **③ Impacto** es el nombre de cara al usuario para lo que el modelo llama internamente **Recomendación**. "Impacto" responde "¿qué implica esto para mí?", un lenguaje menos directivo que "qué debo hacer" — pero cumple exactamente la misma función: traducir la interpretación en algo accionable. Los principios de este documento (sección anterior) siguen hablando de "recomendación" como término del modelo; "Impacto" es solo su etiqueta visible.
- **④ Evidencias** y **② Interpretación** corresponden 1:1 a las capas de Evidencia e Interpretación del modelo.
- **⑤ Detalle** es nuevo respecto al modelo de 4 capas — es el acordeón expandible (ya existente en `app/resultado/detalle/page.tsx`) para quien quiere profundizar más allá de lo que el flujo muestra por defecto. No es una capa de razonamiento nueva, es el mecanismo de profundidad opcional sobre la capa de Evidencia.

Esta estructura es lo que hace que la experiencia se sienta consistente sin importar qué combinación de hechos e interpretaciones haya detrás en un caso particular. Ver `ROADMAP.md`, ítem 1.4, para el diseño concreto por cada uno de los 9 estados SPEI.

---

## Principios del modelo

1. **Toda conclusión debe derivarse de hechos verificables.** Ninguna interpretación o recomendación aparece sin que existan hechos que la sustenten.
2. **Los hechos son independientes de las interpretaciones.** Un hecho no se ajusta para que la interpretación se vea mejor o peor — la relación va siempre en un solo sentido: de hecho a interpretación, nunca al revés.
3. **Las recomendaciones derivan de las interpretaciones**, no directamente de los hechos crudos. La recomendación es una traducción de la interpretación a una acción concreta para el usuario.
4. **Toda recomendación debe ser trazable a sus evidencias.** Si no se puede explicar de dónde sale una recomendación, esa recomendación no debería mostrarse.
5. **La interfaz nunca muestra una conclusión sin explicar cómo se obtuvo.** Ninguna pantalla presenta un resultado "pelón" — siempre acompañado, aunque sea de forma colapsada, de su evidencia.

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

Cada una de esas futuras fuentes entra al modelo exactamente en la capa 1 (Hechos), alimenta una interpretación en la capa 2, y aparece como una línea más en el componente de evidencia de la capa 4 — **sin rediseñar la interfaz ni la estructura de presentación.** El usuario sigue viendo "Resultado → Recomendación → ¿Cómo se llegó a este resultado? → Ver detalles", sin importar cuántas fuentes de evidencia haya detrás.

Esta es una nota de diseño para el futuro, no un compromiso de roadmap — ninguna de estas fuentes está planeada para construirse todavía (ver `ROADMAP.md`).

---

## Cómo se usa este documento en la práctica

Cuando aparezca una idea nueva — y van a aparecer muchas — antes de implementarla se responden cuatro preguntas de diagnóstico, en este orden:

1. **¿Esta idea aporta un nuevo hecho, o interpreta hechos existentes?** Si es un hecho nuevo, entra en la capa 1 como una evidencia más. Si reinterpreta hechos que ya existen, es un cambio en la capa 2.
2. **¿Modifica una recomendación, o solo agrega evidencia?** Cambiar qué se le dice al usuario que haga es un cambio de capa 3, con más peso que agregar una línea más al componente de evidencia (capa 4).
3. **¿Rompe alguno de los principios de este documento?** Revisar contra los cinco principios de la sección anterior antes de construir.
4. **¿Necesita un documento nuevo, o pertenece a uno existente?** No toda idea justifica un archivo nuevo en `docs/` — la mayoría de las veces la respuesta correcta es una entrada en `DECISION_LOG.md` o un ajuste a `MOTOR_DECISIONES.md`/`SCORING.md`/`ROADMAP.md`. Un documento nuevo se justifica solo cuando la idea define una capa de conocimiento distinta a las que ya existen (ver `PRODUCT_VISION.md` y `MODELO_DECISION_EXPLICABLE.md` como ejemplos de cuándo sí ameritó uno nuevo).

Estas cuatro preguntas son las que mantienen el crecimiento del producto ordenado — no evitan que el producto crezca, evitan que crezca sin disciplina.

Adicionalmente, antes de agregar cualquier fuente nueva de información al sistema (un motor nuevo, una integración nueva, una señal nueva), la pregunta de diseño de fondo sigue siendo: *¿en qué capa entra esto?*

- ¿Es un hecho nuevo? → se agrega a la capa 1, se expone como una evidencia más.
- ¿Cambia cómo se interpreta un hecho existente? → se ajusta la capa 2, documentado en `MOTOR_DECISIONES.md` o `SCORING.md`.
- ¿Cambia qué se le recomienda al usuario? → se ajusta la capa 3, documentado en el catálogo de mensajes contextuales (ver `ROADMAP.md`, ítem 1.2).

Si una propuesta no encaja claramente en ninguna capa, o intenta saltarse una (por ejemplo, una recomendación sin interpretación que la sustente), es señal de que rompe el modelo y debe reconsiderarse antes de implementarse.

---

## Documentos relacionados

- `MOTOR_DECISIONES.md` — la fuente de las capas 1 y 2 (Hechos e Interpretación)
- `SCORING.md` — el cálculo detrás de los hechos e interpretaciones
- `ROADMAP.md` — dónde se aplica este modelo (ítems 1.2 y 1.4 de la Etapa 1)
- `DECISION_LOG.md` (ver "Modelo de decisión explicable")