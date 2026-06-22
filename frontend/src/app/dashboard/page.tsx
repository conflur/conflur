import { redirect } from "next/navigation";

// La cuenta se movió a /cuenta (dentro del shell del producto).
export default function Dashboard() {
  redirect("/cuenta");
}
