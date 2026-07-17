"use client";
import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAnalisis } from "./context/AnalisisContext";
import { useAuth } from "./context/AuthContext";

const TEAL = "#00BFA5";

// Item 6.2.8 (Etapa 6, ajuste posterior): la pantalla de inicio es
// pública (ver RequireAuth.tsx) -- cualquiera puede ver el área de
// carga, elegir un archivo, y llenar banco/CLABE sin sesión. El
// bloqueo real está en irAAnalizar(): si no hay sesión, redirige a
// /login en vez de proceder -- no antes. El backend ya exige JWT en
// /analizar desde 6.2.8; este cambio solo hace que el frontend
// reaccione visiblemente en vez de que la petición falle sin más.
export default function Home() {
  const router = useRouter();
  const { file, setFile, preview, setPreview, bankHint, setBankHint, clabeInput, setClabeInput } = useAnalisis();
  const { session } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const manejarArchivo = (f: File) => {
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setError(null);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const f = e.dataTransfer.files?.[0];
    if (f) manejarArchivo(f);
  };

  const onSelectFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) manejarArchivo(f);
  };

  const irAAnalizar = () => {
    if (!session) {
      router.push("/login");
      return;
    }
    if (!file) {
      setError("Selecciona un comprobante antes de continuar.");
      return;
    }
    router.push("/analizando");
  };

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ textAlign: "center", padding: "20px 0" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8 }}>
          <span style={{ fontSize: 20 }}>🛡️</span>
          <span style={{ color: "#fff", fontWeight: 800, fontSize: 22 }}>
            Verifica<span style={{ color: TEAL }}>Pago</span>
          </span>
        </div>
        <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 13, marginTop: 6 }}>
          Detecta fraudes. Evita pérdidas. Toma decisiones seguras.
        </p>
      </div>

      <div style={{ background: "rgba(255,255,255,0.08)", borderRadius: 14, padding: "12px 16px", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
        <span>ℹ️</span>
        <span style={{ color: "rgba(255,255,255,0.85)", fontSize: 13 }}>
          Sube el comprobante desde la app de tu banco, correo o captura. Los números ocultos (****1234) son normales.
        </span>
      </div>

      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        style={{
          border: "2px dashed rgba(255,255,255,0.25)", borderRadius: 16, padding: "40px 20px",
          textAlign: "center", cursor: "pointer", marginBottom: 16,
        }}
      >
        <input ref={inputRef} type="file" accept="image/*,.pdf" onChange={onSelectFile} style={{ display: "none" }} />
        <div style={{ fontSize: 40, marginBottom: 12 }}>📤</div>
        {file ? (
          <p style={{ color: "#fff", fontWeight: 700, fontSize: 14, margin: 0 }}>{file.name}</p>
        ) : (
          <>
            <p style={{ color: "#fff", fontWeight: 700, fontSize: 15, margin: 0 }}>Arrastra o toca para cargar</p>
            <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 13, marginTop: 6 }}>PNG, JPG o PDF</p>
          </>
        )}
      </div>

      {preview && (
        <div style={{ background: "#0D1117", borderRadius: 14, padding: 16, marginBottom: 16, textAlign: "center" }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={preview} alt="Vista previa" style={{ maxWidth: "100%", maxHeight: 240, borderRadius: 8 }} />
        </div>
      )}

      {file && (
        <>
          <div style={{ marginBottom: 14 }}>
            <label style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>🏦 Banco emisor (opcional)</label>
            <input
              value={bankHint}
              onChange={(e) => setBankHint(e.target.value)}
              placeholder="Ej: Banco Azteca, BBVA, Santander..."
              style={{ width: "100%", marginTop: 6, padding: 12, borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.05)", color: "#fff", fontSize: 14, boxSizing: "border-box" }}
            />
          </div>

          <div style={{ marginBottom: 8 }}>
            <label style={{ color: "rgba(255,255,255,0.6)", fontSize: 12 }}>🔢 CLABE, número de cuenta o tarjeta (opcional)</label>
            <input
              value={clabeInput}
              onChange={(e) => setClabeInput(e.target.value)}
              placeholder="CLABE, número de cuenta o tarjeta"
              style={{ width: "100%", marginTop: 6, padding: 12, borderRadius: 10, border: "1px solid rgba(255,255,255,0.15)", background: "rgba(255,255,255,0.05)", color: "#fff", fontSize: 14, boxSizing: "border-box", fontFamily: "monospace" }}
            />
          </div>
          <p style={{ color: "rgba(255,255,255,0.4)", fontSize: 11, marginBottom: 14 }}>
            ℹ️ Este dato permite realizar una validación más completa cuando esté disponible. Corrobora la operación mediante la información oficial del CEP de Banxico.
          </p>

          <button onClick={irAAnalizar} style={{ marginTop: 14, width: "100%", padding: 15, fontSize: 15, fontWeight: 700, borderRadius: 14, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
            🔍 Analizar comprobante
          </button>
        </>
      )}
      {error && <div style={{ marginTop: 12, padding: "12px 16px", background: "rgba(229,57,53,0.15)", color: "#FF6B6B", borderRadius: 12, fontSize: 14, border: "1px solid rgba(229,57,53,0.3)" }}>⚠️ {error}</div>}
    </div>
  );
}