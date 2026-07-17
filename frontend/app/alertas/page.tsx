"use client";
import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../lib/apiFetch";

const TEAL = "#00BFA5";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";
const CRITICA_COLOR = "#B91C1C";
const GRAY = "#9CA3AF";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
const LIMIT = 20;

interface AlertaItem {
  id: string;
  tipo_alerta: string;
  severidad: string;
  entidad_tipo: string;
  entidad_id: string;
  analisis_origen: string | null;
  estado: string;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

const SEVERIDAD_OPCIONES = ["BAJA", "MEDIA", "ALTA", "CRITICA"];
const ESTADO_OPCIONES = ["NUEVA", "REVISADA", "DESCARTADA"];

const ETIQUETAS_TIPO: Record<string, string> = {
  REUTILIZACION_HASH: "Comprobante reutilizado",
  CLABE_FRECUENTE: "Cuenta receptora frecuente",
  CLAVE_RASTREO_REPETIDA: "Clave de rastreo inconsistente",
};

const ETIQUETAS_ENTIDAD: Record<string, string> = {
  HASH: "Documento",
  CLABE: "Cuenta (CLABE)",
  CLAVE_RASTREO: "Clave de rastreo",
  CUENTA: "Cuenta",
  BANCO: "Banco",
  DISPOSITIVO: "Dispositivo",
};

function colorSeveridad(severidad: string): string {
  switch (severidad) {
    case "BAJA": return GREEN;
    case "MEDIA": return ORANGE;
    case "ALTA": return RED;
    case "CRITICA": return CRITICA_COLOR;
    default: return GRAY;
  }
}

function iconoSeveridad(severidad: string): string {
  switch (severidad) {
    case "BAJA": return "ℹ️";
    case "MEDIA": return "⚠️";
    case "ALTA": return "🔴";
    case "CRITICA": return "🚨";
    default: return "🔔";
  }
}

function etiquetaTipo(tipo: string): string {
  return ETIQUETAS_TIPO[tipo] || tipo;
}

function etiquetaEntidad(tipo: string): string {
  return ETIQUETAS_ENTIDAD[tipo] || tipo;
}

function truncarEntidad(entidadId: string): string {
  if (entidadId.length <= 16) return entidadId;
  return `${entidadId.slice(0, 8)}...${entidadId.slice(-6)}`;
}

function tiempoRelativo(fechaISO: string | null): string {
  if (!fechaISO) return "";
  const fecha = new Date(fechaISO);
  const ahora = new Date();
  const diffMin = Math.floor((ahora.getTime() - fecha.getTime()) / 60000);
  if (diffMin < 1) return "Justo ahora";
  if (diffMin < 60) return `Hace ${diffMin} min`;
  const diffHoras = Math.floor(diffMin / 60);
  if (diffHoras < 24) return `Hace ${diffHoras} h`;
  const diffDias = Math.floor(diffHoras / 24);
  if (diffDias === 1) return "Ayer";
  return `Hace ${diffDias} días`;
}

function descripcionAlerta(alerta: AlertaItem): string {
  const meta = alerta.metadata || {};
  switch (alerta.tipo_alerta) {
    case "REUTILIZACION_HASH":
      return `Este comprobante ya fue analizado ${meta.veces_visto ?? "varias"} veces.`;
    case "CLABE_FRECUENTE":
      return `Esta cuenta apareció ${meta.apariciones ?? "muchas"} veces en los últimos ${meta.ventana_dias ?? 30} días.`;
    case "CLAVE_RASTREO_REPETIDA": {
      const bancos = Array.isArray(meta.bancos_conflicto) ? (meta.bancos_conflicto as string[]).join(", ") : "otro banco";
      return `La misma clave de rastreo apareció con ${bancos} — posible comprobante falsificado.`;
    }
    default:
      return "";
  }
}

// Item 6.2.7b (Etapa 6): las 2 llamadas de esta pantalla (listar
// alertas, cambiar estado) migradas a apiFetch() -- agrega el JWT si
// hay sesión, sin cambiar nada si no la hay.
export default function Alertas() {
  const [items, setItems] = useState<AlertaItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actualizandoId, setActualizandoId] = useState<string | null>(null);

  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const [estadoFiltro, setEstadoFiltro] = useState("NUEVA"); // Nivel 1 por defecto: solo lo que necesita atención
  const [severidad, setSeveridad] = useState("");
  const [tipoAlerta, setTipoAlerta] = useState("");

