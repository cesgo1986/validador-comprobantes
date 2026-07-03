"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis, EstadoOperacion } from "../context/AnalisisContext";
import { getMensajeContextual } from "./mensajesContextuales";

const TEAL = "#00BFA5";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";

function dimensionColor(score: number): string {
  if (score >= 75) return GREEN;
  if (score >= 45) return ORANGE;
  return RED;
}

// ── Jerarquía de información (rediseño 2026-07) ──────────────────────────
// Principio: la pantalla responde UNA pregunta -- "¿puedo entregar o no?"
// -- y todo lo demás es evidencia de respaldo, no protagonista.
//
// Nivel 1 (fijo, ~5 seg): ① Resultado (semáforo SPEI) + ②③④ "¿Qué
// significa esto?" (Interpretación + Impacto + Recomendación inmediata).
// Nada de integridad documental, reutilización, dimensiones ni
// diagnóstico técnico compite visualmente con esto.
//
// Nivel 2+ (expandible, bajo demanda): "Ver detalles del análisis" abre
// un panel con Integridad del comprobante, evidencias, dimensiones y
// diagnóstico técnico -- para el 5% de casos donde hace falta demostrar
// o justificar la decisión ante el cliente.
//
// La integridad documental, cuando contradice visualmente al estado SPEI
// (ej. "posible alteración" con SPEI liquidada), se redacta dando primero
// el contexto favorable y después la observación -- para no inducir al
// usuario a pensar "no debo entregar" cuando la respuesta real es sí.
export default function Resultado() {
  const router = useRouter();
  const { result, file } = useAnalisis();
  const [detallesAbiertos, setDetallesAbiertos] = useState(false);
  const [diagnosticoAbierto, setDiagnosticoAbierto] = useState(false);

  useEffect(() => {
    if (!result) router.replace("/");
  }, [result, router]);

  if (!result) return null;

  const mensaje = getMensajeContextual(result.estado_operacion);

  const descargarReporte = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte_${file?.name || "comprobante"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const spei = result.semaforo_spei;
  const colorSpei = spei?.color === "verde" ? GREEN
    : spei?.color === "amarillo" ? "#EAB308"
    : spei?.color === "naranja" ? ORANGE
    : spei?.color === "rojo" ? RED
    : "#9CA3AF";
  const speiEsFavorable = spei?.color === "verde";
  const fuenteLabel = result.nivel_evidencia === "xml_oficial"
    ? "Banxico — XML oficial"
    : result.nivel_evidencia === "cep_html"
    ? "Banxico — CEP"
    : "No verificado con Banxico";

  // Integridad documental: rojo solo con evidencia acumulada fuerte
  // (confianza < 30 O discrepancia en XML). Ver DECISION_LOG.md.
  const integ = result.integridad_config;
  const tieneXmlDiscrepante = (result as {cep_xml?: {comparacion_campos?: {discrepancias?: number}}}).cep_xml?.comparacion_campos?.discrepancias ?? 0 > 0;
  const esCasoExtremo = result.confianza_documental < 30 || tieneXmlDiscrepante;

  const integIcono = integ?.icono === "✅" ? "✓" : "⚠";
  const colorInteg = integ?.color === "verde" ? GREEN
    : integ?.color === "rojo" && esCasoExtremo ? RED
    : integ?.color === "rojo" || integ?.color === "naranja" ? "#EAB308"
    : "#9CA3AF";

  // El texto contextualiza primero el estado SPEI (si es favorable) y
  // después la observación documental, para no invertir la lectura:
  // "la operación sí fue validada; el documento tiene observaciones" en
  // vez de "posible alteración" leído en aislado.
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
  if (result.nivel_evidencia === "xml_oficial" || result.nivel_evidencia === "cep_html") {
    fuentes.push("Estado SPEI");
  }
  if (result.nivel_evidencia === "xml_oficial") {
    fuentes.push("XML oficial CEP");
    fuentes.push("Comparación de campos");
  }

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
        <button onClick={() => router.replace("/")} aria-label="Volver" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Resultado del análisis</span>
      </div>

      <div style={{ background: "#fff", borderRadius: 20, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.15)" }}>
        <div style={{ padding: "14px 18px", borderBottom: "1px solid #F0F4F8", display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>📄</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: "#1E293B", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{file?.name || "comprobante"}</div>
          </div>
        </div>

        {/* ═══ NIVEL 1 (fijo) — ① Resultado ═══════════════════════════════ */}
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

        {/* ═══ NIVEL 1 (fijo) — ②③④ ¿Qué significa esto? ═══════════════════ */}
        <div style={{ padding: "0 22px 20px" }}>
          <div style={{ background: "#F8FAFC", borderRadius: 16, padding: "18px 18px 16px", border: "1px solid #EEF2F7" }}>
            <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
              ¿Qué significa esto?
            </div>
            <p style={{ fontSize: 13.5, color: "#64748B", lineHeight: 1.6, marginBottom: 10 }}>
              {mensaje.interpretacion}
            </p>
            <p style={{ fontSize: 16, color: "#1E293B", fontWeight: 700, lineHeight: 1.5, marginBottom: mensaje.recomendacion ? 12 : 0 }}>
              {mensaje.impacto}
            </p>
            {mensaje.recomendacion && (
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 14px", background: `${TEAL}12`, border: `1px solid ${TEAL}30`, borderRadius: 10 }}>
                <span style={{ fontSize: 14 }}>👉</span>
                <span style={{ fontSize: 13, color: "#0F766E", fontWeight: 600 }}>{mensaje.recomendacion}</span>
              </div>
            )}
          </div>
        </div>

        {/* ═══ Entrada única al Nivel 2+ ════════════════════════════════════ */}
        <button onClick={() => setDetallesAbiertos(o => !o)}
          style={{ width: "calc(100% - 44px)", margin: "0 22px 22px", padding: 14, fontSize: 13.5, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#fff", color: "#334155", border: "1.5px solid #E2E8F0", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          {detallesAbiertos ? "Ocultar detalles del análisis" : "Ver detalles del análisis"}
          <span style={{ color: "#CBD5E1", fontSize: 12 }}>{detallesAbiertos ? "▲" : "▼"}</span>
        </button>

        {/* ═══ NIVEL 2+ (expandible) ════════════════════════════════════════ */}
        {detallesAbiertos && (
          <div>
            {/* Integridad del comprobante */}
            <div style={{ padding: "0 22px 18px" }}>
              <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
                Integridad del comprobante
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 13, color: colorInteg, fontWeight: 700 }}>{integIcono}</span>
                <span style={{ fontSize: 13, color: colorInteg, fontWeight: 700 }}>{integ?.etiqueta || "—"}</span>
              </div>
              <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6 }}>{integSubtexto}</div>

              {result.documento_reutilizado && (
                <div style={{ marginTop: 10, padding: "10px 14px", background: `${ORANGE}12`, border: `1px solid ${ORANGE}40`, borderRadius: 10, fontSize: 12, color: "#7C4A0A", lineHeight: 1.5 }}>
                  ⚠️ Este comprobante exacto ya fue analizado antes (visto {result.veces_visto} veces).
                </div>
              )}
            </div>

            <div style={{ height: 1, background: "#F0F4F8", margin: "0 22px 18px" }} />

            {/* Evidencias utilizadas */}
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

            {/* 4 dimensiones */}
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

            <div style={{ height: 1, background: "#F0F4F8", margin: "0 22px 4px" }} />

            {/* Diagnóstico técnico — el nivel más profundo, para auditorías/soporte */}
            <button onClick={() => setDiagnosticoAbierto(o => !o)}
              style={{ width: "100%", padding: "14px 22px", display: "flex", alignItems: "center", gap: 10, background: "none", border: "none", cursor: "pointer", textAlign: "left" }}>
              <span style={{ flex: 1, fontSize: 13, fontWeight: 600, color: "#334155" }}>Diagnóstico técnico</span>
              <span style={{ color: "#CBD5E1", fontSize: 14 }}>{diagnosticoAbierto ? "▲" : "▼"}</span>
            </button>
            {diagnosticoAbierto && (
              <div style={{ padding: "0 22px 20px" }}>
                <span style={{ fontSize: 13, color: "#475569", lineHeight: 1.7 }}>
                  {result.interpretacion || result.resumen}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Botones */}
        <div style={{ padding: "8px 22px 22px", display: "flex", flexDirection: "column", gap: 10 }}>
          <button onClick={() => router.push("/resultado/detalle")}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#F1F5F9", color: "#334155", border: "none" }}>
            Ver validaciones completas
          </button>
          <button onClick={descargarReporte}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#fff", color: "#334155", border: "1.5px solid #E2E8F0" }}>
            ⬇ Descargar reporte
          </button>
          <button onClick={() => router.push("/resultado/detalle")}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
            Siguiente →
          </button>
        </div>
      </div>
    </div>
  );
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