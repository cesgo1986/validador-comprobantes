import type { Metadata } from "next";
import "./globals.css";
import { AnalisisProvider } from "./context/AnalisisContext";
import BottomNav from "./components/BottomNav";

export const metadata: Metadata = {
  title: "VerificaPago",
  description: "Detecta fraudes. Evita pérdidas. Toma decisiones seguras.",
};

const DARK = "#1A2340";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body style={{
        margin: 0,
        background: `linear-gradient(160deg, ${DARK} 0%, #0D2137 100%)`,
        fontFamily: "'Inter',system-ui,sans-serif",
        minHeight: "100vh",
      }}>
        <AnalisisProvider>
          {/* item 5.2/5.3: ancho responsive vía .vp-container (globals.css),
              ya no un valor fijo de 480px -- ver LABORATORIO.md */}
          <div className="vp-container" style={{ paddingBottom: 90, minHeight: "100vh" }}>
            {children}
          </div>
          <BottomNav />
        </AnalisisProvider>
      </body>
    </html>
  );
}