# DESIGN_SYSTEM.md — Lenguaje visual de VerificaPago

**Versión del documento:** 0.24.8 · **Última actualización:** 07/07/2026

Este documento no describe "el diseño de Desktop". Describe el lenguaje visual único de VerificaPago — móvil y escritorio son dos presentaciones de ese mismo lenguaje, no dos productos distintos. Ver `DECISION_LOG.md`, ADR "no se diseña Desktop, se diseña el lenguaje visual definitivo de VerificaPago".

**Flujo de trabajo para todo lo que toque este documento:** `ROADMAP.md` → este documento → wireframes/mockups → validación → código. Distinto del flujo `ROADMAP → Implementación → Código` que se usa para motores y backend — un mal diseño cuesta mucho menos corregir aquí que después de implementar veinte pantallas.

---

## 1. Filosofía visual

**Minimalista + ejecutivo + confianza.** No "oscuro y tecnológico" — VerificaPago ya dejó de ser un validador de comprobantes y se está convirtiendo en una plataforma de verificación y monitoreo; el diseño debe transmitir eso.

Referencia de inspiración (Stripe, Linear, Figma): **la filosofía, no la apariencia literal.** Lo que se toma de ahí:
- Mucho espacio negativo — la información nunca se siente amontonada aunque haya mucha.
- Menos cajas con borde, más jerarquía tipográfica llevando el peso visual (tamaño, peso de fuente, color) en vez de recuadros anidados.
- Todo perfectamente alineado a una grilla — nada "flotando" sin relación con lo que lo rodea.

**Principio de espacio, no de contenido:** al ganar espacio (Desktop vs. Mobile), la pregunta correcta es *"¿qué contexto adicional muestro simultáneamente?"*, no *"¿cómo lleno este espacio?"*. Ver `DECISION_LOG.md` para la cita completa de esta distinción.

---

## 2. Jerarquía de información: lineal vs. exploratoria

**Mobile — flujo lineal:** Subir comprobante → Esperar → ¿Es válido? → Salir. Una decisión a la vez, con divulgación progresiva ocultando el detalle (patrón ya implementado: `DetalleExpandible` colapsado por defecto).

**Desktop — flujo exploratorio:** el usuario está revisando 20, 30, 100 comprobantes. Quiere comparar, detectar patrones, navegar. Ya no es "una decisión", es "una sesión de trabajo". Esto significa que en Desktop, información que en Mobile vive detrás de un toggle puede mostrarse simultáneamente — no porque "haya espacio", sino porque el modo de trabajo lo pide.

**Consecuencia práctica:** `DetalleExpandible` en Desktop se muestra sin el botón de "Ver detalles del análisis" — expandido por defecto (ver ítem 5.3, `ROADMAP.md`). El componente no cambia, cambia si el toggle envuelve o no su contenido.

---

## 3. Grid de escritorio: 3 zonas

Inspirado en el mockup de referencia (Figma/Stripe/Linear/GitHub comparten este patrón), pero **solo se construye la zona cuyo contenido ya existe realmente** — no se inventan secciones para llenar espacio.

```
┌──── Navigation ────┬──────────── Workspace ────────────┬──── Context ────┐
│                     │                                   │                 │
│  NavigationShell    │  Resultado / Historial / Alertas  │  Evidencias     │
│  (sidebar, 5        │  (el contenido principal de la    │  (DetalleExpandible,
│  destinos, ver      │  pantalla — nunca cambia entre     │  siempre visible│
│  sección 7)         │  Mobile y Desktop, solo su         │  en Desktop)    │
│                     │  distribución)                     │                 │
└─────────────────────┴───────────────────────────────────┴─────────────────┘
```

**Estado real hoy (2026-07):** Navigation y Workspace tienen contenido real y construido. La zona de Context, para `/resultado`, hoy solo tiene un candidato claro: `DetalleExpandible` expandido. Un cuarto elemento del mockup — la imagen del comprobante — **no puede vivir ahí sin resolver antes una pregunta abierta** (sección 8).

---

## 4. Espaciados

No se tokenizan valores fijos todavía (ver `DECISION_LOG.md`, ADR de Tailwind: "spacing no se tokeniza retroactivamente, se tokeniza conforme se construyen componentes nuevos"). Principio, no número: **en Desktop, más aire entre bloques que en Mobile — no los mismos paddings de Mobile estirados a un contenedor más ancho.** Cuando se construyan wireframes reales de 5.3, ahí se decide el valor concreto y se agrega a `globals.css` como token (`--vp-spacing-*`), no antes.

---

## 5. Componentes base

Los componentes de `app/components/resultado/` (`SemaforoSpei`, `QueSignificaEsto`, `DetalleExpandible`) **no se reimplementan para Desktop** — se redistribuyen. Esa es literalmente la razón por la que existen como componentes compartidos desde el refactor previo a Etapa 4 (ver `DECISION_LOG.md`).

