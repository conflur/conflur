"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { registerAccount, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await registerAccount({ email, password, full_name: fullName });
      // Establecer la sesión de NextAuth con las mismas credenciales.
      const res = await signIn("password", { email, password, redirect: false });
      if (res?.error) throw new Error("No se pudo iniciar sesión tras el registro");
      router.push("/dashboard");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Ese email ya está registrado");
      } else {
        setError("No se pudo crear la cuenta");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 360, margin: "4rem auto", fontFamily: "system-ui" }}>
      <h1>Conflur</h1>
      <h2 style={{ fontSize: "1.1rem", fontWeight: 500 }}>Crear cuenta</h2>
      <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <input
          type="text" placeholder="Nombre completo" value={fullName} required
          onChange={(e) => setFullName(e.target.value)}
        />
        <input
          type="email" placeholder="Email" value={email} required
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password" placeholder="Contraseña (mín. 8)" value={password} required minLength={8}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit" disabled={loading}>Crear cuenta</button>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      <p style={{ marginTop: 16 }}>
        ¿Ya tenés cuenta? <Link href="/login">Iniciar sesión</Link>
      </p>
    </main>
  );
}
