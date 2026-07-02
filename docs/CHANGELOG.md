# CHANGELOG.md — Historial de versiones

Formato: `[versión] — fecha — descripción`. Las versiones siguen Semantic Versioning: MAJOR.MINOR.PATCH.

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