**Reducción de cajas (pendiente de validar con wireframes):** hoy varios bloques usan `border: 1px solid #EEF2F7` para separarse entre sí. En Desktop, evaluar reemplazar por separación tipográfica/espacial (líneas divisorias delgadas o solo espacio en blanco) en vez de tarjetas anidadas dentro de tarjetas — coincide con "menos cajas, más aire" de la sección 1. No implementado todavía, es hipótesis de diseño a validar.

---

## 6. Color

Se mantiene la paleta ya existente (`app/lib/colores.ts`: `TEAL`, `GREEN`, `ORANGE`, `RED`, `GRAY`) — no se introduce una paleta nueva para Desktop. Lo que cambia es el **uso**: menos "cajas de color" (fondos de color sólido para indicar estado), más color aplicado con moderación sobre texto/íconos, dejando que la tipografía lleve la jerarquía principal.

---

## 7. `NavigationShell`

Renombrado de `BottomNav.tsx` (ver `DECISION_LOG.md`). Un componente, dos presentaciones según el viewport — el resto de la aplicación nunca sabe cuál está renderizando:

- **< 1200px (Mobile/Tablet):** barra fija abajo, horizontal, 5 destinos.
- **≥ 1200px (Desktop/Wide Desktop):** sidebar fija a la izquierda, vertical, mismos 5 destinos.

**Estado real hoy:** la bifurcación es puramente CSS (clases `.vp-nav`/`.vp-nav-item` en `globals.css`, ver `ARQUITECTURA.md`) — los 5 destinos son idénticos en contenido entre ambas presentaciones, solo cambia posición/orientación. **No existen todavía** subcomponentes `MobileNavigation`/`DesktopNavigation` separados — se introducirían el día que el *contenido* (no solo la posición) de la navegación diverja entre presentaciones (ej. Desktop agrega un destino que Mobile no tiene). Forzar esa separación hoy duplicaría el mismo `.map()` sin ninguna ganancia real.

---

## 8. Animaciones

**El escudo animado de la pantalla de análisis (`/analizando`) se queda exclusivo de Mobile.** Funciona bien ahí — transmite "el sistema está trabajando", no "estás esperando". La versión de Desktop se diseña por separado cuando se llegue a esa pantalla específica, con un criterio explícito: más conservador, más "Stripe calculando algo importante" que "app procesando" — sin especificar el detalle todavía, es tarea de prototipo/validación, no de este documento.

---

## 9. Pendiente de resolver antes de escribir código de 5.3

Preguntas abiertas, sin resolver, que hay que decidir explícitamente antes de construir la zona de Context de `/resultado` en Desktop:

- **¿Se muestra la imagen del comprobante en Desktop?** Para un análisis **recién hecho**, es técnicamente posible — `AnalisisContext.tsx` ya guarda un `preview` (blob URL en memoria) antes de que la imagen se descarte. Para un análisis **histórico** (`/historial/[id]`), es imposible — la imagen nunca se persiste (decisión de Etapa 2, `historial/[id]/page.tsx`). Si se muestra en un caso y no en el otro, la zona de Context tendría una forma distinta según el origen del análisis — hay que decidir si eso es aceptable o si se busca una alternativa (ej. mostrar solo en vivo, u omitir siempre por consistencia).
- **Qué va en la zona de Context cuando no hay imagen que mostrar** (todo el caso histórico, y potencialmente el caso en vivo si se decide no mostrarla). Candidatos sin decidir: más evidencias del XML, timeline de pasos del análisis, o dejar la zona de Context solo para cuando sí aplique.
- **Valor concreto de espaciados** (sección 4) — pendiente de wireframes reales.
- **Reducción de cajas** (sección 5) — hipótesis sin validar.
- **Animación de Desktop** (sección 8) — sin diseñar.

---

## 10. Centro Operativo — wireframe conceptual (V1, solo Nivel A)

Estructura, no código. Ver `DECISION_LOG.md` para las decisiones que originan cada bloque — este wireframe es la traducción directa de esas decisiones a pantalla, sin agregar nada nuevo.

**Aclaración sobre el grid de 3 zonas (sección 3):** ese grid es para pantallas de **un solo elemento** (`/resultado`, donde "Contexto" son las evidencias de *ese* análisis). El Centro Operativo es agregado, no tiene un elemento único — aquí solo aplican 2 zonas: Navigation (sidebar) + Workspace (todo el contenido operativo). No se fuerza una tercera columna sin nada real que mostrar.

