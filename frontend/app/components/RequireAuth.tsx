"use client";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "../context/AuthContext";

// Item 6.2.6 (Etapa 6): /aceptar-invitacion agregada -- igual que
// /restablecer, usa una sesión TEMPORAL de Supabase (del enlace del
// correo) que no debe tratarse como una sesión normal ya vinculada.
// "/usuarios" NO se agrega aquí a propósito -- requiere sesión normal
// como cualquier otra pantalla protegida; el control de si puede
// GESTIONAR usuarios (permiso USERS) lo hace el backend, no esta ruta.
const RUTAS_PUBLICAS = ["/login", "/", "/recuperar", "/restablecer", "/aceptar-invitacion"];

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
