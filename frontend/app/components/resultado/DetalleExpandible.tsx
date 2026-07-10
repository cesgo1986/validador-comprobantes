"use client";
import { useState, ReactNode } from "react";
import { Resultado } from "../../context/AnalisisContext";
import { GREEN, ORANGE, RED } from "../../lib/colores";

function dimensionColor(score: number): string {
  if (score >= 75) return GREEN;
  if (score >= 45) return ORANGE;
  return RED;
}

function DimensionCard({ label, score, sublabel }: { label: string; score: number; sublabel?: string }) {
  const color = dimensionColor(score);
  return (
    <div style={{ flex: 1, minWidth: 0, background: "#F8FAFC", borderRadius: 14, padding: 14, border: "1px solid #EEF2F7" }}>
      <div style={{ fontSize: 11, color: "#94A3B8", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 8 }}>{label}</div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 4, marginBottom: 8 }}>
        <span style={{ fontSize: 24, fontWeight: 800, color, lineHeight: 1 }}>{Math.round(score)}</span>
        <span style={{ fontSize: 12, color: "#CBD5E1", fontWeight: 600 }}>/100</span>
      </div>
      <div style={{ height: 5, background: "#E8EDF5", borderRadius: 3, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${Math.max(0, Math.min(100, score))}%`, background: color, borderRadius: 3 }} />
      </div>
      {sublabel && <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 6, lineHeight: 1.4 }}>{sublabel}</div>}
    </div>
  );
}

// Componente compartido -- refactor previo a Etapa 4 (ver DECISION_LOG.md).
// Nivel 2+ del flujo de decisión: integridad, evidencias, dimensiones,
// diagnóstico técnico.
//
// `siempreAbierto` (nuevo, item 5.3 -- Etapa 5): en Desktop/Wide Desktop,
// /resultado muestra este panel sin el botón de toggle. IMPORTANTE: esto
// NUNCA se decide en JS (no hay detección de viewport) -- se logra con
// una clase CSS (.vp-detalle-forzar-desktop) que, solo a partir de
// 1200px, oculta el botón y fuerza el contenido a visible con
// `display: block !important` (una regla de clase con !important sí
// puede ganarle a un estilo inline, al revés de lo que pasa siempre).
// Por debajo de 1200px esa regla no existe -- el toggle funciona
// exactamente igual que si `siempreAbierto` nunca se hubiera pasado.
// Por defecto es `false` -- no rompe ningún consumidor existente
// (historial/[id]/page.tsx no pasa este prop, su tratamiento de
// Desktop se decide en 5.4, no aquí).
export function DetalleExpandible({
  result,
  avisoReutilizacion,
  extra,
  siempreAbierto = false,
}: {
  result: Resultado;
  avisoReutilizacion?: ReactNode;
  extra?: ReactNode;
  siempreAbierto?: boolean;
}) {
  const [detallesAbiertos, setDetallesAbiertos] = useState(false);
  const [diagnosticoAbierto, setDiagnosticoAbierto] = useState(false);

  const spei = result.semaforo_spei;
  const speiEsFavorable = spei?.color === "verde";

  const integ = result.integridad_config;
  const tieneXmlDiscrepante = (result.evidencias?.xml_discrepancias ?? 0) > 0;
  const esCasoExtremo = result.confianza_documental < 30 || tieneXmlDiscrepante;
  const integIcono = integ?.icono === "✅" ? "✓" : "⚠";
  const colorInteg = integ?.color === "verde" ? GREEN
    : integ?.color === "rojo" && esCasoExtremo ? RED
    : integ?.color === "rojo" || integ?.color === "naranja" ? "#EAB308"
    : "#9CA3AF";
  const integSubtexto = result.integridad_comprobante === "sin_observaciones"
    ? "El comprobante es visualmente consistente."
    : result.integridad_comprobante === "con_observaciones"
    ? (speiEsFavorable
        ? "La operación sí fue validada por Banxico. El comprobante presenta algunas diferencias menores que conviene revisar."
        : "Se detectaron algunas diferencias menores en el comprobante.")
    : (speiEsFavorable
        ? `La operación sí fue validada por Banxico (${spei?.etiqueta?.toLowerCase() || "confirmada"}). El documento presenta diferencias relevantes respecto al comprobante presentado, y conviene revisarlo.`
        : esCasoExtremo
        ? "Se detectaron diferencias relevantes respecto al comprobante presentado."
        : "Se detectaron diferencias respecto al comprobante presentado.");

  const fuentes: string[] = [];
  if (result.nivel_evidencia === "xml_oficial" || result.nivel_evidencia === "cep_html") fuentes.push("Estado SPEI");
  if (result.nivel_evidencia === "xml_oficial") { fuentes.push("XML oficial CEP"); fuentes.push("Comparación de campos"); }

  return (
    <div className={siempreAbierto ? "vp-detalle-forzar-desktop" : undefined}>
      <button onClick={() => setDetallesAbiertos(o => !o)}
        className="vp-detalle-toggle-btn"
        style={{ width: "calc(100% - 44px)", margin: "0 22px 22px", padding: 14, fontSize: 13.5, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#fff", color: "#334155", border: "1.5px solid #E2E8F0", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
        {detallesAbiertos ? "Ocultar detalles del análisis" : "Ver detalles del análisis"}
        <span style={{ color: "#CBD5E1", fontSize: 12 }}>{detallesAbiertos ? "▲" : "▼"}</span>
      </button>

      <div className="vp-detalle-contenido" style={{ display: detallesAbiertos ? "block" : "none" }}>
        <div style={{ padding: "0 22px 18px" }}>
          <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
            Integridad del comprobante
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 4 }}>
            <span style={{ fontSize: 13, color: colorInteg, fontWeight: 700 }}>{integIcono}</span>
            <span style={{ fontSize: 13, color: colorInteg, fontWeight: 700 }}>{integ?.etiqueta || "—"}</span>
          </div>
          <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6 }}>{integSubtexto}</div>
          {avisoReutilizacion}
        </div>

        <div style={{ height: 1, background: "#F0F4F8", margin: "0 22px 18px" }} />

        {fuentes.length > 0 && (
          <div style={{ padding: "0 22px 18px" }}>
            <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
              ¿Cómo se llegó a este resultado?
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {fuentes.map(f => (
                <div key={f} style={{ fontSize: 12, color: "#64748B", display: "flex", alignItems: "center", gap: 6 }}>
                  <span style={{ color: GREEN, fontWeight: 700, fontSize: 13 }}>✓</span> {f}
                </div>
              ))}
            </div>
          </div>
        )}

        <div style={{ padding: "0 22px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: -2 }}>
            Dimensiones del análisis
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <DimensionCard label="Confianza documental" score={result.confianza_documental} sublabel="¿Parece auténtico?" />
            <DimensionCard label="Verificabilidad" score={result.verificabilidad} sublabel="¿Se puede corroborar?" />
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <DimensionCard label="Contexto temporal" score={result.contexto_temporal} sublabel="¿El tiempo es consistente?" />
            <DimensionCard label="Confianza fusionada" score={Math.max(0, 100 - result.score)} sublabel="Score general" />
          </div>
        </div>

        {result.detalle_temporal && (
          <div style={{ margin: "0 22px 18px", padding: "8px 12px", background: "#F8FAFC", borderRadius: 8, fontSize: 11, color: "#64748B", lineHeight: 1.5 }}>
            🕐 {result.detalle_temporal}
          </div>
        )}

        {extra}

        <div style={{ height: 1, background: "#F0F4F8", margin: "0 22px 4px" }} />

        <button onClick={() => setDiagnosticoAbierto(o => !o)}
          style={{ width: "100%", padding: "14px 22px", display: "flex", alignItems: "center", gap: 10, background: "none", border: "none", cursor: "pointer", textAlign: "left" }}>
          <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "#334155" }}>Diagnóstico técnico</span>
          <span style={{ color: "#CBD5E1", fontSize: 14 }}>{diagnosticoAbierto ? "▲" : "▼"}</span>
        </button>
        {diagnosticoAbierto && (
          <div style={{ padding: "0 22px 20px" }}>
            <span style={{ fontSize: 13, color: "#475569", lineHeight: 1.7 }}>{result.interpretacion || result.resumen}</span>
          </div>
        )}
      </div>
    </div>
  );
}