"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useAnalisis, Resultado } from "../../context/AnalisisContext";
import { SemaforoSpei } from "../../components/resultado/SemaforoSpei";
import { QueSignificaEsto } from "../../components/resultado/QueSignificaEsto";
import { DetalleExpandible } from "../../components/resultado/DetalleExpandible";
import { TEAL, ORANGE, RED } from "../../lib/colores";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

interface HistorialHash {
  veces_visto: number;
  primer_analisis: string;
  ultimo_analisis: string;
}

interface AnalisisDetalle {
  id: string;
  fecha: string | null;
  hash_sha256: string | null;
  archivo_nombre: string | null;
  archivo_tipo: string | null;
  banco_detectado: string | null;
  monto_detectado: number | null;
  clabe_detectada: string | null;
  riesgo: string | null;
  estado_operacion: string | null;
  fuente_estado: string | null;
  nivel_evidencia: string | null;
  resultado: Resultado;
  historial_hash: HistorialHash | null;
}

function formatearFecha(fechaISO: string | null): string {
  if (!fechaISO) return "";
  const d = new Date(fechaISO);
  return d.toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" }) +
    " · " + d.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" });
}

function etiquetaFuenteEstado(fuente: string | null): string {
  switch (fuente) {
    case "xml_oficial": return "XML oficial de Banxico";
    case "cep_html": return "CEP de Banxico (scraping)";
    case "no_disponible": return "No disponible";
    default: return fuente || "—";
  }
}

function formatearMonto(monto: number | null): string {
  if (monto === null || monto === undefined) return "—";
  return "$" + monto.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Refactor previo a Etapa 4 (ver DECISION_LOG.md, ADR "todas las vistas
// de análisis reutilizan el mismo modelo de presentación"): el bloque
// central (SemaforoSpei, QueSignificaEsto, DetalleExpandible) ya NO se
// duplica aquí -- se importa de app/components/resultado/, mismo
// refactor aplicado a /resultado. Solo lo específico de la vista
// histórica (badge, ficha de auditoría, aviso de reutilización con
// datos de historial_hash, espacio de Actividad relacionada) vive en
// este archivo.
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

  const descargarReporte = () => {
    if (!detalle) return;
    const blob = new Blob([JSON.stringify(detalle.resultado, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte_${detalle.archivo_nombre || "comprobante"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
          <p style={{ color: RED, fontSize: 13, margin: 0 }}>{error || "No se pudo cargar este análisis."}</p>
        </div>
      </div>
    );
  }

  const avisoReutilizacion = detalle.historial_hash && detalle.historial_hash.veces_visto > 1 ? (
    <div style={{ marginTop: 10, padding: "10px 14px", background: `${ORANGE}12`, border: `1px solid ${ORANGE}40`, borderRadius: 10, fontSize: 12, color: "#7C4A0A", lineHeight: 1.5 }}>
      ⚠️ Este comprobante ha sido analizado {detalle.historial_hash.veces_visto} veces — primera vez el {formatearFecha(detalle.historial_hash.primer_analisis)}, la más reciente el {formatearFecha(detalle.historial_hash.ultimo_analisis)}.
    </div>
  ) : null;

  const actividadRelacionada = (
    <>
      <div style={{ height: 1, background: "#F0F4F8", margin: "0 22px 18px" }} />
      <div style={{ padding: "0 22px 18px" }}>
        <div style={{ fontSize: 10, color: "#CBD5E1", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
          Actividad relacionada
        </div>
        <div style={{ padding: "12px 14px", background: "#F8FAFC", borderRadius: 10, fontSize: 12, color: "#94A3B8", fontStyle: "italic" }}>
          No disponible todavía
        </div>
      </div>
    </>
  );

  return (
    <div style={{ padding: "16px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "4px 4px 16px" }}>
        <button onClick={() => router.push("/historial")} aria-label="Volver al historial" style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer", padding: 4 }}>←</button>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 16 }}>Volver al historial</span>
      </div>

      <div style={{ background: "#fff", borderRadius: 20, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,0.15)" }}>

        <div style={{ padding: "12px 18px", background: "#F1F5F9", display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 12 }}>📁</span>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#64748B", letterSpacing: "0.04em", textTransform: "uppercase" }}>
            Análisis archivado
          </span>
        </div>

        <div style={{ padding: "18px 18px 16px", borderBottom: "1px solid #F0F4F8" }}>
          <div style={{ fontSize: 10, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
            Análisis realizado
          </div>
          <FichaFila label="Fecha" valor={formatearFecha(detalle.fecha)} />
          <FichaFila label="Archivo" valor={detalle.archivo_nombre || "—"} />
          <FichaFila label="Banco" valor={detalle.banco_detectado || "No detectado"} />
          <FichaFila label="Monto" valor={formatearMonto(detalle.monto_detectado)} />
          <FichaFila label="Hash" valor={detalle.hash_sha256 ? `${detalle.hash_sha256.slice(0, 16)}...` : "—"} mono />
          <FichaFila label="Nivel de evidencia" valor={etiquetaFuenteEstado(detalle.nivel_evidencia)} />
          <FichaFila label="Fuente del estado" valor={etiquetaFuenteEstado(detalle.fuente_estado)} last />
        </div>

        <SemaforoSpei result={detalle.resultado} />
        <QueSignificaEsto result={detalle.resultado} />
        <DetalleExpandible result={detalle.resultado} avisoReutilizacion={avisoReutilizacion} extra={actividadRelacionada} />

        <div style={{ padding: "8px 22px 22px", display: "flex", flexDirection: "column", gap: 10 }}>
          <button onClick={() => router.push("/resultado/detalle")}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#F1F5F9", color: "#334155", border: "none" }}>
            Ver validaciones completas
          </button>
          <button onClick={descargarReporte}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#fff", color: "#334155", border: "1.5px solid #E2E8F0" }}>
            ⬇ Descargar reporte
          </button>
          <button onClick={() => router.push("/historial")}
            style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
            ← Volver al historial
          </button>
        </div>

        <div style={{ padding: "0 22px 20px" }}>
          <p style={{ fontSize: 11, color: "#94A3B8", textAlign: "center", lineHeight: 1.5, margin: 0 }}>
            🔒 Por privacidad, VerificaPago no almacena imágenes de comprobantes una vez concluido el análisis.
          </p>
        </div>
      </div>
    </div>
  );
}

function FichaFila({ label, valor, mono, last }: { label: string; valor: string; mono?: boolean; last?: boolean }) {
  return (
    <div style={{
      display: "flex", justifyContent: "space-between", alignItems: "center",
      padding: "6px 0", borderBottom: last ? "none" : "1px solid #F8FAFC",
    }}>
      <span style={{ fontSize: 11, color: "#94A3B8" }}>{label}</span>
      <span style={{ fontSize: 12, color: "#334155", fontWeight: 600, fontFamily: mono ? "monospace" : "inherit" }}>{valor}</span>
    </div>
  );
}