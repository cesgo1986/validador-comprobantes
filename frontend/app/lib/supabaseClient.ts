import { createClient } from "@supabase/supabase-js";

// Item 6.2.8 (Etapa 6, Identity Layer): requiere las variables de
// entorno NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY
// configuradas en Vercel. El "anon key" (o "publishable key" en el
// sistema nuevo de llaves) es seguro de exponer en el navegador -- por
// eso Supabase lo llama "publishable", ver DECISION_LOG.md.
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);