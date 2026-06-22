import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * El backend (FastAPI) es dueño de la verificación de credenciales (D11).
 * NextAuth es la capa de sesión: dos Credentials providers que terminan en un
 * access token emitido por el backend, guardado en el JWT de NextAuth y
 * reenviado como Bearer en cada request a la API.
 */
export const authOptions: NextAuthOptions = {
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 días (architecture.md D7)
  },
  providers: [
    // Login por email + contraseña: la verificación ocurre en el backend.
    CredentialsProvider({
      id: "password",
      name: "Email y contraseña",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Contraseña", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;
        const res = await fetch(`${API}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: credentials.email, password: credentials.password }),
        });
        if (!res.ok) return null;
        const data = await res.json(); // { access_token, principal }
        return {
          id: data.principal.user.id,
          email: data.principal.user.email,
          name: data.principal.user.full_name,
          accessToken: data.access_token,
          principal: data.principal,
        } as any;
      },
    }),
    // Login por passkey: la ceremonia WebAuthn ya ocurrió en el cliente y produjo
    // un access token; acá solo lo validamos contra /auth/me.
    CredentialsProvider({
      id: "passkey",
      name: "Passkey",
      credentials: { accessToken: { label: "token", type: "text" } },
      async authorize(credentials) {
        if (!credentials?.accessToken) return null;
        const res = await fetch(`${API}/auth/me`, {
          headers: { Authorization: `Bearer ${credentials.accessToken}` },
        });
        if (!res.ok) return null;
        const principal = await res.json();
        return {
          id: principal.user.id,
          email: principal.user.email,
          name: principal.user.full_name,
          accessToken: credentials.accessToken,
          principal,
        } as any;
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.accessToken = (user as any).accessToken;
        token.principal = (user as any).principal;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.principal = token.principal as any;
      return session;
    },
  },
};
