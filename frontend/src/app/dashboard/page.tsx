"use client";

import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { passkeyRegister } from "@/lib/api";

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === "loading") return <main style={{ margin: "4rem auto", maxWidth: 480 }}>Cargando…</main>;
  if (status === "unauthenticated" || !session) {
    router.push("/login");
    return null;
  }

  const principal = session.principal;

  async function activatePasskey() {
    setMsg(null);
    setBusy(true);
    try {
      await passkeyRegister(session!.accessToken!, navigator.userAgent.slice(0, 60));
      setMsg("Passkey activada en este dispositivo ✓");
    } catch {
      setMsg("No se pudo activar la passkey");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 480, margin: "4rem auto", fontFamily: "system-ui" }}>
      <h1>Conflur</h1>
      <p>Hola, <strong>{principal?.user.full_name ?? principal?.user.email}</strong></p>
      <ul>
        <li>Email: {principal?.user.email}</li>
        <li>Consultorio (tenant): {principal?.tenant_id}</li>
        <li>Rol: {principal?.role}</li>
      </ul>
      <button onClick={activatePasskey} disabled={busy}>Activar passkey en este dispositivo</button>
      {msg && <p>{msg}</p>}
      <p style={{ marginTop: 24 }}>
        <button onClick={() => signOut({ callbackUrl: "/login" })}>Cerrar sesión</button>
      </p>
    </main>
  );
}
