export default function Perfil() {
  return (
    <div style={{ padding: "16px" }}>
      <div style={{ padding: "8px 4px 20px" }}>
        <span style={{ color: "#fff", fontWeight: 700, fontSize: 18 }}>Perfil</span>
      </div>
      <div style={{ background: "#fff", borderRadius: 16, padding: "40px 20px", textAlign: "center" }}>
        <div style={{ fontSize: 32, marginBottom: 10 }}>👤</div>
        <p style={{ color: "#64748B", fontSize: 13, lineHeight: 1.6, margin: 0 }}>
          Aquí podrás gestionar tus datos, preferencias, seguridad y suscripción.
        </p>
      </div>
    </div>
  );
}