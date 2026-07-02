# ARQUITECTURA.md — Arquitectura técnica de VerificaPago

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
│   ├── page.tsx                 ← Pantalla 3: semáforo + 4 dimensiones
│   ├── detalle/page.tsx         ← Pantalla 4: validaciones colapsables
│   └── comprobante/page.tsx     ← Pantalla 5/6: vista comprobante + OCR
├── historial/page.tsx           ← Placeholder (Sprint D)
├── alertas/page.tsx             ← Placeholder (Sprint D)
├── perfil/page.tsx              ← Placeholder (Sprint E)
├── context/AnalisisContext.tsx  ← Estado compartido entre pantallas
├── components/BottomNav.tsx     ← Navegación inferior fija
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
│   └── hash_documento.py        ← Tabla hashes_documentos (UNIQUE empresa_id + hash_sha256)
├── services/
│   ├── hash_service.py          ← SHA-256 del comprobante, detección de reutilización
│   ├── auditoria_service.py     ← Persistencia del análisis completo
│   ├── dashboard_service.py     ← Queries del dashboard
│   ├── cep_xml_service.py       ← Parseo y comparación del XML del CEP
│   └── cep_xml_auto_service.py  ← Descarga automática del XML desde Banxico
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
analisis          ← resultado completo en JSONB + columnas desnormalizadas para filtros rápidos
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