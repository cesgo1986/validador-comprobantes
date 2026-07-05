"use client";
import { Resultado } from "../../context/AnalisisContext";
import { getMensajeContextual } from "../../resultado/mensajesContextuales";
import { TEAL } from "../../lib/colores";

// Componente compartido -- refactor previo a Etapa 4 (ver DECISION_LOG.md).
// Nivel 1 del flujo de decisión: Interpretación + Impacto + Recomendación
// inmediata (si aplica), usando el catálogo de mensajesContextuales.ts.
export function QueSignificaEsto({ result }: { result: Resultado }) {
  const mensaje = getMensajeContextual(result.estado_operacion);

  return (
    <div style={{ padding: "0 22px 20px" }}>
      <div style={{ background: "#F8FAFC", borderRadius: 16, padding: "18px 18px 16px", border: "1px solid #EEF2F7" }}>
        <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          ¿Qué significa esto?
        </div>
        <p style={{ fontSize: 13.5, color: "#64748B", lineHeight: 1.6, marginBottom: 10 }}>{mensaje.interpretacion}</p>
        <p style={{ fontSize: 16, color: "#1E293B", fontWeight: 700, lineHeight: 1.5, marginBottom: mensaje.recomendacion ? 12 : 0 }}>{mensaje.impacto}</p>
        {mensaje.recomendacion && (
          <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", background: `${TEAL}12`, border: `1px solid ${TEAL}30`, borderRadius: 10 }}>
            <span style={{ fontSize: 14 }}>👉</span>
            <span style={{ fontSize: 13, color: "#0F766E", fontWeight: 600 }}>{mensaje.recomendacion}</span>
          </div>
        )}
      </div>
    </div>
  );
}