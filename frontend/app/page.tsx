"use client";
import { useState, useRef, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type RiskLevel = "BAJO" | "MEDIO" | "ALTO" | "INDETERMINADO";
type Status = "ok" | "warn" | "fail" | "info";

interface Validacion {
  categoria: string;
  nombre: string;
  status: Status;
  detalle: string;
}

interface Resultado {
  riesgo: RiskLevel;
  score: number;
  campos_extraidos: Record<string, string | null>;
  validaciones: Validacion[];
  resumen: string;
  recomendacion: string;
}

const CAT_LABELS: Record<string, string> = {
  estructural: "Estructural",
  visual: "Visual / Forense",
  contextual: "Contextual",
  temporal: "Temporal",
  semantica: "Semántica",
  reputacion: "Reputación / Inteligencia",
  general: "General",
};

const RISK_CFG = {
  ALTO:          { bg: "#FCEBEB", color: "#A32D2D", border: "#F09595", label: "RIESGO ALTO" },
  MEDIO:         { bg: "#FAEEDA", color: "#854F0B", border: "#FAC775", label: "RIESGO MEDIO" },
  BAJO:          { bg: "#EAF3DE", color: "#3B6D11", border: "#C0DD97", label: "RIESGO BAJO" },
  INDETERMINADO: { bg: "#F1EFE8", color: "#5F5E5A", border: "#D3D1C7", label: "INDETERMINADO" },
};

const STATUS_CFG = {
  ok:   { color: "#3B6D11", bg: "#EAF3DE", symbol: "✓" },
  warn: { color: "#854F0B", bg: "#FAEEDA", symbol: "⚠" },
  fail: { color: "#A32D2D", bg: "#FCEBEB", symbol: "✗" },
  info: { color: "#185FA5", bg: "#E6F1FB", symbol: "ℹ" },
};

const STAGES = [
  "Cargando comprobante...",
  "Extrayendo datos con OCR...",
  "Normalizando campos...",
  "Ejecutando validaciones estructurales...",
  "Analizando consistencia visual y contextual...",
  "Calculando score de riesgo...",
  "Generando reporte final...",
];

function RiskBadge({ level }: { level: RiskLevel }) {
  const c = RISK_CFG[level] || RISK_CFG.INDETERMINADO;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 8, background: c.bg, color: c.color, border: `1.5px solid ${c.border}`, borderRadius: 10, padding: "10px 20px", fontWeight: 600, fontSize: 16 }}>
      {c.label}
    </span>
  );
}

