# MODELO_DECISION_EXPLICABLE.md — Cómo "piensa" VerificaPago

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

## Estructura fija de presentación

Toda pantalla o componente que muestre un resultado de VerificaPago sigue el mismo orden, sin excepción:

```
Resultado
   ↓
Recomendación
   ↓
¿Cómo se llegó a este resultado?
   ↓
Ver detalles
```

Esta estructura es lo que hace que la experiencia se sienta consistente sin importar qué combinación de hechos e interpretaciones haya detrás en un caso particular.

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

Antes de agregar cualquier fuente nueva de información al sistema (un motor nuevo, una integración nueva, una señal nueva), la pregunta de diseño es: *¿en qué capa entra esto?*

- ¿Es un hecho nuevo? → se agrega a la capa 1, se expone como una evidencia más.
- ¿Cambia cómo se interpreta un hecho existente? → se ajusta la capa 2, documentado en `MOTOR_DECISIONES.md` o `SCORING.md`.
- ¿Cambia qué se le recomienda al usuario? → se ajusta la capa 3, documentado en el catálogo de mensajes contextuales (ver `ROADMAP.md`, ítem 1.2).

Si una propuesta no encaja claramente en ninguna capa, o intenta saltarse una (por ejemplo, una recomendación sin interpretación que la sustente), es señal de que rompe el modelo y debe reconsiderarse antes de implementarse.