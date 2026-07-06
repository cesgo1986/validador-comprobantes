"use client";
import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";

interface ResumenEjecutivo {
  analisis_hoy: number;
  alertas_nuevas: number;
  alertas_notificables: number;
  riesgo_alto: number;
  pct_confirmadas: number | null;
}

// Item 4.2 (Etapa 4): Perfil evoluciona temporalmente a "Perfil / Empresa"
// mientras no exista autenticación real (Etapa 6) -- ver DECISION_LOG.md.
// Deliberadamente NO incluye datos de la empresa (nombre, plan) porque
// no existe todavía un endpoint que los expongan -- se agrega cuando
// exista, en vez de inventar un valor fijo aquí. Solo el resumen
// ejecutivo: sin gráficas, sin tablas, sin filtros -- ver ADR "una sola
// experiencia, múltiples presentaciones".
export default function Perfil() {
  const [resumen, setResumen] = useState<ResumenEjecutivo | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function cargar() {
      try {
        const resp = await fetch(`${API_URL}/api/v1/dashboard/resumen-ejecutivo`);
        if (!resp.ok) throw new Error();
        setResumen(await resp.json());
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
      <div style={{ padding: "8px 4px 20px" }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Perfil</span>
      </div>

      <div style={{ background: "#fff", borderRadius: 16, padding: "18px 18px 16px", marginBottom: 16 }}>
        <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12 }}>
          Resumen de hoy
        </div>

        {cargando && <div style={{ color: "#94A3B8", fontSize: 12, textAlign: "center", padding: 10 }}>Cargando...</div>}
        {error && <div style={{ color: RED, fontSize: 12, textAlign: "center", padding: 10 }}>{error}</div>}

        {resumen && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <ResumenFila label="Análisis" valor={String(resumen.analisis_hoy)} />
            <ResumenFila
              label="Alertas nuevas"
              valor={String(resumen.alertas_nuevas)}
              color={resumen.alertas_notificables > 0 ? ORANGE : undefined}
            />
            <ResumenFila
              label="Riesgo alto"
              valor={String(resumen.riesgo_alto)}
              color={resumen.riesgo_alto > 0 ? RED : undefined}
            />
            <ResumenFila
              label="Transferencias confirmadas"
              valor={resumen.pct_confirmadas !== null ? `${resumen.pct_confirmadas}%` : "—"}
              color={resumen.pct_confirmadas !== null && resumen.pct_confirmadas >= 90 ? GREEN : undefined}
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