import { useEffect, useState, type FormEvent } from "react";
import { Maximize2, MessageCircle, Minus, Plus, Send, Sparkles, X } from "lucide-react";
import { createCandidateAssistantSession, fetchCandidateAssistantSession, fetchCandidateAssistantSessions, sendCandidateAssistantSessionMessage, type CandidateAssistantSession } from "../auth";

export function FloatingAssistant({ token, onExpand }: { token: string; onExpand: () => void }) {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState<CandidateAssistantSession | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open || session) return;
    let cancelled = false;
    setBusy(true);
    (async () => {
      try {
        const history = await fetchCandidateAssistantSessions(token);
        const remembered = sessionStorage.getItem("mahara-assistant-session");
        const selected = history.find((item) => item.id === remembered) ?? history[0];
        const loaded = selected ? await fetchCandidateAssistantSession(token, selected.id) : await createCandidateAssistantSession(token);
        if (!cancelled) {
          setSession(loaded);
          sessionStorage.setItem("mahara-assistant-session", loaded.id);
        }
      } catch (cause) { if (!cancelled) setError(cause instanceof Error ? cause.message : "Impossible de charger la conversation."); }
      finally { if (!cancelled) setBusy(false); }
    })();
    return () => { cancelled = true; };
  }, [open, session, token]);

  async function newChat() {
    setBusy(true); setError("");
    try { const created = await createCandidateAssistantSession(token); setSession(created); sessionStorage.setItem("mahara-assistant-session", created.id); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Impossible de créer une conversation."); }
    finally { setBusy(false); }
  }
  async function send(event: FormEvent) {
    event.preventDefault();
    if (!text.trim() || !session || busy) return;
    const content = text.trim(); setText(""); setBusy(true); setError("");
    try { setSession(await sendCandidateAssistantSessionMessage(token, session.id, content)); }
    catch (cause) { setText(content); setError(cause instanceof Error ? cause.message : "Votre message n’a pas pu être envoyé."); }
    finally { setBusy(false); }
  }

  return <div className="floating-assistant">
    {open ? <section className="floating-assistant__panel" aria-label="Assistant carrière">
      <header className="floating-assistant__header"><span className="assistant-workspace__icon"><Sparkles size={17} /></span><div><strong>Assistant carrière</strong><small>Disponible pour vous aider</small></div>
        <button className="icon-button" aria-label="Ouvrir l’espace assistant" onClick={onExpand}><Maximize2 size={16}/></button>
        <button className="icon-button" aria-label="Réduire" onClick={() => setOpen(false)}><Minus size={17}/></button>
        <button className="icon-button" aria-label="Nouvelle conversation" onClick={() => void newChat()} disabled={busy}><Plus size={17}/></button>
        <button className="icon-button" aria-label="Fermer" onClick={() => setOpen(false)}><X size={17}/></button>
      </header>
      <div className="floating-assistant__messages" aria-live="polite">{busy && !session ? <p>Chargement…</p> : session?.messages.length ? session.messages.map((m, i) => <p className={`profile-assistant__message profile-assistant__message--${m.role}`} key={`${i}-${m.role}`}>{m.content}</p>) : <p className="profile-assistant__message profile-assistant__message--assistant">Aslema ! Comment puis-je vous accompagner aujourd’hui ?</p>}{busy && session && <p className="profile-assistant__pending">L’assistant prépare sa réponse…</p>}{error && <p className="career-assistant-error" role="alert">{error}</p>}</div>
      <form className="floating-assistant__composer" onSubmit={(e) => void send(e)}><textarea aria-label="Votre message" value={text} onChange={(e) => setText(e.target.value)} placeholder="Écrivez votre message…" maxLength={3000} disabled={busy || !session}/><button className="button button--primary" aria-label="Envoyer" disabled={busy || !text.trim()}><Send size={17}/></button></form>
    </section> : <button className="floating-assistant__launcher" aria-label="Ouvrir l’assistant" onClick={() => { const remembered = sessionStorage.getItem("mahara-assistant-session"); if (remembered && session?.id !== remembered) setSession(null); setOpen(true); }}><MessageCircle size={22}/><span>Assistant</span><i aria-hidden="true"/></button>}
  </div>;
}
