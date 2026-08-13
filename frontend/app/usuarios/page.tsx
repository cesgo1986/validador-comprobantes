"use client";

import { useState, useEffect, useCallback, FormEvent } from "react";
import { apiFetch } from "../lib/apiFetch";

const TEAL = "#00BFA5";
const RED = "#E53935";
const ORANGE = "#F5A623";
const GREEN = "#43A047";
const GRAY = "#9CA3AF";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

const ROLES_OPCIONES = [
  { valor: "viewer", etiqueta: "Viewer -- solo ver" },
  { valor: "analyst", etiqueta: "Analyst -- analizar y exportar" },
  { valor: "admin", etiqueta: "Admin -- gestión operativa" },
  { valor: "owner", etiqueta: "Owner -- control total" },
];

interface UsuarioItem {
  email: string;
  nombre: string | null;
  rol: string;
  status: string;
}

function colorEstado(status: string): string {
  switch (status) {
    case "active": return GREEN;
    case "invited": return ORANGE;
    case "suspended": return RED;
    default: return GRAY;
  }
}

function etiquetaEstado(status: string): string {
  switch (status) {
    case "active": return "Activo";
    case "invited": return "Invitación pendiente";
    case "suspended": return "Suspendido";
    default: return status;
  }
}

// Item 6.2.6 (Etapa 6): pantalla dedicada, no un formulario provisional
// dentro de Perfil -- estructura preparada para agregar después
// (cambiar rol, revocar acceso, reenviar invitación) sin refactor.
// Requiere permiso USERS -- si el backend rechaza con 403, se muestra
// un mensaje claro en vez de una lista vacía confusa.
export default function Usuarios() {
  const [usuarios, setUsuarios] = useState<UsuarioItem[]>([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sinPermiso, setSinPermiso] = useState(false);
  const [mostrarFormulario, setMostrarFormulario] = useState(false);
  const [email, setEmail] = useState("");
  const [rol, setRol] = useState("viewer");
  const [enviandoInvitacion, setEnviandoInvitacion] = useState(false);
  const [mensajeInvitacion, setMensajeInvitacion] = useState<{ texto: string; error: boolean } | null>(null);

  const cargarUsuarios = useCallback(async () => {
    setCargando(true);
    setError(null);
    setSinPermiso(false);
    try {
      const resp = await apiFetch(`${API_URL}/api/v1/dashboard/usuarios`);
      if (resp.status === 403) {
        setSinPermiso(true);
        return;
      }
      if (!resp.ok) throw new Error();
      setUsuarios(await resp.json());
    } catch {
      setError("No se pudo cargar la lista de usuarios. Intenta de nuevo.");
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargarUsuarios(); }, [cargarUsuarios]);

  const invitar = async (e: FormEvent) => {
    e.preventDefault();
    setMensajeInvitacion(null);
    setEnviandoInvitacion(true);
    try {
      const params = new URLSearchParams({ email, rol });
      const resp = await apiFetch(`${API_URL}/api/v1/dashboard/usuarios/invitar?${params.toString()}`, { method: "POST" });
      if (resp.status === 409) {
        setMensajeInvitacion({ texto: "Este correo ya está registrado en VerificaPago.", error: true });
        return;
      }
      if (!resp.ok) throw new Error();
      setMensajeInvitacion({ texto: `Invitación enviada a ${email}.`, error: false });
      setEmail("");
      setRol("viewer");
      cargarUsuarios();
    } catch {
      setMensajeInvitacion({ texto: "No se pudo enviar la invitación. Intenta de nuevo.", error: true });
    } finally {
      setEnviandoInvitacion(false);
    }
  };

  return (
    <div style={{ padding: "16px", paddingBottom: 90 }}>
      <div style={{ padding: "8px 4px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Usuarios</span>
        {!sinPermiso && (
          <button onClick={() => setMostrarFormulario(o => !o)}
            style={{ padding: "8px 16px", borderRadius: 10, background: TEAL, border: "none", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
            + Invitar usuario
          </button>
        )}
      </div>

      {sinPermiso && (
        <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>🔒</div>
          <p style={{ color: "#64748B", fontSize: 13, lineHeight: 1.6, margin: 0 }}>
            Tu rol no tiene permiso para gestionar usuarios. Solo Owner y Admin pueden ver o invitar usuarios.
          </p>
        </div>
      )}

      {mostrarFormulario && !sinPermiso && (
        <form onSubmit={invitar} style={{ background: "#fff", borderRadius: 14, padding: 16, marginBottom: 14, display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: "#64748B" }}>Correo a invitar</label>
            <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
              style={{ width: "100%", marginTop: 4, padding: 12, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: "#64748B" }}>Rol</label>
            <select value={rol} onChange={e => setRol(e.target.value)}
              style={{ width: "100%", marginTop: 4, padding: 12, borderRadius: 10, border: "1.5px solid #E2E8F0", background: "#F8FAFC", color: "#1E293B", fontSize: 14, boxSizing: "border-box" }}>
              {ROLES_OPCIONES.map(r => <option key={r.valor} value={r.valor}>{r.etiqueta}</option>)}
            </select>
          </div>
          {mensajeInvitacion && (
            <div style={{ fontSize: 12, color: mensajeInvitacion.error ? RED : GREEN }}>{mensajeInvitacion.texto}</div>
          )}
          <button type="submit" disabled={enviandoInvitacion}
            style={{ padding: 12, borderRadius: 10, background: TEAL, border: "none", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer", opacity: enviandoInvitacion ? 0.6 : 1 }}>
            {enviandoInvitacion ? "Enviando..." : "Enviar invitación"}
          </button>
        </form>
      )}

      {error && (
        <div style={{ background: "#fff", borderRadius: 14, padding: 20, textAlign: "center", marginBottom: 14 }}>
          <p style={{ color: RED, fontSize: 13, margin: 0 }}>{error}</p>
        </div>
      )}

      {cargando && !sinPermiso && (
        <div style={{ textAlign: "center", padding: 20, color: "#94A3B8", fontSize: 12 }}>Cargando...</div>
      )}

      {!cargando && !sinPermiso && !error && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {usuarios.map(u => (
            <div key={u.email} style={{ background: "#fff", borderRadius: 14, padding: "14px 16px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B" }}>{u.nombre || u.email}</div>
                <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{u.email} · {u.rol}</div>
              </div>
              <span style={{ fontSize: 11, fontWeight: 700, color: colorEstado(u.status), flexShrink: 0 }}>
                {etiquetaEstado(u.status)}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
