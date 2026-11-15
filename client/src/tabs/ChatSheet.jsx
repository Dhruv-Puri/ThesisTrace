import { useEffect, useRef, useState } from "react";
import { askPaper } from "../api.js";
import MarkdownLite from "../components/MarkdownLite.jsx";
import { Icon } from "../components/ui.jsx";

export const NO_KEY_NOTICE =
  "Ask needs a Gemini key. Everything else in this analysis runs locally.";

const STARTERS = [
  "What problem does this paper solve?",
  "Which claims are actually supported?",
  "Why did it get this readiness level?",
  "What is missing to reproduce it?",
];

const MAX_HISTORY = 6;

export function useChat(jobId) {
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const live = useRef({ messages: [], pending: false });

  useEffect(() => {
    live.current = { messages: [], pending: false };
    setMessages([]);
    setPending(false);
  }, [jobId]);

  function commit(next) {
    live.current.messages = next;
    setMessages(next);
  }

  async function send(text) {
    const question = String(text || "").trim();
    if (!question || !jobId || live.current.pending) return;
    const history = live.current.messages
      .filter((message) => !message.error)
      .slice(-MAX_HISTORY)
      .map(({ role, content }) => ({ role, content }));

    commit([...live.current.messages, { role: "user", content: question }]);
    live.current.pending = true;
    setPending(true);
    try {
      const reply = await askPaper(jobId, question, history);
      commit([
        ...live.current.messages,
        {
          role: "assistant",
          content: reply.answer,
          sources: reply.sources || [],
          findings: reply.findings || [],
        },
      ]);
    } catch (error) {
      commit([
        ...live.current.messages,
        { role: "assistant", error: true, content: error.message || "The request failed." },
      ]);
    } finally {
      live.current.pending = false;
      setPending(false);
    }
  }

  function clear() {
    if (!live.current.pending) commit([]);
  }

  return { messages, pending, send, clear };
}

function Sources({ message }) {
  const sources = message.sources || [];
  const findings = message.findings || [];
  if (!sources.length && !findings.length) return null;
  return (
    <details className="chat-sources">
      <summary>
        {sources.length} passage{sources.length === 1 ? "" : "s"} retrieved
        {findings.length ? ` · ${findings.length} findings used` : ""}
      </summary>
      <ol>
        {sources.map((source) => (
          <li key={`s-${source.id}`}>
            <span className="cite">p.{source.page}</span> {source.text}
          </li>
        ))}
        {findings.map((finding) => (
          <li key={`f-${finding.id}`}>
            <span className="cite">[{finding.id}]</span> {finding.text}
          </li>
        ))}
      </ol>
    </details>
  );
}

export default function ChatSheet({ open, onClose, analysis, geminiEnabled, chat }) {
  const { messages, pending, send, clear } = chat;
  const [draft, setDraft] = useState("");
  const logRef = useRef(null);
  const jobId = analysis?.job_id || "";
  const isDemo = !jobId || jobId.startsWith("demo");

  const notice = isDemo
    ? "The sample analysis has no source document to search."
    : geminiEnabled === false
      ? NO_KEY_NOTICE
      : "";
  const disabled = Boolean(notice);

  useEffect(() => {
    function onKey(event) {
      if (event.key === "Escape") onClose();
    }
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    const node = logRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, pending, open]);

  if (!open) return null;

  function submit(event) {
    event.preventDefault();
    if (disabled || pending || !draft.trim()) return;
    send(draft);
    setDraft("");
  }

  return (
    <div
      className="sheet-backdrop"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section className="sheet" role="dialog" aria-modal="true" aria-label="Ask this paper">
        <header className="sheet-head">
          <div>
            <h2>Ask this paper</h2>
            <p className="muted">Answers cite the pages they came from.</p>
          </div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
            <Icon name="close" size={18} />
          </button>
        </header>

        {notice ? <p className="sheet-notice">{notice}</p> : null}

        <div className="chat-log" ref={logRef} aria-live="polite">
          {!messages.length && !disabled ? (
            <div className="chat-starters">
              {STARTERS.map((starter) => (
                <button
                  key={starter}
                  type="button"
                  className="chip"
                  onClick={() => send(starter)}
                  disabled={pending}
                >
                  {starter}
                </button>
              ))}
            </div>
          ) : null}

          {messages.map((message, index) => (
            <div
              key={`msg-${index}`}
              className={`chat-msg ${message.role}${message.error ? " is-error" : ""}`}
            >
              {message.role === "assistant" && !message.error ? (
                <MarkdownLite text={message.content} />
              ) : (
                <p>{message.content}</p>
              )}
              {message.role === "assistant" ? <Sources message={message} /> : null}
            </div>
          ))}

          {pending ? (
            <div className="chat-msg assistant is-pending" aria-label="Answering">
              <span className="dots" aria-hidden="true"><i /><i /><i /></span>
            </div>
          ) : null}
        </div>

        <form className="chat-form" onSubmit={submit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) submit(event);
            }}
            placeholder={disabled ? "Unavailable" : "Ask a question…"}
            rows={2}
            maxLength={1000}
            disabled={disabled}
            aria-label="Your question"
          />
          <button type="submit" className="button" disabled={disabled || pending || !draft.trim()}>
            Ask
          </button>
        </form>

        {messages.length && !disabled ? (
          <button type="button" className="text-button sheet-clear" onClick={clear} disabled={pending}>
            Clear conversation
          </button>
        ) : null}
      </section>
    </div>
  );
}
