"use client";
import { Resultado } from "../../context/AnalisisContext";
import { GREEN, ORANGE, RED } from "../../lib/colores";

// Componente compartido -- refactor previo a Etapa 4 (ver DECISION_LOG.md,
// ADR "todas las vistas de análisis reutilizan el mismo modelo de
// presentación"). Extraído de resultado/page.tsx e historial/[id]/page.tsx,
// que lo tenían duplicado. Nivel 1 del flujo de decisión: el semáforo
// SPEI, protagonista de la pantalla.
export function SemaforoSpei({ result }: { result: Resultado }) {
  const spei = result.semaforo_spei;
  const colorSpei = spei?.color === "verde" ? GREEN
    : spei?.color === "amarillo" ? "#EAB308"
    : spei?.color === "naranja" ? ORANGE
    : spei?.color === "rojo" ? RED
    : "#9CA3AF";
  const fuenteLabel = result.nivel_evidencia === "xml_oficial"
    ? "Banxico — XML oficial"
    : result.nivel_evidencia === "cep_html"
    ? "Banxico — CEP"
    : "No verificado con Banxico";

  return (
    <div style={{ padding: "24px 22px 20px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ position: "relative", width: 84, height: 84, marginBottom: 12 }}>
        <svg width="84" height="84" viewBox="0 0 84 84">
          <circle cx="42" cy="42" r="36" fill="none" stroke="#E8EDF5" strokeWidth="7" />
          <circle cx="42" cy="42" r="36" fill="none" stroke={colorSpei} strokeWidth="7" strokeLinecap="round" />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: 28 }}>{spei?.icono || "⚪"}</span>
        </div>
      </div>
      <div style={{ fontSize: 28, fontWeight: 800, color: colorSpei, lineHeight: 1, marginBottom: 4 }}>
        {spei?.etiqueta || "No verificado"}
      </div>
      <div style={{ fontSize: 11, color: "#94A3B8", fontWeight: 500 }}>{fuenteLabel}</div>
    </div>
  );
}