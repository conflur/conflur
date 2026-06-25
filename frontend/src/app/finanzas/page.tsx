"use client";

import { useEffect, useMemo, useState } from "react";
import { useSession } from "next-auth/react";
import AppShell from "@/components/AppShell";
import {
  getDashboard, listExpenses, createExpense, deleteExpense,
  listIncome, createIncome, listCollections, createCollection,
  getMonthlySetting, upsertMonthlySetting, getMetas, upsertMetas,
  listPatients, money, EXPENSE_TIPOS,
  type Dashboard, type Expense, type Income, type Collection,
  type MonthlySetting, type AnnualGoal, type Patient,
} from "@/lib/conflur";
import { ApiError } from "@/lib/apiClient";

const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
const today = new Date();

type Tab = "dashboard" | "movimientos" | "config";

export default function FinanzasPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;

  const [tab, setTab] = useState<Tab>("dashboard");
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);

  return (
    <AppShell>
      <div className="page-header">
        <h1>Finanzas</h1>
        <span className="spacer" />
        <PeriodPicker year={year} month={month} onYear={setYear} onMonth={setMonth} />
      </div>

      <div className="tabs">
        {(["dashboard", "movimientos", "config"] as Tab[]).map((t) => (
          <button key={t} className={`tab${tab === t ? " active" : ""}`} onClick={() => setTab(t)}>
            {t === "dashboard" ? "Dashboard" : t === "movimientos" ? "Movimientos" : "Configuración"}
          </button>
        ))}
      </div>

      {!token ? (
        <div className="spinner-wrap">Cargando…</div>
      ) : tab === "dashboard" ? (
        <DashboardTab token={token} year={year} month={month} />
      ) : tab === "movimientos" ? (
        <MovimientosTab token={token} />
      ) : (
        <ConfigTab token={token} year={year} month={month} />
      )}
    </AppShell>
  );
}

