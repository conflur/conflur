"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";
import AppShell from "@/components/AppShell";
import { listPatients, createPatient, type Patient, type PatientInput } from "@/lib/conflur";
import { ApiError } from "@/lib/apiClient";

export default function PacientesPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;
  const router = useRouter();

  const [patients, setPatients] = useState<Patient[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showForm, setShowForm] = useState(false);

  async function load(t: string) {
    setError(null);
    try {
      setPatients(await listPatients(t));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudieron cargar los pacientes");
    }
  }

  useEffect(() => {
    if (token) load(token);
  }, [token]);

  const filtered = useMemo(() => {
    if (!patients) return [];
    const q = query.trim().toLowerCase();
    return q ? patients.filter((p) => p.full_name.toLowerCase().includes(q)) : patients;
  }, [patients, query]);

  return (
    <AppShell>
      <div className="page-header">
        <h1>Pacientes</h1>
        <span className="spacer" />
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cerrar" : "Nuevo paciente"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {showForm && token && (
        <NewPatientForm
          token={token}
          onCreated={(p) => {
            setShowForm(false);
            router.push(`/pacientes/${p.id}`);
          }}
        />
      )}

      <div className="card">
        <input
          className="input"
          placeholder="Buscar por nombre…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ marginBottom: "1rem", maxWidth: 320 }}
        />
        {patients === null ? (
          <div className="spinner-wrap">Cargando…</div>
        ) : filtered.length === 0 ? (
          <div className="empty">
            {patients.length === 0 ? "Todavía no cargaste pacientes." : "Sin resultados para la búsqueda."}
          </div>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Nombre</th><th>Teléfono</th><th>Email</th></tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.id} className="clickable" onClick={() => router.push(`/pacientes/${p.id}`)}>
                  <td>{p.full_name}</td>
                  <td className="muted">{p.phone ?? "—"}</td>
                  <td className="muted">{p.email ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </AppShell>
  );
}

function NewPatientForm({ token, onCreated }: { token: string; onCreated: (p: Patient) => void }) {
  const [form, setForm] = useState<PatientInput>({ full_name: "", fee_currency: "ARS" });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  function set<K extends keyof PatientInput>(k: K, v: PatientInput[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const clean: PatientInput = {
        ...form,
        full_name: form.full_name?.trim(),
        session_fee: form.session_fee ? Number(form.session_fee) : undefined,
      };
      onCreated(await createPatient(token, clean));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el paciente");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <div className="section-title">Nuevo paciente</div>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="field">
        <label className="label">Nombre completo *</label>
        <input className="input" required value={form.full_name ?? ""} onChange={(e) => set("full_name", e.target.value)} />
      </div>
      <div className="row">
        <div className="field">
          <label className="label">Teléfono</label>
          <input className="input" value={form.phone ?? ""} onChange={(e) => set("phone", e.target.value)} />
        </div>
        <div className="field">
          <label className="label">Email</label>
          <input className="input" type="email" value={form.email ?? ""} onChange={(e) => set("email", e.target.value)} />
        </div>
      </div>
      <div className="row">
        <div className="field">
          <label className="label">Honorario por sesión</label>
          <input className="input" type="number" min="0" value={form.session_fee ?? ""} onChange={(e) => set("session_fee", e.target.value as unknown as number)} />
        </div>
        <div className="field">
          <label className="label">Moneda</label>
          <select className="select" value={form.fee_currency ?? "ARS"} onChange={(e) => set("fee_currency", e.target.value)}>
            <option>ARS</option><option>MXN</option><option>COP</option><option>USD</option>
          </select>
        </div>
        <div className="field">
          <label className="label">Inicio de tratamiento</label>
          <input className="input" type="date" value={form.treatment_start_date ?? ""} onChange={(e) => set("treatment_start_date", e.target.value)} />
        </div>
      </div>
      <button className="btn" disabled={saving}>{saving ? "Guardando…" : "Crear paciente"}</button>
    </form>
  );
}
