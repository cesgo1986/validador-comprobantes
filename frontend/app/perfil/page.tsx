"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CentroOperativo, CentroOperativoData } from "../components/perfil/CentroOperativo";
import { useAuth } from "../context/AuthContext";
import { apiFetch } from "../lib/apiFetch";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";

// Item 4.2 (Etapa 4): Perfil evoluciona temporalmente a "Perfil / Empresa"
// mientras no exista autenticación real (Etapa 6) -- ver DECISION_LOG.md.
//
// Item 5.5 (Etapa 5): en Desktop+, el resumen compacto de Mobile/Tablet
// se acompaña del Centro Operativo completo.
//
// FIX (2026-07, revisión de arquitectura): una sola llamada a
// /centro-operativo en vez de 2 endpoints distintos -- ver DECISION_LOG.md.
//
// Item 6.2.7b (Etapa 6): agrega estado de sesión (login/logout), y la
// llamada fetch() migrada a apiFetch() -- agrega el JWT si hay sesión.
export default function Perfil() {
  const { session, logout } = useAuth();
  const router = useRouter();
  const [datos, setDatos] = useState<CentroOperativoData | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function cargar() {
      try {
        const resp = await apiFetch(`${API_URL}/api/v1/dashboard/centro-operativo`);
        if (!resp.ok) throw new Error();
        setDatos(await resp.json());
      } catch {
        setError("No se pudo cargar el resumen. Intenta de nuevo.");
      } finally {
        setCargando(false);
      }
    }
    cargar();
  }, []);

  return (
    <div style={{ padding: "16px" }}>
      <div className="vp-mobile-only">
        <div style={{ padding: "8px 4px 20px" }}>
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Perfil</span>
        </div>

        <div style={{ background: "#fff", borderRadius: 16, padding: "18px 18px 16px", marginBottom: 16 }}>
          <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12 }}>
            Resumen de hoy
          </div>

          {cargando && <div style={{ color: "#94A3B8", fontSize: 12, textAlign: "center", padding: 10 }}>Cargando...</div>}
          {error && <div style={{ color: RED, fontSize: 12, textAlign: "center", padding: 10 }}>{error}</div>}

          {datos && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <ResumenFila label="Análisis" valor={String(datos.resumen_compacto.analisis_hoy)} />
              <ResumenFila
                label="Alertas nuevas"
                valor={String(datos.resumen_compacto.alertas_nuevas)}
                color={datos.resumen_compacto.alertas_notificables > 0 ? ORANGE : undefined}
              />
              <ResumenFila
                label="Riesgo alto"
                valor={String(datos.resumen_compacto.riesgo_alto)}
                color={datos.resumen_compacto.riesgo_alto > 0 ? RED : undefined}
              />
              <ResumenFila
                label="Transferencias confirmadas"
                valor={datos.resumen_compacto.pct_confirmadas !== null ? `${datos.resumen_compacto.pct_confirmadas}%` : "—"}
                color={datos.resumen_compacto.pct_confirmadas !== null && datos.resumen_compacto.pct_confirmadas >= 90 ? GREEN : undefined}
              />
            </div>
          )}
        </div>

        <div style={{ background: "#fff", borderRadius: 16, padding: "24px 20px", textAlign: "center" }}>
          {session ? (
            <>
              <div style={{ fontSize: 32, marginBottom: 10 }}>👤</div>
              <p style={{ color: "#1E293B", fontSize: 13, fontWeight: 600, margin: "0 0 4px" }}>
                {session.user.email}
              </p>
              <p style={{ color: "#94A3B8", fontSize: 12, lineHeight: 1.6, margin: "0 0 16px" }}>
                Sesión iniciada
              </p>
              <button
                onClick={async () => { await logout(); router.push("/login"); }}
                style={{ padding: "10px 20px", borderRadius: 10, background: "#F1F5F9", border: "none", color: "#334155", fontSize: 13, fontWeight: 700, cursor: "pointer" }}
              >
                Cerrar sesión
              </button>
            </>
          ) : (
            <>
              <div style={{ fontSize: 32, marginBottom: 10 }}>👤</div>
              <p style={{ color: "#64748B", fontSize: 13, lineHeight: 1.6, margin: "0 0 16px" }}>
                Aquí podrás gestionar tus datos, preferencias, seguridad y suscripción.
              </p>
              <button
                onClick={() => router.push("/login")}
                style={{ padding: "10px 20px", borderRadius: 10, background: "#00BFA5", border: "none", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}
              >
                Iniciar sesión
              </button>
            </>
          )}
        </div>
      </div>

      <div className="vp-desktop-only">
        {cargando && <div style={{ padding: 40, textAlign: "center", color: "#94A3B8", fontSize: 13 }}>Cargando Centro Operativo...</div>}
        {error && (
          <div style={{ background: "#fff", borderRadius: 20, padding: 40, textAlign: "center" }}>
            <p style={{ color: RED, fontSize: 13, margin: 0 }}>{error}</p>
          </div>
        )}
        {datos && <CentroOperativo datos={datos} />}
      </div>
    </div>
  );
}

function ResumenFila({ label, valor, color }: { label: string; valor: string; color?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ fontSize: 13, color: "#64748B" }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: 700, color: color || "#1E293B" }}>{valor}</span>
    </div>
  );
}