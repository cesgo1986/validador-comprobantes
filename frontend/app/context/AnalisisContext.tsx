"use client";
import { createContext, useContext, useState, ReactNode } from "react";

// ── Tipos compartidos ─────────────────────────────────────────────────────
export type Status = "ok" | "warn" | "fail" | "info";
export type EstadoOperacion =
  | "acreditada" | "liquidada" | "en_proceso" | "devuelta" | "en_devolucion"
  | "rechazada" | "cancelada" | "no_liquidada" | "desconocida";

export interface Validacion {
  categoria: string;
  nombre: string;
  status: Status;
  detalle: string;
  cep_url?: string;
}

export interface ClabeResultado {
  valid: boolean;
  bank?: string;
  bank_code?: string;
  reason?: string;
  clabe?: string;
}

export interface CepResultado {
  found: boolean;
  status: string;
  confidence: number;
  match_monto?: boolean | null;
  cep_sin_monto?: boolean;
  monto_comprobante?: number;
  montos_cep?: number[];
  clave_usada?: string;
  tipo_clave?: string;
  cep_url?: string;
  detalle?: string;
}

export interface Resultado {
  riesgo: "BAJO" | "MEDIO" | "ALTO" | "CRITICO" | "INDETERMINADO";
  score: number;
  campos_extraidos: Record<string, string | null>;
  validaciones: Validacion[];
  resumen: string;
  recomendacion: string;
  requiere_confirmacion_fecha?: boolean;
  mensaje_confirmacion_fecha?: string;
  dias_diferencia?: number;
  clabe_resultado?: ClabeResultado;
  clabe_comprobante?: { valid: boolean; bank?: string; bank_code?: string };
  cep_resultado?: CepResultado;
  audit_id?: string;

  confianza_documental: number;
  verificabilidad: number;
  contexto_temporal: number;
  estado_operacion: EstadoOperacion;
  contexto_operacional: number | null;
  interpretacion: string;
  detalle_temporal?: string;
  elementos_verificabilidad?: string[];

  hash_documento?: string;
  veces_visto?: number;
  documento_reutilizado?: boolean;
}

interface AnalisisContextValue {
  file: File | null;
  setFile: (f: File | null) => void;
  preview: string | null;
  setPreview: (p: string | null) => void;
  bankHint: string;
  setBankHint: (b: string) => void;
  clabeInput: string;
  setClabeInput: (c: string) => void;
  result: Resultado | null;
  setResult: (r: Resultado | null) => void;
  reset: () => void;
}

const AnalisisContext = createContext<AnalisisContextValue | null>(null);

export function AnalisisProvider({ children }: { children: ReactNode }) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [bankHint, setBankHint] = useState("");
  const [clabeInput, setClabeInput] = useState("");
  const [result, setResult] = useState<Resultado | null>(null);

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview);
    setFile(null);
    setPreview(null);
    setBankHint("");
    setClabeInput("");
    setResult(null);
  };

  return (
    <AnalisisContext.Provider value={{
      file, setFile, preview, setPreview, bankHint, setBankHint,
      clabeInput, setClabeInput, result, setResult, reset,
    }}>
      {children}
    </AnalisisContext.Provider>
  );
}

export function useAnalisis() {
  const ctx = useContext(AnalisisContext);
  if (!ctx) throw new Error("useAnalisis debe usarse dentro de AnalisisProvider");
  return ctx;
}