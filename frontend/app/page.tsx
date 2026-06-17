"use client";
import { useState, useRef, useCallback, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TEAL = "#00BFA5";
const DARK = "#1A2340";
const ORANGE = "#F5A623";
const RED = "#E53935";
const GREEN = "#43A047";

const BANKS: Record<string, string> = {
  "002":"BBVA","006":"BANCOMEXT","009":"BANOBRAS","012":"HSBC","014":"SANTANDER",
  "021":"HSBC","030":"BAJIO","036":"INBURSA","037":"MULTIVA","044":"SCOTIABANK",
  "058":"BANREGIO","059":"INVEX","062":"AFIRME","072":"BANORTE","127":"AZTECA",
  "128":"AUTOFIN","130":"COMPARTAMOS","137":"BANCOPPEL","145":"BANJERCITO",
  "147":"BANKAOOL","600":"MONEXCB","601":"GBM","646":"STP","706":"ARCUS",
  "722":"MERCADO PAGO","723":"CUENCA","728":"SPIN BY OXXO","741":"KLAR","748":"BINEO",
};

type Stage = "idle" | "loading" | "done" | "fecha_banner";
type RiskLevel = "BAJO" | "MEDIO" | "ALTO" | "CRITICO" | "INDETERMINADO";
type Status = "ok" | "warn" | "fail" | "info";

interface Validacion {
  categoria: string;
  nombre: string;
  status: Status;
  detalle: string;
  cep_url?: string;
}

interface ClabeResultado {
  valid: boolean;
  bank?: string;
  bank_code?: string;
  reason?: string;
  clabe?: string;
}

interface CepResultado {
  found: boolean;
  status: string;
  confidence: number;
  match_monto?: boolean | null;
  cep_sin_monto?: boolean;
  monto_comprobante?: number;
  montos_cep?: number[];
  clave_usada?: string;
  tipo_clave?: string;
  cep_url?: string;
  detalle?: string;
}

interface Resultado {
  riesgo: RiskLevel;
  score: number;
  campos_extraidos: Record<string, string | null>;
  validaciones: Validacion[];
  resumen: string;
  recomendacion: string;
  requiere_confirmacion_fecha?: boolean;
  mensaje_confirmacion_fecha?: string;
  dias_diferencia?: number;
  // Mejora 1: CLABE ya validada por el backend
  clabe_resultado?: ClabeResultado;
  clabe_comprobante?: { valid: boolean; bank?: string; bank_code?: string };
  // Mejora 4: CEP completo
  cep_resultado?: CepResultado;
  confianza_modelo?: number;
  audit_id?: string;
}

// ── Mejora 2: progress independiente del fetch ────────────────────────────────
function useProgress(active: boolean) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (!active) { setProgress(0); return; }
    startRef.current = Date.now();

    const tick = () => {
      const elapsed = (Date.now() - startRef.current) / 1000; // segundos
      // Curva logarítmica: llega rápido al 80% y luego frena — nunca llega al 100% sola
      const pct = Math.min(82, Math.round(80 * (1 - Math.exp(-elapsed / 4))));
      setProgress(pct);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [active]);

  const complete = () => setProgress(100);
  return { progress, complete };
}

