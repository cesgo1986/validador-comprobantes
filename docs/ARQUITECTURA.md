# ARQUITECTURA.md — Arquitectura técnica de VerificaPago

**Versión del documento:** 0.24.2 · **Última actualización:** 07/07/2026

## Visión general

```
Usuario (móvil/web)
       │
       ▼
Frontend Next.js 14 App Router
(Vercel — auto-deploy desde main)
       │
       ├── /api/v1/*  ──────────────────────────────────────────────────────┐
       │                                                                     │
       ▼                                                                     │
Backend FastAPI (Python)                                                     │
(Render — auto-deploy desde main)                                           │
       │                                                                     │
       ├── Claude Vision API (Anthropic) ← OCR + análisis visual            │
       ├── Banxico CEP portal ← verificación SPEI                           │
       ├── Supabase PostgreSQL ← persistencia                               │
       └── /api/v1/dashboard/* ──────────────────────────────────────────── ┘
```

---

## Frontend

**Tecnología:** Next.js 14, App Router, TypeScript, Tailwind (utilidades base solamente), estilos inline para componentes críticos.

**Estructura de rutas:**
```
app/
├── page.tsx                     ← Pantalla 1: upload + campos opcionales
├── analizando/page.tsx          ← Pantalla 2: loading + banner fecha pasada
├── resultado/
│   ├── page.tsx                 ← Pantalla 3: semáforo + 4 dimensiones (usa components/resultado/)
│   ├── mensajesContextuales.ts  ← Catálogo de mensajes por estado SPEI (ítem 1.2)
│   ├── detalle/page.tsx         ← Pantalla 4: validaciones colapsables
│   └── comprobante/page.tsx     ← Pantalla 5/6: vista comprobante + OCR
├── historial/
│   ├── page.tsx                 ← Lista con filtros y divulgación progresiva (Etapa 2, ítem 2.1 ✅)
│   └── [id]/page.tsx            ← Detalle de análisis histórico (Etapa 2, ítem 2.3 ✅) — hidrata AnalisisContext, usa components/resultado/
├── components/
│   ├── resultado/                ← Compartido entre /resultado y /historial/[id] (refactor previo a Etapa 4, ver DECISION_LOG.md)
│   │   ├── SemaforoSpei.tsx       ← Nivel 1: semáforo SPEI
│   │   ├── QueSignificaEsto.tsx   ← Nivel 1: Interpretación + Impacto + Recomendación
│   │   └── DetalleExpandible.tsx  ← Nivel 2+: integridad, evidencias, dimensiones, diagnóstico
│   └── NavigationShell.tsx       ← Renombrado de BottomNav.tsx (2026-07, ver DECISION_LOG.md). Navegación responsive: barra fija abajo (Mobile/Tablet) o sidebar a la izquierda (Desktop+, ≥1200px) — ver .vp-nav en globals.css, y DESIGN_SYSTEM.md sección 7. Badge de Alertas conectado a /alertas/conteo (Etapa 3, ítem 3.5)
├── lib/
│   ├── estadoSpei.ts            ← Espejo de SEMAFORO_SPEI (backend), única fuente de verdad de color/etiqueta/icono fuera de /resultado
│   └── colores.ts               ← Paleta compartida (TEAL/GREEN/ORANGE/RED/GRAY), antes duplicada por archivo
├── alertas/page.tsx             ← Lista con divulgación progresiva (Etapa 3, ítem 3.4)
├── perfil/page.tsx              ← "Perfil / Empresa": Resumen ejecutivo (Etapa 4, ítem 4.2) + placeholder de gestión de cuenta (Sprint E)
├── context/AnalisisContext.tsx  ← Estado compartido entre pantallas
├── globals.css                  ← YA EXISTÍA desde el scaffold de create-next-app (trae `@import "tailwindcss"` — Tailwind está instalado pero deliberadamente no adoptado, ver DECISION_LOG.md). Design System incremental: `--vp-container-width` (contenedor responsive), `--vp-sidebar-width`, y las clases `.vp-nav`/`.vp-nav-item`/`.vp-nav-label`/`.vp-nav-plus-wrapper`/`.vp-content-area`/`.vp-page-padding` (Etapa 5, ítem 5.3 — conversión de BottomNav a sidebar)
└── layout.tsx                   ← AnalisisProvider + BottomNav
```

**Gestión de estado:** React Context (`AnalisisContext`) — el resultado del análisis se comparte entre pantallas sin usar URL params ni localStorage (que no funciona en Claude.ai artifacts y sería un punto de fallo innecesario).

---

## Backend

**Tecnología:** FastAPI, Python 3.14, SQLAlchemy 2.0, Alembic, Psycopg 3, httpx, Anthropic SDK.

