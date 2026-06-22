import { redirect } from "next/navigation";

export default function Home() {
  // El dashboard está protegido por middleware: si no hay sesión, redirige a /login.
  redirect("/dashboard");
}
