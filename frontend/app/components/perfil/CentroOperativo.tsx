"use client";
import { useRouter } from "next/navigation";
import { GREEN, ORANGE, RED } from "../../lib/colores";

export interface BancoIncidencia {
  banco: string;
  alertas: number;
  porcentaje_del_total: number;
}

export interface Comparacion {
  hoy: number;
  promedio?: number;
  ayer?: number;
  variacion_pct: number | null;
}

export interface ResumenCompacto {
  analisis_hoy: number;
  alertas_nuevas: number;
  alertas_notificables: number;
  riesgo_alto: number;
  pct_confirmadas: number | null;
}

export interface CentroOperativoData {
  estado_operacion_general: "verde" | "naranja" | "rojo";
  hero: { monto_procesado_hoy: number };
  secundarios: { volumen_hoy: number; pct_liquidados: number | null; alertas_criticas: number };
  atencion: { alertas_criticas: number; hashes_reutilizados: number };
  tendencias: {
    banco_mayor_incidencia: BancoIncidencia | null;
    comparacion_volumen: Comparacion;
    comparacion_alertas: Comparacion;
  };
  resumen_compacto: ResumenCompacto;
}

function formatearMonto(monto: number): string {
  return "$" + monto.toLocaleString("es-MX", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + " MXN";
}

function fechaHoyLarga(): string {
  const texto = new Date().toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

const ESTADO_CONFIG: Record<string, { color: string; icono: string; texto: string }> = {
  verde: { color: GREEN, icono: "🟢", texto: "Puedes seguir operando normalmente." },
  naranja: { color: ORANGE, icono: "🟠", texto: "Hay alertas que conviene revisar antes de continuar." },
  rojo: { color: RED, icono: "🔴", texto: "Hay un problema que requiere atención inmediata." },
};

// Item 5.5 (Etapa 5): estructura calcada del wireframe conceptual
// (DESIGN_SYSTEM.md, sección 10). Solo Nivel A (Motor de Verdad) --
// ningún widget aparece si no hay nada real que decir.
//
// FIX (2026-07, revisión de arquitectura): este componente ya NO hace
// su propio fetch -- recibe `datos` por prop. Antes hacía una llamada
// independiente a /centro-operativo mientras Mobile llamaba a
// /resumen-ejecutivo -- 2 peticiones, 2 fuentes de verdad para el
// mismo dominio de datos. Ahora `app/perfil/page.tsx` hace una sola
// llamada y la reparte a ambas presentaciones.
export function CentroOperativo({ datos }: { datos: CentroOperativoData }) {
  const router = useRouter();

  const estado = ESTADO_CONFIG[datos.estado_operacion_general] || ESTADO_CONFIG.verde;
  const hayAtencion = datos.atencion.alertas_criticas > 0 || datos.atencion.hashes_reutilizados > 0;
  const cv = datos.tendencias.comparacion_volumen;
  const ca = datos.tendencias.comparacion_alertas;
  const hayTendencias = datos.tendencias.banco_mayor_incidencia !== null || cv.variacion_pct !== null || ca.variacion_pct !== null;

  return (
    <div>
      <div style={{ padding: "4px 4px 20px" }}>
        <span style={{ color: "#fff", fontSize: 13, fontWeight: 600 }}>{fechaHoyLarga()}</span>
      </div>

      {/* Nivel 1: estado + hero stat + secundarios */}
      <div style={{ background: "#fff", borderRadius: 20, padding: "24px 28px", marginBottom: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20, padding: "10px 16px", background: `${estado.color}12`, borderRadius: 12 }}>
          <span style={{ fontSize: 16 }}>{estado.icono}</span>
          <span style={{ fontSize: 13, fontWeight: 700, color: estado.color }}>{estado.texto}</span>
        </div>

        <div style={{ fontSize: 42, fontWeight: 800, color: "#1E293B", lineHeight: 1 }}>
          {formatearMonto(datos.hero.monto_procesado_hoy)}
        </div>
        <div style={{ fontSize: 13, color: "#94A3B8", marginTop: 6, marginBottom: 20 }}>procesados hoy</div>

        <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
          <SecundarioStat label="Pagos" valor={String(datos.secundarios.volumen_hoy)} />
          <SecundarioStat label="Liquidados" valor={datos.secundarios.pct_liquidados !== null ? `${datos.secundarios.pct_liquidados}%` : "—"} />
          <SecundarioStat label="Alertas críticas" valor={String(datos.secundarios.alertas_criticas)} color={datos.secundarios.alertas_criticas > 0 ? RED : undefined} />
        </div>
      </div>

      {/* Nivel 2: qué requiere atención -- no aparece si no hay nada */}
      {hayAtencion && (
        <div style={{ background: "#fff", borderRadius: 20, padding: "20px 24px", marginBottom: 20 }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 14 }}>
            Qué requiere atención
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {datos.atencion.alertas_criticas > 0 && (
              <AccionFila
                icono="⚠️"
                texto={`${datos.atencion.alertas_criticas} operaciones requieren revisión inmediata`}
                boton="Revisar"
                onClick={() => router.push("/alertas")}
              />
            )}
            {datos.atencion.hashes_reutilizados > 0 && (
              <AccionFila
                icono="🔁"
                texto={`${datos.atencion.hashes_reutilizados} comprobantes reutilizados`}
                boton="Revisar"
                onClick={() => router.push("/alertas")}
              />
            )}
          </div>
        </div>
      )}

      {/* Nivel 3: tendencias -- no aparece si no hay nada que comparar */}
      {hayTendencias && (
        <div style={{ background: "#fff", borderRadius: 20, padding: "20px 24px" }}>
          <div style={{ fontSize: 11, color: "#9CA3AF", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 14 }}>
            Tendencias
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {datos.tendencias.banco_mayor_incidencia && (
              <AccionFila
                icono="🏦"
                texto={`${datos.tendencias.banco_mayor_incidencia.banco} concentra el ${datos.tendencias.banco_mayor_incidencia.porcentaje_del_total}% de las incidencias activas`}
                boton="Analizar"
                onClick={() => router.push("/historial")}
              />
            )}
            {cv.variacion_pct !== null && (
              <InfoFila
                icono="📈"
                texto={`Hoy procesaste ${Math.abs(cv.variacion_pct)}% ${cv.variacion_pct >= 0 ? "más" : "menos"} volumen que el promedio de la semana`}
              />
            )}
            {ca.variacion_pct !== null && (
              <AccionFila
                icono="🔔"
                texto={`Las alertas ${ca.variacion_pct >= 0 ? "aumentaron" : "disminuyeron"} ${Math.abs(ca.variacion_pct)}% respecto a ayer`}
                boton="Ver causas"
                onClick={() => router.push("/alertas")}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function SecundarioStat({ label, valor, color }: { label: string; valor: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 20, fontWeight: 700, color: color || "#1E293B" }}>{valor}</div>
      <div style={{ fontSize: 11, color: "#94A3B8", marginTop: 2 }}>{label}</div>
    </div>
  );
}

function AccionFila({ icono, texto, boton, onClick }: { icono: string; texto: string; boton: string; onClick: () => void }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0" }}>
      <span style={{ fontSize: 16 }}>{icono}</span>
      <span style={{ flex: 1, fontSize: 13, color: "#334155" }}>{texto}</span>
      <button onClick={onClick}
        style={{ padding: "6px 14px", borderRadius: 8, border: "1.5px solid #E2E8F0", background: "#fff", color: "#334155", fontSize: 12, fontWeight: 700, cursor: "pointer" }}>
        {boton}
      </button>
    </div>
  );
}

function InfoFila({ icono, texto }: { icono: string; texto: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0" }}>
      <span style={{ fontSize: 16 }}>{icono}</span>
      <span style={{ flex: 1, fontSize: 13, color: "#334155" }}>{texto}</span>
    </div>
  );
}