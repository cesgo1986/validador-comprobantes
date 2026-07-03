// mensajesContextuales.ts
// Catálogo de mensajes contextuales por estado SPEI — ROADMAP.md ítem 1.2
// Modelo de referencia: MODELO_DECISION_EXPLICABLE.md (5 capas: Hechos → Interpretación → Impacto → Recomendación → Evidencia)
// Regla de fondo: nunca inducir al usuario a una acción cuando la evidencia todavía no lo permite.

export type EstadoOperacionKey =
  | "acreditada"
  | "liquidada"
  | "en_proceso"
  | "devuelta"
  | "en_devolucion"
  | "rechazada"
  | "cancelada"
  | "no_liquidada"
  | "desconocida";

export interface MensajeContextual {
  interpretacion: string;
  impacto: string;
  recomendacion?: string; // capa 4 — opcional, solo si agrega una acción concreta más allá del impacto
}

export const MENSAJES_CONTEXTUALES: Record<EstadoOperacionKey, MensajeContextual> = {
  acreditada: {
    interpretacion:
      "El banco receptor confirmó que los recursos fueron acreditados al beneficiario. Es la evidencia oficial de mayor certeza disponible.",
    impacto:
      "Puedes considerar el pago confirmado y entregar el producto o servicio con confianza.",
  },
  liquidada: {
    interpretacion:
      "La operación fue liquidada correctamente en SPEI y forma parte del registro oficial de Banxico.",
    impacto: "Puedes considerar el pago realizado. Es seguro continuar con la operación.",
  },
  en_proceso: {
    interpretacion:
      "La operación aún está siendo procesada por SPEI; todavía no hay confirmación de liquidación.",
    impacto:
      "Espera unos minutos y vuelve a consultar antes de emitir un juicio sobre la operación. Si el comprobante presenta alta integridad documental, es una señal favorable, aunque todavía no constituye confirmación oficial.",
    recomendacion: "Esperar y volver a consultar.",
  },
  devuelta: {
    interpretacion: "La operación existió, pero los recursos fueron devueltos al banco emisor.",
    impacto:
      "No consideres el pago como realizado. Pide al comprador que verifique con su banco por qué se devolvió.",
    recomendacion: "Solicitar un nuevo comprobante.",
  },
  en_devolucion: {
    interpretacion: "La devolución de esta operación está en curso — el proceso todavía no concluye.",
    impacto: "No consideres el pago como realizado todavía. Espera a que el proceso de devolución termine.",
    recomendacion: "Esperar a que concluya la devolución.",
  },
  rechazada: {
    interpretacion: "SPEI rechazó la operación — la transferencia no se procesó.",
    impacto: "No entregues el producto o servicio. Esta transferencia no ocurrió.",
  },
  cancelada: {
    interpretacion: "El banco emisor canceló la operación antes de que se liquidara.",
    impacto: "No entregues el producto o servicio. La transferencia no se completó.",
  },
  no_liquidada: {
    interpretacion: "La operación no logró liquidarse dentro del proceso establecido por SPEI.",
    impacto:
      "No consideres el pago como realizado. Solicita un comprobante actualizado o verifica directamente con el banco del comprador.",
  },
  desconocida: {
    interpretacion:
      "No fue posible obtener una confirmación oficial del estado de esta operación con Banxico. Esto puede deberse a datos insuficientes, indisponibilidad temporal del servicio o a que la operación aún no esté disponible para consulta.",
    impacto:
      "La ausencia de confirmación oficial no implica que la transferencia sea falsa ni que sea válida. Antes de entregar un producto o servicio, considera la integridad del comprobante y, si el monto lo amerita, verifica directamente con el banco o espera una nueva consulta.",
    recomendacion: "Verificar nuevamente los datos del comprobante.",
  },
};

export function getMensajeContextual(estado: string | undefined): MensajeContextual {
  const key = (estado?.toLowerCase() as EstadoOperacionKey) || "desconocida";
  return MENSAJES_CONTEXTUALES[key] ?? MENSAJES_CONTEXTUALES.desconocida;
}