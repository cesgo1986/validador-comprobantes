import { supabase } from "./supabaseClient";

// Item 6.2.8 (Etapa 6): reemplaza fetch() normal en llamadas a la API
// de VerificaPago -- agrega el header Authorization automáticamente si
// hay una sesión activa. Si no hay sesión, hace la petición igual, sin
// el header (el backend sigue tolerando eso mientras exista
// obtener_contexto_empresa(), ver DECISION_LOG.md -- deja de tolerarlo
// en 6.2.8, cuando ese fallback se retire).
//
// Uso: reemplazar cada `fetch(url, opciones)` existente por
// `apiFetch(url, opciones)` -- misma firma, mismo tipo de respuesta.
// Pendiente: migrar los fetch() existentes de historial/page.tsx,
// perfil/page.tsx, CentroOperativo.tsx, resultado/page.tsx,
// alertas/page.tsx, NavigationShell.tsx (badge) -- uno por uno, no de
// golpe.
export async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;

  const headers = new Headers(options.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  return fetch(url, { ...options, headers });
}