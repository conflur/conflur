"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { passkeyLogin } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handlePassword(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    const res = await signIn("password", { email, password, redirect: false });
    setLoading(false);
    if (res?.error) {
      setError("Email o contraseña incorrectos");
      return;
    }
    router.push("/dashboard");
  }

  async function handlePasskey() {
    setError(null);
    if (!email) {
      setError("Ingresá tu email para entrar con passkey");
      return;
    }
    setLoading(true);
    try {
      const token = await passkeyLogin(email);
      const res = await signIn("passkey", { accessToken: token, redirect: false });
      if (res?.error) throw new Error();
      router.push("/dashboard");
    } catch {
      setError("No se pudo entrar con passkey");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: "4rem auto", fontFamily: "system-ui" }}>
      <h1>Conflur</h1>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 500 }}>Iniciar sesión</h2>
      <form onSubmit={handlePassword} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <input
          type="email" placeholder="Email" value={email} required
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password" placeholder="Contraseña" value={password} required
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={loading}>Entrar</button>
      </form>
      <button onClick={handlePasskey} disabled={loading} style={{ marginTop: 10, width: "100%" }}>
        Entrar con passkey
      </button>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <p style={{ marginTop: 16 }}>
        ¿No tenés cuenta? <Link href="/register">Crear cuenta</Link>
      </p>
    </main>
  );
}
