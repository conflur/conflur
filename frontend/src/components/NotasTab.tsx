"use client";

import { useEffect, useState } from "react";
import {
  listNotes, generateNote, saveNote, sendNoteFeedback,
  type Note, type GeneratedNote,
} from "@/lib/conflur";
import { ApiError } from "@/lib/apiClient";

export default function NotasTab({ token, patientId }: { token: string; patientId: string }) {
  const [notes, setNotes] = useState<Note[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // estado del editor de nueva nota
  const [bullets, setBullets] = useState("");
  const [draft, setDraft] = useState("");
  const [gen, setGen] = useState<GeneratedNote | null>(null);
  const [edited, setEdited] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);

  async function load() {
    try { setNotes(await listNotes(token, patientId)); }
    catch (e) { setError(e instanceof ApiError && e.status === 404 ? "Sin acceso clínico a este paciente." : "No se pudieron cargar las notas."); }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [token, patientId]);

  async function generate() {
    setMsg(null); setGenerating(true);
    try {
      const g = await generateNote(token, patientId, bullets);
      setGen(g); setDraft(g.content); setEdited(false);
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "No se pudo generar la nota" });
    } finally { setGenerating(false); }
  }

  async function save() {
    setMsg(null); setSaving(true);
    try {
      await saveNote(token, patientId, {
        input_bullets: bullets, content: draft,
        model_used: gen?.model_used, tokens_used: gen?.tokens_used, is_edited: edited,
      });
      setBullets(""); setDraft(""); setGen(null); setEdited(false);
      setMsg({ kind: "ok", text: "Nota guardada." });
      await load();
    } catch (err) {
      setMsg({ kind: "error", text: err instanceof ApiError ? err.message : "No se pudo guardar la nota" });
    } finally { setSaving(false); }
  }

  if (error) return <div className="alert alert-error">{error}</div>;

  return (
    <>
      {msg && <div className={`alert ${msg.kind === "ok" ? "alert-ok" : "alert-error"}`}>{msg.text}</div>}

      <div className="card">
        <div className="section-title">Nueva nota de evolución</div>
        <div className="field">
          <label className="label">Apuntes de la sesión (bullets)</label>
          <textarea
            className="textarea" value={bullets} onChange={(e) => setBullets(e.target.value)}
            placeholder="Ej: paciente refiere mejoría del sueño; trabajamos exposición; tarea: registro de pensamientos"
          />
        </div>
        <button className="btn" onClick={generate} disabled={generating || !bullets.trim()}>
          {generating ? "Generando…" : "✨ Generar nota"}
        </button>

        {gen && (
          <>
            <div className="divider" />
            <div className="field">
              <label className="label">Borrador generado (revisá y editá antes de guardar)</label>
              <textarea
                className="textarea" style={{ minHeight: 180 }} value={draft}
                onChange={(e) => { setDraft(e.target.value); setEdited(true); }}
              />
              <span className="muted small">
                Modelo: {gen.model_used} · {gen.tokens_used} tokens{edited ? " · editado" : ""}
              </span>
            </div>
            <button className="btn" onClick={save} disabled={saving || !draft.trim()}>
              {saving ? "Guardando…" : "Guardar nota"}
            </button>
          </>
        )}
      </div>

      <div className="card">
        <div className="section-title">Historial de notas</div>
        {notes === null ? (
          <div className="spinner-wrap">Cargando…</div>
        ) : notes.length === 0 ? (
          <div className="empty">Todavía no hay notas para este paciente.</div>
        ) : (
          notes.map((n) => <NoteItem key={n.id} token={token} note={n} />)
        )}
      </div>
    </>
  );
}

function NoteItem({ token, note }: { token: string; note: Note }) {
  const [rated, setRated] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  async function rate(r: number) {
    setBusy(true);
    try { await sendNoteFeedback(token, note.id, r); setRated(r); }
    finally { setBusy(false); }
  }

  return (
    <div style={{ padding: "0.75rem 0", borderBottom: "1px solid var(--border)" }}>
      <div style={{ whiteSpace: "pre-wrap" }}>{note.content}</div>
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginTop: "0.5rem" }}>
        {note.is_edited && <span className="badge">editada</span>}
        <span className="spacer" style={{ flex: 1 }} />
        {rated ? (
          <span className="muted small">¡Gracias por tu feedback!</span>
        ) : (
          <>
            <span className="muted small">¿La nota refleja la sesión?</span>
            {[1, 2, 3].map((r) => (
              <button key={r} className="btn btn-secondary btn-sm" disabled={busy} onClick={() => rate(r)}>
                {r === 1 ? "👎" : r === 2 ? "👌" : "👍"}
              </button>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
