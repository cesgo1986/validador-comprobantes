# API.md — Documentación de endpoints

Base URL producción: `https://validador-comprobantes.onrender.com`  
Base URL local: `http://localhost:8000`

Todos los endpoints devuelven `application/json`. No requieren autenticación por ahora (Sprint B implementará JWT y API Keys).

---

## POST /analizar

Endpoint principal. Recibe un comprobante bancario, lo analiza y devuelve el resultado completo con los 2 motores independientes.

### Request

`Content-Type: multipart/form-data`

| Campo | Tipo | Requerido | Descripción |
|---|---|---|---|
| `file` | File | ✅ | Imagen del comprobante (PNG, JPG, PDF) |
| `banco_hint` | string | — | Nombre del banco emisor (ej. "BBVA", "Azteca") |
| `clabe_hint` | string | — | CLABE, número de cuenta o tarjeta (hasta 18 dígitos) |
| `fecha_pasada_confirmada` | string | — | `"true"` si el comprobante es de una fecha anterior y el usuario lo confirmó |
| `xml_cep` | File | — | XML oficial del CEP descargado de banxico.org.mx/cep/ (opcional, mejora la verificabilidad) |

### Response 200

```json
{
  "riesgo": "BAJO",
  "score": 18.5,

  "confianza_documental": 85.0,
  "verificabilidad": 75.0,
  "contexto_temporal": 100,

  "estado_operacion": "liquidada",
  "fuente_estado": "xml_oficial",
  "nivel_evidencia": "xml_oficial",
  "semaforo_spei": {
    "color": "verde",
    "etiqueta": "Liquidada",
    "icono": "✅"
  },

  "integridad_comprobante": "sin_observaciones",
  "integridad_config": {
    "color": "verde",
    "etiqueta": "Sin observaciones",
    "icono": "✅"
  },

  "interpretacion": "El comprobante presenta alta consistencia documental (85/100)...",
  "detalle_temporal": "El estado de la operación ya fue determinado independientemente...",
  "elementos_verificabilidad": ["clave de rastreo presente", "XML oficial del CEP coincide..."],

  "campos_extraidos": {
    "banco_origen": "BBVA MEXICO",
    "banco_destino": "AZTECA",
    "monto": "20",
    "fecha": "2026-06-17",
    "hora": "00:15:14",
    "clave_rastreo": "MBAN01002606170065727438",
    "referencia": "0307218423",
    "folio": "0307218423",
    "clabe_parcial": "****7331",
    "nombre_receptor": "CESAR ABRAHAM GOMEZ M",
    "concepto": "reverso"
  },

  "validaciones": [
    {
      "categoria": "cep",
      "nombre": "CEP Banxico - Verificación SPEI",
      "status": "ok",
      "detalle": "Operación localizada en Banxico con coincidencia de monto.",
      "cep_url": "https://www.banxico.org.mx/cep/..."
    }
  ],

  "cep_resultado": {
    "found": true,
    "status": "EXISTE",
    "confidence": 85,
    "match_monto": true,
    "cep_url": "https://www.banxico.org.mx/cep/..."
  },

  "cep_xml": {
    "xml_proporcionado": true,
    "origen": "automatico",
    "estructura_xml_valida": true,
    "clave_rastreo": "MBAN01002606170065727438",
    "numero_certificado_presente": "00001000000518750173",
    "comparacion_campos": {
      "total_campos_comparados": 4,
      "coincidencias": 4,
      "discrepancias": 0,
      "comparaciones": [
        { "campo": "monto", "valor_xml": 20.0, "valor_comprobante": 20.0, "coincide": true }
      ]
    },
    "nota_validacion_criptografica": "El XML contiene un número de certificado y un sello digital, pero VerificaPago no realiza validación criptográfica local..."
  },

  "clabe_resultado": {
    "valid": true,
    "bank": "AZTECA",
    "bank_code": "127",
    "clabe": "4027665005017331"
  },

  "resumen": "El comprobante presenta elementos consistentes...",
  "recomendacion": "Verificar la acreditación real consultando el CEP de Banxico...",

  "hash_documento": "ad85f0c4df3295ee3095d89275d75f1146e7e2371ba115df95c9b644d9b6da5e",
  "veces_visto": 1,
  "documento_reutilizado": false,

  "audit_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",

  "contexto_operacional": null
}
```

### Campos del resultado por categoría

