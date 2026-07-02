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
export const NOTE_FORMATS: Record<string, string> = { libre: "Libre", soap: "SOAP" };

export const generateNote = (t: string, id: string, input_bullets: string, note_format = "libre") =>
  authedFetch<GeneratedNote>(t, `/patients/${id}/notes/generate`, {
    method: "POST", body: JSON.stringify({ input_bullets, note_format }),
  });
export const saveNote = (
  t: string, id: string,
  data: { input_bullets: string; content: string; template_type?: string; model_used?: string; tokens_used?: number; is_edited?: boolean },
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

export const APPOINTMENT_MODALITY: Record<string, string> = {
  presencial: "Presencial",
  telepsicologia: "Telepsicología",
};

export interface Appointment {
  id: string;
  tenant_id: string;
  professional_user_id: string;
  patient_id: string;
  starts_at: string;
  duration_minutes: number;
  status: string;
  modality: string;
  meeting_url: string | null;
  session_number: number | null;
  internal_notes: string | null;
  created_at: string;
  updated_at: string;
}
export interface AppointmentInput {
  patient_id: string;
  starts_at: string;
  duration_minutes?: number;
  modality?: string;
  meeting_url?: string | null;
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

// ---- finanzas ----
export const EXPENSE_TIPOS: Record<string, string> = {
  durable: "Bien durable",
  fijo: "Costo fijo",
  variable: "Costo variable",
};

export interface Expense {
  id: string;
  tenant_id: string;
  fecha: string;
  tipo: string;
  descripcion: string;
  categoria: string | null;
  monto: number;
  currency: string | null;
  payment_status: string;
  useful_life_months: number | null;
  notes: string | null;
}
export interface ExpenseInput {
  fecha: string;
  tipo: string;
  descripcion: string;
  monto: number;
  categoria?: string | null;
  useful_life_months?: number | null;
  notes?: string | null;
}

export interface Income {
  id: string;
  fecha: string;
  patient_id: string | null;
  amount: number;
  currency: string | null;
  notes: string | null;
}
export interface IncomeInput {
  fecha: string;
  amount: number;
  patient_id?: string | null;
  notes?: string | null;
}

export interface Collection {
  id: string;
  fecha: string;
  patient_id: string | null;
  amount: number;
  payment_method: string | null;
  currency: string | null;
  notes: string | null;
}
export interface CollectionInput {
  fecha: string;
  amount: number;
  patient_id?: string | null;
  payment_method?: string | null;
  notes?: string | null;
}

export interface MonthlySetting {
  year: number;
  month: number;
  planned_hours: number;
  opening_cash_balance: number;
}
export interface AnnualGoal {
  year: number;
  meta_margen_neto: number | null;
  meta_ticket_promedio: number | null;
  meta_rentabilidad_por_hora: number | null;
}

export interface Dashboard {
  year: number;
  month: number;
  estado_resultado: {
    ingresos: number; costos_variables: number; costos_fijos: number;
    resultado_neto: number; margen_neto_pct: number | null;
  };
  flujo_caja: {
    saldo_inicial: number; entradas: number; salidas: number;
    flujo_neto: number; saldo_final: number;
  };
  matriz_salud: { codigo: string; label: string; detalle: string };
  kpis: {
    atenciones: number; ticket_promedio: number | null; pct_cobro: number | null;
    costo_por_paciente: number | null; rentabilidad_por_hora: number | null;
  };
  metas: AnnualGoal | null;
  alertas: string[];
}

export const getDashboard = (t: string, year: number, month: number) =>
  authedFetch<Dashboard>(t, `/finanzas/dashboard?year=${year}&month=${month}`);

export const listExpenses = (t: string) => authedFetch<Expense[]>(t, "/finanzas/gastos");
export const createExpense = (t: string, data: ExpenseInput) =>
  authedFetch<Expense>(t, "/finanzas/gastos", { method: "POST", body: JSON.stringify(data) });
export const deleteExpense = (t: string, id: string) =>
  authedFetch<void>(t, `/finanzas/gastos/${id}`, { method: "DELETE" });

export const listIncome = (t: string) => authedFetch<Income[]>(t, "/finanzas/ingresos");
export const createIncome = (t: string, data: IncomeInput) =>
  authedFetch<Income>(t, "/finanzas/ingresos", { method: "POST", body: JSON.stringify(data) });

export const listCollections = (t: string) => authedFetch<Collection[]>(t, "/finanzas/cobros");
export const createCollection = (t: string, data: CollectionInput) =>
  authedFetch<Collection>(t, "/finanzas/cobros", { method: "POST", body: JSON.stringify(data) });

export const getMonthlySetting = (t: string, year: number, month: number) =>
  authedFetch<MonthlySetting>(t, `/finanzas/configuracion-mensual?year=${year}&month=${month}`);
export const upsertMonthlySetting = (t: string, data: MonthlySetting) =>
  authedFetch<MonthlySetting>(t, "/finanzas/configuracion-mensual", { method: "PUT", body: JSON.stringify(data) });

export const getMetas = (t: string, year: number) =>
  authedFetch<AnnualGoal>(t, `/finanzas/metas?year=${year}`);
export const upsertMetas = (t: string, data: AnnualGoal) =>
  authedFetch<AnnualGoal>(t, "/finanzas/metas", { method: "PUT", body: JSON.stringify(data) });

// ---- Discovery ---

export interface DiscoverySessionOut {
  token: string;
  url: string;
  nombre: string;
  referidor: string | null;
  history: { role: "assistant" | "user"; content: string }[];
  closed: boolean;
}

export interface DiscoverySessionSummary {
  token: string;
  nombre: string;
  referidor: string | null;
  closed: boolean;
  finding_id: string | null;
  created_at: string;
  url: string;
}

export interface DiscoveryFindingsOut {
  sessions: DiscoverySessionSummary[];
  consolidated: {
    total_charlas: number;
    interesados: number;
    pct_interes: number | null;
    dolores_frecuentes: [string, number][];
    contactos: string[];
  };
}

export const createDiscoverySession = (t: string, nombre: string, referidor?: string) =>
  authedFetch<DiscoverySessionOut>(t, "/discovery/sessions", {
    method: "POST",
    body: JSON.stringify({ nombre, referidor: referidor || null }),
  });

export const listDiscoveryFindings = (t: string) =>
  authedFetch<DiscoveryFindingsOut>(t, "/discovery/findings");

/** Formatea un monto en la moneda dada (default ARS). */
export function money(n: number | null | undefined, currency = "ARS"): string {
  if (n === null || n === undefined) return "—";
  return new Intl.NumberFormat("es-AR", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);
}
