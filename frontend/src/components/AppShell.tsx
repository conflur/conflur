"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import { useEffect } from "react";

const NAV = [
  { href: "/pacientes", label: "Pacientes" },
  // Próximos módulos: Agenda, Finanzas
  { href: "/cuenta", label: "Mi cuenta" },
];

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { data: session, status } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  if (status === "loading" || status === "unauthenticated") {
    return <div className="spinner-wrap">Cargando…</div>;
  }

  return (
    <>
      <nav className="app-nav">
        <div className="app-nav-inner">
          <Link href="/pacientes" className="app-brand">Conflur</Link>
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={`nav-link${pathname.startsWith(n.href) ? " active" : ""}`}
            >
              {n.label}
            </Link>
          ))}
          <span className="spacer" />
          <span className="muted small">{session?.principal?.user.full_name ?? session?.user?.email}</span>
          <button className="btn btn-secondary btn-sm" onClick={() => signOut({ callbackUrl: "/login" })}>
            Salir
          </button>
        </div>
      </nav>
      <main className="container">{children}</main>
    </>
  );
}
