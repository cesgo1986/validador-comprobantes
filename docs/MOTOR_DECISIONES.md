# MOTOR_DECISIONES.md — Arquitectura del motor de evaluación

## Los 2 motores independientes

VerificaPago evalúa un comprobante con dos motores que corren en paralelo y nunca se influyen mutuamente.

```
Comprobante (imagen/PDF)
         │
         ├── Motor 1: Estado SPEI ──── fuente: Banxico
         │         │                   jerarquía: XML > CEP HTML > no disponible
         │         └── estado_operacion + nivel_evidencia + semaforo_spei
         │
         └── Motor 2: Integridad documental ──── fuente: VerificaPago
                   │                              OCR + Claude Vision + IAT
                   └── integridad_comprobante + confianza_documental
```

**Regla fundamental:** el Motor 1 nunca puede ser modificado por el Motor 2. Un documento con señales graves de alteración (`posible_alteracion`) no puede degradar un estado SPEI `liquidada` a algo peor. Son preguntas distintas con fuentes distintas.

---

## Motor 1 — Estado SPEI

### Fuentes de evidencia (en orden de jerarquía)

| Nivel | Fuente | Descripción |
|---|---|---|
| `xml_oficial` | XML descargado de banxico.org.mx/cep/ | Máxima certeza. El XML es el documento oficial emitido por Banxico con cadena original y sello digital. |
| `cep_html` | Scraping del portal CEP | Alta certeza. Banxico procesó la consulta y encontró la operación. |
| `no_disponible` | Sin consulta posible | No se pudo contactar a Banxico, o faltaban datos para la consulta. |

Una fuente de nivel superior siempre reemplaza a una de nivel inferior. Una de nivel inferior nunca puede actualizar el estado establecido por una superior.

### Estados de operación SPEI

Basados en la página oficial de Banxico "Definición del estado de tu transferencia bancaria" (banxico.org.mx, sección Ley de Transparencia):

| Estado interno | Etiqueta | Color | Significado |
|---|---|---|---|
| `acreditada` | Acreditada | 🟢 Verde | CEP disponible. Evidencia máxima de acreditación. |
| `liquidada` | Liquidada | 🟢 Verde | SPEI procesó la operación. El receptor ya puede abonar. |
| `en_proceso` | En proceso | 🟡 Amarillo | SPEI recibió la instrucción, aún no liquida. |
| `devuelta` | Devuelta | 🟠 Naranja | Operación existió pero fue devuelta al emisor. |
| `en_devolucion` | En devolución | 🟠 Naranja | Devolución en curso. |
| `rechazada` | Rechazada | 🔴 Rojo | SPEI rechazó la operación. |
| `cancelada` | Cancelada | 🔴 Rojo | El banco canceló antes de liquidar. |
| `no_liquidada` | No liquidada | 🔴 Rojo | No se liquidó en la jornada, fue eliminada. |
| `desconocida` | No verificado | ⚪ Gris | No se pudo determinar el estado. |

### Tiempos regulatorios (Circular 14/2017, artículo 19a)

- El banco receptor tiene **30 segundos** (montos ≤ $8,000 MXN) o **5 segundos** (montos > $8,000 MXN) para abonar al cliente beneficiario tras recibir el Aviso de Liquidación de Banxico.
- El banco emisor tiene **30 segundos** desde que el cliente da la instrucción para introducirla al SPEI.
- El tiempo total de punta a punta esperado es de **1-2 minutos** en condiciones normales.

Estos plazos son la base del `contexto_temporal` — si han pasado horas sin confirmación y no existe evidencia de `liquidada` o `acreditada`, eso reduce la verificabilidad (no la confianza documental).

---

## Motor 2 — Integridad documental

### Componentes del análisis

**Claude Vision (claude-sonnet-4-5):** analiza la imagen del comprobante en busca de señales visuales de manipulación — inconsistencias de tipografía, píxeles sobrepuestos, recortes, logos incorrectos, fechas imposibles, etc. Devuelve un `score` de riesgo documental (0 = bajo riesgo, 100 = crítico).

**IAT (Índice de Autenticidad Transaccional):** motor estadístico propio que evalúa entropía de campos, longitud de identificadores, secuencias anómalas de referencia/folio, y horarios inusuales de operación. Complementa el análisis visual con señales estructurales.

**Fusión:** `final_score = 0.7 * claude_score + 0.3 * iat_score`, con clamping a [0, 100].

### Estados de integridad

| Estado | Umbral | Significado |
|---|---|---|
| `sin_observaciones` | confianza_documental ≥ 75 | Todo consistente, sin señales de alteración. |
| `con_observaciones` | 45 ≤ confianza_documental < 75 | Algunas señales menores, no concluyentes. Conviene revisar. |
| `posible_alteracion` | confianza_documental < 45, o anomalía IAT grave | Señales fuertes de manipulación documental. |

Los umbrales (75 y 45) son decisiones de producto, no normativa de Banxico. Pueden ajustarse con evidencia de falsos positivos/negativos en producción.

---

## Dimensiones del scoring v3

Las cuatro dimensiones son independientes entre sí. Ninguna afecta a las otras.

### 1. Confianza documental (0-100)
Inverso del `claude_score` de riesgo visual. Responde: ¿el documento parece auténtico?

### 2. Verificabilidad (0-100)
Responde: ¿qué tan corroborable es esta operación externamente? Sube con CEP encontrado, clave de rastreo válida, referencia presente. Sube +10 si el XML coincide con el comprobante sin discrepancias. **No penaliza por ausencia de evidencia** — la falta de CEP no es fraude, es ausencia de información.

### 3. Contexto temporal (0-100)
Responde: ¿el tiempo transcurrido desde la fecha del comprobante es consistente con el comportamiento normal de SPEI? Ancla regulatoria: Circular 14/2017 art.19a (30s/5s de abono). Los cortes de banda (15 min, 24h) son decisiones de producto, no de Banxico. Solo aplica penalización cuando `estado_operacion = desconocida` — si el estado ya fue determinado por Banxico, el tiempo transcurrido deja de ser relevante.

### 4. Estado de la operación (categórico)
Ver Motor 1. Este es el único campo que puede ser actualizado por una fuente de mayor jerarquía de evidencia.

---

## Semáforo categórico (resultado combinado)

Para dar al usuario una señal rápida, se calcula un semáforo que combina ambos motores por reglas explícitas (no por promedio):

| Resultado | Condición |
|---|---|
| `verificado` | estado_operacion = `acreditada` |
| `consistente` | Las 3 dimensiones numéricas ≥ 75, o estado SPEI liquidado/devuelto |
| `revisar` | Al menos una dimensión entre 45-74, sin contradicciones fuertes |
| `riesgo_alto` | confianza_documental < 45, o estado SPEI contradictorio (rechazada/cancelada/no_liquidada) |