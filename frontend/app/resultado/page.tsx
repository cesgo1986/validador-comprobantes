"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis, EstadoOperacion } from "../context/AnalisisContext";

const TEAL = "#00BFA5";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";

const ESTADO_OPERACION_LABEL: Record<EstadoOperacion, string> = {
  acreditada: "Acreditada en Banxico",
  liquidada: "Liquidada, CEP pendiente",
  en_proceso: "En proceso",
  devuelta: "Devuelta al emisor",
  en_devolucion: "En proceso de devolución",
  rechazada: "Rechazada por SPEI",
  cancelada: "Cancelada antes de liquidar",
  no_liquidada: "No liquidada en la jornada",
  desconocida: "Sin información disponible",
};

function dimensionColor(score: number): string {
  if (score >= 75) return GREEN;
  if (score >= 45) return ORANGE;
  return RED;
}

export default function Resultado() {
  const router = useRouter();
  const { result, file } = useAnalisis();

  useEffect(() => {
    if (!result) router.replace("/");
  }, [result, router]);

  if (!result) return null;

  const minDimension = Math.min(result.confianza_documental, result.verificabilidad, result.contexto_temporal);
  const tonoGeneral = dimensionColor(minDimension);

  const descargarReporte = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte_${file?.name || "comprobante"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

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

        <div style={{ padding: "16px 20px 4px" }}>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={{ width: 4, height: 18, background: tonoGeneral, borderRadius: 2, flexShrink: 0, marginTop: 2 }} />
            <span style={{ fontSize: 14, color: "#1E293B", lineHeight: 1.6, fontWeight: 500 }}>
              {result.interpretacion || result.resumen}
            </span>
          </div>
        </div>

        {result.documento_reutilizado && (
          <div style={{ margin: "12px 20px 0", padding: "10px 14px", background: `${ORANGE}12`, border: `1px solid ${ORANGE}40`, borderRadius: 10, fontSize: 12, color: "#7C4A0A", lineHeight: 1.5 }}>
            ⚠️ Este comprobante exacto ya fue analizado antes (visto {result.veces_visto} veces).
          </div>
        )}

        <div style={{ padding: "16px 20px 4px", display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", gap: 10 }}>
            <DimensionCard label="Confianza documental" score={result.confianza_documental} sublabel="¿Parece auténtico?" />
            <DimensionCard label="Verificabilidad" score={result.verificabilidad} sublabel="¿Se puede corroborar?" />
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <DimensionCard label="Contexto temporal" score={result.contexto_temporal} sublabel="¿El tiempo es consistente?" />
            <div style={{ flex: 1, minWidth: 0, background: "#F8FAFC", borderRadius: 14, padding: 14, border: "1px solid #EEF2F7" }}>
              <div style={{ fontSize: 11, color: "#94A3B8", fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase", marginBottom: 8 }}>Estado de la operación</div>
              <div style={{ display: "inline-block", padding: "6px 10px", borderRadius: 8, background: "rgba(156,163,175,0.15)", color: "#6B7280", fontSize: 12, fontWeight: 700 }}>
                {ESTADO_OPERACION_LABEL[result.estado_operacion] || "Sin información"}
              </div>
            </div>
          </div>
        </div>

        {result.detalle_temporal && (
          <div style={{ margin: "4px 20px 16px", padding: "8px 12px", background: "#F8FAFC", borderRadius: 8, fontSize: 11, color: "#64748B", lineHeight: 1.5 }}>
            🕐 {result.detalle_temporal}
          </div>
        )}

        <div style={{ padding: "0 20px 20px", display: "flex", flexDirection: "column", gap: 10 }}>
          <button onClick={() => router.push("/resultado/detalle")}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#F1F5F9", color: "#334155", border: "none" }}>
            Ver detalles
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