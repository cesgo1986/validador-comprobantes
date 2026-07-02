# DECISION_LOG.md — Registro de decisiones

Registro de decisiones importantes tomadas durante el desarrollo de VerificaPago. No es un changelog de código — es el "por qué" detrás de las decisiones de arquitectura y producto. Cada entrada incluye la decisión, el motivo y las consecuencias para que puedan revisarse y cuestionarse en el futuro.

---

## 2026-06 — Separar Estado SPEI de Integridad Documental

**Decisión:** el resultado de VerificaPago se divide en dos dimensiones completamente independientes: Motor 1 (Estado SPEI, fuente Banxico) y Motor 2 (Integridad del comprobante, fuente VerificaPago).

**Motivo:** un comprobante puede estar visualmente alterado aunque la transferencia SPEI haya existido y se haya liquidado. Mezclar ambas señales en un solo score produce falsos positivos inaceptables — comprobantes reales de BBVA con un concepto "inusual" terminaban clasificados como ALTO RIESGO aunque Banxico confirmara la liquidación.

**Consecuencia:**
- Banxico responde por la operación. VerificaPago responde por el documento.
- El estado SPEI nunca puede ser degradado por el análisis documental, ni siquiera si el documento presenta señales graves de alteración.
- La combinación más importante a comunicarle al usuario es: `LIQUIDADA + Posible alteración` — el dinero llegó, pero el comprobante fue manipulado después.

---

## 2026-06 — No realizar validación criptográfica local del XML del CEP

**Decisión:** VerificaPago parsea el XML oficial del CEP y compara sus campos contra el comprobante visual, pero no valida la firma digital criptográfica del XML de forma local.

