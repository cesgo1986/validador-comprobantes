"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis, Validacion } from "../../context/AnalisisContext";

const TEAL = "#00BFA5";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";

function agruparPorCategoria(validaciones: Validacion[]) {
  const grupos: Record<string, Validacion[]> = {};
  for (const v of validaciones) {
    const cat = v.categoria || "otros";
    if (!grupos[cat]) grupos[cat] = [];
    grupos[cat].push(v);
  }
  return grupos;
}

const NOMBRES_GRUPO: Record<string, string> = {
  cep: "Verificación Banxico / CEP",
  estructural: "Validaciones estructurales",
  visual: "Consistencia visual y OCR",
  temporal: "Validaciones temporales",
  contextual: "Validaciones contextuales",
  semantica: "Consistencia semántica",
  reputacion: "Reputación e historial",
  historial: "Historial del documento",
};

function resumenGrupo(items: Validacion[]) {
  const total = items.length;
  const ok = items.filter(v => v.status === "ok").length;
  const warns = items.filter(v => v.status === "warn" || v.status === "fail").length;
  if (warns === 0) return { texto: "Todo correcto", color: GREEN, ratio: `${ok}/${total}` };
  return { texto: `${warns} advertencia${warns > 1 ? "s" : ""}`, color: ORANGE, ratio: `${ok}/${total}` };
}

export default function Detalle() {
  const router = useRouter();
  const { result } = useAnalisis();
  const [abierto, setAbierto] = useState<string | null>(null);

  useEffect(() => {
    if (!result) router.replace("/");
  }, [result, router]);

  if (!result) return null;

  const grupos = agruparPorCategoria(result.validaciones || []);
  const ordenGrupos = Object.keys(grupos).sort((a, b) => {
    const prioridad = ["cep", "estructural", "visual", "temporal", "contextual", "semantica", "reputacion", "historial"];
    return prioridad.indexOf(a) - prioridad.indexOf(b);
  });

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
        <button onClick={() => router.back()} aria-label="Volver" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Detalles del análisis</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {ordenGrupos.map((cat, idx) => {
          const items = grupos[cat];
          const resumen = resumenGrupo(items);
          const isOpen = abierto === cat;
          return (
            <div key={cat} style={{ background: "#fff", borderRadius: 16, overflow: "hidden" }}>
              <button onClick={() => setAbierto(isOpen ? null : cat)}
                style={{ width: "100%", padding: "14px 16px", display: "flex", alignItems: "center", gap: 12, background: "none", border: "none", cursor: "pointer", textAlign: "left" }}>
                <span style={{ width: 26, height: 26, borderRadius: 8, background: "#F1F5F9", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13, fontWeight: 700, color: "#475569", flexShrink: 0 }}>{idx + 1}</span>
                <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: "#1E293B" }}>{NOMBRES_GRUPO[cat] || cat}</span>
                <span style={{ fontSize: 11, fontWeight: 700, padding: "4px 8px", borderRadius: 8, background: `${resumen.color}18`, color: resumen.color }}>{resumen.texto}</span>
                <span style={{ fontSize: 11, color: "#94A3B8", fontWeight: 600 }}>{resumen.ratio}</span>
                <span style={{ color: "#CBD5E1", fontSize: 14 }}>{isOpen ? "▲" : "▼"}</span>
              </button>
              {isOpen && (
                <div style={{ borderTop: "1px solid #F0F4F8" }}>
                  {items.map((v, i) => {
                    const color = v.status === "ok" ? GREEN : v.status === "warn" ? ORANGE : v.status === "fail" ? RED : TEAL;
                    return (
                      <div key={i} style={{ padding: "12px 16px", borderBottom: i < items.length - 1 ? "1px solid #F8FAFC" : "none" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: v.detalle ? 6 : 0 }}>
                          <span style={{ width: 20, height: 20, borderRadius: "50%", background: v.status === "ok" ? GREEN : `${color}20`, border: v.status === "ok" ? "none" : `1.5px solid ${color}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                            <span style={{ color: v.status === "ok" ? "#fff" : color, fontSize: 10, fontWeight: 700 }}>{v.status === "ok" ? "✓" : "!"}</span>
                          </span>
                          <span style={{ fontSize: 13, color: "#334155", fontWeight: 500 }}>{v.nombre}</span>
                        </div>
                        {v.detalle && <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.5, marginLeft: 30 }}>{v.detalle}</div>}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {result.recomendacion && (
        <div style={{ marginTop: 14, background: "#fff", borderRadius: 16, padding: "16px 18px" }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 8 }}>Recomendación</div>
          <div style={{ fontSize: 14, fontWeight: 700, color: ORANGE, marginBottom: 4 }}>Revisar manualmente</div>
          <div style={{ fontSize: 13, color: "#64748B", lineHeight: 1.6 }}>{result.recomendacion}</div>
        </div>
      )}

      <button onClick={() => router.push("/resultado/comprobante")}
        style={{ marginTop: 14, width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
        Siguiente →
      </button>
    </div>
  );
}