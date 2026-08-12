"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";

// Item 6.2.1 (Etapa 6): /recuperar y /restablecer agregadas -- ambas
// deben ser accesibles sin sesión (restablecer incluso usa una sesión
// TEMPORAL de recuperación que no debe tratarse como login normal).
const RUTAS_PUBLICAS = ["/login", "/", "/recuperar", "/restablecer"];

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