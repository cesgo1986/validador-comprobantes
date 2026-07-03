"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAnalisis, Resultado } from "../../context/AnalisisContext";
import { getMensajeContextual } from "../../resultado/mensajesContextuales";

const TEAL = "#00BFA5";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface HistorialHash {
  veces_visto: number;
  primer_analisis: string;
  ultimo_analisis: string;
}

interface AnalisisDetalle {
  id: string;
  fecha: string | null;
  hash_sha256: string | null;
  archivo_nombre: string | null;
  archivo_tipo: string | null;
  banco_detectado: string | null;
  monto_detectado: number | null;
  clabe_detectada: string | null;
  riesgo: string | null;
  estado_operacion: string | null;
  fuente_estado: string | null;
  nivel_evidencia: string | null;
  resultado: Resultado;
  historial_hash: HistorialHash | null;
}

function dimensionColor(score: number): string {
  if (score >= 75) return GREEN;
  if (score >= 45) return ORANGE;
  return RED;
}

function formatearFecha(fechaISO: string | null): string {
  if (!fechaISO) return "";
  const d = new Date(fechaISO);
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" }) +
    " · " + d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function etiquetaFuenteEstado(fuente: string | null): string {
  switch (fuente) {
    case "xml_oficial": return "XML oficial de Banxico";
    case "cep_html": return "CEP de Banxico (scraping)";
    case "no_disponible": return "No disponible";
    default: return fuente || "—";
  }
}

function formatearMonto(monto: number | null): string {
  if (monto === null || monto === undefined) return "—";
  return "$" + monto.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ── Vista de detalle de un análisis histórico (ítem 2.3, Etapa 2) ─────────
// Reutiliza la misma jerarquía de divulgación progresiva y el mismo
// lenguaje visual que /resultado (ver DECISION_LOG.md, ADR de divulgación
// progresiva). Al montar, hidrata el AnalisisContext con el resultado
// histórico (setResult) para que "Ver validaciones completas" navegue a
// /resultado/detalle sin tocar ese archivo.
//
// Nota de arquitectura (pendiente, no bloqueante): el bloque central de
// esta pantalla duplica una parte significativa del JSX de
// resultado/page.tsx. Se decidió NO extraerlo a un componente compartido
// en esta etapa para no tocar un archivo ya estable en producción bajo
// presión de tiempo -- queda anotado en ROADMAP.md como refactor
// pendiente antes de que exista un tercer consumidor (Dashboard Empresa).
//
// Por privacidad, VerificaPago no almacena imágenes de comprobantes una
// vez concluido el análisis -- por eso esta vista no tiene "Ver
// comprobante". No es una limitación técnica, es una decisión de diseño.
export default function HistorialDetalle() {
  const router = useRouter();
  const params = useParams();
  const { setResult } = useAnalisis();

  const [detalle, setDetalle] = useState<AnalisisDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detallesAbiertos, setDetallesAbiertos] = useState(false);
  const [diagnosticoAbierto, setDiagnosticoAbierto] = useState(false);

  useEffect(() => {
    async function cargar() {
      setCargando(true);
      setError(null);
      try {
        const resp = await fetch(`${API_URL}/api/v1/dashboard/analisis/${params.id}`);
        if (resp.status === 404) {
          setError("Este análisis no existe o fue eliminado.");
          return;
        }
        if (!resp.ok) throw new Error();
        const data: AnalisisDetalle = await resp.json();
        setDetalle(data);
        setResult(data.resultado);
      } catch {
        setError("No se pudo cargar este análisis. Intenta de nuevo.");
      } finally {
        setCargando(false);
      }
    }
    if (params.id) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  const descargarReporte = () => {
    if (!detalle) return;
    const blob = new Blob([JSON.stringify(detalle.resultado, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte_${detalle.archivo_nombre || "comprobante"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (cargando) {
    return (
      <div style={{ padding: "16px", textAlign: "center", paddingTop: 60 }}>
        <span style={{ color: "rgba(255,255,255,0.6)", fontSize: 13 }}>Cargando análisis...</span>
      </div>
    );
  }

  if (error || !detalle) {
    return (
      <div style={{ padding: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
          <button onClick={() => router.push("/historial")} aria-label="Volver al historial" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Volver al historial</span>
        </div>
        <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
          <p style={{ color: RED, fontSize: 13, margin: 0 }}>{error || "No se pudo cargar este análisis."}</p>
        </div>
      </div>
    );
  }

  const result = detalle.resultado;
  const mensaje = getMensajeContextual(result.estado_operacion);
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

  const integ = result.integridad_config;
  const tieneXmlDiscrepante = (result as unknown as {cep_xml?: {comparacion_campos?: {discrepancias?: number}}}).cep_xml?.comparacion_campos?.discrepancias ?? 0 > 0;
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
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
        <button onClick={() => router.push("/historial")} aria-label="Volver al historial" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Volver al historial</span>
      </div>

      <div style={{ background: "#fff", borderRadius: 20, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.15)" }}>

        {/* Badge de contexto histórico — cambia la expectativa del usuario:
            no es un análisis en curso, es un registro archivado. */}
        <div style={{ padding: "12px 18px", background: "#F1F5F9", display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12 }}>📁</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#64748B", letterSpacing: "0.04em", textTransform: "uppercase" }}>
            Análisis archivado
          </span>
        </div>

        {/* Ficha de auditoría — antes del semáforo, para ubicar al usuario primero */}
        <div style={{ padding: "18px 18px 16px", borderBottom: "1px solid #F0F4F8" }}>
          <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
            Análisis realizado
          </div>
          <FichaFila label="Fecha" valor={formatearFecha(detalle.fecha)} />
          <FichaFila label="Archivo" valor={detalle.archivo_nombre || "—"} />
          <FichaFila label="Banco" valor={detalle.banco_detectado || "No detectado"} />
          <FichaFila label="Monto" valor={formatearMonto(detalle.monto_detectado)} />
          <FichaFila label="Hash" valor={detalle.hash_sha256 ? `${detalle.hash_sha256.slice(0, 16)}...` : "—"} mono />
          <FichaFila label="Nivel de evidencia" valor={etiquetaFuenteEstado(detalle.nivel_evidencia)} />
          <FichaFila label="Fuente del estado" valor={etiquetaFuenteEstado(detalle.fuente_estado)} last />
        </div>

        {/* Nivel 1 — Resultado */}
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

        {/* Nivel 1 — ¿Qué significa esto? */}
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

        {/* Entrada a Nivel 2+ */}
        <button onClick={() => setDetallesAbiertos(o => !o)}
          style={{ width: "calc(100% - 44px)", margin: "0 22px 22px", padding: 14, fontSize: 13.5, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#fff", color: "#334155", border: "1.5px solid #E2E8F0", display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          {detallesAbiertos ? "Ocultar detalles del análisis" : "Ver detalles del análisis"}
          <span style={{ color: "#CBD5E1", fontSize: 12 }}>{detallesAbiertos ? "▲" : "▼"}</span>
        </button>

        {detallesAbiertos && (
          <div>
            <div style={{ padding: "0 22px 18px" }}>
              <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
                Integridad del comprobante
              </div>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 4 }}>
                <span style={{ fontSize: 13, color: colorInteg, fontWeight: 700 }}>{integIcono}</span>
                <span style={{ fontSize: 13, color: colorInteg, fontWeight: 700 }}>{integ?.etiqueta || "—"}</span>
              </div>
              <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.6 }}>{integSubtexto}</div>

              {detalle.historial_hash && detalle.historial_hash.veces_visto > 1 && (
                <div style={{ marginTop: 10, padding: "10px 14px", background: `${ORANGE}12`, border: `1px solid ${ORANGE}40`, borderRadius: 10, fontSize: 12, color: "#7C4A0A", lineHeight: 1.5 }}>
                  ⚠️ Este comprobante ha sido analizado {detalle.historial_hash.veces_visto} veces — primera vez el {formatearFecha(detalle.historial_hash.primer_analisis)}, la más reciente el {formatearFecha(detalle.historial_hash.ultimo_analisis)}.
                </div>
              )}
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

            <div style={{ height: 1, background: "#F0F4F8", margin: "0 22px 18px" }} />

            {/* Espacio reservado — Historial Inteligente (visión futura, ver ROADMAP.md) */}
            <div style={{ padding: "0 22px 18px" }}>
              <div style={{ fontSize: 10, color: "#CBD5E1", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
                Actividad relacionada
              </div>
              <div style={{ padding: "12px 14px", background: "#F8FAFC", borderRadius: 10, fontSize: 12, color: "#94A3B8", fontStyle: "italic" }}>
                No disponible todavía
              </div>
            </div>

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
          <button onClick={() => router.push("/historial")}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
            ← Volver al historial
          </button>
        </div>

        {/* Nota de privacidad — reencuadre, no disculpa */}
        <div style={{ padding: "0 22px 20px" }}>
          <p style={{ fontSize: 11, color: "#94A3B8", textAlign: "center", lineHeight: 1.5, margin: 0 }}>
            🔒 Por privacidad, VerificaPago no almacena imágenes de comprobantes una vez concluido el análisis.
          </p>
        </div>
      </div>
    </div>
  );
}

function FichaFila({ label, valor, mono, last }: { label: string; valor: string; mono?: boolean; last?: boolean }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "6px 0", borderBottom: last ? "none" : "1px solid #F8FAFC",
    }}>
      <span style={{ fontSize: 11, color: "#94A3B8" }}>{label}</span>
      <span style={{ fontSize: 12, color: "#334155", fontWeight: 600, fontFamily: mono ? "monospace" : "inherit" }}>{valor}</span>
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