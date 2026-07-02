"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Message {
  role: "assistant" | "user";
  content: string;
}

type PageState = "loading" | "chat" | "closed" | "not_found" | "error";

export default function DiscoveryPage() {
  const { token } = useParams<{ token: string }>();

  const [state, setState] = useState<PageState>("loading");
  const [nombre, setNombre] = useState("");
  const [history, setHistory] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [closing, setClosing] = useState(false);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!token) return;
    fetch(`${API_URL}/discovery/sessions/${token}`)
      .then((r) => {
        if (r.status === 404) { setState("not_found"); return null; }
        if (!r.ok) { setState("error"); return null; }
        return r.json();
      })
      .then((data) => {
        if (!data) return;
        setNombre(data.nombre);
        setHistory(data.history ?? []);
        setState(data.closed ? "closed" : "chat");
      })
      .catch(() => setState("error"));
  }, [token]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  async function handleSend() {
    const msg = input.trim();
    if (!msg || sending) return;
    setSending(true);
    setInput("");
    setHistory((h) => [...h, { role: "user", content: msg }]);

    const res = await fetch(`${API_URL}/discovery/sessions/${token}/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: msg }),
    });

    if (res.ok) {
      const data = await res.json();
      setHistory((h) => [...h, { role: "assistant", content: data.reply }]);
    }
    setSending(false);
  }

  async function handleClose() {
    if (closing) return;
    setClosing(true);
    await fetch(`${API_URL}/discovery/sessions/${token}/close`, { method: "POST" });
    setState("closed");
    setClosing(false);
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSend(); }
  }

  if (state === "loading") return <Screen><p className="dc-muted">Cargando…</p></Screen>;
  if (state === "not_found") return <Screen><p className="dc-muted">El link no existe o ya expiró.</p></Screen>;
  if (state === "error") return <Screen><p className="dc-muted">Algo salió mal. Intentá de nuevo más tarde.</p></Screen>;

  if (state === "closed") {
    return (
      <Screen>
        <div className="dc-closed">
          <div className="dc-closed-icon">✓</div>
          <h2>¡Gracias, {nombre}!</h2>
          <p>Tu charla quedó registrada. Te vamos a contactar pronto.</p>
        </div>
      </Screen>
    );
  }

  return (
    <Screen>
      <div className="dc-header">
        <span className="dc-brand">Conflur</span>
        <span className="dc-subtitle">Charla de descubrimiento</span>
      </div>

      <div className="dc-messages">
        {history.map((m, i) => (
          <div key={i} className={`dc-msg dc-msg-${m.role}`}>
            <div className="dc-bubble">{m.content}</div>
          </div>
        ))}
        {sending && (
          <div className="dc-msg dc-msg-assistant">
            <div className="dc-bubble dc-typing">…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="dc-input-row">
        <textarea
          className="dc-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Escribí tu respuesta…"
          rows={2}
          disabled={sending}
        />
        <button className="dc-send" onClick={handleSend} disabled={sending || !input.trim()}>
          Enviar
        </button>
      </div>

      {history.length >= 6 && (
        <div className="dc-footer">
          <button className="dc-end-btn" onClick={handleClose} disabled={closing}>
            {closing ? "Cerrando…" : "Terminar la conversación"}
          </button>
        </div>
      )}

      <style>{`
        .dc-screen { min-height: 100vh; background: #f6f8f9; display: flex; flex-direction: column; align-items: center; }
        .dc-inner { width: 100%; max-width: 680px; display: flex; flex-direction: column; min-height: 100vh; }
        .dc-header { padding: 18px 20px 12px; border-bottom: 1px solid #e3e8ec; display: flex; align-items: baseline; gap: 12px; background: #fff; }
        .dc-brand { font-weight: 700; font-size: 17px; color: #0e8f8a; }
        .dc-subtitle { font-size: 13px; color: #66788a; }
        .dc-messages { flex: 1; padding: 20px 16px; display: flex; flex-direction: column; gap: 14px; overflow-y: auto; }
        .dc-msg { display: flex; }
        .dc-msg-assistant { justify-content: flex-start; }
        .dc-msg-user { justify-content: flex-end; }
        .dc-bubble { max-width: 78%; padding: 11px 15px; border-radius: 16px; font-size: 15px; line-height: 1.55; white-space: pre-wrap; }
        .dc-msg-assistant .dc-bubble { background: #fff; border: 1px solid #e3e8ec; color: #1b2733; border-bottom-left-radius: 4px; }
        .dc-msg-user .dc-bubble { background: #0e8f8a; color: #fff; border-bottom-right-radius: 4px; }
        .dc-typing { color: #66788a; font-size: 20px; letter-spacing: 4px; padding: 8px 14px; }
        .dc-input-row { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #e3e8ec; background: #fff; }
        .dc-textarea { flex: 1; border: 1px solid #e3e8ec; border-radius: 10px; padding: 10px 13px; font-size: 15px; resize: none; font-family: inherit; outline: none; color: #1b2733; }
        .dc-textarea:focus { border-color: #0e8f8a; }
        .dc-send { background: #0e8f8a; color: #fff; border: none; border-radius: 10px; padding: 0 20px; font-size: 15px; font-weight: 600; cursor: pointer; }
        .dc-send:disabled { opacity: 0.4; cursor: default; }
        .dc-footer { padding: 10px 16px 18px; background: #fff; text-align: center; }
        .dc-end-btn { background: none; border: 1px solid #ccd6de; border-radius: 8px; padding: 7px 18px; font-size: 13px; color: #66788a; cursor: pointer; }
        .dc-end-btn:hover { border-color: #0e8f8a; color: #0e8f8a; }
        .dc-closed { text-align: center; padding: 60px 20px; }
        .dc-closed-icon { width: 56px; height: 56px; background: #e6f4f3; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 24px; color: #0e8f8a; margin: 0 auto 20px; }
        .dc-closed h2 { font-size: 22px; margin: 0 0 10px; }
        .dc-closed p { color: #66788a; font-size: 15px; }
        .dc-muted { color: #66788a; text-align: center; padding: 60px 20px; }
      `}</style>
    </Screen>
  );
}

function Screen({ children }: { children: React.ReactNode }) {
  return (
    <div className="dc-screen" style={{ minHeight: "100vh", background: "#f6f8f9", display: "flex", justifyContent: "center" }}>
      <div className="dc-inner" style={{ width: "100%", maxWidth: 680, display: "flex", flexDirection: "column", minHeight: "100vh" }}>
        {children}
      </div>
    </div>
  );
}