function PeriodPicker({ year, month, onYear, onMonth }: {
  year: number; month: number; onYear: (y: number) => void; onMonth: (m: number) => void;
}) {
  const years = [today.getFullYear() - 1, today.getFullYear(), today.getFullYear() + 1];
  return (
    <div style={{ display: "flex", gap: "0.5rem" }}>
      <select className="select" value={month} onChange={(e) => onMonth(Number(e.target.value))} style={{ width: "auto" }}>
        {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
      </select>
      <select className="select" value={year} onChange={(e) => onYear(Number(e.target.value))} style={{ width: "auto" }}>
        {years.map((y) => <option key={y} value={y}>{y}</option>)}
      </select>
    </div>
  );
}

// ----------------------------------------------------------------- dashboard -- #
function DashboardTab({ token, year, month }: { token: string; year: number; month: number }) {
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null); setError(null);
    getDashboard(token, year, month)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "No se pudo cargar el dashboard"));
  }, [token, year, month]);

  if (error) return <div className="alert alert-error">{error}</div>;
  if (!data) return <div className="spinner-wrap">Cargando…</div>;

  const { estado_resultado: er, flujo_caja: fc, kpis, matriz_salud, metas, alertas } = data;
  const pct = (n: number | null) => (n === null ? "—" : `${n.toFixed(1)}%`);

  return (
    <>
      {alertas.length > 0 && (
        <div className="alert" style={{ background: "#fbf0dc", color: "var(--warning)" }}>
          {alertas.map((a, i) => <div key={i}>⚠ {a}</div>)}
        </div>
      )}

      <div className="kpi-grid">
        <Kpi label="Atenciones" value={String(kpis.atenciones)} />
        <Kpi label="Ticket promedio" value={money(kpis.ticket_promedio)} />
        <Kpi label="% Cobrado" value={pct(kpis.pct_cobro)} />
        <Kpi label="Costo / paciente" value={money(kpis.costo_por_paciente)} />
        <Kpi label="Rentabilidad / hora" value={money(kpis.rentabilidad_por_hora)}
             tone={kpis.rentabilidad_por_hora != null ? (kpis.rentabilidad_por_hora >= 0 ? "pos" : "neg") : undefined} />
      </div>

      <div className="row">
        <div className="card" style={{ flex: 1 }}>
          <div className="section-title">Estado de Resultado <span className="muted small">(devengado)</span></div>
          <table className="table">
            <tbody>
              <Line label="Ingresos" value={money(er.ingresos)} />
              <Line label="Costos variables" value={money(-er.costos_variables)} />
              <Line label="Costos fijos" value={money(-er.costos_fijos)} />
              <Line label="Resultado neto" value={money(er.resultado_neto)} strong
                    tone={er.resultado_neto >= 0 ? "pos" : "neg"} />
              <Line label="Margen neto" value={pct(er.margen_neto_pct)} />
            </tbody>
          </table>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <div className="section-title">Flujo de Caja <span className="muted small">(percibido)</span></div>
          <table className="table">
            <tbody>
              <Line label="Saldo inicial" value={money(fc.saldo_inicial)} />
              <Line label="Entradas (cobros)" value={money(fc.entradas)} />
              <Line label="Salidas (pagos)" value={money(-fc.salidas)} />
              <Line label="Flujo neto" value={money(fc.flujo_neto)} tone={fc.flujo_neto >= 0 ? "pos" : "neg"} />
              <Line label="Saldo final" value={money(fc.saldo_final)} strong
                    tone={fc.saldo_final >= 0 ? "pos" : "neg"} />
            </tbody>
          </table>
        </div>
      </div>

      <div className="row">
        <div className="card" style={{ flex: 1 }}>
          <div className="section-title">Salud financiera</div>
          <div style={{ fontSize: "1.1rem", fontWeight: 600 }}>{matriz_salud.label}</div>
          <div className="muted">{matriz_salud.detalle}</div>
        </div>
        <div className="card" style={{ flex: 1 }}>
          <div className="section-title">Metas {year} <span className="muted small">vs. real</span></div>
          {metas ? (
            <table className="table">
              <tbody>
                <MetaLine label="Margen neto" meta={metas.meta_margen_neto} real={er.margen_neto_pct} suffix="%" higherBetter />
                <MetaLine label="Ticket promedio" meta={metas.meta_ticket_promedio} real={kpis.ticket_promedio} money higherBetter />
                <MetaLine label="Rentabilidad / hora" meta={metas.meta_rentabilidad_por_hora} real={kpis.rentabilidad_por_hora} money higherBetter />
              </tbody>
            </table>
          ) : (
            <div className="empty small">Sin metas para {year}. Cargalas en Configuración.</div>
          )}
        </div>
      </div>
    </>
  );
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: "pos" | "neg" }) {
  return (
    <div className="kpi">
      <div className="kpi-label">{label}</div>
      <div className={`kpi-value${tone ? ` ${tone}` : ""}`}>{value}</div>
    </div>
  );
}
function Line({ label, value, strong, tone }: { label: string; value: string; strong?: boolean; tone?: "pos" | "neg" }) {
  return (
    <tr>
      <td style={{ fontWeight: strong ? 600 : 400 }}>{label}</td>
      <td className={`num${tone ? ` ${tone === "pos" ? "kpi-value pos" : "kpi-value neg"}` : ""}`}
          style={{ fontWeight: strong ? 600 : 400 }}>{value}</td>
    </tr>
  );
}
function MetaLine({ label, meta, real, suffix, money: isMoney, higherBetter }: {
  label: string; meta: number | null; real: number | null; suffix?: string; money?: boolean; higherBetter?: boolean;
}) {
  const fmt = (n: number | null) => (n === null ? "—" : isMoney ? money(n) : `${n.toFixed(1)}${suffix ?? ""}`);
  const ok = meta != null && real != null ? (higherBetter ? real >= meta : real <= meta) : null;
  return (
    <tr>
      <td>{label}</td>
      <td className="num muted">{fmt(meta)}</td>
      <td className="num" style={{ color: ok === null ? undefined : ok ? "#1f7a3d" : "var(--danger)" }}>{fmt(real)}</td>
    </tr>
  );
}