**Motor 1 — Estado SPEI (fuente: Banxico)**
- `estado_operacion`: estado oficial de la transferencia (ver tabla en MOTOR_DECISIONES.md)
- `fuente_estado`: `"xml_oficial"` | `"cep_html"` | `"no_disponible"`
- `nivel_evidencia`: igual a `fuente_estado`
- `semaforo_spei`: objeto con `color`, `etiqueta` e `icono` para el frontend

**Motor 2 — Integridad documental (fuente: VerificaPago)**
- `integridad_comprobante`: `"sin_observaciones"` | `"con_observaciones"` | `"posible_alteracion"`
- `integridad_config`: objeto con `color`, `etiqueta` e `icono` para el frontend
- `confianza_documental`: 0-100, inverso del score de riesgo visual de Claude

**Dimensiones adicionales**
- `verificabilidad`: 0-100, qué tan corroborable es la operación externamente
- `contexto_temporal`: 0-100, consistencia del tiempo transcurrido con SPEI

**Legacy (compatibilidad)**
- `score`: 0-100, score de riesgo fusionado (mantenido para compatibilidad)
- `riesgo`: `"BAJO"` | `"MEDIO"` | `"ALTO"` | `"CRITICO"`

---

## GET /

Healthcheck. Devuelve el estado del servicio y el modelo de Claude en uso.

```json
{ "status": "ok", "servicio": "VerificaPago API v2", "modelo": "claude-sonnet-4-5" }
```

---

## GET /api/v1/dashboard/stats

Estadísticas generales de análisis.

**Query params:** `empresa_id` (opcional), `fecha_desde` (YYYY-MM-DD), `fecha_hasta` (YYYY-MM-DD)

```json
{
  "total_analisis": 142,
  "analisis_hoy": 8,
  "score_promedio": 23.4,
  "distribucion_riesgo": [
    { "riesgo": "BAJO", "total": 98 },
    { "riesgo": "MEDIO", "total": 31 }
  ],
  "documentos_unicos": 139,
  "documentos_reutilizados": 3
}
```

---

## GET /api/v1/dashboard/analisis

Lista paginada de análisis realizados.

**Query params:** `empresa_id`, `limit` (máx. 200, default 50), `offset`, `riesgo`, `hash_sha256`

```json
{
  "items": [
    {
      "id": "uuid",
      "created_at": "2026-06-17T00:15:14Z",
      "riesgo": "BAJO",
      "score_final": 18.5,
      "archivo_nombre": "comprobante.png",
      "banco_detectado": "BBVA",
      "monto_detectado": 20.0,
      "hash_sha256": "ad85f0c4..."
    }
  ],
  "total": 142
}
```

---

## GET /api/v1/dashboard/analisis/{analisis_id}

Detalle completo de un análisis, incluyendo el resultado JSON original y el historial del hash.

**Query params:** `empresa_id`

---

## GET /api/v1/dashboard/hashes

Documentos más reutilizados (señal de posible fraude por reuso).

**Query params:** `empresa_id`, `min_veces` (default 2), `limit` (máx. 100)

```json
[
  {
    "hash_sha256": "ad85f0c4...",
    "veces_visto": 9,
    "primer_analisis": "2026-06-01T10:00:00Z",
    "ultimo_analisis": "2026-06-17T00:15:14Z",
    "riesgo_max": "MEDIO"
  }
]
```

---

## GET /api/v1/dashboard/tendencia

Volumen de análisis por día en los últimos N días.

**Query params:** `empresa_id`, `dias` (máx. 365, default 30)

```json
[
  { "fecha": "2026-06-17", "total": 8, "score_promedio": 21.3 }
]
```

---

## Códigos de error

| Status | Descripción |
|---|---|
| `200` | Análisis completado exitosamente |
| `400` | Archivo inválido o parámetros incorrectos |
| `404` | Recurso no encontrado (en endpoints de dashboard) |
| `422` | Error de validación de parámetros (FastAPI) |
| `500` | Error interno del servidor |

Los errores de análisis (ej. Claude no pudo extraer datos, Banxico no respondió) devuelven `200` con el mejor resultado disponible — el sistema degrada con gracia, nunca falla completamente.

---

## Notas para integración B2B (futuro)

- Sprint B implementará API Keys por empresa para autenticación
- Sprint E activará el aislamiento completo por `empresa_id`
- El endpoint `/api/v1/dashboard/*` ya acepta `empresa_id` como query param — preparado para multiempresa
- CEP por lotes (`banxico.org.mx/cep-scl/`) está documentado y es viable para volúmenes altos (ver XML_CEP.md)