function CheckItem({ status, label, detail }: { status: Status; label: string; detail?: string }) {
  const c = STATUS_CFG[status] || STATUS_CFG.info;
  return (
    <div style={{ display: "flex", gap: 10, padding: "8px 12px", borderRadius: 8, background: c.bg, marginBottom: 6 }}>
      <span style={{ color: c.color, fontWeight: 700, flexShrink: 0, fontSize: 15 }}>{c.symbol}</span>
      <div>
        <span style={{ fontSize: 14, fontWeight: 500, color: c.color }}>{label}</span>
        {detail && <div style={{ fontSize: 13, color: "#666", marginTop: 2 }}>{detail}</div>}
      </div>
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct <= 33 ? "#639922" : pct <= 66 ? "#BA7517" : "#E24B4A";
  return (
    <div style={{ margin: "16px 0" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#666", marginBottom: 6 }}>
        <span>Índice de riesgo</span>
        <span style={{ fontWeight: 600, color }}>{Math.round(pct)}/100</span>
      </div>
      <div style={{ height: 8, background: "#eee", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ height: "100%", width: `${pct}%`, background: color, borderRadius: 4, transition: "width 0.6s ease" }} />
      </div>
    </div>
  );
}

export default function Home() {
  const [file, setFile]         = useState<File | null>(null);
  const [preview, setPreview]   = useState<string | null>(null);
  const [bankHint, setBankHint] = useState("");
  const [stage, setStage]       = useState<"idle" | "loading" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult]     = useState<Resultado | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    const allowed = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];
    if (!allowed.includes(f.type)) { setError("Formato no soportado. Usa PNG, JPG o PDF."); return; }
    setError(null); setFile(f); setResult(null);
    if (f.type !== "application/pdf") setPreview(URL.createObjectURL(f));
    else setPreview(null);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const tick = (i: number) => new Promise<void>(res => setTimeout(() => { setProgress(i); res(); }, 600));

  const analyze = async () => {
    if (!file) return;
    setStage("loading"); setProgress(0); setResult(null); setError(null);
    for (let i = 1; i <= 5; i++) await tick(i);

    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("banco_hint", bankHint);

      const res = await fetch(`${API_URL}/analizar`, { method: "POST", body: fd });
      await tick(6);
      if (!res.ok) throw new Error(`Error del servidor: ${res.status}`);
      const data: Resultado = await res.json();
      await tick(7);
      setResult(data);
      setStage("done");
    } catch (e: unknown) {
      setError(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setStage("idle");
    }
  };

  const reset = () => { setFile(null); setPreview(null); setStage("idle"); setProgress(0); setResult(null); setError(null); setBankHint(""); };

  const grouped = result?.validaciones.reduce<Record<string, Validacion[]>>((acc, v) => {
    const cat = v.categoria || "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(v);
    return acc;
  }, {}) ?? {};

  return (
    <main style={{ maxWidth: 680, margin: "0 auto", padding: "2rem 1rem", fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 4 }}>🛡️ Validador de comprobantes</h1>
      <p style={{ fontSize: 14, color: "#666", marginBottom: 16 }}>Análisis preventivo de autenticidad — No confirma transferencias oficialmente</p>

      <div style={{ background: "#E6F1FB", border: "0.5px solid #B5D4F4", borderRadius: 10, padding: "10px 14px", marginBottom: 20, fontSize: 13, color: "#185FA5" }}>
        ℹ️ <strong>¿Qué comprobantes puedes analizar?</strong> Cualquier comprobante de transferencia: app del banco, correo, captura o PDF. Los números de cuenta parcialmente ocultos (****1234) son normales y no afectan el análisis.
      </div>

      {stage === "idle" && (
        <>
          <div
            onDrop={onDrop}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onClick={() => inputRef.current?.click()}
            style={{ border: `1.5px dashed ${dragging ? "#185FA5" : "#ccc"}`, borderRadius: 12, padding: "2.5rem 1.5rem", textAlign: "center", cursor: "pointer", background: dragging ? "#E6F1FB" : "#fafafa", transition: "all 0.2s" }}
          >
            <div style={{ fontSize: 32, marginBottom: 10 }}>📤</div>
            <p style={{ margin: 0, fontWeight: 500, fontSize: 15 }}>{file ? file.name : "Arrastra o haz clic para cargar"}</p>
            <p style={{ margin: "6px 0 0", fontSize: 13, color: "#888" }}>PNG, JPG o PDF — máx. 10 MB</p>
            <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,.pdf" style={{ display: "none" }} onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
          </div>

          {preview && (
            <div style={{ marginTop: 12, borderRadius: 10, overflow: "hidden", border: "0.5px solid #ddd", maxHeight: 220, display: "flex", alignItems: "center", justifyContent: "center", background: "#f5f5f5" }}>
              <img src={preview} alt="Vista previa" style={{ maxWidth: "100%", maxHeight: 220, objectFit: "contain" }} />
            </div>
          )}

          {file && (
            <>
              <div style={{ marginTop: 14 }}>
                <label style={{ fontSize: 13, color: "#666", display: "block", marginBottom: 6 }}>
                  🏦 ¿Cuál es el banco emisor? <span style={{ color: "#aaa" }}>(opcional, ayuda si el logo no tiene texto)</span>
                </label>
                <input
                  value={bankHint}
                  onChange={e => setBankHint(e.target.value)}
                  placeholder="Ej: Banco Azteca, BBVA, Santander..."
                  style={{ width: "100%", padding: "9px 12px", fontSize: 14, borderRadius: 8, border: "0.5px solid #ccc", background: "#fafafa", boxSizing: "border-box" }}
                />
              </div>
              <button onClick={analyze} style={{ marginTop: 12, width: "100%", padding: 12, fontSize: 15, fontWeight: 500, borderRadius: 10, cursor: "pointer", background: "#111", color: "#fff", border: "none" }}>
                🔍 Analizar comprobante
              </button>
            </>
          )}

          {error && <div style={{ marginTop: 12, padding: "10px 14px", background: "#FCEBEB", color: "#A32D2D", borderRadius: 8, fontSize: 14 }}>⚠️ {error}</div>}
        </>
      )}

      {stage === "loading" && (
        <div style={{ background: "#fafafa", borderRadius: 12, padding: "2rem 1.5rem", border: "0.5px solid #eee" }}>
          <p style={{ fontWeight: 500, marginBottom: 16, fontSize: 15 }}>{STAGES[Math.min(progress, STAGES.length - 1)]}</p>
          <div style={{ height: 6, background: "#eee", borderRadius: 3, overflow: "hidden", marginBottom: 20 }}>
            <div style={{ height: "100%", width: `${(progress / 7) * 100}%`, background: "#111", borderRadius: 3, transition: "width 0.5s ease" }} />
          </div>
          {STAGES.map((s, i) => (
            <div key={i} style={{ display: "flex", gap: 10, padding: "6px 0", opacity: progress >= i + 1 ? 1 : 0.3, transition: "opacity 0.3s" }}>
              <span style={{ color: progress >= i + 1 ? "#639922" : "#bbb" }}>{progress >= i + 1 ? "✓" : "○"}</span>
              <span style={{ fontSize: 13, color: "#555" }}>{s}</span>
            </div>
          ))}
        </div>
      )}

      {stage === "done" && result && (
        <div>
          <div style={{ background: "#fafafa", borderRadius: 12, padding: "1.25rem 1.5rem", marginBottom: 16, border: "0.5px solid #eee" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12, marginBottom: 12 }}>
              <RiskBadge level={result.riesgo} />
              {file && <span style={{ fontSize: 13, color: "#888" }}>📄 {file.name}</span>}
            </div>
            <ScoreBar score={result.score} />
            {result.resumen && <p style={{ fontSize: 14, color: "#555", margin: "8px 0 0", lineHeight: 1.6 }}>{result.resumen}</p>}
          </div>

          {result.campos_extraidos && Object.values(result.campos_extraidos).some(Boolean) && (
            <div style={{ background: "#fafafa", borderRadius: 12, padding: "1.25rem 1.5rem", marginBottom: 16, border: "0.5px solid #eee" }}>
              <p style={{ fontWeight: 600, fontSize: 14, margin: "0 0 10px" }}>📋 Campos extraídos</p>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 6 }}>
                {Object.entries(result.campos_extraidos).filter(([, v]) => v).map(([k, v]) => (
                  <div key={k} style={{ background: "#fff", borderRadius: 8, padding: "7px 10px", border: "0.5px solid #ddd" }}>
                    <div style={{ fontSize: 11, color: "#aaa", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>{k.replace(/_/g, " ")}</div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {Object.entries(grouped).map(([cat, items]) => (
            <div key={cat} style={{ marginBottom: 14 }}>
              <p style={{ fontWeight: 600, fontSize: 12, color: "#888", margin: "0 0 8px", textTransform: "uppercase", letterSpacing: "0.06em" }}>{CAT_LABELS[cat] || cat}</p>
              {items.map((v, i) => <CheckItem key={i} status={v.status} label={v.nombre} detail={v.detalle} />)}
            </div>
          ))}

          {result.recomendacion && (
            <div style={{ marginTop: 8, padding: "12px 16px", background: "#E6F1FB", borderRadius: 10, border: "0.5px solid #B5D4F4", fontSize: 14, color: "#185FA5" }}>
              💡 <strong>Recomendación:</strong> {result.recomendacion}
            </div>
          )}

          <div style={{ marginTop: 12, padding: "10px 14px", background: "#f5f5f5", borderRadius: 8, fontSize: 12, color: "#aaa", textAlign: "center" }}>
            ℹ️ Este sistema no confirma transferencias oficialmente. Solo evalúa consistencia y autenticidad aparente.
          </div>

          <button onClick={reset} style={{ marginTop: 14, width: "100%", padding: 11, fontSize: 14, borderRadius: 10, cursor: "pointer", background: "#fff", border: "0.5px solid #ccc" }}>
            🔄 Analizar otro comprobante
          </button>
        </div>
      )}
    </main>
  );
}