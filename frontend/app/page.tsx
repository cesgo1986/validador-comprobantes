"use client";
import { useState, useRef, useCallback } from "react";

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

type RiskLevel = "BAJO" | "MEDIO" | "ALTO" | "INDETERMINADO";
type Status = "ok" | "warn" | "fail" | "info";

interface Validacion { categoria: string; nombre: string; status: Status; detalle: string; }
interface Resultado {
  riesgo: RiskLevel; score: number;
  campos_extraidos: Record<string, string | null>;
  validaciones: Validacion[]; resumen: string; recomendacion: string;
}

function validateCLABE(clabe: string) {
  const c = clabe.replace(/\s/g, "");
  if (c.length !== 18 || !/^\d{18}$/.test(c)) return { valid: false, reason: "CLABE inválida" };
  const w = [3,7,1,3,7,1,3,7,1,3,7,1,3,7,1,3,7];
  let s = 0; for (let i = 0; i < 17; i++) s += parseInt(c[i]) * w[i];
  const chk = (10 - (s % 10)) % 10;
  if (chk !== parseInt(c[17])) return { valid: false, reason: "Dígito verificador incorrecto" };
  return { valid: true, bank: BANKS[c.substring(0, 3)] || "Banco no reconocido", bankCode: c.substring(0, 3) };
}

function toBase64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res((r.result as string).split(",")[1]);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
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
          transform="rotate(135 50 58)" style={{ transition: "stroke-dasharray 1s ease, stroke 0.5s" }} />
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
        </div>
      )}
    </div>
  );
}

