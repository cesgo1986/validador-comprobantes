"use client";
import { useEffect, useState } from "react";
import { CentroOperativo, CentroOperativoData } from "../components/perfil/CentroOperativo";

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
// FIX (2026-07, revisión de arquitectura): antes esta pantalla hacía 2
// llamadas -- /resumen-ejecutivo para Mobile, /centro-operativo para
// Desktop -- duplicando tráfico y creando 2 fuentes de verdad para el
// mismo dominio de datos (mismo error que la arquitectura ya evita con
// los motores). Ahora es una sola llamada a /centro-operativo; su
// campo `resumen_compacto` trae exactamente lo que Mobile necesita.
// CSS (.vp-mobile-only / .vp-desktop-only en globals.css) decide qué
// presentación se muestra -- sin detección de viewport en JS.
export default function Perfil() {
  const [datos, setDatos] = useState<CentroOperativoData | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function cargar() {
      try {
        const resp = await fetch(`${API_URL}/api/v1/dashboard/centro-operativo`);
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
      {/* Mobile/Tablet: resumen compacto (mismo contenido de 4.2, ahora
          alimentado por datos.resumen_compacto en vez de su propia
          llamada) */}
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

        <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>👤</div>
          <p style={{ color: "#64748B", fontSize: 13, lineHeight: 1.6, margin: 0 }}>
            Aquí podrás gestionar tus datos, preferencias, seguridad y suscripción.
          </p>
        </div>
      </div>

      {/* Desktop+: Centro Operativo completo (item 5.5) -- mismo `datos` */}
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