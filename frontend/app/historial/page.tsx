"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getSemaforoSpei } from "../lib/estadoSpei";
import { useAnalisis } from "../context/AnalisisContext";
import { HistorialDetalleContenido, AnalisisDetalle } from "../components/historial/HistorialDetalleContenido";

const TEAL = "#00BFA5";
const GREEN = "#43A047";
const ORANGE = "#F5A623";
const RED = "#E53935";
const GRAY = "#9CA3AF";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "";
const DESKTOP_BREAKPOINT_QUERY = "(min-width: 1200px)";

interface AnalisisItem {
  id: string;
  fecha: string | null;
  hash_sha256: string | null;
  score_final: number | null;
  riesgo: string | null;
  estado_operacion: string | null;
  fuente_estado: string | null;
  nivel_evidencia: string | null;
  clave_rastreo: string | null;
  referencia: string | null;
  tipo_transferencia: string | null;
  archivo_nombre: string | null;
  banco_detectado: string | null;
  monto_detectado: number | null;
  veces_visto: number;
}

interface Stats {
  total_analisis: number;
  analisis_hoy: number;
  score_promedio: number | null;
  distribucion_riesgo: { riesgo: string; total: number }[];
  documentos_unicos: number;
  documentos_reutilizados: number;
}

const RIESGO_OPCIONES = ["BAJO", "MEDIO", "ALTO", "CRITICO"];
const LIMIT = 20;

function colorRiesgo(riesgo: string | null): string {
  switch (riesgo) {
    case "BAJO": return GREEN;
    case "MEDIO": return ORANGE;
    case "ALTO": return RED;
    case "CRITICO": return "#B91C1C";
    default: return GRAY;
  }
}

function tiempoRelativo(fechaISO: string | null): string {
  if (!fechaISO) return "";
  const fecha = new Date(fechaISO);
  const ahora = new Date();
  const diffMs = ahora.getTime() - fecha.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Justo ahora";
  if (diffMin < 60) return `Hace ${diffMin} min`;
  const diffHoras = Math.floor(diffMin / 60);
  if (diffHoras < 24) return `Hace ${diffHoras} h`;
  const diffDias = Math.floor(diffHoras / 24);
  if (diffDias === 1) return "Ayer";
  if (diffDias < 7) return `Hace ${diffDias} días`;
  return fecha.toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
}

function grupoDelDia(fechaISO: string | null): string {
  if (!fechaISO) return "Sin fecha";
  const fecha = new Date(fechaISO);
  const hoy = new Date();
  const ayer = new Date(hoy);
  ayer.setDate(hoy.getDate() - 1);
  const esMismoDia = (a: Date, b: Date) => a.toDateString() === b.toDateString();
  if (esMismoDia(fecha, hoy)) return "Hoy";
  if (esMismoDia(fecha, ayer)) return "Ayer";
  return fecha.toLocaleDateString("es-MX", { day: "2-digit", month: "long", year: "numeric" });
}

