# README.md — Índice de la documentación de VerificaPago

**Versión del documento:** 0.11.0 · **Última actualización:** 02/07/2026

Este no es el README del repositorio (ese sigue viviendo en la raíz, en GitHub). Este es el punto de entrada a `/docs`: qué contiene, en qué orden leerlo, y cómo se mantiene actualizado.

---

## Estructura de `/docs`

```
docs/
├── README.md                        ← estás aquí
│
├── PRODUCTO
│   ├── PRODUCT.md                   — qué es VerificaPago, stack, filosofía de diseño
│   ├── PRODUCT_VISION.md            — visión estratégica, modelo de negocio, roadmap a 3 años
│   └── PRINCIPIOS_DE_PRODUCTO.md    — (futuro, pospuesto hasta Beta) reglas innegociables del producto
│
├── ARQUITECTURA
│   ├── ARQUITECTURA.md              — arquitectura técnica: frontend, backend, BD, CI/CD
│   ├── MOTOR_DECISIONES.md          — los 2 motores independientes (Estado SPEI + Integridad documental)
│   ├── SCORING.md                   — las 4 dimensiones del motor de evaluación
│   ├── XML_CEP.md                   — todo lo investigado sobre el CEP de Banxico y su XML
│   └── API.md                       — documentación de endpoints
│
├── DECISIONES
│   ├── DECISION_LOG.md              — el "por qué" de cada decisión de arquitectura y producto
│   └── MODELO_DECISION_EXPLICABLE.md — cómo "piensa" VerificaPago (Hechos → Interpretación → Recomendación → Evidencia)
│
├── EVOLUCIÓN
│   ├── ROADMAP.md                   — plan de desarrollo, Etapas 1-7
│   └── CHANGELOG.md                 — historial de versiones de `/docs`
│
└── LABORATORIO
    └── LABORATORIO.md               — investigaciones y hallazgos experimentales
```

---

## Orden recomendado de lectura (para alguien nuevo en el proyecto)

1. **`PRODUCT_VISION.md`** — para qué existe VerificaPago y hacia dónde va
2. **`PRODUCT.md`** — qué es concretamente, stack y filosofía de diseño
3. **`PRINCIPIOS_DE_PRODUCTO.md`** — cuando exista (Beta)
4. **`ARQUITECTURA.md`** — cómo está construido
5. **`MODELO_DECISION_EXPLICABLE.md`** — cómo razona el sistema
6. **`MOTOR_DECISIONES.md`** — el detalle de los 2 motores
7. **`SCORING.md`** — el detalle de las 4 dimensiones
8. **`XML_CEP.md`** — el detalle de la integración con Banxico
9. **`API.md`** — los endpoints concretos
10. **`DECISION_LOG.md`** — por qué se tomó cada decisión relevante en el camino
11. **`ROADMAP.md`** — qué sigue
12. **`CHANGELOG.md`** — el historial de todo lo anterior

Con este orden, cualquier desarrollador nuevo debería entender el proyecto en una o dos horas, en vez de varios días.

---

## Cómo documentamos en VerificaPago

Durante las sesiones de trabajo (Verificapago, Verificapago1.1, y cualquier sesión futura), lo que amerita quedar registrado se marca con uno de estos identificadores, para traerlo después a este chat (Arquitecto de Conocimiento):

| Marcador | Nombre | Para qué | Dónde vive |
|---|---|---|---|
| 📘 `#DOC-VP` | Documentación rutinaria | Cualquier decisión, hallazgo o ajuste que valga la pena registrar, sin importar el tamaño | `DECISION_LOG.md` o el documento correspondiente |
| 🏛️ `#ADR-VP` | Architecture Decision Record | Decisiones que cambian la arquitectura del sistema (origen de verdad de un dato, lógica que cambia de capa, jerarquía de evidencia) | `DECISION_LOG.md`, formato Decisión / Motivo / Impacto / Documentos afectados |
| 🧪 `#LAB-VP` | Investigación / hallazgo experimental | Experimentos, benchmarks, ideas descartadas — no son (todavía) una decisión oficial | `LABORATORIO.md` |
| 🎯 `#PDR-VP` *(reservado, no activo)* | Product Decision Record | Decisiones de producto que no son arquitectura ni investigación (renombrar un concepto, reordenar el roadmap, mover un entregable entre etapas) | Por definir — anotado como posible cuarto marcador, sin activar todavía |

**Regla de fondo de todos los marcadores:** cada pieza de conocimiento tiene una única fuente de verdad. Las decisiones referencian investigaciones, pero no las duplican; los documentos especializados profundizan en su dominio, el resto solo enlaza o resume cuando hace falta. Ver `DECISION_LOG.md`, principio de gobernanza documental.

---

## Política de versionado documental

`/docs` sigue Semantic Versioning, igual que el código:

- **Patch (`0.10.3`, `0.10.4`...)** — correcciones, cambios menores, actualización de texto sobre contenido ya existente.
- **Minor (`0.11.0`, `0.12.0`...)** — documento nuevo, arquitectura nueva, módulo nuevo documentado por primera vez.
- **Major (`1.0.0`)** — entrada a Beta, o cambio importante de identidad del producto.

Cada versión queda registrada en `CHANGELOG.md`. El número de versión y la fecha de "última actualización" en el encabezado de cada documento reflejan la versión de `/docs` (no la del documento individual) al momento del último cambio que lo tocó — así nadie duda cuál es el estado vigente.

---

## Estructura documental congelada

**Principio (2026-07):** no se crean documentos nuevos en `/docs` salvo que representen un dominio propio y reutilizable — el mismo criterio que ya se aplicó al crear `MODELO_DECISION_EXPLICABLE.md` y `LABORATORIO.md`. Toda funcionalidad nueva se integra primero a la estructura documental existente. Ver `DECISION_LOG.md` para el principio completo.

A partir de esta versión, `/docs` se actualiza solo cuando ocurre alguno de estos eventos — no como tarea de mantenimiento aparte:

- Aparece un módulo nuevo
- Cambia una arquitectura
- Cambia una decisión importante
- Se realiza una investigación relevante

Es decir, exactamente a través de los tres marcadores activos: 📘 `#DOC-VP`, 🏛️ `#ADR-VP`, 🧪 `#LAB-VP`.