# ROADMAP.md — Plan de desarrollo de VerificaPago

## Estado actual (post Sprint 0)

El núcleo del producto está funcionando en producción:

- ✅ OCR + análisis IA con Claude Vision
- ✅ Motor IAT (análisis estadístico propio)
- ✅ Scoring v3 con 4 dimensiones independientes
- ✅ 2 motores independientes: Estado SPEI + Integridad documental
- ✅ Jerarquía de evidencia: XML oficial > CEP HTML > análisis documental
- ✅ Descarga automática del XML del CEP desde Banxico
- ✅ Comparación XML vs. comprobante visual campo por campo
- ✅ Detección de reutilización de comprobantes (hash SHA-256)
- ✅ Flujo móvil de 6 pantallas (App Router Next.js)
- ✅ Backend multiempresa preparado (empresa_id en todas las tablas)
- ✅ Endpoints de dashboard (`/api/v1/dashboard/*`)
- ✅ Auditoría de análisis en base de datos (Supabase)
- ✅ Documentación técnica fundacional (`/docs`)

---

## Sprint A — Consolidación del núcleo

**Objetivo:** cerrar completamente la experiencia de resultados y endurecer el flujo del XML antes de crecer.

### A.1 — UX de resultados (pendiente)
- Mensajes contextuales por cada estado SPEI ("En proceso — la operación aún puede concluir correctamente, espere antes de emitir un juicio")
- Manejo explícito de intermitencias de Banxico en la UI
- Sección colapsable "Verificación XML Banxico" en `/resultado/detalle` cuando existe XML

### A.2 — Arquitectura XML (pendiente)
- Reintentos con backoff exponencial cuando `valida.do` falla por timeout
- Caché de resultado de consulta (evitar re-consultar Banxico si el mismo comprobante se analiza dos veces en minutos, usando el hash SHA-256)
- Métricas de descarga: porcentaje de éxito/fallo, tiempo promedio de respuesta

### A.3 — Observabilidad (pendiente)
- Porcentaje de XML descargados automáticamente vs. fallidos
- Tiempo promedio de análisis completo
- Causas más frecuentes de fallo en la descarga del XML
- OCR promedio y distribución de scores por banco
- Errores de scraping del CEP HTML

---

## Sprint B — Seguridad

**Objetivo:** hacer el sistema seguro para escalar a usuarios reales.

- JWT / autenticación real (hoy no existe — `DEFAULT_EMPRESA_ID` para todos)
- Rate limiting por IP y por cuenta
- Eliminación automática de imágenes tras el análisis (no almacenar comprobantes en disco)
- API Keys para acceso B2B
- Auditoría de acceso (quién consultó qué y cuándo)
- Sanitización de inputs (validación de tipos de archivo más estricta)

---

## Sprint C — Desktop

**Objetivo:** nueva experiencia para clientes empresariales que procesan volúmenes altos.

**No es adaptar la UI móvil.** Es diseñar desde cero para pantallas grandes:
- Análisis de múltiples comprobantes simultáneos
- Vista de resultados en tabla con filtros
- Integración con el historial y dashboard
- Exportación de reportes
- Workflow de aprobación/rechazo por operador

Desktop cambia el mercado: pasa de "analizo un comprobante" a "analizo 500 comprobantes diarios".

### C.1 — Motor de Presentación (backend)

Desktop es el segundo consumidor real del backend (después de Mobile). Por la regla de arquitectura fijada en `DECISION_LOG.md` ("Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores"), este es el momento de mover la lógica de colores/iconos/niveles de severidad — hoy vive solo en `app/resultado/page.tsx` — a un objeto `presentation` calculado por el backend:

```json
{
  "presentation": {
    "integridad": { "nivel": "warning", "texto": "Con observaciones" },
    "spei": { "nivel": "success", "texto": "Liquidada" }
  }
}
```

Antes de este sprint, el paso intermedio es exponer `evidencias` (hechos crudos: `xml_valido`, `xml_discrepancias`, `confianza_documental`, `verificabilidad`, `contexto_temporal`, `hash_reutilizado`) para que Mobile decida sobre datos explícitos mientras se estabiliza la UX — ver `DECISION_LOG.md`.

Sin este motor, Mobile y Desktop terminarían con dos implementaciones distintas del mismo criterio de severidad, con alto riesgo de divergir silenciosamente.

---

## Sprint D — Historial y búsqueda

**Objetivo:** conectar el historial con datos reales y hacerlo buscable.

**Nota:** el backend ya está listo (`/api/v1/dashboard/analisis` existe). Solo falta el frontend.

Funcionalidades:
- Lista de análisis con filtros (fecha, banco, riesgo, hash)
- Búsqueda por clave de rastreo, monto, banco, cuenta
- Vista de detalle de un análisis histórico
- Exportación de historial

---

## Sprint E — Multiempresa real

**Objetivo:** activar la arquitectura multiempresa que ya existe en el esquema de datos.

- Autenticación por empresa (JWT con empresa_id)
- Invitación de usuarios
- Aislamiento de datos entre empresas (el `UNIQUE(empresa_id, hash_sha256)` ya existe)
- Gestión de sucursales y permisos
- Facturación por créditos o por volumen
- API Keys por empresa para integración B2B

---

## Roadmap B2B futuro (no comprometido)

- **CEP por lotes:** `banxico.org.mx/cep-scl/` — ya investigado y documentado, viable para volúmenes altos
- **Integración Open Finance:** cuando la regulación mexicana avance
- **Módulo de contexto operativo:** consulta de estado de SPEI y conectividad de participantes vía MonSPEI (sin API pública hoy, requiere scraping del portal o acuerdo con Banxico)
- **Motor de reputación:** scoring por CLABE/cuenta basado en historial de análisis propios