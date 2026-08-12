"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../lib/supabaseClient";

const TEAL = "#00BFA5";
const RED = "#E53935";

// Item 6.2.1 (Etapa 6): pide el correo y dispara el envío del enlace
// de recuperación vía Supabase Auth (que ya usa Resend como SMTP,
// ver DECISION_LOG.md). El enlace del correo apunta a /restablecer.
export default function Recuperar() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCargando(true);

    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/restablecer`,
    });

    setCargando(false);
    if (error) {
      setError("No se pudo enviar el correo. Intenta de nuevo.");
      return;
    }
    setEnviado(true);
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", justifyContent: "center", minHeight: "80vh" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>VerificaPago</span>
      </div>

      <div style={{ background: "#fff", borderRadius: 20, padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#1E293B", marginBottom: 4 }}>Recuperar contraseña</div>

        {enviado ? (
          <>
            <p style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>
              Si <strong>{email}</strong> tiene una cuenta con nosotros, te enviamos un correo con instrucciones para restablecer tu contraseña. Revisa también tu carpeta de spam.
            </p>
            <button onClick={() => router.push("/login")}
              style={{ padding: 14, borderRadius: 12, background: TEAL, color: "#fff", border: "none", fontWeight: 700, fontSize: 14, cursor: "pointer" }}>
              Volver a iniciar sesión
            </button>
          </>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <p style={{ fontSize: 13, color: "#64748B", margin: 0 }}>
              Escribe tu correo y te enviaremos un enlace para restablecer tu contraseña.
            </p>
            <div>
              <label style={{ fontSize: 12, color: "#64748B" }}>Correo</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                style={{ width: "100%", padding: 12, marginTop: 4, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }} />
            </div>

            {error && <div style={{ color: RED, fontSize: 12 }}>{error}</div>}

            <button type="submit" disabled={cargando}
              style={{ padding: 14, borderRadius: 12, background: TEAL, color: "#fff", border: "none", fontWeight: 700, fontSize: 14, cursor: "pointer", opacity: cargando ? 0.6 : 1 }}>
              {cargando ? "Enviando..." : "Enviar enlace de recuperación"}
            </button>

            <button type="button" onClick={() => router.push("/login")}
              style={{ padding: 10, borderRadius: 12, background: "none", color: "#64748B", border: "none", fontSize: 13, cursor: "pointer" }}>
              Volver a iniciar sesión
            </button>
          </form>
        )}
      </div>
    </div>
  );
}