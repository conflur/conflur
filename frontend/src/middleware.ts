export { default } from "next-auth/middleware";

// Rutas que requieren sesión. NextAuth redirige a /login (pages.signIn) si no hay.
export const config = {
  matcher: ["/dashboard/:path*"],
};