**Estructura:**
```
backend/
├── main.py                      ← Endpoint /analizar + router /api/v1/dashboard/*
├── scoring_v3.py                ← Motor de evaluación: 4 dimensiones + 2 motores independientes
├── iat.py                       ← Motor IAT: análisis estadístico propio
├── database.py                  ← SQLAlchemy engine + DEFAULT_EMPRESA_ID
├── catalogo_bancos.json         ← Catálogo de bancos + config del flujo CEP (actualizable sin código)
├── models/
│   ├── empresa.py               ← Tabla empresas
│   ├── usuario.py               ← Tabla usuarios
│   ├── analisis.py              ← Tabla analisis (JSONB + columnas desnormalizadas)
│   ├── hash_documento.py        ← Tabla hashes_documentos (UNIQUE empresa_id + hash_sha256)
│   └── alerta.py                ← Tabla alertas (eventos del Alert Engine, ítem 3.2 — Etapa 3)
├── services/
│   ├── hash_service.py          ← SHA-256 del comprobante, detección de reutilización
│   ├── auditoria_service.py     ← Persistencia del análisis completo
│   ├── dashboard_service.py     ← Queries del dashboard
│   ├── cep_xml_service.py       ← Parseo y comparación del XML del CEP
│   ├── cep_xml_auto_service.py  ← Descarga automática del XML desde Banxico
│   ├── cache_service.py         ← Cache genérico en memoria (get/set/delete + TTL), reutilizable por cualquier servicio
│   ├── metrics_service.py       ← Métricas genéricas en memoria por namespace de servicio, reutilizable por cualquier servicio
│   ├── alerta_service.py        ← Persistencia de alertas (crear/listar/cambiar estado) — sin las reglas de detección, ver alert_engine/
│   └── aggregation_service.py   ← Única pieza autorizada a construir queries agregadas (Etapa 4, ítem 4.1); dashboard_service.py la consume, no la reemplaza
├── alert_engine/                ← (planeado, ítem 3.3 — Etapa 3, aún no creado) reglas de detección, cada una un archivo independiente
└── alembic/
    └── versions/
        └── ade15461db9e_*.py    ← Migración inicial multiempresa
```

---

## Base de datos

**Motor:** PostgreSQL (Supabase).
**Migraciones:** Alembic exclusivamente — `Base.metadata.create_all()` solo en desarrollo aislado.
**Comando de start en Render:** `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`

**Esquema:**
```
empresas          ← multiempresa (DEFAULT_EMPRESA_ID mientras no hay auth real)
usuarios          ← por empresa
analisis          ← resultado completo en JSONB + columnas desnormalizadas para filtros rápidos (estado_operacion/fuente_estado/nivel_evidencia y clave_rastreo/referencia/tipo_transferencia — Motor 1 e identificadores, desde 2026-07)
hashes_documentos ← UNIQUE(empresa_id, hash_sha256) — detecta reutilización entre análisis
```

---

## Flujo de análisis completo

```
1. Usuario sube comprobante (PNG/JPG/PDF)
        │
2. SHA-256 del archivo → ¿ya fue analizado antes?
        │
3. Claude Vision API → OCR + análisis visual + score de riesgo
        │
4. IAT → análisis estadístico de campos extraídos
        │
5. Fusión de scores → confianza_documental
        │
6. CLABE detectada → validación de checksum + banco
        │
7. CEP Banxico (scraping) → estado SPEI inicial (nivel: cep_html)
        │
8. Descarga automática del XML (si hay datos suficientes)
   ├── GET /cep/ → sesión
   ├── POST /cep/valida.do → validar operación
   └── GET /cep/descarga.do?formato=XML → XML oficial
        │
        ├── Si XML exitoso → actualizar estado SPEI (nivel: xml_oficial)
        │                    comparar campos vs. comprobante
        │
9. Motor 1: Estado SPEI final con nivel_evidencia
        │
10. Motor 2: Integridad documental (confianza_documental + anomalías IAT)
        │
11. Contexto temporal (Circular 14/2017 art.19a)
        │
12. Verificabilidad (base por estado + bonos por identificadores)
        │
13. Persistencia en DB (empresa_id, hash, scores, resultado JSONB)
        │
14. Respuesta JSON al frontend
```

---

## Variables de entorno

| Variable | Descripción | Dónde se configura |
|---|---|---|
| `ANTHROPIC_API_KEY` | API key de Claude | Render Environment |
| `DATABASE_URL` | PostgreSQL Supabase | Render Environment |
| `CLAUDE_MODEL` | Modelo de Claude a usar | Render Environment (default: claude-sonnet-4-5) |
| `NEXT_PUBLIC_API_URL` | URL del backend | Vercel Environment |

**Importante:** las credenciales nunca van al repositorio. El `.env` está en `.gitignore`. El historial de git fue limpiado con `git filter-repo` después de un incidente de exposición accidental de credenciales (ver `DECISION_LOG.md`).

