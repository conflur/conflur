"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import AppShell from "@/components/AppShell";
import {
  listAppointments, createAppointment, updateAppointment, cancelAppointment,
  listPatients, APPOINTMENT_STATUS,
  type Appointment, type AppointmentInput, type Patient,
} from "@/lib/conflur";
import { ApiError } from "@/lib/apiClient";

const DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"];

/** Lunes 00:00 de la semana que contiene `d` (hora local). */
function mondayOf(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const dow = (x.getDay() + 6) % 7; // 0 = lunes
  x.setDate(x.getDate() - dow);
  return x;
}
function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}
/** "YYYY-MM-DDTHH:MM:SS" en hora local, sin zona (lo que el backend espera). */
function localISO(d: Date): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}
function fmtTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
}
function fmtRange(start: Date): string {
  const end = addDays(start, 6);
  const f = (d: Date) => d.toLocaleDateString("es-AR", { day: "numeric", month: "short" });
  return `${f(start)} – ${f(end)}`;
}

export default function AgendaPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;

  const [weekStart, setWeekStart] = useState<Date>(() => mondayOf(new Date()));
  const [appts, setAppts] = useState<Appointment[] | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const patientName = useMemo(() => {
    const m = new Map(patients.map((p) => [p.id, p.full_name]));
    return (id: string) => m.get(id) ?? "Paciente";
  }, [patients]);

  async function load(t: string) {
    setError(null);
    try {
      const desde = localISO(weekStart);
      const hasta = localISO(addDays(weekStart, 7));
      const [a, p] = await Promise.all([listAppointments(t, desde, hasta), listPatients(t)]);
      setAppts(a);
      setPatients(p);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cargar la agenda");
    }
  }

  useEffect(() => {
    if (token) load(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, weekStart]);

  const byDay = useMemo(() => {
    const groups: Appointment[][] = [[], [], [], [], [], [], []];
    for (const a of appts ?? []) {
      const d = new Date(a.starts_at);
      const idx = Math.floor((new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime() - weekStart.getTime()) / 86400000);
      if (idx >= 0 && idx < 7) groups[idx].push(a);
    }
    for (const g of groups) g.sort((x, y) => x.starts_at.localeCompare(y.starts_at));
    return groups;
  }, [appts, weekStart]);

  async function changeStatus(a: Appointment, status: string) {
    if (!token) return;
    try {
      await updateAppointment(token, a.id, { status });
      await load(token);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo actualizar el turno");
    }
  }

  async function cancel(a: Appointment) {
    if (!token) return;
    if (!confirm(`¿Cancelar el turno de ${patientName(a.patient_id)}?`)) return;
    try {
      await cancelAppointment(token, a.id);
      await load(token);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "No se pudo cancelar el turno");
    }
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>Agenda</h1>
        <span className="spacer" />
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cerrar" : "Nuevo turno"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card" style={{ display: "flex", alignItems: "center", gap: "1rem" }}>
        <button className="btn btn-secondary btn-sm" onClick={() => setWeekStart((w) => addDays(w, -7))}>← Semana anterior</button>
        <strong>{fmtRange(weekStart)}</strong>
        <button className="btn btn-secondary btn-sm" onClick={() => setWeekStart((w) => addDays(w, 7))}>Semana siguiente →</button>
        <span className="spacer" />
        <button className="btn btn-secondary btn-sm" onClick={() => setWeekStart(mondayOf(new Date()))}>Hoy</button>
      </div>

      {showForm && token && (
        <NewAppointmentForm
          token={token}
          patients={patients}
          defaultDate={weekStart}
          onCreated={() => { setShowForm(false); load(token); }}
        />
      )}

      {appts === null ? (
        <div className="spinner-wrap">Cargando…</div>
      ) : (
        <div className="agenda-grid">
          {DAYS.map((label, i) => {
            const day = addDays(weekStart, i);
            return (
              <div key={label} className="card">
                <div className="section-title">
                  {label} <span className="muted small">{day.toLocaleDateString("es-AR", { day: "numeric", month: "short" })}</span>
                </div>
                {byDay[i].length === 0 ? (
                  <div className="empty small">Sin turnos</div>
                ) : (
                  byDay[i].map((a) => (
                    <div key={a.id} className={`appt-row appt-${a.status}`}>
                      <div className="appt-time">{fmtTime(a.starts_at)}</div>
                      <div className="appt-body">
                        <div>{patientName(a.patient_id)}</div>
                        <div className="muted small">
                          {a.duration_minutes} min · <span className={`badge badge-${a.status}`}>{APPOINTMENT_STATUS[a.status] ?? a.status}</span>
                          {a.session_number ? ` · sesión ${a.session_number}` : ""}
                        </div>
                      </div>
                      {a.status === "scheduled" && (
                        <div className="appt-actions">
                          <button className="btn btn-secondary btn-sm" title="Marcar realizado" onClick={() => changeStatus(a, "completed")}>✓</button>
                          <button className="btn btn-secondary btn-sm" title="No asistió" onClick={() => changeStatus(a, "no_show")}>✗</button>
                          <button className="btn btn-secondary btn-sm" title="Cancelar" onClick={() => cancel(a)}>🗑</button>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            );
          })}
        </div>
      )}
    </AppShell>
  );
}

function NewAppointmentForm({
  token, patients, defaultDate, onCreated,
}: {
  token: string;
  patients: Patient[];
  defaultDate: Date;
  onCreated: () => void;
}) {
  const [patientId, setPatientId] = useState("");
  const [datetime, setDatetime] = useState(() => {
    const d = new Date(defaultDate);
    d.setHours(9, 0, 0, 0);
    return localISO(d).slice(0, 16);
  });
  const [duration, setDuration] = useState(50);
  const [sessionNumber, setSessionNumber] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!patientId) { setError("Elegí un paciente"); return; }
    setSaving(true);
    try {
      const data: AppointmentInput = {
        patient_id: patientId,
        starts_at: `${datetime}:00`,
        duration_minutes: duration,
        session_number: sessionNumber ? Number(sessionNumber) : null,
        internal_notes: notes.trim() || null,
      };
      await createAppointment(token, data);
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo crear el turno");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="card" onSubmit={submit}>
      <div className="section-title">Nuevo turno</div>
      {error && <div className="alert alert-error">{error}</div>}
      {patients.length === 0 && <div className="alert">Cargá un paciente antes de agendar un turno.</div>}
      <div className="row">
        <div className="field">
          <label className="label">Paciente *</label>
          <select className="select" value={patientId} onChange={(e) => setPatientId(e.target.value)} required>
            <option value="">Elegir…</option>
            {patients.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
          </select>
        </div>
        <div className="field">
          <label className="label">Fecha y hora *</label>
          <input className="input" type="datetime-local" value={datetime} onChange={(e) => setDatetime(e.target.value)} required />
        </div>
      </div>
      <div className="row">
        <div className="field">
          <label className="label">Duración (min)</label>
          <input className="input" type="number" min="1" max="600" value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
        </div>
        <div className="field">
          <label className="label">N° de sesión</label>
          <input className="input" type="number" min="1" value={sessionNumber} onChange={(e) => setSessionNumber(e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label className="label">Notas internas</label>
        <input className="input" value={notes} onChange={(e) => setNotes(e.target.value)} />
      </div>
      <button className="btn" disabled={saving || patients.length === 0}>{saving ? "Guardando…" : "Crear turno"}</button>
    </form>
  );
}
