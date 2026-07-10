"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAnalisis } from "../../context/AnalisisContext";
import { HistorialDetalleContenido, AnalisisDetalle } from "../../components/historial/HistorialDetalleContenido";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

// Item 5.4 (Etapa 5): este archivo ya no contiene el JSX del detalle --
// vive en HistorialDetalleContenido (compartido con la columna derecha
// del maestro-detalle de /historial en Desktop+). Esta ruta sigue
// existiendo para Mobile/Tablet, donde tocar una tarjeta del historial
// navega aquí, exactamente como antes de 5.4.
export default function HistorialDetalle() {
  const router = useRouter();
  const params = useParams();
  const { setResult } = useAnalisis();

  const [detalle, setDetalle] = useState<AnalisisDetalle | null>(null);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function cargar() {
      setCargando(true);
      setError(null);
      try {
        const resp = await fetch(`${API_URL}/api/v1/dashboard/analisis/${params.id}`);
        if (resp.status === 404) {
          setError("Este análisis no existe o fue eliminado.");
          return;
        }
        if (!resp.ok) throw new Error();
        const data: AnalisisDetalle = await resp.json();
        setDetalle(data);
        setResult(data.resultado);
      } catch {
        setError("No se pudo cargar este análisis. Intenta de nuevo.");
      } finally {
        setCargando(false);
      }
    }
    if (params.id) cargar();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params.id]);

  if (cargando) {
    return (
      <div style={{ padding: "16px", textAlign: "center", paddingTop: 60 }}>
        <span style={{ color: "rgba(255,255,255,0.6)", fontSize: 13 }}>Cargando análisis...</span>
      </div>
    );
  }

  if (error || !detalle) {
    return (
      <div style={{ padding: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
          <button onClick={() => router.push("/historial")} aria-label="Volver al historial" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
          <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Volver al historial</span>
        </div>
        <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
          <p style={{ color: "#E53935", fontSize: 13, margin: 0 }}>{error || "No se pudo cargar este análisis."}</p>
        </div>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
        <button onClick={() => router.push("/historial")} aria-label="Volver al historial" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Volver al historial</span>
      </div>

      <HistorialDetalleContenido
        detalle={detalle}
        onVolver={() => router.push("/historial")}
        onVerValidaciones={() => router.push("/resultado/detalle")}
      />
    </div>
  );
}