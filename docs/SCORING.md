# SCORING.md — Motor de evaluación multidimensional

## Principio de diseño

El scoring de VerificaPago **no** produce un único número que represente "qué tan falso es el comprobante". Produce cuatro señales independientes, porque mezclarlas en un solo score destruye información valiosa:

- Un comprobante puede tener **alta confianza documental** (se ve auténtico) pero **baja verificabilidad** (Banxico no lo encontró). Eso no es fraude — es falta de información.
- Un comprobante puede tener **estado SPEI = Liquidada** (Banxico confirma que el dinero llegó) pero **posible alteración documental** (el comprobante fue editado después). Eso no es fraude de la transferencia — es fraude del documento.

Separar estas señales produce resultados más honestos y más accionables para el usuario.

---

## Las 4 dimensiones

### Dimensión 1 — Confianza documental (0-100)

**Pregunta que responde:** ¿el comprobante parece auténtico como documento?

**Fuente:** Claude Vision API (análisis visual) fusionado con IAT (análisis estadístico estructural).

**Cálculo:**
```python
claude_score = result.get("score", 50)  # escala de RIESGO: 0=bajo, 100=crítico
iat_score = calculate_iat(campos, banco_origen)["iat_score"]
final_score = 0.7 * claude_score + 0.3 * iat_score  # fusión ponderada
confianza_documental = max(0, min(100, 100 - final_score))  # invertido a escala de CONFIANZA
```

**Señales que Claude Vision evalúa:** inconsistencias de tipografía, píxeles sobrepuestos o reemplazados, recortes o bordes inusuales, logos incorrectos, fechas imposibles, inconsistencias entre campos (monto en texto vs. monto en número), nombre de banco incoherente con el formato del comprobante.

**Señales del IAT:** entropía anormal de campos de texto, longitud de identificadores fuera de rango estadístico, secuencias de referencia/folio repetidas o demasiado similares a análisis previos, horarios de operación inusuales para el banco detectado.

---

### Dimensión 2 — Verificabilidad (0-100)

**Pregunta que responde:** ¿qué tan posible es corroborar esta operación externamente?

**Fuente:** consulta a Banxico (CEP HTML o XML) + presencia de identificadores en el comprobante.

**Lógica:** parte de un valor base según el estado de operación SPEI, y ajusta según los identificadores disponibles.

| Estado SPEI | Base de verificabilidad |
|---|---|
| `acreditada` | 100 |
| `liquidada` | 85 |
| `devuelta` / `en_devolucion` | 75-80 (existió, no acreditada) |
| `en_proceso` | 50 (neutro, no concluye nada) |
| `rechazada` / `cancelada` / `no_liquidada` | 65-70 (sabe con certeza el estado) |
| `desconocida` | 20 (base) + bonos por identificadores |

**Bonos cuando estado = `desconocida`:** +15 si tiene clave de rastreo, +8 si tiene referencia, +5 si tiene folio. Porque aunque Banxico no lo encontró, esos identificadores permiten una consulta manual posterior.

**Nota importante:** una verificabilidad baja no es evidencia de fraude. Es ausencia de evidencia. Estos son conceptos distintos.

---

### Dimensión 3 — Contexto temporal (0-100)

**Pregunta que responde:** ¿el tiempo transcurrido desde la fecha del comprobante es consistente con el comportamiento normal de SPEI?

**Ancla regulatoria (Circular 14/2017, art. 19a):** la ventana completa de punta a punta es de ~1-2 minutos en condiciones normales. Los cortes de banda que se usan son decisiones de producto:

| Tiempo transcurrido | Score temporal | Nota |
|---|---|---|
| < 15 minutos | 100 | Dentro de lo esperado, con margen |
| 15 min – 24 horas | 75 | Fuera de ventana, sin confirmación |
| > 24 horas | 40 | Muy fuera de ventana |

**Solo aplica penalización cuando `estado_operacion = desconocida`.** Si el estado ya fue determinado por Banxico (liquidada, devuelta, etc.), el tiempo transcurrido deja de ser relevante — la operación ya tiene una conclusión, sin importar cuándo se analice el comprobante.

---

### Dimensión 4 — Estado de la operación (categórico)

No es un score numérico. Es el resultado del Motor 1 (Estado SPEI). Ver `MOTOR_DECISIONES.md` para la tabla completa de estados, colores e interpretaciones.

---

## Campos en la respuesta del API

```json
{
  "confianza_documental": 85.0,
  "verificabilidad": 75.0,
  "contexto_temporal": 100,
  "estado_operacion": "liquidada",
  "fuente_estado": "xml_oficial",
  "nivel_evidencia": "xml_oficial",
  "semaforo_spei": { "color": "verde", "etiqueta": "Liquidada", "icono": "✅" },
  "integridad_comprobante": "con_observaciones",
  "integridad_config": { "color": "naranja", "etiqueta": "Con observaciones", "icono": "🟠" },
  "interpretacion": "El comprobante presenta alta consistencia documental...",
  "detalle_temporal": "El estado de la operación ya fue determinado...",
  "score": 24.5,
  "riesgo": "BAJO"
}
```

Los campos `score` y `riesgo` son legacy — se mantienen para compatibilidad con el frontend durante la transición al nuevo modelo de 2 motores.

---

## Implementación

- `scoring_v3.py` — Motor 2 completo: `EstadoOperacion`, `NivelEvidencia`, `evaluar_verificabilidad()`, `evaluar_contexto_temporal()`, `calcular_integridad_comprobante()`, `SEMAFORO_SPEI`, `INTEGRIDAD_CONFIG`
- `iat.py` — Motor IAT: cálculo de entropía, detección de anomalías estadísticas
- `main.py` — Orquestación: fusión de dimensiones, aplicación de jerarquía de evidencia, integración con el XML