"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";

const TEAL = "#00BFA5";
const RED = "#E53935";

export default function Login() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [cargando, setCargando] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setCargando(true);
    const { error } = await login(email, password);
    setCargando(false);
    if (error) {
      setError("Correo o contraseña incorrectos.");
      return;
    }
    router.push("/");
  };

  return (
    <div style={{ padding: "16px", display: "flex", flexDirection: "column", justifyContent: "center", minHeight: "80vh" }}>
      <div style={{ textAlign: "center", marginBottom: 24 }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 20 }}>VerificaPago</span>
      </div>

      <form onSubmit={handleSubmit} style={{ background: "#fff", borderRadius: 20, padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: "#1E293B", marginBottom: 4 }}>Iniciar sesión</div>

        <div>
          <label style={{ fontSize: 12, color: "#64748B" }}>Correo</label>
          <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
            style={{ width: "100%", padding: 12, marginTop: 4, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }} />
        </div>

        <div>
          <label style={{ fontSize: 12, color: "#64748B" }}>Contraseña</label>
          <input type="password" required value={password} onChange={e => setPassword(e.target.value)}
            style={{ width: "100%", padding: 12, marginTop: 4, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }} />
        </div>

        {error && <div style={{ color: RED, fontSize: 12 }}>{error}</div>}

        <button type="submit" disabled={cargando}
          style={{ padding: 14, borderRadius: 12, background: TEAL, color: "#fff", border: "none", fontWeight: 700, fontSize: 14, cursor: "pointer", opacity: cargando ? 0.6 : 1 }}>
          {cargando ? "Entrando..." : "Entrar"}
        </button>

        <p style={{ fontSize: 11, color: "#94A3B8", textAlign: "center", margin: 0 }}>
          Recuperación de contraseña disponible próximamente.
        </p>
      </form>
    </div>
  );
}