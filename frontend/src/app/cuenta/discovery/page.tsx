"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import AppShell from "@/components/AppShell";
import {
  createDiscoverySession, listDiscoveryFindings,
  type DiscoverySessionOut, type DiscoveryFindingsOut,
} from "@/lib/conflur";

type Tab = "nueva" | "charlas";

export default function DiscoveryPage() {
  const { data: session } = useSession();
  const token = session?.accessToken;

  const [tab, setTab] = useState<Tab>("nueva");
  const [nombre, setNombre] = useState("");
  const [referidor, setReferidor] = useState("");
  const [genero, setGenero] = useState<"M" | "F" | null>(null);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<DiscoverySessionOut | null>(null);
  const [createError, setCreateError] = useState<string | null>(null);
  const urlInputRef = useRef<HTMLInputElement>(null);

  const [findings, setFindings] = useState<DiscoveryFindingsOut | null>(null);
  const [loadingFindings, setLoadingFindings] = useState(false);

  useEffect(() => {
    if (tab === "charlas" && token) {
      setLoadingFindings(true);
      listDiscoveryFindings(token)
        .then(setFindings)
        .catch(() => setFindings(null))
        .finally(() => setLoadingFindings(false));
    }
  }, [tab, token]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!token || !nombre.trim()) return;
    setCreating(true);
    setCreateError(null);
    setCreated(null);
    try {
      const res = await createDiscoverySession(token, nombre.trim(), referidor.trim() || undefined, genero);
      setCreated(res);
      setNombre("");
      setReferidor("");
      setGenero(null);
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Error al crear la sesión");
    } finally {
      setCreating(false);
    }
  }

  function copyUrl() {
    if (!created) return;
    navigator.clipboard.writeText(created.url);
    urlInputRef.current?.select();
  }

  return (
    <AppShell>
      <div className="page-header">
        <h1>Agente de Descubrimiento</h1>
        <p className="muted">
          Creá un link personalizado para cada profesional. El agente conduce la
          charla y guarda los hallazgos acá.
        </p>
      </div>

      <div className="tab-row">
        <button
          className={`tab-btn${tab === "nueva" ? " active" : ""}`}
          onClick={() => setTab("nueva")}
        >
          Nueva charla
        </button>
        <button
          className={`tab-btn${tab === "charlas" ? " active" : ""}`}
          onClick={() => setTab("charlas")}
        >
          Charlas y hallazgos
        </button>
      </div>

      {tab === "nueva" && (
        <div className="card" style={{ maxWidth: 520 }}>
          <h2 className="card-title">Crear link de charla</h2>
          <form onSubmit={handleCreate}>
            <div className="field">
              <label className="label">Nombre del/a profesional *</label>
              <input
                className="input"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Ej: Juan García"
                required
              />
            </div>
            <div className="field">
              <label className="label">Género (opcional)</label>
              <div className="radio-row">
                {(["M", "F", null] as const).map((g) => (
                  <label key={String(g)} className="radio-label">
                    <input
                      type="radio"
                      name="genero"
                      checked={genero === g}
                      onChange={() => setGenero(g)}
                    />
                    {g === "M" ? "Masculino" : g === "F" ? "Femenino" : "No especificar"}
                  </label>
                ))}
              </div>
            </div>
            <div className="field">
              <label className="label">¿Quién lo/a refirió? (opcional)</label>
              <input
                className="input"
                value={referidor}
                onChange={(e) => setReferidor(e.target.value)}
                placeholder="Ej: Mariana Pérez"
              />
            </div>
            {createError && <p className="error-msg">{createError}</p>}
            <button className="btn btn-primary" type="submit" disabled={creating || !nombre.trim()}>
              {creating ? "Generando…" : "Generar link"}
            </button>
          </form>

          {created && (
            <div className="created-box">
              <p className="created-label">
                ✓ Link listo para <strong>{created.nombre}</strong>. Compartilo por WhatsApp o mail:
              </p>
              <div className="url-row">
                <input
                  ref={urlInputRef}
                  className="input url-input"
                  value={created.url}
                  readOnly
                  onFocus={(e) => e.target.select()}
                />
                <button className="btn btn-secondary" onClick={copyUrl}>
                  Copiar
                </button>
              </div>
              <p className="muted small" style={{ marginTop: 8 }}>
                El primer mensaje del agente ya está generado — cuando ella abra el link, la charla
                empieza sola.
              </p>
            </div>
          )}
        </div>
      )}

      {tab === "charlas" && (
        <div>
          {loadingFindings && <p className="muted">Cargando…</p>}

          {findings && (
            <>
              {findings.market_insight && (
                <div className="card insight-card" style={{ maxWidth: 640, marginBottom: 24 }}>
                  <div className="insight-header">
                    <h2 className="card-title" style={{ margin: 0 }}>Lo que aprendimos</h2>
                    <span className="muted small">
                      Basado en {findings.market_insight.sessions_count} charlas
                    </span>
                  </div>
                  <p className="insight-narrative">{findings.market_insight.narrative}</p>
                  {findings.market_insight.insights.aprendizajes_clave.length > 0 && (
                    <ul className="aprendizajes-list">
                      {findings.market_insight.insights.aprendizajes_clave.map((a, i) => (
                        <li key={i} className="aprendizaje-item">{a}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {findings.consolidated.total_charlas > 0 && (
                <div className="card" style={{ maxWidth: 640, marginBottom: 24 }}>
                  <h2 className="card-title">Hallazgos consolidados</h2>
                  <div className="stats-row">
                    <Stat label="Charlas" value={findings.consolidated.total_charlas} />
                    <Stat label="Con interés" value={findings.consolidated.interesados} />
                    <Stat
                      label="% interés"
                      value={findings.consolidated.pct_interes != null
                        ? `${findings.consolidated.pct_interes}%`
                        : "—"}
                    />
                  </div>
                  {findings.consolidated.dolores_frecuentes.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <p className="label" style={{ marginBottom: 8 }}>Dolores más mencionados</p>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                        {findings.consolidated.dolores_frecuentes.slice(0, 8).map(([dolor, n]) => (
                          <span key={dolor} className="tag">
                            {dolor} <span className="tag-count">{n}</span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {findings.consolidated.contactos.length > 0 && (
                    <div style={{ marginTop: 16 }}>
                      <p className="label" style={{ marginBottom: 6 }}>Contactos interesados</p>
                      {findings.consolidated.contactos.map((c, i) => (
                        <p key={i} className="small muted" style={{ margin: "2px 0" }}>{c}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
                Charlas ({findings.sessions.length})
              </h2>
              {findings.sessions.length === 0 ? (
                <p className="muted">Todavía no hay charlas. Creá la primera en la pestaña "Nueva charla".</p>
              ) : (
                <div className="sessions-list">
                  {findings.sessions.map((s) => (
                    <div key={s.token} className="session-row card-sm">
                      <div className="session-info">
                        <span className="session-nombre">{s.nombre}</span>
                        {s.referidor && (
                          <span className="muted small"> · ref: {s.referidor}</span>
                        )}
                      </div>
                      <div className="session-meta">
                        <span className={`badge ${s.closed ? "badge-done" : "badge-open"}`}>
                          {s.closed ? "Cerrada" : "Abierta"}
                        </span>
                        <span className="muted small">
                          {new Date(s.created_at).toLocaleDateString("es-AR", {
                            day: "numeric", month: "short",
                          })}
                        </span>
                        <a href={s.url} target="_blank" rel="noopener" className="link-sm">
                          Ver chat
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      )}

      <style>{`
        .tab-row { display: flex; gap: 4px; margin-bottom: 24px; border-bottom: 1px solid var(--border); }
        .tab-btn { background: none; border: none; padding: 10px 18px; font-size: 14px; cursor: pointer; color: var(--muted); border-bottom: 2px solid transparent; margin-bottom: -1px; }
        .tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }
        .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 24px; }
        .card-sm { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 14px 18px; }
        .card-title { font-size: 16px; font-weight: 600; margin: 0 0 18px; }
        .field { margin-bottom: 16px; }
        .label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 6px; color: var(--text); }
        .input { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: 9px 12px; font-size: 14px; font-family: inherit; color: var(--text); background: #fff; outline: none; box-sizing: border-box; }
        .input:focus { border-color: var(--primary); }
        .radio-row { display: flex; gap: 16px; flex-wrap: wrap; }
        .radio-label { display: flex; align-items: center; gap: 6px; font-size: 14px; cursor: pointer; color: var(--text); }
        .error-msg { color: var(--danger); font-size: 13px; margin-bottom: 12px; }
        .created-box { margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border); }
        .created-label { font-size: 14px; margin-bottom: 10px; color: var(--text); }
        .url-row { display: flex; gap: 8px; }
        .url-input { font-family: monospace; font-size: 13px; }
        .stats-row { display: flex; gap: 24px; flex-wrap: wrap; }
        .stat { text-align: center; }
        .stat-value { font-size: 28px; font-weight: 700; color: var(--primary); }
        .stat-label { font-size: 12px; color: var(--muted); margin-top: 2px; }
        .tag { background: var(--primary-soft); color: var(--primary); font-size: 12px; padding: 3px 10px; border-radius: 20px; display: inline-flex; align-items: center; gap: 5px; }
        .tag-count { background: var(--primary); color: #fff; border-radius: 10px; padding: 1px 6px; font-size: 11px; }
        .sessions-list { display: flex; flex-direction: column; gap: 8px; }
        .session-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
        .session-info { display: flex; align-items: baseline; gap: 4px; }
        .session-nombre { font-weight: 500; font-size: 14px; }
        .session-meta { display: flex; align-items: center; gap: 12px; }
        .badge { font-size: 12px; padding: 2px 10px; border-radius: 12px; font-weight: 500; }
        .badge-open { background: #fff8e1; color: #b9770e; }
        .badge-done { background: var(--primary-soft); color: var(--primary); }
        .link-sm { font-size: 13px; color: var(--primary); text-decoration: none; }
        .link-sm:hover { text-decoration: underline; }
        .small { font-size: 13px; }
        .insight-card { border-color: var(--primary); background: var(--primary-soft); }
        .insight-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
        .insight-narrative { font-size: 14px; color: var(--text); line-height: 1.6; margin: 0 0 12px; }
        .aprendizajes-list { margin: 0; padding-left: 18px; }
        .aprendizaje-item { font-size: 13px; color: var(--text); margin-bottom: 4px; line-height: 1.5; }
      `}</style>
    </AppShell>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="stat">
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  );
}
