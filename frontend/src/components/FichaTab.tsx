"use client";

import { useEffect, useState } from "react";
import { getFicha, saveFicha, type FichaSchema, type FichaField } from "@/lib/conflur";
import { ApiError } from "@/lib/apiClient";

export default function FichaTab({ token, patientId }: { token: string; patientId: string }) {
  const [schema, setSchema] = useState<FichaSchema | null>(null);
  const [values, setValues] = useState<Record<string, unknown>>({});
  const [loadError, setLoadError] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getFicha(token, patientId)
      .then((f) => { setSchema(f.ficha_schema); setValues(f.values || {}); })
      .catch((e) => setLoadError(
        e instanceof ApiError && e.status === 404
          ? "No tenés acceso clínico a la ficha de este paciente."
          : "No se pudo cargar la ficha."
      ));
  }, [token, patientId]);

  function setVal(key: string, v: unknown) { setValues((prev) => ({ ...prev, [key]: v })); }

  async function save() {
    setMsg(null); setSaving(true);
    try {
      // Limpia vacíos para no enviar strings vacíos como valores.
      const clean: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(values)) {
        if (v !== "" && v !== null && v !== undefined) clean[k] = v;
      }
      const f = await saveFicha(token, patientId, clean);
      setValues(f.values || {});
      setMsg({ kind: "ok", text: "Ficha guardada." });
    } catch (err) {
      const text = err instanceof ApiError
        ? (typeof err.message === "string" ? err.message : "Datos inválidos")
        : "No se pudo guardar la ficha";
      setMsg({ kind: "error", text });
    } finally { setSaving(false); }
  }

  if (loadError) return <div className="alert alert-error">{loadError}</div>;
  if (!schema) return <div className="spinner-wrap">Cargando ficha…</div>;

  return (
    <>
      {msg && <div className={`alert ${msg.kind === "ok" ? "alert-ok" : "alert-error"}`}>{msg.text}</div>}
      {schema.sections.map((section) => (
        <div className="card" key={section.key}>
          <div className="section-title">{section.label}</div>
          {section.fields.map((field) => (
            <Field key={field.key} field={field} value={values[field.key]} onChange={(v) => setVal(field.key, v)} />
          ))}
        </div>
      ))}
      <div style={{ marginTop: "1rem" }}>
        <button className="btn" onClick={save} disabled={saving}>{saving ? "Guardando…" : "Guardar ficha"}</button>
      </div>
    </>
  );
}

function Field({ field, value, onChange }: { field: FichaField; value: unknown; onChange: (v: unknown) => void }) {
  const label = <label className="label">{field.label}{field.required ? " *" : ""}</label>;
  const v = value ?? "";

  if (field.type === "textarea") {
    return <div className="field">{label}<textarea className="textarea" value={String(v)} onChange={(e) => onChange(e.target.value)} /></div>;
  }
  if (field.type === "select") {
    return (
      <div className="field">{label}
        <select className="select" value={String(v)} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">—</option>
          {field.options?.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>
    );
  }
  if (field.type === "boolean") {
    return (
      <div className="field" style={{ flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
        <input type="checkbox" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        <span className="label" style={{ margin: 0 }}>{field.label}</span>
      </div>
    );
  }
  const inputType = field.type === "date" ? "date" : field.type === "number" ? "number" : "text";
  return (
    <div className="field">{label}
      <input
        className="input" type={inputType} value={String(v)}
        onChange={(e) => onChange(field.type === "number" ? (e.target.value === "" ? null : Number(e.target.value)) : e.target.value)}
      />
    </div>
  );
}