// --------------------------------------------------------------- movimientos -- #
function MovimientosTab({ token }: { token: string }) {
  const [patients, setPatients] = useState<Patient[]>([]);
  useEffect(() => { listPatients(token).then(setPatients).catch(() => {}); }, [token]);
  return (
    <>
      <GastosSection token={token} />
      <IngresosSection token={token} patients={patients} />
      <CobrosSection token={token} patients={patients} />
    </>
  );
}

const todayStr = () => new Date().toISOString().slice(0, 10);

function GastosSection({ token }: { token: string }) {
  const [rows, setRows] = useState<Expense[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fecha, setFecha] = useState(todayStr());
  const [tipo, setTipo] = useState("fijo");
  const [descripcion, setDescripcion] = useState("");
  const [monto, setMonto] = useState("");
  const [vida, setVida] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => listExpenses(token).then(setRows).catch((e) => setError(e instanceof ApiError ? e.message : "Error"));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [token]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!descripcion.trim() || !monto) { setError("Completá descripción y monto"); return; }
    setSaving(true);
    try {
      await createExpense(token, {
        fecha, tipo, descripcion: descripcion.trim(), monto: Number(monto),
        useful_life_months: tipo === "durable" ? (vida ? Number(vida) : null) : null,
      });
      setDescripcion(""); setMonto(""); setVida("");
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el gasto");
    } finally { setSaving(false); }
  }

  async function remove(id: string) {
    if (!confirm("¿Eliminar este gasto?")) return;
    try { await deleteExpense(token, id); await load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : "No se pudo eliminar"); }
  }

  return (
    <div className="card">
      <div className="section-title">Gastos</div>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={add} className="row" style={{ alignItems: "flex-end" }}>
        <div className="field"><label className="label">Fecha</label>
          <input className="input" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></div>
        <div className="field"><label className="label">Tipo</label>
          <select className="select" value={tipo} onChange={(e) => setTipo(e.target.value)}>
            {Object.entries(EXPENSE_TIPOS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></div>
        <div className="field" style={{ flex: 2 }}><label className="label">Descripción</label>
          <input className="input" value={descripcion} onChange={(e) => setDescripcion(e.target.value)} /></div>
        <div className="field"><label className="label">Monto</label>
          <input className="input" type="number" min="0" value={monto} onChange={(e) => setMonto(e.target.value)} /></div>
        {tipo === "durable" && (
          <div className="field"><label className="label">Amortiz. (meses)</label>
            <input className="input" type="number" min="1" value={vida} onChange={(e) => setVida(e.target.value)} /></div>
        )}
        <button className="btn" disabled={saving}>{saving ? "…" : "Agregar"}</button>
      </form>
      {rows.length === 0 ? <div className="empty small">Sin gastos cargados.</div> : (
        <table className="table">
          <thead><tr><th>Fecha</th><th>Tipo</th><th>Descripción</th><th className="num">Monto</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="muted">{r.fecha}</td>
                <td><span className="badge">{EXPENSE_TIPOS[r.tipo] ?? r.tipo}</span></td>
                <td>{r.descripcion}</td>
                <td className="num">{money(r.monto, r.currency ?? "ARS")}</td>
                <td className="num"><button className="btn btn-secondary btn-sm" onClick={() => remove(r.id)}>🗑</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function IngresosSection({ token, patients }: { token: string; patients: Patient[] }) {
  const [rows, setRows] = useState<Income[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fecha, setFecha] = useState(todayStr());
  const [amount, setAmount] = useState("");
  const [patientId, setPatientId] = useState("");
  const [saving, setSaving] = useState(false);
  const nameOf = useMemo(() => new Map(patients.map((p) => [p.id, p.full_name])), [patients]);

  const load = () => listIncome(token).then(setRows).catch((e) => setError(e instanceof ApiError ? e.message : "Error"));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [token]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!amount) { setError("Ingresá un monto"); return; }
    setSaving(true);
    try {
      await createIncome(token, { fecha, amount: Number(amount), patient_id: patientId || null });
      setAmount(""); setPatientId("");
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "No se pudo guardar el ingreso"); }
    finally { setSaving(false); }
  }

  return (
    <div className="card">
      <div className="section-title">Ingresos <span className="muted small">(devengado)</span></div>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={add} className="row" style={{ alignItems: "flex-end" }}>
        <div className="field"><label className="label">Fecha</label>
          <input className="input" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></div>
        <div className="field" style={{ flex: 2 }}><label className="label">Paciente</label>
          <select className="select" value={patientId} onChange={(e) => setPatientId(e.target.value)}>
            <option value="">(opcional)</option>
            {patients.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
          </select></div>
        <div className="field"><label className="label">Monto</label>
          <input className="input" type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
        <button className="btn" disabled={saving}>{saving ? "…" : "Agregar"}</button>
      </form>
      {rows.length === 0 ? <div className="empty small">Sin ingresos cargados.</div> : (
        <table className="table">
          <thead><tr><th>Fecha</th><th>Paciente</th><th className="num">Monto</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="muted">{r.fecha}</td>
                <td>{r.patient_id ? nameOf.get(r.patient_id) ?? "—" : "—"}</td>
                <td className="num">{money(r.amount, r.currency ?? "ARS")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function CobrosSection({ token, patients }: { token: string; patients: Patient[] }) {
  const [rows, setRows] = useState<Collection[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fecha, setFecha] = useState(todayStr());
  const [amount, setAmount] = useState("");
  const [patientId, setPatientId] = useState("");
  const [method, setMethod] = useState("");
  const [saving, setSaving] = useState(false);
  const nameOf = useMemo(() => new Map(patients.map((p) => [p.id, p.full_name])), [patients]);

  const load = () => listCollections(token).then(setRows).catch((e) => setError(e instanceof ApiError ? e.message : "Error"));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [token]);

  async function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!amount) { setError("Ingresá un monto"); return; }
    setSaving(true);
    try {
      await createCollection(token, { fecha, amount: Number(amount), patient_id: patientId || null, payment_method: method || null });
      setAmount(""); setPatientId(""); setMethod("");
      await load();
    } catch (err) { setError(err instanceof ApiError ? err.message : "No se pudo guardar el cobro"); }
    finally { setSaving(false); }
  }

  return (
    <div className="card">
      <div className="section-title">Cobros <span className="muted small">(percibido)</span></div>
      {error && <div className="alert alert-error">{error}</div>}
      <form onSubmit={add} className="row" style={{ alignItems: "flex-end" }}>
        <div className="field"><label className="label">Fecha</label>
          <input className="input" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></div>
        <div className="field" style={{ flex: 2 }}><label className="label">Paciente</label>
          <select className="select" value={patientId} onChange={(e) => setPatientId(e.target.value)}>
            <option value="">(opcional)</option>
            {patients.map((p) => <option key={p.id} value={p.id}>{p.full_name}</option>)}
          </select></div>
        <div className="field"><label className="label">Medio</label>
          <input className="input" value={method} onChange={(e) => setMethod(e.target.value)} placeholder="efectivo…" /></div>
        <div className="field"><label className="label">Monto</label>
          <input className="input" type="number" min="0" value={amount} onChange={(e) => setAmount(e.target.value)} /></div>
        <button className="btn" disabled={saving}>{saving ? "…" : "Agregar"}</button>
      </form>
      {rows.length === 0 ? <div className="empty small">Sin cobros cargados.</div> : (
        <table className="table">
          <thead><tr><th>Fecha</th><th>Paciente</th><th>Medio</th><th className="num">Monto</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="muted">{r.fecha}</td>
                <td>{r.patient_id ? nameOf.get(r.patient_id) ?? "—" : "—"}</td>
                <td className="muted">{r.payment_method ?? "—"}</td>
                <td className="num">{money(r.amount, r.currency ?? "ARS")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ----------------------------------------------------------------- config ---- #
function ConfigTab({ token, year, month }: { token: string; year: number; month: number }) {
  const [setting, setSetting] = useState<MonthlySetting>({ year, month, planned_hours: 0, opening_cash_balance: 0 });
  const [metas, setMetas] = useState<AnnualGoal>({ year, meta_margen_neto: null, meta_ticket_promedio: null, meta_rentabilidad_por_hora: null });
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setMsg(null); setError(null);
    getMonthlySetting(token, year, month)
      .then((s) => setSetting(s))
      .catch(() => setSetting({ year, month, planned_hours: 0, opening_cash_balance: 0 }));
    getMetas(token, year)
      .then((m) => setMetas(m))
      .catch(() => setMetas({ year, meta_margen_neto: null, meta_ticket_promedio: null, meta_rentabilidad_por_hora: null }));
  }, [token, year, month]);

  async function saveSetting(e: React.FormEvent) {
    e.preventDefault(); setMsg(null); setError(null);
    try { await upsertMonthlySetting(token, { ...setting, year, month }); setMsg("Configuración del mes guardada."); }
    catch (err) { setError(err instanceof ApiError ? err.message : "No se pudo guardar"); }
  }
  async function saveMetas(e: React.FormEvent) {
    e.preventDefault(); setMsg(null); setError(null);
    try { await upsertMetas(token, { ...metas, year }); setMsg("Metas guardadas."); }
    catch (err) { setError(err instanceof ApiError ? err.message : "No se pudo guardar"); }
  }

  const numOrNull = (v: string) => (v === "" ? null : Number(v));

  return (
    <>
      {msg && <div className="alert alert-ok">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}

      <form className="card" onSubmit={saveSetting}>
        <div className="section-title">Configuración de {MONTHS[month - 1]} {year}</div>
        <div className="row">
          <div className="field"><label className="label">Horas planificadas (mes)</label>
            <input className="input" type="number" min="0" step="0.5" value={setting.planned_hours}
                   onChange={(e) => setSetting((s) => ({ ...s, planned_hours: Number(e.target.value) }))} /></div>
          <div className="field"><label className="label">Saldo de caja inicial</label>
            <input className="input" type="number" value={setting.opening_cash_balance}
                   onChange={(e) => setSetting((s) => ({ ...s, opening_cash_balance: Number(e.target.value) }))} /></div>
        </div>
        <div className="muted small" style={{ marginBottom: "0.75rem" }}>
          Las horas planificadas alimentan el costo-hora; el saldo inicial, el flujo de caja del mes.
        </div>
        <button className="btn">Guardar mes</button>
      </form>

      <form className="card" onSubmit={saveMetas}>
        <div className="section-title">Metas anuales {year}</div>
        <div className="row">
          <div className="field"><label className="label">Margen neto objetivo (%)</label>
            <input className="input" type="number" min="0" value={metas.meta_margen_neto ?? ""}
                   onChange={(e) => setMetas((m) => ({ ...m, meta_margen_neto: numOrNull(e.target.value) }))} /></div>
          <div className="field"><label className="label">Ticket promedio objetivo</label>
            <input className="input" type="number" min="0" value={metas.meta_ticket_promedio ?? ""}
                   onChange={(e) => setMetas((m) => ({ ...m, meta_ticket_promedio: numOrNull(e.target.value) }))} /></div>
          <div className="field"><label className="label">Rentabilidad/hora objetivo</label>
            <input className="input" type="number" min="0" value={metas.meta_rentabilidad_por_hora ?? ""}
                   onChange={(e) => setMetas((m) => ({ ...m, meta_rentabilidad_por_hora: numOrNull(e.target.value) }))} /></div>
        </div>
        <button className="btn">Guardar metas</button>
      </form>
    </>
  );
}
