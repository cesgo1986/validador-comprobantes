"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";

// Rutas que NO requieren sesión. "/" se agrega deliberadamente (2026-07,
// decisión de César): cualquiera puede ver la pantalla de inicio y el
// área de carga -- el análisis en sí sigue exigiendo sesión, pero el
// bloqueo pasa a estar en el momento de "analizar", no en "ver la
// pantalla". Cuando exista registro/invitaciones (después de 6.2.8, ver
// ROADMAP.md), sus rutas se agregan aquí también.
const RUTAS_PUBLICAS = ["/login", "/"];

// Item 6.2.8 (Etapa 6, cierre): protección de rutas en el frontend.
// El backend ya rechaza peticiones sin JWT válido (obtener_usuario_actual,
// sin fallback) -- esto complementa esa protección mostrando una
// redirección real a /login en vez de dejar que cada pantalla intente
// cargar y falle con errores sueltos.
export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session, cargando } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const esRutaPublica = RUTAS_PUBLICAS.includes(pathname);

  useEffect(() => {
    if (!cargando && !session && !esRutaPublica) {
      router.replace("/login");
    }
  }, [cargando, session, esRutaPublica, router]);

  if (esRutaPublica) {
    return <>{children}</>;
  }

  if (cargando) {
    return (
      <div style={{ padding: 40, textAlign: "center", color: "rgba(255,255,255,0.6)", fontSize: 13 }}>
        Cargando...
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return <>{children}</>;
}