**Motivo:** se realizó una prueba criptográfica real (operación RSA pura: `sello^e mod n`) con el certificado cuyo número de serie coincide con el que el XML referencia, descargado del portal del SAT. El bloque resultante no exhibió ninguna estructura de padding reconocida (ni PKCS#1 v1.5 ni RSASSA-PSS). Conclusión: ese certificado del SAT no es la llave que firmó el XML. La llave privada real pertenece a la infraestructura interna de Banxico/SPEI (IES) y no está disponible públicamente.

**Consecuencia:**
- La validación de firma oficial solo puede obtenerse a través del validador web de Banxico (`banxico.org.mx/validador-cep-spei/`).
- VerificaPago redirige al usuario a esa herramienta cuando necesita la validación criptográfica formal.
- El comentario en el código (`cep_xml_auto_service.py`) dice explícitamente: "este comportamiento puede cambiar sin previo aviso" — no "confirmado experimentalmente", para mantener un tono neutral y mantenible.

---

## 2026-06 — Jerarquía de fuentes de evidencia SPEI

**Decisión:** se establece una jerarquía formal de fuentes, implementada como `NivelEvidencia` en `scoring_v3.py`:

```
XML oficial de Banxico  (nivel máximo)
        ↓
CEP HTML / scraping     (nivel alto)
        ↓
Análisis documental     (nivel menor)
        ↓
No disponible           (sin evidencia externa)
```

Una fuente de nivel superior puede actualizar el estado SPEI. Una fuente de nivel inferior nunca puede hacerlo.

**Motivo:** garantiza que cuando el sistema obtiene el XML oficial, ese dato siempre prevalece sobre cualquier inferencia previa del scraping del CEP HTML, sin necesidad de lógica condicional compleja dispersa en el código.

**Consecuencia:** el campo `nivel_evidencia` en la respuesta del API le indica al frontend (y a cualquier consumidor futuro del API) exactamente qué tan confiable es el estado SPEI reportado.

---

## 2026-06 — Parámetros de valida.do externalizados a JSON

**Decisión:** `tipoCriterio`, `tipoConsulta`, señales de éxito del HTML, content-types válidos y catálogo de bancos viven en `catalogo_bancos.json`, no hardcodeados en el código Python.

**Motivo:** el endpoint `valida.do` de Banxico no está documentado públicamente. Sus parámetros y el HTML de respuesta pueden cambiar sin aviso. Un string hardcodeado como `"boton-descarga-xml"` rompería silenciosamente la descarga automática del XML si Banxico cambia el nombre de esa clase CSS.

**Consecuencia:** cuando Banxico cambia algo del portal, se actualiza el JSON sin necesidad de un deploy de código. El historial de Git del JSON documenta exactamente cuándo y qué cambió en el comportamiento del portal.

---

## 2026-06 — El captcha del portal CEP no se valida del lado del servidor

**Decisión:** la descarga automática del XML manda el campo `captcha` vacío en el POST a `valida.do`.

**Motivo:** investigación empírica con una instalación de prueba en Render (`banxico-test.onrender.com`): el servidor respondió con éxito (`varHideCaptcha=true` en el HTML) sin que se resolviera ningún captcha. El campo captcha existe en el HTML del formulario, pero la lógica del servidor no lo valida para este flujo específico al momento de implementar este módulo.

**Consecuencia:** este comportamiento puede cambiar. Si Banxico activa la validación del captcha, la descarga automática fallará y el sistema degradará a "no fue posible obtener el XML automáticamente", sin interrumpir el análisis principal. La traza registrada en cada petición (`traza` en la respuesta) permitirá detectar este cambio rápidamente.

---

## 2026-06 — Score legacy mantenido para compatibilidad del frontend

**Decisión:** los campos `score` y `riesgo` siguen existiendo en la respuesta del API aunque el motor v3 usa dimensiones independientes.

**Motivo:** el frontend tenía `GaugeCircle` y lógica de colores basada en `score`/`riesgo`. Eliminarlos hubiera roto producción. Se mantienen calculados a partir de las nuevas dimensiones como un campo de compatibilidad.

**Consecuencia:** en una versión futura, cuando el frontend esté completamente migrado a los 2 motores, estos campos legacy pueden eliminarse del API sin afectar la lógica del motor.

---

## 2026-07 — Semáforo de integridad documental: el rojo se reserva para evidencia acumulada fuerte

**Decisión:** en la pantalla `/resultado`, el color del indicador de integridad documental (Motor 2) ya no se mapea 1:1 desde `integridad_config.color`. Se agrega una regla de frontend: el color rojo solo se muestra cuando hay evidencia acumulada fuerte — `confianza_documental < 30` **o** el XML oficial reporta discrepancias de campo. El caso `integridad_config.color = "rojo"` sin esas condiciones (o `"naranja"`) se muestra en ámbar, no en rojo.

**Motivo:** un usuario que ve simultáneamente "🟢 Liquidada" (Motor 1) y "🔴 Posible alteración" (Motor 2) tiende a leer la combinación como contradictoria y concluye erróneamente que la transferencia no ocurrió, aunque Banxico ya la haya confirmado. Esto es el mismo problema de falsos positivos que motivó separar los dos motores (ver entrada de 2026-06 "Separar Estado SPEI de Integridad Documental"), pero manifestado en la capa de presentación en vez de en el cálculo del score.

**Consecuencia:**
- El backend no cambia — `scoring_v3.py` sigue calculando `integridad_comprobante` y `integridad_config` exactamente igual.
- La reinterpretación de color vive solo en `app/resultado/page.tsx`, como una decisión de UX, no de scoring. Si se necesita este mismo criterio en otra pantalla (ej. `/resultado/detalle` o el dashboard desktop de Sprint C), debe replicarse explícitamente ahí — no es automático.
- El subtexto explicativo bajo el indicador de integridad también se ajusta según `esCasoExtremo`, para que el texto sea consistente con el color mostrado.
- **Resuelto (2026-07):** se decidió no subir esta lógica al backend todavía. Ver la entrada siguiente, "Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores", que fija el criterio general para este caso y para futuros similares.

---

## 2026-07 — Regla arquitectónica: la lógica de presentación migra al backend solo con múltiples consumidores

**Decisión:** por ahora, la lógica que decide cómo se presenta un resultado al usuario (colores, iconos, umbrales de severidad, prioridad visual) permanece en el frontend, incluso cuando esa lógica interpreta datos que vienen del backend (ej. el criterio de "evidencia acumulada fuerte" de la entrada anterior). Se fija una regla explícita para saber cuándo debe dejar de ser así:

> Toda regla de presentación utilizada por más de un cliente (Mobile, Desktop, Dashboard, API pública) debe migrar al backend como un motor de presentación compartido. Mientras exista un único consumidor, la lógica visual puede permanecer en el frontend para facilitar la iteración del producto.

**Motivo:** la experiencia visual de `/resultado` todavía está en ajuste activo — posición del bloque, tamaño, color y prioridad visual ya cambiaron varias veces y es previsible que cambien más antes de estabilizarse. Si la severidad se sube al backend ahora mismo, cada ajuste visual implica tocar API, pruebas y despliegue del backend por un cambio que es puramente de presentación. Hoy solo existe un consumidor (Mobile), así que no hay todavía un problema de lógica duplicada que resolver — solo el costo de acoplar iteración visual a un ciclo de release más pesado.

**Paso intermedio (no es el motor de presentación, es preparación para él):** en vez de exponer un campo ya interpretado como `severidad_integridad`, el backend expondrá los **hechos crudos** que hoy se usan para decidir el color, agrupados como `evidencias`:

```json
{
  "evidencias": {
    "xml_valido": true,
    "xml_discrepancias": 0,
    "confianza_documental": 85,
    "verificabilidad": 90,
    "contexto_temporal": 100,
    "hash_reutilizado": false
  }
}
```

El frontend sigue decidiendo verde/ámbar/rojo a partir de esto. La diferencia es que la decisión se toma sobre datos explícitos y nombrados, no sobre una combinación de campos legacy (`confianza_documental`, `cep_xml.comparacion_campos.discrepancias`) leídos de forma ad hoc como hoy.

**Consecuencia:**
- No se crea `severidad_integridad` ni ningún campo de severidad pre-interpretado en esta etapa.
- El hito de "mover la lógica de presentación al backend" queda formalmente atado a Sprint C, y no como una tarea aislada — porque Sprint C es cuando aparece el segundo consumidor real (Desktop). El roadmap de Sprint C se actualiza para incluir un **Motor de Presentación**, no solo la UI de escritorio (ver `ROADMAP.md`).
- Cuando ese motor se construya, la forma esperada de la respuesta no es un campo suelto por dimensión, sino un objeto `presentation` con nivel + texto ya resueltos por el backend, consumible igual por Mobile, Desktop, Dashboard y API pública:

```json
{
  "presentation": {
    "integridad": { "nivel": "warning", "texto": "Con observaciones" },
    "spei": { "nivel": "success", "texto": "Liquidada" }
  }
}
```

- Regla de disparo para revisar esta decisión: en cuanto exista un segundo consumidor real del backend (no un prototipo — un cliente en desarrollo activo), esta decisión debe revisitarse antes de construir ese segundo cliente, no después.

---

## 2026-06 — Arquitectura multiempresa desde el inicio

**Decisión:** el esquema de base de datos incluye `empresa_id` en todas las tablas desde la primera migración, aunque la autenticación multiempresa real no existe todavía.

**Motivo:** agregar `empresa_id` a una tabla con datos existentes en producción es costoso y riesgoso. Hacerlo desde el inicio con un `DEFAULT_EMPRESA_ID` es barato y preserva la opción de activar multiempresa en el futuro sin migraciones destructivas.

**Consecuencia:** todos los endpoints del dashboard ya aceptan `empresa_id` como parámetro. Cuando se implemente autenticación real, los endpoints no necesitan cambiar — solo el frontend necesita empezar a enviar el `empresa_id` correcto.