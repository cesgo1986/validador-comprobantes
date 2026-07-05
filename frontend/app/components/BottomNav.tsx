"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const TEAL = "#00BFA5";
const DARK = "#1A2340";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "";

const ICONS = {
  home: (active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? TEAL : "rgba(255,255,255,0.45)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1V9.5Z" />
    </svg>
  ),
  historial: (active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? TEAL : "rgba(255,255,255,0.45)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 3v5h5" /><path d="M3.05 13a9 9 0 1 0 .5-4.5L3 8" /><path d="M12 7v5l4 2" />
    </svg>
  ),
  plus: (_active: boolean) => (
    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  ),
  alertas: (active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? TEAL : "rgba(255,255,255,0.45)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  ),
  perfil: (active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={active ? TEAL : "rgba(255,255,255,0.45)"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" /><path d="M4 21c0-4 3.5-7 8-7s8 3 8 7" />
    </svg>
  ),
};

export default function BottomNav() {
  const pathname = usePathname();
  const router = useRouter();

  // Item 3.5: badge inteligente -- ya no hardcodeado. Usa "notificables"
  // (Motor de Prioridad: severidad MEDIA o superior, ver
  // services/alerta_service.py), no el total de alertas NUEVA -- una
  // alerta BAJA no debe inflar el contador igual que una ALTA.
  const [alertasBadge, setAlertasBadge] = useState(0);

  useEffect(() => {
    let activo = true;

    async function cargarConteo() {
      try {
        const resp = await fetch(`${API_URL}/api/v1/dashboard/alertas/conteo`);
        if (!resp.ok) return;
        const data = await resp.json();
        if (activo) setAlertasBadge(data.notificables ?? 0);
      } catch {
        // El badge es un extra -- si falla, la navegación sigue funcionando
        // con el badge en 0 en vez de romper la barra inferior.
      }
    }

    cargarConteo();
    // Refresca cada 60s mientras la app esté abierta -- suficiente para
    // sentirse "vivo" sin necesitar WebSockets todavía (ver ROADMAP.md,
    // posible evolución futura si se necesita tiempo real de verdad).
    const intervalo = setInterval(cargarConteo, 60000);
    return () => { activo = false; clearInterval(intervalo); };
  }, []);

  // El botón central "+" siempre regresa al flujo de nuevo análisis,
  // sin importar en qué pantalla del flujo este el usuario.
  const items = [
    { key: "inicio", label: "Inicio", href: "/", icon: ICONS.home, badge: 0 },
    { key: "historial", label: "Historial", href: "/historial", icon: ICONS.historial, badge: 0 },
    { key: "plus", label: "", href: "/", icon: ICONS.plus, badge: 0, isPlus: true },
    { key: "alertas", label: "Alertas", href: "/alertas", icon: ICONS.alertas, badge: alertasBadge },
    { key: "perfil", label: "Perfil", href: "/perfil", icon: ICONS.perfil, badge: 0 },
  ];

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/" || pathname.startsWith("/analizando") || pathname.startsWith("/resultado");
    return pathname.startsWith(href);
  };

  return (
    <nav style={{
      position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 50,
      background: "rgba(13, 22, 41, 0.96)", backdropFilter: "blur(10px)",
      borderTop: "1px solid rgba(255,255,255,0.08)",
      display: "flex", alignItems: "center", justifyContent: "space-around",
      padding: "10px 8px calc(10px + env(safe-area-inset-bottom))",
      maxWidth: 480, margin: "0 auto",
    }}>
      {items.map((item) => {
        const active = isActive(item.href);
        if (item.isPlus) {
          return (
            <button key={item.key} onClick={() => router.push(item.href)}
              aria-label="Nuevo análisis"
              style={{
                width: 50, height: 50, borderRadius: "50%", background: TEAL,
                border: "none", display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", boxShadow: `0 4px 14px ${TEAL}55`, marginTop: -22,
              }}>
              {item.icon(true)}
            </button>
          );
        }
        return (
          <button key={item.key} onClick={() => router.push(item.href)}
            aria-label={item.label}
            style={{
              display: "flex", flexDirection: "column", alignItems: "center", gap: 3,
              background: "none", border: "none", cursor: "pointer", position: "relative",
              padding: "4px 10px", minWidth: 52,
            }}>
            <div style={{ position: "relative" }}>
              {item.icon(active)}
              {item.badge > 0 && (
                <span style={{
                  position: "absolute", top: -4, right: -7, background: "#F5A623",
                  color: "#1A2340", fontSize: 9, fontWeight: 800, borderRadius: 9,
                  minWidth: 15, height: 15, display: "flex", alignItems: "center", justifyContent: "center",
                  padding: "0 3px",
                }}>{item.badge}</span>
              )}
            </div>
            <span style={{ fontSize: 10, fontWeight: 600, color: active ? TEAL : "rgba(255,255,255,0.45)" }}>
              {item.label}
            </span>
          </button>
        );
      })}
    </nav>
  );
}