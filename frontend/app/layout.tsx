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
          {/* item 5.3: vp-content-area se corre a la derecha del sidebar
              en Desktop+ (margin-left: var(--vp-sidebar-width)) -- en
              Mobile/Tablet no hace nada, BottomNav es una barra abajo. */}
          <div className="vp-content-area">
            <div className="vp-container vp-page-padding" style={{ minHeight: "100vh" }}>
              {children}
            </div>
          </div>
          <BottomNav />
        </AnalisisProvider>
      </body>
    </html>
  );
}