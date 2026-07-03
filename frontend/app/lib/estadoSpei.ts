// app/lib/estadoSpei.ts
// Espejo en frontend de SEMAFORO_SPEI (backend/scoring_v3.py) y de la
// tabla de MOTOR_DECISIONES.md. Si se agrega o cambia un estado SPEI en
// el backend, este archivo debe actualizarse en el mismo cambio -- es
// la única fuente de verdad del lado del frontend para pintar el estado
// SPEI fuera de /resultado (donde el backend ya manda semaforo_spei
// completo). Historial es el primer consumidor que necesita esto.

export interface SemaforoSpei {
  color: string;   // hex, ya resuelto para usar directo en style
  etiqueta: string;
  icono: string;
}

const GREEN = "#43A047";
const AMARILLO = "#EAB308";
const NARANJA = "#F5A623";
const ROJO = "#E53935";
const GRIS = "#9CA3AF";

const MAPA_ESTADO_SPEI: Record<string, SemaforoSpei> = {
  acreditada: { color: GREEN, etiqueta: "Acreditada", icono: "✅" },
  liquidada: { color: GREEN, etiqueta: "Liquidada", icono: "✅" },
  en_proceso: { color: AMARILLO, etiqueta: "En proceso", icono: "🟡" },
  devuelta: { color: NARANJA, etiqueta: "Devuelta", icono: "🟠" },
  en_devolucion: { color: NARANJA, etiqueta: "En devolución", icono: "🟠" },
  rechazada: { color: ROJO, etiqueta: "Rechazada", icono: "🔴" },
  cancelada: { color: ROJO, etiqueta: "Cancelada", icono: "🔴" },
  no_liquidada: { color: ROJO, etiqueta: "No liquidada", icono: "🔴" },
  desconocida: { color: GRIS, etiqueta: "No verificado", icono: "⚪" },
};

export function getSemaforoSpei(estadoOperacion: string | null | undefined): SemaforoSpei {
  if (!estadoOperacion) return MAPA_ESTADO_SPEI.desconocida;
  return MAPA_ESTADO_SPEI[estadoOperacion.toLowerCase()] ?? MAPA_ESTADO_SPEI.desconocida;
}