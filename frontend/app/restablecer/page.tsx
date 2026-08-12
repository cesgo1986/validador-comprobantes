"use client";
import { useState, useEffect, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "../lib/supabaseClient";

const TEAL = "#00BFA5";
const RED = "#E53935";

// Item 6.2.1 (Etapa 6): a esta pantalla llega el usuario desde el
// enlace del correo de recuperación. Supabase-js reconoce
// automáticamente los parámetros del enlace (detectSessionInUrl, por
// defecto) y arma una sesión temporal de recuperación -- no hace falta
// leer el token manualmente. Solo se necesita esperar a que la sesión
// exista antes de permitir el envío del formulario.
export default function Restablecer() {
  const router = useRouter();
  const [listo, setListo] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmar, setConfirmar] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [exito, setExito] = useState(false);
  const [cargando, setCargando] = useState(false);

  useEffect(() => {
    // Da tiempo a que supabase-js procese el enlace de recuperación y
    // arme la sesión temporal antes de mostrar el formulario.
    const { data: listener } = supabase.auth.onAuthStateChange((event) => {
      if (event === "PASSWORD_RECOVERY" || event === "SIGNED_IN") {
        setListo(true);
      }
    });
    // Si ya había una sesión (poco probable en este flujo, pero por si acaso).
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
    const { error } = await supabase.auth.updateUser({ password });
    setCargando(false);

    if (error) {
      setError("No se pudo actualizar la contraseña. El enlace puede haber expirado -- solicita uno nuevo.");
      return;
    }
    setExito(true);
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", justifyContent: "center", minHeight: "80vh" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>VerificaPago</span>
      </div>

      <div style={{ background: "#fff", borderRadius: 20, padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#1E293B", marginBottom: 4 }}>Nueva contraseña</div>

        {exito ? (
          <>
            <p style={{ fontSize: 13, color: "#334155", lineHeight: 1.6 }}>
              Tu contraseña se actualizó correctamente.
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
            <div>
              <label style={{ fontSize: 12, color: "#64748B" }}>Nueva contraseña</label>
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
              {cargando ? "Guardando..." : "Guardar nueva contraseña"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}