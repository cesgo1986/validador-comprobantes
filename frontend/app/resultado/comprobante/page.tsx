"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis } from "../../context/AnalisisContext";

const TEAL = "#00BFA5";

export default function VistaComprobante() {
  const router = useRouter();
  const { result, preview, file, reset } = useAnalisis();

  useEffect(() => {
    if (!result) router.replace("/");
  }, [result, router]);

  if (!result) return null;

  const finalizar = () => {
    reset();
    router.push("/");
  };

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
        <button onClick={() => router.back()} aria-label="Volver" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16, flex: 1 }}>Vista del comprobante</span>
      </div>

      {preview && (
        <div style={{ background: "#fff", borderRadius: 16, padding: 12, marginBottom: 14 }}>
          <img src={preview} alt="Comprobante analizado" style={{ width: "100%", borderRadius: 10, display: "block" }} />
        </div>
      )}
      {!preview && file && (
        <div style={{ background: "#fff", borderRadius: 16, padding: "24px 16px", marginBottom: 14, textAlign: "center", color: "#94A3B8", fontSize: 13 }}>
          📄 {file.name} (vista previa no disponible para PDF)
        </div>
      )}

      {result.campos_extraidos && Object.values(result.campos_extraidos).some(Boolean) && (
        <div style={{ background: "#fff", borderRadius: 16, padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 12 }}>Datos extraídos (OCR)</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {Object.entries(result.campos_extraidos).filter(([, v]) => v).map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", paddingBottom: 8, borderBottom: "1px solid #F8FAFC" }}>
                <span style={{ fontSize: 12, color: "#94A3AF", textTransform: "capitalize" }}>{k.replace(/_/g, " ")}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#1E293B", textAlign: "right" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {result.elementos_verificabilidad && result.elementos_verificabilidad.length > 0 && (
        <div style={{ background: "#fff", borderRadius: 16, padding: "16px 18px", marginBottom: 14 }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 }}>Elementos de verificabilidad</div>
          {result.elementos_verificabilidad.map((el, i) => (
            <div key={i} style={{ fontSize: 13, color: "#334155", padding: "4px 0", display: "flex", gap: 8 }}>
              <span style={{ color: TEAL }}>✓</span> {el}
            </div>
          ))}
        </div>
      )}

      {result.cep_resultado?.cep_url && (
        <a href={result.cep_resultado.cep_url} target="_blank" rel="noopener noreferrer"
          style={{ display: "block", marginBottom: 14, padding: "13px 16px", fontSize: 13, fontWeight: 700, borderRadius: 12, background: "#fff", color: TEAL, border: `1.5px solid ${TEAL}`, textAlign: "center", textDecoration: "none" }}>
          🔗 Verificar en Banxico
        </a>
      )}

      <button onClick={finalizar}
        style={{ width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
        Analizar otro comprobante
      </button>
    </div>
  );
}