function ResultScreen({ result, file, onReset }: { result: Resultado; file: File | null; onReset: () => void }) {
  const riskCfg = {
    BAJO: { label: "BAJO", color: GREEN },
    MEDIO: { label: "MEDIO", color: ORANGE },
    ALTO: { label: "ALTO", color: RED },
    INDETERMINADO: { label: "INDETERMINADO", color: "#9CA3AF" },
  };
  const rc = riskCfg[result.riesgo] || riskCfg.INDETERMINADO;
  const oks = (result.validaciones || []).filter(v => v.status === "ok");
  const warns = (result.validaciones || []).filter(v => v.status === "warn" || v.status === "fail");
  const infos = (result.validaciones || []).filter(v => v.status === "info");

  return (
    <div style={{ background: "#fff", borderRadius: 24, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.15)", maxWidth: 380, margin: "0 auto" }}>
      <div style={{ background: DARK, padding: "18px 20px", textAlign: "center" }}>
        <div style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 2 }}>Resultado del análisis</div>
        {file && <div style={{ fontSize: 11, color: "rgba(255,255,255,0.4)", marginTop: 2 }}>📄 {file.name}</div>}
      </div>
      <div style={{ padding: "24px 24px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid #F0F4F8" }}>
        <div>
          <div style={{ fontSize: 12, color: "#9CA3AF", fontWeight: 500, letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 4 }}>RIESGO</div>
          <div style={{ fontSize: 36, fontWeight: 800, color: rc.color, lineHeight: 1, letterSpacing: "-1px" }}>{rc.label}</div>
        </div>
        <GaugeCircle score={result.score} />
      </div>
      {result.resumen && (
        <div style={{ padding: "12px 24px", background: "#F8FAFC", borderBottom: "1px solid #F0F4F8" }}>
          <p style={{ margin: 0, fontSize: 13, color: "#64748B", lineHeight: 1.6 }}>{result.resumen}</p>
        </div>
      )}
      {oks.length > 0 && <div style={{ padding: "8px 0" }}>{oks.map((v, i) => <ValidationRow key={i} v={v} />)}</div>}
      {warns.length > 0 && <div style={{ padding: "8px 0" }}>{warns.map((v, i) => <ValidationRow key={i} v={v} />)}</div>}
      {infos.length > 0 && <div style={{ padding: "8px 0" }}>{infos.map((v, i) => <ValidationRow key={i} v={v} />)}</div>}
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

const STAGES = [
  "Cargando comprobante...", "Extrayendo datos con OCR...", "Normalizando campos...",
  "Ejecutando validaciones estructurales...", "Analizando consistencia visual y contextual...",
  "Calculando score de riesgo...", "Generando reporte final..."
];

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [bankHint, setBankHint] = useState("");
  const [clabeInput, setClabeInput] = useState("");
  const [fechaPasadaConfirmada, setFechaPasadaConfirmada] = useState(false);
  const [showFechaBanner, setShowFechaBanner] = useState(false);
  const [stage, setStage] = useState<"idle" | "loading" | "done">("idle");
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<Resultado | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

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

  const tick = (i: number) => new Promise<void>(r => setTimeout(() => { setProgress(i); r(); }, 600));

  const analyze = async () => {
    if (!file) return;
    setStage("loading"); setProgress(0); setResult(null); setError(null);
    for (let i = 1; i <= 5; i++) await tick(i);
    let b64: string;
    try { b64 = await toBase64(file); } catch { setError("Error leyendo archivo."); setStage("idle"); return; }
    const now = new Date();
    const fechaHoy = now.toISOString().split("T")[0];
    const fechaLeg = now.toLocaleDateString("es-MX", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
    const bHint = bankHint.trim() ? `\nBANCO EMISOR: "${bankHint.trim()}". Úsalo como banco origen.` : "";
    const clabeHint = clabeInput.length === 18
      ? `\nCLABE INGRESADA POR USUARIO: ${clabeInput}. Compara con la CLABE o cuenta destino visible en el comprobante.`
      : clabeInput.length > 0 ? `\nCUENTA PARCIAL INGRESADA: ${clabeInput} (${clabeInput.length} dígitos).` : "";

    const fd = new FormData();
    fd.append("file", file);
    fd.append("banco_hint", bankHint);
    fd.append("clabe_hint", clabeInput);

    try {
      const resp = await fetch(`${API_URL}/analizar`, { method: "POST", body: fd });
      await tick(6);
      if (!resp.ok) throw new Error(`Error del servidor: ${resp.status}`);
      const parsed: Resultado = await resp.json();

      if (clabeInput.length === 18) {
        const cv = validateCLABE(clabeInput);
        const entry: Validacion = {
          categoria: "estructural",
          nombre: "CLABE ingresada — dígito verificador",
          status: cv.valid ? "ok" : "fail",
          detalle: cv.valid
            ? `CLABE válida. Banco: ${cv.bank} (${cv.bankCode})`
            : `CLABE inválida: ${cv.reason}`
        };
        parsed.validaciones = [entry, ...(parsed.validaciones || [])];
        if (!cv.valid) { parsed.score = Math.max(parsed.score || 0, 70); parsed.riesgo = "ALTO"; }
      }

      await tick(7); 

      // Detectar si el resultado tiene alerta de fecha futura/pasada
      const tieneFechaAlert = parsed.validaciones?.some((v: Validacion) =>
        v.nombre?.toLowerCase().includes("fecha") && v.status === "fail"
      );
      if (tieneFechaAlert && !fechaPasadaConfirmada) {
        setShowFechaBanner(true);
      }

      setResult(parsed); setStage("done");
    } catch (e: unknown) {
      setError(`Error: ${e instanceof Error ? e.message : String(e)}`);
      setStage("idle");
    }
  };

  const reset = () => { setFile(null); setPreview(null); setStage("idle"); setProgress(0); setResult(null); setError(null); setBankHint(""); setClabeInput(""); setFechaPasadaConfirmada(false); setShowFechaBanner(false); };

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
                      🔢 CLABE o número de cuenta <span style={{ color: "rgba(255,255,255,0.3)" }}>(opcional — mejora el análisis)</span>
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
                <button onClick={analyze} style={{ marginTop: 14, width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
                  🔍 Analizar comprobante
                </button>
              </>
            )}

            {error && <div style={{ marginTop: 12, padding: "12px 16px", background: "rgba(229,57,53,0.15)", color: "#FF6B6B", borderRadius: 12, fontSize: 14, border: "1px solid rgba(229,57,53,0.3)" }}>⚠️ {error}</div>}
          </>
        )}

        {stage === "loading" && (
          <div style={{ background: "rgba(255,255,255,0.07)", borderRadius: 20, padding: "2rem 1.5rem", marginTop: 8, border: "1px solid rgba(255,255,255,0.1)" }}>
            <p style={{ fontWeight: 600, margin: "0 0 1rem", fontSize: 15, color: TEAL }}>{STAGES[Math.min(progress, STAGES.length - 1)]}</p>
            <div style={{ height: 4, background: "rgba(255,255,255,0.1)", borderRadius: 2, overflow: "hidden", marginBottom: 20 }}>
              <div style={{ height: "100%", width: `${(progress / 7) * 100}%`, background: TEAL, borderRadius: 2, transition: "width 0.5s ease" }} />
            </div>
            {STAGES.map((s, i) => (
              <div key={i} style={{ display: "flex", gap: 10, padding: "7px 0", opacity: progress >= i + 1 ? 1 : 0.3, transition: "opacity 0.3s", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span style={{ color: progress >= i + 1 ? TEAL : "rgba(255,255,255,0.3)", fontWeight: 700, fontSize: 14 }}>{progress >= i + 1 ? "✓" : "○"}</span>
                <span style={{ fontSize: 13, color: "rgba(255,255,255,0.6)" }}>{s}</span>
              </div>
            ))}
          </div>
        )}

        {stage === "done" && result && showFechaBanner && !fechaPasadaConfirmada && (
          <div style={{ background: "#FFF8E1", border: "1.5px solid #F5A623", borderRadius: 14, padding: "16px 20px", marginBottom: 16, marginTop: 8 }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: "#854F0B", marginBottom: 6 }}>
              📅 ¿Este comprobante es de una fecha pasada?
            </div>
            <div style={{ fontSize: 13, color: "#5C3D0A", marginBottom: 12, lineHeight: 1.6 }}>
              El sistema detectó una posible inconsistencia en la fecha. Si estás validando un comprobante de días o meses anteriores, confírmalo para que el análisis sea más preciso.
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => { setFechaPasadaConfirmada(true); setShowFechaBanner(false); analyze(); }}
                style={{ flex: 1, padding: "10px", fontSize: 13, fontWeight: 700, borderRadius: 10, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
                ✓ Sí, es un comprobante pasado
              </button>
              <button
                onClick={() => setShowFechaBanner(false)}
                style={{ flex: 1, padding: "10px", fontSize: 13, fontWeight: 600, borderRadius: 10, cursor: "pointer", background: "#fff", color: "#854F0B", border: "1.5px solid #F5A623" }}>
                ✗ No, mantener alerta
              </button>
            </div>
          </div>
        )}
        {stage === "done" && result && <ResultScreen result={result} file={file} onReset={reset} />}
      </div>
    </div>
  );
}