  const hayFiltrosAvanzadosActivos = !!(severidad || tipoAlerta || estadoFiltro !== "NUEVA");

  const construirQuery = useCallback((offsetActual: number) => {
    const params = new URLSearchParams();
    params.set("limit", String(LIMIT));
    params.set("offset", String(offsetActual));
    if (estadoFiltro) params.set("estado", estadoFiltro);
    if (severidad) params.set("severidad", severidad);
    if (tipoAlerta) params.set("tipo_alerta", tipoAlerta);
    return params.toString();
  }, [estadoFiltro, severidad, tipoAlerta]);

  const cargarAlertas = useCallback(async (offsetActual: number, reemplazar: boolean) => {
    setCargando(true);
    setError(null);
    try {
      const resp = await apiFetch(`${API_URL}/api/v1/dashboard/alertas?${construirQuery(offsetActual)}`);
      if (!resp.ok) throw new Error();
      const data = await resp.json();
      setItems(prev => reemplazar ? data.items : [...prev, ...data.items]);
      setTotal(data.total);
      setOffset(offsetActual);
    } catch {
      setError("No se pudieron cargar las alertas. Intenta de nuevo.");
    } finally {
      setCargando(false);
    }
  }, [construirQuery]);

  useEffect(() => {
    cargarAlertas(0, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [estadoFiltro, severidad, tipoAlerta]);

  const limpiarFiltrosAvanzados = () => {
    setEstadoFiltro("NUEVA"); setSeveridad(""); setTipoAlerta("");
  };

  const cambiarEstado = async (alertaId: string, nuevoEstado: string) => {
    setActualizandoId(alertaId);
    try {
      const resp = await apiFetch(
        `${API_URL}/api/v1/dashboard/alertas/${alertaId}/estado?nuevo_estado=${nuevoEstado}`,
        { method: "PATCH" }
      );
      if (!resp.ok) throw new Error();
      setItems(prev => prev.filter(a => a.id !== alertaId));
      setTotal(t => Math.max(0, t - 1));
    } catch {
      setError("No se pudo actualizar la alerta. Intenta de nuevo.");
    } finally {
      setActualizandoId(null);
    }
  };

  return (
    <div style={{ padding: "16px", paddingBottom: 90 }}>
      <div style={{ padding: "8px 4px 16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Alertas</span>
        <button onClick={() => setFiltrosAbiertos(o => !o)}
          style={{
            padding: "6px 14px", borderRadius: 10, cursor: "pointer",
            border: hayFiltrosAvanzadosActivos ? `1.5px solid ${TEAL}` : "1.5px solid rgba(255,255,255,0.25)",
            background: hayFiltrosAvanzadosActivos ? `${TEAL}20` : "transparent",
            color: hayFiltrosAvanzadosActivos ? TEAL : "rgba(255,255,255,0.75)", fontSize: 12, fontWeight: 700,
          }}>
          Filtros
        </button>
      </div>

      {filtrosAbiertos && (
        <div style={{ background: "#fff", borderRadius: 14, padding: 16, marginBottom: 14, display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>Estado</label>
            <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
              {ESTADO_OPCIONES.map(e => (
                <button key={e} onClick={() => setEstadoFiltro(e)}
                  style={{
                    padding: "6px 12px", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer",
                    border: `1.5px solid ${estadoFiltro === e ? TEAL : "#E2E8F0"}`,
                    background: estadoFiltro === e ? `${TEAL}15` : "#fff",
                    color: estadoFiltro === e ? TEAL : "#64748B",
                  }}>
                  {e}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>Severidad</label>
            <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
              {SEVERIDAD_OPCIONES.map(s => (
                <button key={s} onClick={() => setSeveridad(severidad === s ? "" : s)}
                  style={{
                    padding: "6px 12px", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer",
                    border: `1.5px solid ${severidad === s ? colorSeveridad(s) : "#E2E8F0"}`,
                    background: severidad === s ? `${colorSeveridad(s)}15` : "#fff",
                    color: severidad === s ? colorSeveridad(s) : "#64748B",
                  }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>Tipo</label>
            <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
              {Object.keys(ETIQUETAS_TIPO).map(t => (
                <button key={t} onClick={() => setTipoAlerta(tipoAlerta === t ? "" : t)}
                  style={{
                    padding: "6px 12px", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer",
                    border: `1.5px solid ${tipoAlerta === t ? TEAL : "#E2E8F0"}`,
                    background: tipoAlerta === t ? `${TEAL}15` : "#fff",
                    color: tipoAlerta === t ? TEAL : "#64748B",
                  }}>
                  {etiquetaTipo(t)}
                </button>
              ))}
            </div>
          </div>
          {hayFiltrosAvanzadosActivos && (
            <button onClick={limpiarFiltrosAvanzados}
              style={{ padding: "8px", borderRadius: 8, background: "#F1F5F9", border: "none", color: "#334155", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
              Restablecer (ver solo nuevas)
            </button>
          )}
        </div>
      )}

      {error && (
        <div style={{ background: "#fff", borderRadius: 14, padding: 20, textAlign: "center", marginBottom: 14 }}>
          <p style={{ color: RED, fontSize: 13, margin: 0 }}>{error}</p>
        </div>
      )}

      {!cargando && !error && items.length === 0 && (
        <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
          <div style={{ fontSize: 32, marginBottom: 10 }}>{estadoFiltro === "NUEVA" ? "🎉" : "🔔"}</div>
          <p style={{ color: "#64748B", fontSize: 13, lineHeight: 1.6, margin: 0 }}>
            {estadoFiltro === "NUEVA"
              ? "No tienes alertas nuevas. Aquí verás notificaciones sobre riesgos detectados, comprobantes reutilizados y cuentas frecuentes."
              : "No hay alertas con este filtro."}
          </p>
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {items.map(alerta => (
          <div key={alerta.id} style={{ background: "#fff", borderRadius: 14, padding: "14px 16px" }}>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
              <span style={{ fontSize: 18, flexShrink: 0, marginTop: 1 }}>{iconoSeveridad(alerta.severidad)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
                  <span style={{ fontSize: 13, fontWeight: 700, color: colorSeveridad(alerta.severidad) }}>
                    {etiquetaTipo(alerta.tipo_alerta)}
                  </span>
                </div>
                <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.5, marginBottom: 4 }}>
                  {descripcionAlerta(alerta)}
                </div>
                <div style={{ fontSize: 11, color: "#94A3B8" }}>
                  {etiquetaEntidad(alerta.entidad_tipo)}: {truncarEntidad(alerta.entidad_id)} · {tiempoRelativo(alerta.created_at)}
                </div>
              </div>
            </div>

            {alerta.estado === "NUEVA" && (
              <div style={{ display: "flex", gap: 8, marginTop: 10, paddingLeft: 28 }}>
                <button
                  disabled={actualizandoId === alerta.id}
                  onClick={() => cambiarEstado(alerta.id, "REVISADA")}
                  style={{ flex: 1, padding: "8px", borderRadius: 8, background: "#F1F5F9", border: "none", color: "#334155", fontSize: 12, fontWeight: 700, cursor: "pointer", opacity: actualizandoId === alerta.id ? 0.5 : 1 }}>
                  ✓ Marcar como revisada
                </button>
                <button
                  disabled={actualizandoId === alerta.id}
                  onClick={() => cambiarEstado(alerta.id, "DESCARTADA")}
                  style={{ flex: 1, padding: "8px", borderRadius: 8, background: "#fff", border: "1.5px solid #E2E8F0", color: "#94A3B8", fontSize: 12, fontWeight: 700, cursor: "pointer", opacity: actualizandoId === alerta.id ? 0.5 : 1 }}>
                  ✕ Descartar
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {!cargando && items.length > 0 && items.length < total && (
        <button onClick={() => cargarAlertas(offset + LIMIT, false)}
          style={{ width: "100%", marginTop: 10, padding: 14, borderRadius: 12, background: "#fff", border: "1.5px solid #E2E8F0", color: "#334155", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
          Cargar más ({items.length} de {total})
        </button>
      )}

      {cargando && (
        <div style={{ textAlign: "center", padding: 20, color: "#94A3B8", fontSize: 12 }}>Cargando...</div>
      )}
    </div>
  );
}