---

## CI/CD

- **GitHub** (`cesgo1986/validador-comprobantes`, rama `main`)
- **Render** auto-deploya el backend en cada push a `main`
- **Vercel** auto-deploya el frontend en cada push a `main`
- **Alembic** corre automáticamente al inicio de cada deploy en Render

No hay pipeline de CI separado — los deploys a producción son directos desde `main`. Para cambios de riesgo se recomienda usar una rama de feature y hacer merge después de probar localmente.

---

## Evaluación de preparación para escala (2026-07)

Ver `DECISION_LOG.md`, ADR "evaluación de preparación para escala — evolución incremental, sin reescritura". Pregunta que responde esta evaluación: ¿la arquitectura actual aguanta crecer de decenas a miles de análisis diarios sin necesitar una reescritura? Respuesta corta: sí — lo que sigue es qué evoluciona y cuándo, no una lista de qué está mal.

### Lo que ya está bien, y por qué importa

- **Monolito modular, no microservicios prematuros.** Motor SPEI, Motor Documental, Alert Engine y `AggregationService` son módulos de Python dentro de un solo servicio (Render). Es la arquitectura correcta para este tamaño — separar en servicios independientes ahora sería complejidad sin beneficio real, mismo criterio que ya se aplicó para descartar Electron/Tauri en Desktop.
- **Degradación con gracia como patrón consistente.** Cache, métricas, alertas, CEP, XML — cada servicio nuevo sigue el mismo principio: si algo falla, el análisis principal se completa igual. Reduce el riesgo de fallas en cascada conforme crece el volumen.
- **Migraciones incrementales, nunca reescrituras.** Cada columna nueva llegó con su propia migración de Alembic, sin tocar retroactivamente lo que ya funcionaba.
- **No hay archivos que migrar.** Las imágenes de comprobantes nunca se persisten — se procesan en memoria y se descartan (ver Etapa 2, `historial/[id]/page.tsx`). El riesgo de "¿dónde vivirán los archivos al crecer?" no aplica.

### Riesgos identificados, con plan de evolución (sin código nuevo todavía)

| Riesgo | Estado hoy | Evolución (cuando haga falta) |
|---|---|---|
| Servicios en memoria no distribuidos | `cache_service.py` y `metrics_service.py` guardan estado en la memoria del proceso. Con más de una instancia de Render, cada una tendría su propio cache/métricas — inconsistentes entre sí. | Migrar a Redis, sin cambiar la interfaz de cada servicio (`get`/`set`/`registrar_evento` siguen igual). |
| Descarga de XML/CEP síncrona | Cada `/analizar` consulta a Banxico dentro de la misma petición HTTP. A volumen bajo no se nota; a volumen alto, Banxico se vuelve el cuello de botella, no VerificaPago. | Cola de trabajos (ej. RabbitMQ/Redis Queue + workers), desacoplando la respuesta al usuario de la consulta a Banxico. |
| Sin autenticación real | `DEFAULT_EMPRESA_ID` hardcodeado en cada endpoint. Las columnas `empresa_id` ya existen, pero nada las protege. | Ya en `ROADMAP.md`, Etapa 6/7 — JWT + API Keys. |
| CORS abierto | `allow_origins=["*"]` en `main.py`. | Restringir a los dominios reales antes de producción con empresas externas. |
| Logging no estructurado | Errores registrados con `print(...)`, no con un logger centralizado. | Migrar a `logging` estándar de Python + agregación de logs. |
| Costo económico no modelado | Cada análisis cuesta una llamada a Claude Vision — costo lineal con el volumen. | Modelar el costo unitario antes de definir planes B2B por volumen. |
| Backups y recuperación ante desastres | No verificado explícitamente — Supabase probablemente tiene backups por defecto, pero no está confirmado ni documentado. | Confirmar la política de backups y documentar el procedimiento de recuperación. |

### Lo que NO aplica (corrigiendo dos supuestos)

- **No hay archivos de comprobantes que migrar a S3/R2** — nunca se guardan.
- **Postgres no es el cuello de botella** — con los índices ya construidos en cada migración, aguanta mucho más volumen del que se anticipa a corto/mediano plazo.

**Nota de alcance:** esta evaluación no es una auditoría de penetración ni una prueba de carga — es una revisión de arquitectura basada en el código existente. Ambas valen la pena por separado cuando el proyecto se acerque a clientes empresariales reales.

---

## Documentos relacionados

- `MOTOR_DECISIONES.md` — el motor de evaluación descrito a nivel de negocio
- `SCORING.md` — el detalle de las 4 dimensiones
- `XML_CEP.md` — el detalle de la integración con Banxico
- `DECISION_LOG.md` — por qué la arquitectura es como es