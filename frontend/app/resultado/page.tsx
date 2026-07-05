"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis } from "../context/AnalisisContext";
import { SemaforoSpei } from "../components/resultado/SemaforoSpei";
import { QueSignificaEsto } from "../components/resultado/QueSignificaEsto";
import { DetalleExpandible } from "../components/resultado/DetalleExpandible";
import { TEAL, ORANGE } from "../lib/colores";

// Refactor previo a Etapa 4 (ver DECISION_LOG.md): el bloque central
// (semáforo, "¿Qué significa esto?", panel expandible) ya no vive aquí
// duplicado -- se importa de app/components/resultado/. Este archivo
// solo mantiene lo específico de esta pantalla: header, nombre de
// archivo, aviso de reutilización (con los datos que sí tiene un
// análisis recién hecho) y los botones de acción.
export default function Resultado() {
  const router = useRouter();
  const { result, file } = useAnalisis();

  useEffect(() => {
    if (!result) router.replace("/");
  }, [result, router]);

  if (!result) return null;

  const descargarReporte = () => {
    const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte_${file?.name || "comprobante"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const avisoReutilizacion = result.documento_reutilizado ? (
    <div style={{ marginTop: 10, padding: "10px 14px", background: `${ORANGE}12`, border: `1px solid ${ORANGE}40`, borderRadius: 10, fontSize: 12, color: "#7C4A0A", lineHeight: 1.5 }}>
      ⚠️ Este comprobante exacto ya fue analizado antes (visto {result.veces_visto} veces).
    </div>
  ) : null;

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

        <SemaforoSpei result={result} />
        <QueSignificaEsto result={result} />
        <DetalleExpandible result={result} avisoReutilizacion={avisoReutilizacion} />

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