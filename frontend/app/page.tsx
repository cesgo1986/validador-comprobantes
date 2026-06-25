"use client";
import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis } from "./context/AnalisisContext";

const TEAL = "#00BFA5";

export default function Home() {
  const router = useRouter();
  const { file, setFile, preview, setPreview, bankHint, setBankHint, clabeInput, setClabeInput } = useAnalisis();
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    const ok = ["image/png", "image/jpeg", "image/jpg", "application/pdf"];
    if (!ok.includes(f.type)) { setError("Formato no soportado."); return; }
    setError(null);
    setFile(f);
    if (f.type !== "application/pdf") setPreview(URL.createObjectURL(f));
    else setPreview(null);
  }, [setFile, setPreview]);

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const f = e.dataTransfer.files[0]; if (f) handleFile(f);
  }, [handleFile]);

  const irAAnalizar = () => {
    if (!file) return;
    router.push("/analizando");
  };

  return (
    <div style={{ padding: "0 0 24px" }}>
      <div style={{ padding: "24px 20px 20px", textAlign: "center" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10, marginBottom: 6 }}>
          <div style={{ width: 36, height: 36, borderRadius: 9, background: `${TEAL}25`, border: `2px solid ${TEAL}`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>🛡️</div>
          <span style={{ fontSize: 26, fontWeight: 800, letterSpacing: "-0.5px", color: "#fff" }}>Verifica<span style={{ color: TEAL }}>Pago</span></span>
        </div>
        <div style={{ fontSize: 13, color: "rgba(255,255,255,0.5)" }}>Detecta fraudes. Evita pérdidas. Toma decisiones seguras.</div>
      </div>

      <div style={{ padding: "0 16px" }}>
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
            <button onClick={irAAnalizar} style={{ marginTop: 14, width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
              🔍 Analizar comprobante
            </button>
          </>
        )}
        {error && <div style={{ marginTop: 12, padding: "12px 16px", background: "rgba(229,57,53,0.15)", color: "#FF6B6B", borderRadius: 12, fontSize: 14, border: "1px solid rgba(229,57,53,0.3)" }}>⚠️ {error}</div>}
      </div>
    </div>
  );
}