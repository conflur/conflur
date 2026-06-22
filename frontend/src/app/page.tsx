import { redirect } from "next/navigation";

export default function Home() {
  // Entrada principal del producto. Protegido por middleware → /login si no hay sesión.
  redirect("/pacientes");
}
