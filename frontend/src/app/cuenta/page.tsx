"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import AppShell from "@/components/AppShell";
import { passkeyRegister } from "@/lib/api";

export default function CuentaPage() {
  const { data: session } = useSession();
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const principal = session?.principal;

  async function activatePasskey() {
    setMsg(null);
    setBusy(true);
    try {
      await passkeyRegister(session!.accessToken!, navigator.userAgent.slice(0, 60));
      setMsg({ kind: "ok", text: "Passkey activada en este dispositivo. Ya podés entrar con tu huella/cara." });
    } catch {
      setMsg({ kind: "error", text: "No se pudo activar la passkey en este dispositivo." });
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="page-header"><h1>Mi cuenta</h1></div>

      <div className="card">
        <div className="section-title">Datos</div>
        <p style={{ margin: "0.2rem 0" }}><strong>{principal?.user.full_name ?? principal?.user.email}</strong></p>
        <p className="muted small" style={{ margin: "0.2rem 0" }}>Email: {principal?.user.email}</p>
        <p className="muted small" style={{ margin: "0.2rem 0" }}>Rol: {principal?.role}</p>
      </div>

      <div className="card">
        <div className="section-title">Acceso biométrico (passkey)</div>
        <p className="muted small" style={{ marginTop: 0 }}>
          Activá una passkey para entrar con huella o reconocimiento facial, sin tipear la contraseña.
        </p>
        {msg && <div className={`alert ${msg.kind === "ok" ? "alert-ok" : "alert-error"}`}>{msg.text}</div>}
        <button className="btn" onClick={activatePasskey} disabled={busy}>
          {busy ? "Activando…" : "Activar passkey en este dispositivo"}
        </button>
      </div>
    </AppShell>
  );
}
