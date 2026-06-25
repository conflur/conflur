import { authedFetch } from "./apiClient";

// ---- tipos ----
export interface Patient {
  id: string;
  tenant_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  date_of_birth: string | null;
  treatment_start_date: string | null;
  session_fee: number | null;
  fee_currency: string | null;
  payment_method: string | null;
  notes: string | null;
  is_active: boolean;
}

export type PatientInput = Partial<
  Pick<Patient, "full_name" | "email" | "phone" | "date_of_birth" | "treatment_start_date" | "session_fee" | "fee_currency" | "payment_method" | "notes">
>;

export interface FichaField {
  key: string;
  label: string;
  type: "text" | "textarea" | "date" | "number" | "boolean" | "select" | "multiselect";
  required?: boolean;
  options?: string[];
}
export interface FichaSection { key: string; label: string; fields: FichaField[] }
export interface FichaSchema { version: number; sections: FichaSection[] }
export interface Ficha {
  patient_id: string;
  specialty_code: string;
  ficha_schema: FichaSchema;
  values: Record<string, unknown>;
}

export interface Note {
  id: string;
  patient_id: string;
  author_user_id: string;
  template_type: string;
  content: string;
  is_edited: boolean;
}
export interface GeneratedNote { content: string; model_used: string; tokens_used: number }

// ---- pacientes ----
export const listPatients = (t: string) => authedFetch<Patient[]>(t, "/patients");
export const getPatient = (t: string, id: string) => authedFetch<Patient>(t, `/patients/${id}`);
export const createPatient = (t: string, data: PatientInput) =>
  authedFetch<Patient>(t, "/patients", { method: "POST", body: JSON.stringify(data) });
export const updatePatient = (t: string, id: string, data: PatientInput) =>
  authedFetch<Patient>(t, `/patients/${id}`, { method: "PATCH", body: JSON.stringify(data) });

// ---- ficha ----
export const getFicha = (t: string, id: string) => authedFetch<Ficha>(t, `/patients/${id}/ficha`);
export const saveFicha = (t: string, id: string, values: Record<string, unknown>) =>
  authedFetch<Ficha>(t, `/patients/${id}/ficha`, { method: "PUT", body: JSON.stringify({ values }) });

// ---- notas ----
export const listNotes = (t: string, id: string) => authedFetch<Note[]>(t, `/patients/${id}/notes`);
export const generateNote = (t: string, id: string, input_bullets: string) =>
  authedFetch<GeneratedNote>(t, `/patients/${id}/notes/generate`, {
    method: "POST", body: JSON.stringify({ input_bullets }),
  });
export const saveNote = (
  t: string, id: string,
  data: { input_bullets: string; content: string; model_used?: string; tokens_used?: number; is_edited?: boolean },
) => authedFetch<Note>(t, `/patients/${id}/notes`, { method: "POST", body: JSON.stringify(data) });
export const sendNoteFeedback = (t: string, noteId: string, rating: number, comment?: string) =>
  authedFetch(t, `/notes/${noteId}/feedback`, { method: "POST", body: JSON.stringify({ rating, comment }) });

// ---- agenda (turnos) ----
export const APPOINTMENT_STATUS: Record<string, string> = {
  scheduled: "Agendado",
  completed: "Realizado",
  cancelled: "Cancelado",
  no_show: "No asistió",
};

export interface Appointment {
  id: string;
  tenant_id: string;
  professional_user_id: string;
  patient_id: string;
  starts_at: string;
  duration_minutes: number;
  status: string;
  session_number: number | null;
  internal_notes: string | null;
  created_at: string;
  updated_at: string;
}
export interface AppointmentInput {
  patient_id: string;
  starts_at: string;
  duration_minutes?: number;
  session_number?: number | null;
  internal_notes?: string | null;
}

export const listAppointments = (t: string, desde?: string, hasta?: string) => {
  const qs = new URLSearchParams();
  if (desde) qs.set("desde", desde);
  if (hasta) qs.set("hasta", hasta);
  const q = qs.toString();
  return authedFetch<Appointment[]>(t, `/appointments${q ? `?${q}` : ""}`);
};
export const createAppointment = (t: string, data: AppointmentInput) =>
  authedFetch<Appointment>(t, "/appointments", { method: "POST", body: JSON.stringify(data) });
export const updateAppointment = (
  t: string, id: string,
  data: Partial<{ starts_at: string; duration_minutes: number; status: string; session_number: number | null; internal_notes: string | null }>,
) => authedFetch<Appointment>(t, `/appointments/${id}`, { method: "PATCH", body: JSON.stringify(data) });
export const cancelAppointment = (t: string, id: string) =>
  authedFetch<void>(t, `/appointments/${id}`, { method: "DELETE" });
