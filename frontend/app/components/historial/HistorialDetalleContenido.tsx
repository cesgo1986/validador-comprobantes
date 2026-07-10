"use client";
import { Resultado } from "../../context/AnalisisContext";
import { SemaforoSpei } from "../resultado/SemaforoSpei";
import { QueSignificaEsto } from "../resultado/QueSignificaEsto";
import { DetalleExpandible } from "../resultado/DetalleExpandible";
import { TEAL, ORANGE } from "../../lib/colores";

export interface HistorialHash {
  veces_visto: number;
  primer_analisis: string;
  ultimo_analisis: string;
}

export interface AnalisisDetalle {
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

// Componente compartido -- item 5.4 (Etapa 5). Extraído de lo que antes
// vivía completo dentro de historial/[id]/page.tsx, para reutilizarse
// en 2 lugares sin duplicar JSX:
//   1. /historial/[id]/page.tsx -- Mobile/Tablet, pantalla completa.
//   2. /historial/page.tsx -- Desktop+, columna derecha del maestro-detalle.
// `onVolver` y `onVerValidaciones` se inyectan desde afuera porque su
// comportamiento difiere entre los 2 consumidores (uno navega de ruta,
// el otro solo limpia la selección sin salir de /historial).
export function HistorialDetalleContenido({
  detalle,
  onVolver,
  onVerValidaciones,
  textoBotonVolver = "← Volver al historial",
}: {
  detalle: AnalisisDetalle;
  onVolver: () => void;
  onVerValidaciones: () => void;
  textoBotonVolver?: string;
}) {
  const result = detalle.resultado;

  const descargarReporte = () => {
    const blob = new Blob([JSON.stringify(detalle.resultado, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `reporte_${detalle.archivo_nombre || "comprobante"}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

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

      <SemaforoSpei result={result} />
      <QueSignificaEsto result={result} />
      <DetalleExpandible result={result} avisoReutilizacion={avisoReutilizacion} extra={actividadRelacionada} />

      <div style={{ padding: "8px 22px 22px", display: "flex", flexDirection: "column", gap: 10 }}>
        <button onClick={onVerValidaciones}
          style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#F1F5F9", color: "#334155", border: "none" }}>
          Ver validaciones completas
        </button>
        <button onClick={descargarReporte}
          style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: "#fff", color: "#334155", border: "1.5px solid #E2E8F0" }}>
          ⬇ Descargar reporte
        </button>
        <button onClick={onVolver}
          style={{ width: "100%", padding: 14, fontSize: 14, fontWeight: 700, borderRadius: 12, cursor: "pointer", background: TEAL, color: "#fff", border: "none" }}>
          {textoBotonVolver}
        </button>
      </div>

      <div style={{ padding: "0 22px 20px" }}>
        <p style={{ fontSize: 11, color: "#94A3B8", textAlign: "center", lineHeight: 1.5, margin: 0 }}>
          🔒 Por privacidad, VerificaPago no almacena imágenes de comprobantes una vez concluido el análisis.
        </p>
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