function formatearMonto(monto: number | null): string {
  if (monto === null || monto === undefined) return "";
  return "$" + monto.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Item 5.4 (Etapa 5): en Desktop+ (≥1200px), tocar una tarjeta NO navega
// a /historial/[id] -- selecciona el análisis y lo muestra en la
// columna derecha (maestro-detalle), sin salir de /historial. En
// Mobile/Tablet, navega exactamente como antes de 5.4. La decisión de
// cuál comportamiento usar se toma DENTRO del clic (window.matchMedia),
// nunca durante el renderizado -- así no hay riesgo de mismatch de
// hidratación de Next.js: el HTML inicial es idéntico en servidor y
// cliente, solo el comportamiento del clic (que no afecta el render)
// cambia según el ancho real de la ventana en ese momento.
export default function Historial() {
  const router = useRouter();
  const { setResult } = useAnalisis();

  const [items, setItems] = useState<AnalisisItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [resumenAbierto, setResumenAbierto] = useState(false);
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);

  const [busqueda, setBusqueda] = useState("");
  const [riesgo, setRiesgo] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");
  const [hashBusqueda, setHashBusqueda] = useState("");

  // Item 5.4: estado del panel de detalle (Desktop+)
  const [idSeleccionado, setIdSeleccionado] = useState<string | null>(null);
  const [detalleSeleccionado, setDetalleSeleccionado] = useState<AnalisisDetalle | null>(null);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);
  const [errorDetalle, setErrorDetalle] = useState<string | null>(null);

  const hayFiltrosAvanzadosActivos = !!(riesgo || fechaDesde || fechaHasta || hashBusqueda);

  const construirQuery = useCallback((offsetActual: number) => {
    const params = new URLSearchParams();
    params.set("limit", String(LIMIT));
    params.set("offset", String(offsetActual));
    if (busqueda.trim()) params.set("q", busqueda.trim());
    if (riesgo) params.set("riesgo", riesgo);
    if (fechaDesde) params.set("fecha_desde", fechaDesde);
    if (fechaHasta) params.set("fecha_hasta", fechaHasta);
    if (hashBusqueda.trim()) params.set("hash_sha256", hashBusqueda.trim());
    return params.toString();
  }, [busqueda, riesgo, fechaDesde, fechaHasta, hashBusqueda]);

  const construirQueryExport = useCallback(() => {
    const params = new URLSearchParams();
    if (busqueda.trim()) params.set("q", busqueda.trim());
    if (riesgo) params.set("riesgo", riesgo);
    if (fechaDesde) params.set("fecha_desde", fechaDesde);
    if (fechaHasta) params.set("fecha_hasta", fechaHasta);
    if (hashBusqueda.trim()) params.set("hash_sha256", hashBusqueda.trim());
    return params.toString();
  }, [busqueda, riesgo, fechaDesde, fechaHasta, hashBusqueda]);

  const exportarCSV = () => {
    const url = `${API_URL}/api/v1/dashboard/analisis/exportar?${construirQueryExport()}`;
    window.open(url, "_blank");
  };

  const cargarStats = useCallback(async () => {
    try {
      const resp = await fetch(`${API_URL}/api/v1/dashboard/stats`);
      if (!resp.ok) return;
      setStats(await resp.json());
    } catch {
      // El resumen es un extra bajo demanda -- si falla, el historial sigue funcionando.
    }
  }, []);

  const cargarAnalisis = useCallback(async (offsetActual: number, reemplazar: boolean) => {
    setCargando(true);
    setError(null);
    try {
      const resp = await fetch(`${API_URL}/api/v1/dashboard/analisis?${construirQuery(offsetActual)}`);
      if (!resp.ok) throw new Error();
      const data = await resp.json();
      setItems(prev => reemplazar ? data.items : [...prev, ...data.items]);
      setTotal(data.total);
      setOffset(offsetActual);
    } catch {
      setError("No se pudo cargar el historial. Intenta de nuevo.");
    } finally {
      setCargando(false);
    }
  }, [construirQuery]);

  // Item 5.4: carga el detalle para el panel derecho (Desktop+)
  const cargarDetalle = useCallback(async (id: string) => {
    setCargandoDetalle(true);
    setErrorDetalle(null);
    try {
      const resp = await fetch(`${API_URL}/api/v1/dashboard/analisis/${id}`);
      if (!resp.ok) throw new Error();
      const data: AnalisisDetalle = await resp.json();
      setDetalleSeleccionado(data);
      setResult(data.resultado);
    } catch {
      setErrorDetalle("No se pudo cargar este análisis. Intenta de nuevo.");
    } finally {
      setCargandoDetalle(false);
    }
  }, [setResult]);

  const seleccionarItem = (id: string) => {
    const esDesktop = typeof window !== "undefined" && window.matchMedia(DESKTOP_BREAKPOINT_QUERY).matches;
    if (esDesktop) {
      setIdSeleccionado(id);
      cargarDetalle(id);
    } else {
      router.push(`/historial/${id}`);
    }
  };

  useEffect(() => { cargarStats(); }, [cargarStats]);

  useEffect(() => {
    const t = setTimeout(() => cargarAnalisis(0, true), busqueda ? 350 : 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [busqueda, riesgo, fechaDesde, fechaHasta, hashBusqueda]);

  const limpiarFiltrosAvanzados = () => {
    setRiesgo(""); setFechaDesde(""); setFechaHasta(""); setHashBusqueda("");
  };

  const grupos = useMemo(() => {
    const mapa = new Map<string, AnalisisItem[]>();
    for (const item of items) {
      const clave = grupoDelDia(item.fecha);
      if (!mapa.has(clave)) mapa.set(clave, []);
      mapa.get(clave)!.push(item);
    }
    return Array.from(mapa.entries());
  }, [items]);

  return (
    <div style={{ padding: "16px", paddingBottom: 90 }}>
      <div style={{ padding: "8px 4px 16px" }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Historial</span>
      </div>

      {/* item 5.4: maestro-detalle -- 1 columna en Mobile/Tablet, 2 en Desktop+ */}
      <div className="vp-historial-grid">
        <div>
          {/* Nivel 1: búsqueda unificada + entrada a filtros */}
          <div style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <input
              value={busqueda}
              onChange={e => setBusqueda(e.target.value)}
              placeholder="🔎 Banco, clave de rastreo, cuenta o monto..."
              style={{ flex: 1, padding: "12px 14px", borderRadius: 12, border: "1.5px solid #E2E8F0", background: "#fff", fontSize: 13 }}
            />
            <button onClick={() => setFiltrosAbiertos(o => !o)}
              style={{
                padding: "0 16px", borderRadius: 12, cursor: "pointer",
                border: hayFiltrosAvanzadosActivos ? `1.5px solid ${TEAL}` : "1.5px solid #E2E8F0",
                background: hayFiltrosAvanzadosActivos ? `${TEAL}12` : "#fff",
                color: hayFiltrosAvanzadosActivos ? TEAL : "#334155", fontSize: 13, fontWeight: 700,
              }}>
              Filtros
            </button>
          </div>

          {filtrosAbiertos && (
            <div style={{ background: "#fff", borderRadius: 14, padding: 16, marginBottom: 10, display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Riesgo documental (Motor 2)
                </label>
                <div style={{ display: "flex", gap: 6, marginTop: 6, flexWrap: "wrap" }}>
                  {RIESGO_OPCIONES.map(r => (
                    <button key={r} onClick={() => setRiesgo(riesgo === r ? "" : r)}
                      style={{
                        padding: "6px 12px", borderRadius: 8, fontSize: 12, fontWeight: 700, cursor: "pointer",
                        border: `1.5px solid ${riesgo === r ? colorRiesgo(r) : "#E2E8F0"}`,
                        background: riesgo === r ? `${colorRiesgo(r)}15` : "#fff",
                        color: riesgo === r ? colorRiesgo(r) : "#64748B",
                      }}>
                      {r}
                    </button>
                  ))}
                </div>
              </div>
              <div style={{ display: "flex", gap: 10 }}>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>Desde</label>
                  <input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)}
                    style={{ width: "100%", marginTop: 6, padding: "8px 10px", borderRadius: 8, border: "1.5px solid #E2E8F0", fontSize: 13 }} />
                </div>
                <div style={{ flex: 1 }}>
                  <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>Hasta</label>
                  <input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)}
                    style={{ width: "100%", marginTop: 6, padding: "8px 10px", borderRadius: 8, border: "1.5px solid #E2E8F0", fontSize: 13 }} />
                </div>
              </div>
              <div>
                <label style={{ fontSize: 11, color: "#94A3B8", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.04em" }}>Hash exacto (avanzado)</label>
                <input value={hashBusqueda} onChange={e => setHashBusqueda(e.target.value)} placeholder="Búsqueda exacta"
                  style={{ width: "100%", marginTop: 6, padding: "8px 10px", borderRadius: 8, border: "1.5px solid #E2E8F0", fontSize: 13 }} />
              </div>
              {hayFiltrosAvanzadosActivos && (
                <button onClick={limpiarFiltrosAvanzados}
                  style={{ padding: "8px", borderRadius: 8, background: "#F1F5F9", border: "none", color: "#334155", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                  Limpiar filtros
                </button>
              )}
              <button onClick={exportarCSV}
                style={{ padding: "10px", borderRadius: 8, background: "#fff", border: "1.5px solid #E2E8F0", color: "#334155", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
                ⬇ Exportar a CSV (con estos filtros)
              </button>
            </div>
          )}

          <button onClick={() => setResumenAbierto(o => !o)}
            style={{ width: "100%", padding: "12px 16px", marginBottom: 14, borderRadius: 12, background: "#fff", border: "none", display: "flex", alignItems: "center", gap: 8, cursor: "pointer" }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: "#334155", flex: 1, textAlign: "left" }}>Resumen de actividad</span>
            <span style={{ color: "#CBD5E1", fontSize: 12 }}>{resumenAbierto ? "▲" : "▼"}</span>
          </button>
          {resumenAbierto && stats && (
            <div style={{ background: "#fff", borderRadius: 14, padding: 16, marginTop: -8, marginBottom: 14, display: "flex", flexDirection: "column", gap: 10 }}>
              <ResumenFila label="Total de análisis" valor={stats.total_analisis} />
              <ResumenFila label="Hoy" valor={stats.analisis_hoy} />
              {stats.distribucion_riesgo.map(d => (
                <ResumenFila key={d.riesgo} label={`Riesgo ${d.riesgo}`} valor={d.total} color={colorRiesgo(d.riesgo)} />
              ))}
              <ResumenFila label="Documentos reutilizados" valor={stats.documentos_reutilizados} color={stats.documentos_reutilizados > 0 ? ORANGE : undefined} />
            </div>
          )}

          {error && (
            <div style={{ background: "#fff", borderRadius: 14, padding: 20, textAlign: "center", marginBottom: 14 }}>
              <p style={{ color: RED, fontSize: 13, margin: 0 }}>{error}</p>
            </div>
          )}

          {!cargando && !error && items.length === 0 && (
            <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>📋</div>
              <p style={{ color: "#64748B", fontSize: 13, lineHeight: 1.6, margin: 0 }}>
                {busqueda || hayFiltrosAvanzadosActivos
                  ? "No se encontraron análisis con esta búsqueda."
                  : "Aquí verás tus análisis anteriores en cuanto proceses tu primer comprobante."}
              </p>
            </div>
          )}

          {grupos.map(([dia, itemsDelDia]) => (
            <div key={dia} style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 8, paddingLeft: 4 }}>
                {dia}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {itemsDelDia.map(item => {
                  const spei = getSemaforoSpei(item.estado_operacion);
                  const seleccionado = item.id === idSeleccionado;
                  return (
                    <div key={item.id} onClick={() => seleccionarItem(item.id)}
                      style={{
                        background: "#fff", borderRadius: 14, padding: "14px 16px", display: "flex", alignItems: "center", gap: 12, cursor: "pointer",
                        border: seleccionado ? `1.5px solid ${TEAL}` : "1.5px solid transparent",
                      }}>
                      <span style={{ fontSize: 18, flexShrink: 0 }}>{spei.icono}</span>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 700, color: spei.color }}>
                          {spei.etiqueta}
                        </div>
                        <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>
                          {item.banco_detectado || item.archivo_nombre || "Comprobante"}
                          {item.veces_visto > 1 ? ` · Reutilizado ${item.veces_visto} veces` : ""}
                        </div>
                      </div>
                      <div style={{ textAlign: "right", flexShrink: 0 }}>
                        {item.monto_detectado !== null && (
                          <div style={{ fontSize: 13, fontWeight: 700, color: "#1E293B" }}>{formatearMonto(item.monto_detectado)}</div>
                        )}
                        <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{tiempoRelativo(item.fecha)}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}

          {!cargando && items.length > 0 && items.length < total && (
            <button onClick={() => cargarAnalisis(offset + LIMIT, false)}
              style={{ width: "100%", marginTop: 6, padding: 14, borderRadius: 12, background: "#fff", border: "1.5px solid #E2E8F0", color: "#334155", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
              Cargar más ({items.length} de {total})
            </button>
          )}

          {cargando && (
            <div style={{ textAlign: "center", padding: 20, color: "#94A3B8", fontSize: 12 }}>Cargando...</div>
          )}
        </div>

        {/* Columna derecha -- oculta por completo en Mobile/Tablet vía
            .vp-historial-detalle-panel (ver globals.css), para no
            agregar contenido visible nuevo ahí (idSeleccionado nunca se
            setea en Mobile/Tablet de todas formas -- seleccionarItem
            navega en su lugar -- pero ocultarla explícitamente evita
            depender de esa coincidencia). Solo visible en Desktop+. */}
        <div className="vp-historial-detalle-panel">
          {idSeleccionado && cargandoDetalle && (
            <div style={{ background: "#fff", borderRadius: 20, padding: 40, textAlign: "center", color: "#94A3B8", fontSize: 13 }}>
              Cargando análisis...
            </div>
          )}
          {idSeleccionado && errorDetalle && (
            <div style={{ background: "#fff", borderRadius: 20, padding: 40, textAlign: "center" }}>
              <p style={{ color: RED, fontSize: 13, margin: 0 }}>{errorDetalle}</p>
            </div>
          )}
          {idSeleccionado && !cargandoDetalle && !errorDetalle && detalleSeleccionado && (
            <HistorialDetalleContenido
              detalle={detalleSeleccionado}
              onVolver={() => { setIdSeleccionado(null); setDetalleSeleccionado(null); }}
              onVerValidaciones={() => router.push("/resultado/detalle")}
              textoBotonVolver="Cerrar detalle"
            />
          )}
          {!idSeleccionado && (
            <div style={{ background: "#fff", borderRadius: 20, padding: 60, textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>👈</div>
              <p style={{ color: "#94A3B8", fontSize: 13, margin: 0 }}>
                Selecciona un análisis de la lista para ver su detalle.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ResumenFila({ label, valor, color }: { label: string; valor: number; color?: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
      <span style={{ fontSize: 12, color: "#64748B" }}>{label}</span>
      <span style={{ fontSize: 13, fontWeight: 700, color: color || "#1E293B" }}>{valor}</span>
    </div>
  );
}