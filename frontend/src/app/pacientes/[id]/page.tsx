"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import AppShell from "@/components/AppShell";
import FichaTab from "@/components/FichaTab";
import NotasTab from "@/components/NotasTab";
import { getPatient, updatePatient, type Patient, type PatientInput } from "@/lib/conflur";
import { ApiError } from "@/lib/apiClient";

type Tab = "perfil" | "ficha" | "notas";

export default function PacienteDetailPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const params = useParams();
  const router = useRouter();
  const id = String(params.id);

  const [patient, setPatient] = useState<Patient | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("perfil");

  useEffect(() => {
    if (!token) return;
    getPatient(token, id)
      .then(setPatient)
      .catch((e) => setError(e instanceof ApiError && e.status === 404 ? "Paciente no encontrado" : "No se pudo cargar"));
  }, [token, id]);

  if (error) {
    return (
      <AppShell>
        <div className="alert alert-error">{error}</div>
        <button className="btn btn-secondary" onClick={() => router.push("/pacientes")}>← Volver</button>
      </AppShell>
    );
  }
  if (!token || !patient) {
    return <AppShell><div className="spinner-wrap">Cargando…</div></AppShell>;
  }

  return (
    <AppShell>
      <div className="page-header">
        <button className="btn btn-secondary btn-sm" onClick={() => router.push("/pacientes")}>← Pacientes</button>
        <h1 style={{ margin: 0 }}>{patient.full_name}</h1>
      </div>

      <div className="tabs">
        <button className={`tab${tab === "perfil" ? " active" : ""}`} onClick={() => setTab("perfil")}>Perfil</button>
        <button className={`tab${tab === "ficha" ? " active" : ""}`} onClick={() => setTab("ficha")}>Ficha clínica</button>
        <button className={`tab${tab === "notas" ? " active" : ""}`} onClick={() => setTab("notas")}>Notas</button>
      </div>

      {tab === "perfil" && <PerfilTab token={token} patient={patient} onSaved={setPatient} />}
      {tab === "ficha" && <FichaTab token={token} patientId={id} />}
      {tab === "notas" && <NotasTab token={token} patientId={id} />}
    </AppShell>
  );
}

function PerfilTab({ token, patient, onSaved }: { token: string; patient: Patient; onSaved: (p: Patient) => void }) {
  const [form, setForm] = useState<PatientInput>({
    full_name: patient.full_name, email: patient.email ?? "", phone: patient.phone ?? "",
    treatment_start_date: patient.treatment_start_date ?? "", session_fee: patient.session_fee ?? undefined,
    fee_currency: patient.fee_currency ?? "ARS", payment_method: patient.payment_method ?? "", notes: patient.notes ?? "",
  });
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  function set<K extends keyof PatientInput>(k: K, v: PatientInput[K]) { setForm((f) => ({ ...f, [k]: v })); }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setMsg(null); setSaving(true);
    try {
      const updated = await updatePatient(token, patient.id, {
        ...form, session_fee: form.session_fee ? Number(form.session_fee) : undefined,
      });
      onSaved(updated);
      setMsg({ kind: "ok", text: "Cambios guardados." });
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "No se pudo guardar" });
    } finally { setSaving(false); }
  }

  return (
    <form className="card" onSubmit={save}>
      <div className="section-title">Datos del paciente</div>
      {msg && <div className={`alert ${msg.kind === "ok" ? "alert-ok" : "alert-error"}`}>{msg.text}</div>}
      <div className="field">
        <label className="label">Nombre completo *</label>
        <input className="input" required value={form.full_name ?? ""} onChange={(e) => set("full_name", e.target.value)} />
      </div>
      <div className="row">
        <div className="field"><label className="label">Teléfono</label>
          <input className="input" value={form.phone ?? ""} onChange={(e) => set("phone", e.target.value)} /></div>
        <div className="field"><label className="label">Email</label>
          <input className="input" type="email" value={form.email ?? ""} onChange={(e) => set("email", e.target.value)} /></div>
      </div>
      <div className="row">
        <div className="field"><label className="label">Honorario por sesión</label>
          <input className="input" type="number" min="0" value={form.session_fee ?? ""} onChange={(e) => set("session_fee", e.target.value as unknown as number)} /></div>
        <div className="field"><label className="label">Moneda</label>
          <select className="select" value={form.fee_currency ?? "ARS"} onChange={(e) => set("fee_currency", e.target.value)}>
            <option>ARS</option><option>MXN</option><option>COP</option><option>USD</option></select></div>
        <div className="field"><label className="label">Inicio de tratamiento</label>
          <input className="input" type="date" value={form.treatment_start_date ?? ""} onChange={(e) => set("treatment_start_date", e.target.value)} /></div>
      </div>
      <div className="field"><label className="label">Notas administrativas</label>
        <textarea className="textarea" value={form.notes ?? ""} onChange={(e) => set("notes", e.target.value)} /></div>
      <button className="btn" disabled={saving}>{saving ? "Guardando…" : "Guardar cambios"}</button>
    </form>
  );
}