**Alcance de V1:** solo Nivel A (Motor de Verdad — ver `DECISION_LOG.md`). Nivel 4 (estratégico) **no aparece en V1** — depende de datos de Nivel B (sucursales, clientes) que no existen todavía. No se muestra como sección vacía invitando a capturar datos; simplemente no existe hasta que haya algo real que mostrar ahí, mismo principio de "no inventar secciones para llenar espacio" (sección 3).

```
┌─ Navigation (sidebar) ──┬──────────────── Workspace ─────────────────────┐
│                          │                                                 │
│  VerificaPago            │  Martes 7 de julio de 2026                     │
│                          │                                                 │
│  Dashboard      ←activo  │  ┌─────────────────────────────────────────┐  │
│  Nuevo análisis          │  │ 🟢 Puedes seguir operando normalmente     │  │
│  Historial                │  └─────────────────────────────────────────┘  │
│  Alertas          [3]     │      (Nivel 1 — decisión más simple, sin      │
│  Perfil                   │       abrir nada. 🟠/🔴 si hay problema)      │
│                          │                                                 │
│                          │  $4,850,230 MXN                                │
│                          │  procesados hoy                    ← hero stat │
│                          │                                                 │
│                          │  1,248 pagos · 99.4% liquidados · 3 críticas   │
│                          │                        ← secundarios, Nivel 1  │
│                          │                                                 │
│                          │  ─────────────────────────────────────────    │
│                          │                                                 │
│                          │  Qué requiere atención          ← Nivel 2      │
│                          │  (solo aparece lo que aplica — si no hay        │
│                          │   nada pendiente, esta sección no existe)       │
│                          │                                                 │
│                          │  ⚠️  3 operaciones requieren revisión           │
│                          │      inmediata                  [Revisar]      │
│                          │                                                 │
│                          │  🔁  2 comprobantes reutilizados hoy [Revisar] │
│                          │                                                 │
│                          │  ─────────────────────────────────────────    │
│                          │                                                 │
│                          │  Tendencias                     ← Nivel 3      │
│                          │                                                 │
│                          │  🏦  BBVA concentra el 41% de las              │
│                          │      incidencias de hoy          [Analizar]    │
│                          │                                                 │
│                          │  📈  Hoy procesaste 18% más volumen            │
│                          │      que el promedio de la semana              │
│                          │      (informativo, sin botón — no requiere     │
│                          │       acción, solo contexto positivo)          │
│                          │                                                 │
│                          │  🔔  Las alertas aumentaron 23%                │
│                          │      respecto a ayer              [Ver causas] │
│                          │                                                 │
└──────────────────────────┴─────────────────────────────────────────────────┘
```

**Cada bloque, contra la prueba de "¿responde una pregunta o provoca una acción?":**

| Bloque | Pregunta que responde | Acción que provoca |
|---|---|---|
| Estado 🟢/🟠/🔴 | ¿Puedo operar con normalidad? | Ninguna si es 🟢; revisar si no |
| Hero stat + secundarios | ¿Cómo va mi operación hoy? | Ninguna directa — es el contexto que enmarca todo lo demás |
| "3 requieren revisión" | ¿Qué necesito atender ya? | Botón "Revisar" → filtra `/alertas` |
| "2 hashes reutilizados" | ¿Hay algo sospechoso pendiente? | Botón "Revisar" → filtra por tipo |
| "BBVA concentra 41%" | ¿Dónde está concentrado mi riesgo? | Botón "Analizar" → drill-down por banco |
| "18% más que el promedio" | ¿Cómo voy comparado con lo normal? | Ninguna — refuerzo positivo, no todo tiene que tener botón |
| "Alertas +23% vs. ayer" | ¿Está empeorando algo? | Botón "Ver causas" → alertas del día, agrupadas |

**Lo que deliberadamente NO está en este wireframe:** gráficas, tablas, filtros avanzados, exportación. Eso es real y valioso, pero es la **expansión** de este mismo Workspace cuando haya más ancho/necesidad (Wide Desktop, o cuando el usuario pida "ver más" de una tendencia específica) — no el punto de entrada. El punto de entrada responde "¿qué hago ahora?" en menos de 30 segundos, no invita a explorar.

**Pendiente, todavía sin resolver:** los destinos exactos de cada botón (¿navegan a `/alertas` con un filtro preaplicado? ¿abren un panel lateral sin navegar?) — es la siguiente decisión antes de que esto se convierta en código, y probablemente dependa de cómo termine el layout de `/historial` en 5.4.

---

## Documentos relacionados

- `DECISION_LOG.md` — los ADR que originaron este documento
- `ARQUITECTURA.md` — dónde vive `NavigationShell` y las clases de `globals.css`
- `ROADMAP.md` — Etapa 5, ítems 5.2-5.5
- `LABORATORIO.md` — laboratorio de breakpoints (ítem 5.2)