function GaugeCircle({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = pct <= 33 ? GREEN : pct <= 66 ? ORANGE : RED;
  const r = 38, circ = 2 * Math.PI * r, arc = circ * 0.75, filled = (pct / 100) * arc;
  return (
    <div style={{ position: "relative", width: 100, height: 100, flexShrink: 0 }}>
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="58" r={r} fill="none" stroke="#E8EDF5" strokeWidth="8"
          strokeDasharray={`${arc} ${circ - arc}`} strokeLinecap="round" transform="rotate(135 50 58)" />
        <circle cx="50" cy="58" r={r} fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${filled} ${circ - filled}`} strokeLinecap="round"
          transform="rotate(135 50 58)" style={{ transition: "stroke-dasharray 0.3s ease, stroke 0.5s" }} />
      </svg>
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", paddingTop: 8 }}>
        <span style={{ fontSize: 28, fontWeight: 800, color, lineHeight: 1 }}>{Math.round(pct)}</span>
        <span style={{ fontSize: 12, color: "#9CA3AF", fontWeight: 500 }}>/100</span>
      </div>
    </div>
  );
}

function ValidationRow({ v }: { v: Validacion }) {
  const [open, setOpen] = useState(false);
  const isOk = v.status === "ok";
  const isInfo = v.status === "info";
  const ic = isOk ? GREEN : v.status === "warn" ? ORANGE : v.status === "fail" ? RED : TEAL;
  const symbol = isOk ? "✓" : isInfo ? "ℹ" : "⚠";
  return (
    <div onClick={() => v.detalle && setOpen(o => !o)}
      style={{ borderBottom: "1px solid #F0F4F8", cursor: v.detalle ? "pointer" : "default", background: open ? "#F8FAFC" : "#fff", transition: "background 0.15s" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14, padding: "13px 24px" }}>
        <div style={{ width: 28, height: 28, borderRadius: "50%", background: isOk ? GREEN : `${ic}20`, border: isOk ? "none" : `2px solid ${ic}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
          <span style={{ color: isOk ? "#fff" : ic, fontSize: 13, fontWeight: 700 }}>{symbol}</span>
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 500, color: "#1E293B" }}>{v.nombre}</div>
        </div>
        {!isOk && (
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 24, height: 24, borderRadius: "50%", background: `${ic}20`, border: `1.5px solid ${ic}`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <span style={{ color: ic, fontSize: 11, fontWeight: 700 }}>⚠</span>
            </div>
            {v.detalle && <span style={{ fontSize: 16, color: "#CBD5E1" }}>{open ? "▲" : "▼"}</span>}
          </div>
        )}
        {isOk && v.detalle && <span style={{ fontSize: 16, color: "#CBD5E1" }}>{open ? "▲" : "▼"}</span>}
      </div>
      {open && v.detalle && (
        <div style={{ padding: "0 24px 14px 66px" }}>
          <div style={{ background: `${ic}10`, border: `1px solid ${ic}30`, borderRadius: 10, padding: "10px 14px", fontSize: 13, color: "#334155", lineHeight: 1.6 }}>
            💬 {v.detalle}
          </div>
          {v.cep_url && (
            <a href={v.cep_url} target="_blank" rel="noopener noreferrer"
              style={{ display: "inline-block", marginTop: 8, padding: "8px 14px", fontSize: 12, fontWeight: 700, borderRadius: 8, background: TEAL, color: "#fff", textDecoration: "none" }}>
              🔗 Verificar en Banxico →
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// ── Mejora 4: Tarjeta CEP expandida ──────────────────────────────────────────
function CepCard({ cep }: { cep: CepResultado }) {
  const [open, setOpen] = useState(false);
  const found = cep.found;
  const matchMonto = cep.match_monto;
  const confianza = Math.round((cep.confidence || 0) * 100);

  const bgColor  = found && matchMonto === true  ? "#F0FDF4"
                 : found && matchMonto === false  ? "#FEF9C3"
                 : found                          ? "#F0F9FF"
                 : "#F8FAFC";
  const border   = found && matchMonto === true  ? "#86EFAC"
                 : found && matchMonto === false  ? "#FDE047"
                 : found                          ? "#BAE6FD"
                 : "#E2E8F0";
  const titleColor = found && matchMonto === true  ? "#166534"
                   : found && matchMonto === false  ? "#854D0E"
                   : found                          ? "#0C4A6E"
                   : "#475569";
  const icon = found && matchMonto === true  ? "✅"
             : found && matchMonto === false  ? "⚠️"
             : found                          ? "🔍"
             : "ℹ️";
  const titulo = found && matchMonto === true  ? "Transferencia confirmada en Banxico"
               : found && matchMonto === false  ? "Transferencia encontrada — monto difiere"
               : found                          ? "Transferencia encontrada en Banxico"
               : "No encontrada en CEP Banxico";

  return (
    <div style={{ margin: "0 24px 12px", borderRadius: 12, border: `1.5px solid ${border}`, background: bgColor, overflow: "hidden" }}>
      <div onClick={() => setOpen(o => !o)} style={{ padding: "12px 14px", cursor: "pointer", display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 20 }}>{icon}</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: titleColor }}>{titulo}</div>
          <div style={{ fontSize: 11, color: titleColor, opacity: 0.7, marginTop: 2 }}>
            Confianza: {confianza}% · Toca para ver detalles
          </div>
        </div>
        <span style={{ fontSize: 14, color: "#CBD5E1" }}>{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <div style={{ padding: "0 14px 14px", borderTop: `1px solid ${border}` }}>
          {/* Datos de la consulta */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginTop: 10 }}>
            {cep.clave_usada && (
              <div style={{ background: "rgba(255,255,255,0.6)", borderRadius: 8, padding: "8px 10px" }}>
                <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>{cep.tipo_clave === "clave_rastreo" ? "Clave rastreo" : "Referencia"}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1E293B", wordBreak: "break-all" }}>{cep.clave_usada}</div>
              </div>
            )}
            {cep.monto_comprobante !== undefined && cep.monto_comprobante > 0 && (
              <div style={{ background: "rgba(255,255,255,0.6)", borderRadius: 8, padding: "8px 10px" }}>
                <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>Monto comprobante</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1E293B" }}>${cep.monto_comprobante.toLocaleString("es-MX", { minimumFractionDigits: 2 })}</div>
              </div>
            )}
            {cep.montos_cep && cep.montos_cep.length > 0 && (
              <div style={{ background: "rgba(255,255,255,0.6)", borderRadius: 8, padding: "8px 10px" }}>
                <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>Monto en CEP</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1E293B" }}>
                  {cep.montos_cep.map(m => "$" + m.toLocaleString("es-MX", { minimumFractionDigits: 2 })).join(", ")}
                </div>
              </div>
            )}
            <div style={{ background: "rgba(255,255,255,0.6)", borderRadius: 8, padding: "8px 10px" }}>
              <div style={{ fontSize: 10, color: "#94A3B8", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>Confianza</div>
              <div style={{ fontSize: 12, fontWeight: 600, color: confianza >= 85 ? GREEN : confianza >= 60 ? ORANGE : RED }}>{confianza}%</div>
            </div>
          </div>

          {/* Detalle textual */}
          {cep.detalle && (
            <div style={{ marginTop: 8, padding: "8px 10px", background: "rgba(255,255,255,0.5)", borderRadius: 8, fontSize: 12, color: "#334155", lineHeight: 1.6 }}>
              {cep.detalle}
            </div>
          )}

          {/* Botón verificar en Banxico */}
          {cep.cep_url && (
            <a href={cep.cep_url} target="_blank" rel="noopener noreferrer"
              style={{ display: "block", marginTop: 10, padding: "10px 14px", fontSize: 13, fontWeight: 700, borderRadius: 8, background: TEAL, color: "#fff", textDecoration: "none", textAlign: "center" }}>
              🔗 Verificar en Banxico →
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function ResultScreen({ result, file, onReset }: { result: Resultado; file: File | null; onReset: () => void }) {
  const riskCfg = {
    BAJO:          { label: "BAJO",          color: GREEN },
    MEDIO:         { label: "MEDIO",         color: ORANGE },
    ALTO:          { label: "ALTO",          color: RED },
    CRITICO:       { label: "CRÍTICO",       color: RED },
    INDETERMINADO: { label: "INDETERMINADO", color: "#9CA3AF" },
  };
  const rc = riskCfg[result.riesgo] || riskCfg.INDETERMINADO;
  // Separar validaciones — excluir la de CEP porque la mostramos en CepCard
  const validaciones = result.validaciones || [];
  const oks    = validaciones.filter(v => v.status === "ok"   && v.categoria !== "cep");
  const warns  = validaciones.filter(v => (v.status === "warn" || v.status === "fail") && v.categoria !== "cep");
  const infos  = validaciones.filter(v => v.status === "info" && v.categoria !== "cep");

  return (
    <div style={{ background: "#fff", borderRadius: 24, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.15)", maxWidth: 380, margin: "0 auto" }}>
      {/* Header */}
      <div style={{ background: DARK, padding: "18px 20px", textAlign: "center" }}>
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 2 }}>Resultado del análisis</div>
        {file && <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 2 }}>📄 {file.name}</div>}
      </div>

      {/* Score y riesgo */}
      <div style={{ padding: "24px 24px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #F0F4F8" }}>
        <div>
          <div style={{ fontSize: 12, color: "#9CA3AF", fontWeight: 500, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 4 }}>RIESGO</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: rc.color, lineHeight: 1, letterSpacing: "-1px" }}>{rc.label}</div>
        </div>
        <GaugeCircle score={result.score} />
      </div>

      {/* Resumen */}
      {result.resumen && (
        <div style={{ padding: "12px 24px", background: "#F8FAFC", borderBottom: "1px solid #F0F4F8" }}>
          <p style={{ margin: 0, fontSize: 13, color: "#64748B", lineHeight: 1.6 }}>{result.resumen}</p>
        </div>
      )}

      {/* Mejora 4: Tarjeta CEP destacada */}
      {result.cep_resultado && (
        <div style={{ paddingTop: 12 }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", padding: "0 24px 6px" }}>🏦 Verificación Banxico</div>
          <CepCard cep={result.cep_resultado} />
        </div>
      )}

      {/* Validaciones ok */}
      {oks.length > 0 && <div style={{ padding: "8px 0" }}>{oks.map((v, i) => <ValidationRow key={i} v={v} />)}</div>}

      {/* Validaciones warn/fail */}
      {warns.length > 0 && <div style={{ padding: "8px 0" }}>{warns.map((v, i) => <ValidationRow key={i} v={v} />)}</div>}

      {/* Validaciones info */}
      {infos.length > 0 && <div style={{ padding: "8px 0" }}>{infos.map((v, i) => <ValidationRow key={i} v={v} />)}</div>}

      {/* Datos del comprobante */}
      {result.campos_extraidos && Object.values(result.campos_extraidos).some(Boolean) && (
        <div style={{ padding: "16px 24px", background: "#F8FAFC", borderTop: "1px solid #F0F4F8" }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>Datos del comprobante</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {Object.entries(result.campos_extraidos).filter(([, v]) => v).map(([k, v]) => (
              <div key={k} style={{ background: "#fff", borderRadius: 8, padding: "8px 10px", border: "1px solid #E2E8F0" }}>
                <div style={{ fontSize: 10, color: "#CBD5E1", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 2 }}>{k.replace(/_/g, " ")}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: "#1E293B" }}>{v}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recomendación */}
      {result.recomendacion && (
        <div style={{ padding: "14px 24px", background: `${TEAL}10`, borderTop: "1px solid #F0F4F8", borderBottom: "1px solid #F0F4F8" }}>
          <div style={{ fontSize: 11, color: TEAL, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 4 }}>💡 Recomendación</div>
          <div style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>{result.recomendacion}</div>
        </div>
      )}

      <div style={{ padding: "10px 24px", textAlign: "center" }}>
        <div style={{ fontSize: 11, color: "#CBD5E1" }}>🛡️ VerificaPago no confirma transferencias oficialmente</div>
      </div>
      <div style={{ padding: "4px 20px 24px" }}>
        <button onClick={onReset} style={{ width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
          Analizar otro comprobante
        </button>
      </div>
    </div>
  );
}

const STAGE_LABELS = [
  "Cargando comprobante...", "Extrayendo datos con OCR...", "Normalizando campos...",
  "Ejecutando validaciones estructurales...", "Analizando consistencia visual y contextual...",
  "Calculando score de riesgo...", "Generando reporte final..."
];

export default function Home() {
  const [file, setFile]             = useState<File | null>(null);
  const [preview, setPreview]       = useState<string | null>(null);
  const [bankHint, setBankHint]     = useState("");
  const [clabeInput, setClabeInput] = useState("");
  const [fechaPasadaConfirmada, setFechaPasadaConfirmada] = useState(false);
  const [stage, setStage]           = useState<Stage>("idle");
  const [result, setResult]         = useState<Resultado | null>(null);
  const [error, setError]           = useState<string | null>(null);
  const [dragging, setDragging]     = useState(false);
  // Mejora 2: stage label independiente del fetch
  const [stageLabel, setStageLabel] = useState(STAGE_LABELS[0]);
  const stageLabelIdx               = useRef(0);
  const stageLabelTimer             = useRef<ReturnType<typeof setInterval> | null>(null);
  const inputRef                    = useRef<HTMLInputElement>(null);
  // Mejora 2: progress independiente
  const { progress, complete: completeProgress } = useProgress(stage === "loading");
  // Mejora 3: abort controller para timeout de 30s
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => { if (preview) URL.revokeObjectURL(preview); };
  }, [preview]);

  // Animar labels de stage de forma independiente al fetch
  const startStageLabels = () => {
    stageLabelIdx.current = 0;
    setStageLabel(STAGE_LABELS[0]);
    stageLabelTimer.current = setInterval(() => {
      stageLabelIdx.current = Math.min(stageLabelIdx.current + 1, STAGE_LABELS.length - 1);
      setStageLabel(STAGE_LABELS[stageLabelIdx.current]);
    }, 2200);
  };
  const stopStageLabels = () => {
    if (stageLabelTimer.current) clearInterval(stageLabelTimer.current);
  };

  const handleFile = useCallback((f: File) => {
    const ok = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];
    if (!ok.includes(f.type)) { setError("Formato no soportado."); return; }
    setError(null); setFile(f); setResult(null);
    if (f.type !== "application/pdf") setPreview(URL.createObjectURL(f));
    else setPreview(null);
  }, []);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0]; if (f) handleFile(f);
  }, [handleFile]);

  const analyze = async (fechaConfirmada = false) => {
    if (!file) return;

    // Mejora 3: cancelar petición anterior si existe
    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();

    setStage("loading"); setResult(null); setError(null);
    startStageLabels();

    // Mejora 3: timeout de 30 segundos
    const timeoutId = setTimeout(() => abortRef.current?.abort(), 30000);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("banco_hint", bankHint);
    fd.append("clabe_hint", clabeInput);
    fd.append("fecha_pasada_confirmada", fechaConfirmada ? "true" : "false");

    try {
      const resp = await fetch(`${API_URL}/analizar`, {
        method: "POST",
        body: fd,
        signal: abortRef.current.signal,
      });
      clearTimeout(timeoutId);

      if (!resp.ok) throw new Error(`Error del servidor: ${resp.status}`);
      const parsed: Resultado = await resp.json();

      // Mejora 1: el backend ya validó la CLABE — el frontend NO recalcula
      // Solo ajustar score/riesgo si backend reporta CLABE inválida
      if (parsed.clabe_resultado && !parsed.clabe_resultado.valid) {
        parsed.score = Math.max(parsed.score || 0, 70);
        parsed.riesgo = "ALTO";
      }

      stopStageLabels();
      completeProgress();
      // Pequeña pausa para que la barra llegue visualmente al 100%
      await new Promise(r => setTimeout(r, 400));

      const tieneFechaAlert = !fechaConfirmada && parsed.requiere_confirmacion_fecha === true;
      setResult(parsed);
      setStage(tieneFechaAlert ? "fecha_banner" : "done");

    } catch (e: unknown) {
      clearTimeout(timeoutId);
      stopStageLabels();
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("abort") || msg.includes("AbortError")) {
        setError("El análisis tardó demasiado (30s). Intenta de nuevo o verifica tu conexión.");
      } else {
        setError(`Error: ${msg}`);
      }
      setStage("idle");
    }
  };

  const reset = () => {
    abortRef.current?.abort();
    stopStageLabels();
    setFile(null); setPreview(null); setStage("idle");
    setResult(null); setError(null); setBankHint(""); setClabeInput("");
    setFechaPasadaConfirmada(false);
  };

  const confirmarFechaPasada = () => {
    setFechaPasadaConfirmada(true);
    analyze(true);
  };

  // Etiqueta de progreso para el loading
  const progressLabel = stage === "loading" ? stageLabel : "";
  const progressPct   = progress;

  return (
    <div style={{ minHeight: "100vh", background: `linear-gradient(160deg, ${DARK} 0%, #0D2137 100%)`, fontFamily: "'Inter',system-ui,sans-serif", padding: "0 0 40px" }}>
      <div style={{ padding: "24px 20px 20px", textAlign: "center" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 36, height: 36, borderRadius: 9, background: `${TEAL}25`, border: `2px solid ${TEAL}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🛡️</div>
          <span style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px", color: "#fff" }}>Verifica<span style={{ color: TEAL }}>Pago</span></span>
        </div>
        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)" }}>Detecta fraudes. Evita pérdidas. Toma decisiones seguras.</div>
      </div>

      <div style={{ maxWidth: 420, margin: "0 auto", padding: "0 16px" }}>

        {/* ── IDLE ──────────────────────────────────────────────────────────── */}
        {stage === "idle" && (
          <>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 0, marginBottom: 20, background: "rgba(255,255,255,0.05)", borderRadius: 16, padding: "14px 10px" }}>
              {[["📤","Subes"],["🔍","Analizamos"],["🛡️","Validamos"],["⚡","Evaluamos"],["✅","Resultado"]].map(([ic, lb], i, a) => (
                <div key={i} style={{ display: "flex", alignItems: "center" }}>
                  <div style={{ textAlign: "center", minWidth: 52 }}>
                    <div style={{ fontSize: 22, marginBottom: 4 }}>{ic}</div>
                    <div style={{ fontSize: 9, color: TEAL, fontWeight: 600, letterSpacing: "0.04em" }}>{lb}</div>
                  </div>
                  {i < a.length - 1 && <div style={{ width: 16, height: 1, background: `${TEAL}40`, marginBottom: 14, flexShrink: 0 }} />}
                </div>
              ))}
            </div>
            <div style={{ background: "rgba(255,255,255,0.07)", borderRadius: 16, padding: "14px 16px", marginBottom: 16, fontSize: 13, color: "rgba(255,255,255,0.6)", border: `1px solid ${TEAL}30` }}>
              ℹ️ Sube el comprobante desde la app de tu banco, correo o captura. Los números ocultos (****1234) son normales.
            </div>
            <div onDrop={onDrop} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
              onClick={() => inputRef.current?.click()}
              style={{ border: `2px dashed ${dragging ? TEAL : "rgba(255,255,255,0.2)"}`, borderRadius: 20, padding: "2.5rem 1.5rem", textAlign: "center", cursor: "pointer", background: dragging ? `${TEAL}15` : "rgba(255,255,255,0.05)", transition: "all 0.2s" }}>
              <div style={{ fontSize: 44, marginBottom: 12 }}>📤</div>
              <p style={{ margin: 0, fontWeight: 600, fontSize: 15, color: "#fff" }}>{file ? file.name : "Arrastra o toca para cargar"}</p>
              <p style={{ margin: "6px 0 0", fontSize: 13, color: "rgba(255,255,255,0.4)" }}>PNG, JPG o PDF</p>
              <input ref={inputRef} type="file" accept=".png,.jpg,.jpeg,.pdf" style={{ display: "none" }} onChange={e => e.target.files?.[0] && handleFile(e.target.files[0])} />
            </div>
            {preview && (
              <div style={{ marginTop: 12, borderRadius: 14, overflow: "hidden", border: "1px solid rgba(255,255,255,0.1)", maxHeight: 180, display: "flex", alignItems: "center", justifyContent: "center", background: "rgba(0,0,0,0.3)" }}>
                <img src={preview} alt="Vista previa" style={{ maxWidth: "100%", maxHeight: 180, objectFit: "contain" }} />
              </div>
            )}
            {file && (
              <>
                <div style={{ marginTop: 14, display: "flex", flexDirection: "column", gap: 10 }}>
                  <div>
                    <label style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", display: "block", marginBottom: 6 }}>🏦 Banco emisor <span style={{ color: "rgba(255,255,255,0.3)" }}>(opcional)</span></label>
                    <input value={bankHint} onChange={e => setBankHint(e.target.value)} placeholder="Ej: Banco Azteca, BBVA, Santander..."
                      style={{ width: "100%", padding: "12px 14px", fontSize: 14, borderRadius: 12, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.08)", color: "#fff", boxSizing: "border-box" }} />
                  </div>
                  <div>
                    <label style={{ fontSize: 13, color: "rgba(255,255,255,0.5)", display: "block", marginBottom: 6 }}>
                      🔢 CLABE o número de cuenta <span style={{ color: "rgba(255,255,255,0.3)" }}>(opcional)</span>
                    </label>
                    <input value={clabeInput} onChange={e => setClabeInput(e.target.value.replace(/\D/g, ""))}
                      placeholder="18 dígitos CLABE o número de cuenta" maxLength={18}
                      style={{ width: "100%", padding: "12px 14px", fontSize: 14, borderRadius: 12, border: `1px solid ${clabeInput.length > 0 && clabeInput.length !== 18 ? "rgba(229,57,53,0.5)" : clabeInput.length === 18 ? "rgba(0,191,165,0.5)" : "rgba(255,255,255,0.15)"}`, background: "rgba(255,255,255,0.08)", color: "#fff", boxSizing: "border-box", fontFamily: "monospace", letterSpacing: "0.05em" }} />
                    {clabeInput.length > 0 && (
                      <div style={{ fontSize: 12, marginTop: 4, color: clabeInput.length === 18 ? TEAL : "rgba(229,57,53,0.8)" }}>
                        {clabeInput.length === 18 ? "✓ Longitud correcta" : `${clabeInput.length}/18 dígitos`}
                      </div>
                    )}
                  </div>
                </div>
                <button onClick={() => analyze(false)} style={{ marginTop: 14, width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
                  🔍 Analizar comprobante
                </button>
              </>
            )}
            {error && <div style={{ marginTop: 12, padding: "12px 16px", background: "rgba(229,57,53,0.15)", color: "#FF6B6B", borderRadius: 12, fontSize: 14, border: "1px solid rgba(229,57,53,0.3)" }}>⚠️ {error}</div>}
          </>
        )}

        {/* ── LOADING ───────────────────────────────────────────────────────── */}
        {stage === "loading" && (
          <div style={{ background: "rgba(255,255,255,0.07)", borderRadius: 20, padding: "2rem 1.5rem", marginTop: 8, border: "1px solid rgba(255,255,255,0.1)" }}>
            <p style={{ fontWeight: 600, margin: "0 0 1rem", fontSize: 15, color: TEAL }}>{progressLabel}</p>
            {/* Mejora 2: barra animada con progress real */}
            <div style={{ height: 6, background: "rgba(255,255,255,0.1)", borderRadius: 3, overflow: "hidden", marginBottom: 20 }}>
              <div style={{ height: "100%", width: `${progressPct}%`, background: `linear-gradient(90deg, ${TEAL}, #00E5D0)`, borderRadius: 3, transition: "width 0.4s ease" }} />
            </div>
            {STAGE_LABELS.map((s, i) => {
              const done = s === stageLabel
                ? false
                : STAGE_LABELS.indexOf(stageLabel) > i;
              const current = s === stageLabel;
              return (
                <div key={i} style={{ display: "flex", gap: 10, padding: "7px 0", opacity: done || current ? 1 : 0.3, transition: "opacity 0.3s", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                  <span style={{ color: done ? TEAL : current ? ORANGE : "rgba(255,255,255,0.3)", fontWeight: 700, fontSize: 14 }}>
                    {done ? "✓" : current ? "⟳" : "○"}
                  </span>
                  <span style={{ fontSize: 13, color: current ? "#fff" : "rgba(255,255,255,0.6)" }}>{s}</span>
                </div>
              );
            })}
          </div>
        )}

        {/* ── BANNER FECHA PASADA ───────────────────────────────────────────── */}
        {stage === "fecha_banner" && result && (
          <div style={{ background: "#FFF8E1", border: "1.5px solid #F5A623", borderRadius: 16, padding: "22px 20px", marginTop: 8 }}>
            <div style={{ fontSize: 32, textAlign: "center", marginBottom: 10 }}>📅</div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#854F0B", marginBottom: 10, textAlign: "center" }}>
              Este comprobante es de una fecha pasada
            </div>
            <div style={{ fontSize: 13, color: "#5C3D0A", marginBottom: 8, lineHeight: 1.7, background: "rgba(245,166,35,0.12)", borderRadius: 8, padding: "10px 12px" }}>
              {result.mensaje_confirmacion_fecha ||
                "El comprobante tiene una fecha anterior a hoy. Si estás validando una transferencia pasada, confírmalo para que el sistema no penalice la fecha."}
            </div>
            <div style={{ fontSize: 12, color: "#7C4A0A", marginBottom: 18, lineHeight: 1.5 }}>
              ⚠️ Si no confirmas, el sistema puede marcar la fecha como sospechosa y elevar el riesgo innecesariamente.
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <button onClick={confirmarFechaPasada}
                style={{ width: "100%", padding: "14px", fontSize: 14, fontWeight: 700, borderRadius: 10, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
                ✓ Sí, es un comprobante pasado — re-analizar sin penalizar fecha
              </button>
              <button onClick={() => setStage("done")}
                style={{ width: "100%", padding: "14px", fontSize: 14, fontWeight: 600, borderRadius: 10, cursor: "pointer", background: "#fff", color: "#854F0B", border: "1.5px solid #F5A623" }}>
                ✗ No, analizarlo normalmente
              </button>
            </div>
          </div>
        )}

        {/* ── RESULTADO ─────────────────────────────────────────────────────── */}
        {stage === "done" && result && <ResultScreen result={result} file={file} onReset={reset} />}
      </div>
    </div>
  );
}
