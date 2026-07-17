"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis, Resultado } from "../context/AnalisisContext";
import { apiFetch } from "../lib/apiFetch";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TEAL = "#00BFA5";
const ORANGE = "#F5A623";
const REQUEST_TIMEOUT_MS = 60000;

const STAGE_LABELS = [
  "Cargando comprobante...", "Extrayendo datos con OCR...", "Normalizando campos...",
  "Ejecutando validaciones estructurales...", "Analizando consistencia visual y contextual...",
  "Calculando score de riesgo...", "Generando reporte final...",
];

function useProgress(active: boolean) {
  const [progress, setProgress] = useState(0);
  const rafRef = useRef<number | null>(null);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (!active) { setProgress(0); return; }
    startRef.current = Date.now();
    const tick = () => {
      const elapsed = (Date.now() - startRef.current) / 1000;
      const pct = Math.min(82, Math.round(80 * (1 - Math.exp(-elapsed / 4))));
      setProgress(pct);
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [active]);

  return { progress, complete: () => setProgress(100) };
}

export default function Analizando() {
  const router = useRouter();
  const { file, bankHint, clabeInput, setResult } = useAnalisis();
  const [stageLabel, setStageLabel] = useState(STAGE_LABELS[0]);
  const [error, setError] = useState<string | null>(null);
  const [fechaBanner, setFechaBanner] = useState<{ mensaje: string; resultadoPendiente: Resultado } | null>(null);
  const stageLabelIdx = useRef(0);
  const stageLabelTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { progress, complete: completeProgress } = useProgress(!fechaBanner && !error);

  const startStageLabels = () => {
    stageLabelIdx.current = 0;
    setStageLabel(STAGE_LABELS[0]);
    stageLabelTimer.current = setInterval(() => {
      stageLabelIdx.current = Math.min(stageLabelIdx.current + 1, STAGE_LABELS.length - 1);
      setStageLabel(STAGE_LABELS[stageLabelIdx.current]);
    }, 2200);
  };
  const stopStageLabels = () => { if (stageLabelTimer.current) clearInterval(stageLabelTimer.current); };

  const analyze = async (fechaConfirmada = false) => {
    if (!file) { router.replace("/"); return; }

    if (abortRef.current) abortRef.current.abort();
    abortRef.current = new AbortController();
    setError(null);
    startStageLabels();

    const timeoutId = setTimeout(() => abortRef.current?.abort(), REQUEST_TIMEOUT_MS);

    const fd = new FormData();
    fd.append("file", file);
    fd.append("banco_hint", bankHint);
    fd.append("clabe_hint", clabeInput);
    fd.append("fecha_pasada_confirmada", fechaConfirmada ? "true" : "false");

    try {
      const resp = await apiFetch(`${API_URL}/analizar`, { method: "POST", body: fd, signal: abortRef.current.signal });
      clearTimeout(timeoutId);
      if (!resp.ok) throw new Error(`Error del servidor: ${resp.status}`);
      const parsed: Resultado = await resp.json();

      if (parsed.clabe_resultado && !parsed.clabe_resultado.valid) {
        parsed.score = Math.max(parsed.score || 0, 70);
        parsed.riesgo = "ALTO";
      }

      stopStageLabels();
      completeProgress();
      await new Promise(r => setTimeout(r, 400));

      const tieneFechaAlert = !fechaConfirmada && parsed.requiere_confirmacion_fecha === true;
      if (tieneFechaAlert) {
        setFechaBanner({
          mensaje: parsed.mensaje_confirmacion_fecha || "El comprobante tiene una fecha anterior a hoy. Si estás validando una transferencia pasada, confírmalo para que el sistema no penalice la fecha.",
          resultadoPendiente: parsed,
        });
        return;
      }

      setResult(parsed);
      router.push("/resultado");
    } catch (e: unknown) {
      clearTimeout(timeoutId);
      stopStageLabels();
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("abort") || msg.includes("AbortError")) {
        setError(`El análisis tardó demasiado (${REQUEST_TIMEOUT_MS / 1000}s). Intenta de nuevo o verifica tu conexión.`);
      } else {
        setError(`Error: ${msg}`);
      }
    }
  };

  useEffect(() => {
    analyze(false);
    return () => { abortRef.current?.abort(); stopStageLabels(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const confirmarFechaPasada = () => {
    setFechaBanner(null);
    setResult(fechaBanner!.resultadoPendiente);
    analyze(true);
  };

  const continuarSinConfirmar = () => {
    if (!fechaBanner) return;
    setResult(fechaBanner.resultadoPendiente);
    router.push("/resultado");
  };

  if (error) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center" }}>
        <div style={{ fontSize: 40, marginBottom: 12 }}>⚠️</div>
        <p style={{ color: "#FF6B6B", fontSize: 14, marginBottom: 20 }}>{error}</p>
        <button onClick={() => router.replace("/")} style={{ padding: "12px 24px", borderRadius: 12, background: TEAL, color: "#fff", border: "none", fontWeight: 700 }}>
          Volver a intentar
        </button>
      </div>
    );
  }

  if (fechaBanner) {
    return (
      <div style={{ padding: "16px" }}>
        <div style={{ background: "#FFF8E1", border: "1.5px solid #F5A623", borderRadius: 16, padding: "22px 20px", marginTop: 8 }}>
          <div style={{ fontSize: 32, textAlign: "center", marginBottom: 10 }}>📅</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#854F0B", marginBottom: 10, textAlign: "center" }}>
            Este comprobante es de una fecha pasada
          </div>
          <div style={{ fontSize: 13, color: "#5C3D0A", marginBottom: 8, lineHeight: 1.7, background: "rgba(245,166,35,0.12)", borderRadius: 8, padding: "10px 12px" }}>
            {fechaBanner.mensaje}
          </div>
          <div style={{ fontSize: 12, color: "#7C4A0A", marginBottom: 18, lineHeight: 1.5 }}>
            ⚠️ Si no confirmas, el sistema puede marcar la fecha como sospechosa y elevar el riesgo innecesariamente.
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <button onClick={confirmarFechaPasada} style={{ width: "100%", padding: "14px", fontSize: 14, fontWeight: 700, borderRadius: 10, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
              ✓ Sí, es un comprobante pasado — re-analizar sin penalizar fecha
            </button>
            <button onClick={continuarSinConfirmar} style={{ width: "100%", padding: "14px", fontSize: 14, fontWeight: 600, borderRadius: 10, cursor: "pointer", background: "#fff", color: "#854F0B", border: "1.5px solid #F5A623" }}>
              ✗ No, analizarlo normalmente
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 4px 16px" }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Analizando comprobante</span>
      </div>
      <div style={{ background: "rgba(255,255,255,0.07)", borderRadius: 20, padding: "2rem 1.5rem", border: "1px solid rgba(255,255,255,0.1)" }}>
        <p style={{ fontWeight: 600, margin: "0 0 1rem", fontSize: 15, color: TEAL }}>{stageLabel}</p>
        <div style={{ height: 6, background: "rgba(255,255,255,0.1)", borderRadius: 3, overflow: "hidden", marginBottom: 20 }}>
          <div style={{ height: "100%", width: `${progress}%`, background: `linear-gradient(90deg, ${TEAL}, #00E5D0)`, borderRadius: 3, transition: "width 0.4s ease" }} />
        </div>
        {STAGE_LABELS.map((s, i) => {
          const done = s === stageLabel ? false : STAGE_LABELS.indexOf(stageLabel) > i;
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
    </div>
  );
}