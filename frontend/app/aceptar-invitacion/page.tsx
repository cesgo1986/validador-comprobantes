"use client";

import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../lib/supabaseClient";
import { apiFetch } from "../lib/apiFetch";

const TEAL = "#00BFA5";
const RED = "#E53935";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

// Item 6.2.6 (Etapa 6): a esta pantalla llega la persona invitada
// desde el correo de Supabase. Mismo patrón que /restablecer para
// reconocer el enlace (detectSessionInUrl), pero con un paso extra al
// final: llamar a /auth/aceptar-invitacion para vincular su cuenta
// real de Supabase con la fila "invited" que ya existía en usuarios.
export default function AceptarInvitacion() {
  const router = useRouter();
  const [listo, setListo] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState(false);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") {
        setListo(true);
      }
    });
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) setListo(true);
    });
    return () => listener.subscription.unsubscribe();
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (password.length < 8) {
      setError("La contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (password !== confirmar) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setCargando(true);
    const { error: errorPassword } = await supabase.auth.updateUser({ password });
    if (errorPassword) {
      setCargando(false);
      setError("No se pudo definir la contraseña. El enlace puede haber expirado -- pide una invitación nueva.");
      return;
    }
    try {
      const resp = await apiFetch(`${API_URL}/auth/aceptar-invitacion`, { method: "POST" });
      if (!resp.ok) throw new Error();
      setExito(true);
    } catch {
      setError("Tu contraseña quedó guardada, pero no se pudo vincular tu cuenta a la empresa. Contacta a quien te invitó.");
    } finally {
      setCargando(false);
    }
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", justifyContent: "center", minHeight: "80vh" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>VerificaPago</span>
      </div>
      <div style={{ background: "#fff", borderRadius: 20, padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#1E293B", marginBottom: 4 }}>Completa tu registro</div>
        {exito ? (
          <>
            <p style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>
              Tu cuenta quedó lista. Ya puedes usar VerificaPago.
            </p>
            <button onClick={() => router.push("/")}
              style={{ padding: 14, borderRadius: 12, background: TEAL, color: "#fff", border: "none", fontWeight: 700, fontSize: 14, cursor: "pointer" }}>
              Ir a la app
            </button>
          </>
        ) : !listo ? (
          <p style={{ fontSize: 13, color: "#64748B" }}>Verificando el enlace...</p>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            <p style={{ fontSize: 13, color: "#64748B", margin: 0 }}>
              Define tu contraseña para terminar de unirte a la empresa.
            </p>
            <div>
              <label style={{ fontSize: 12, color: "#64748B" }}>Contraseña</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
                style={{ width: "100%", padding: 12, marginTop: 4, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }} />
            </div>
            <div>
              <label style={{ fontSize: 12, color: "#64748B" }}>Confirmar contraseña</label>
              <input type="password" required value={confirmar} onChange={e => setConfirmar(e.target.value)}
                style={{ width: "100%", padding: 12, marginTop: 4, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }} />
            </div>
            {error && <div style={{ color: RED, fontSize: 12 }}>{error}</div>}
            <button type="submit" disabled={cargando}
              style={{ padding: 14, borderRadius: 12, background: TEAL, color: "#fff", border: "none", fontWeight: 700, fontSize: 14, cursor: "pointer", opacity: cargando ? 0.6 : 1 }}>
              {cargando ? "Guardando..." : "Completar registro"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
