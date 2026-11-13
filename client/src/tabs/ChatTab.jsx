import { useEffect, useRef, useState } from "react";
import { askPaper } from "../api.js";
import MarkdownLite from "../components/MarkdownLite.jsx";
import { Icon } from "../components/ui.jsx";

export const NO_KEY_NOTICE =
  "Chat is unavailable: no Gemini API key is configured. Add GEMINI_API_KEY to your .env " +
  "file and restart the app to ask questions about this paper.";

const STARTERS = [
  "What problem does this paper solve?",
  "What datasets and metrics does it use?",
  "What are the main limitations?",
  "How would I reproduce the main result?",
];

const MAX_HISTORY = 6;

/**
 * Chat state lives in the dashboard (not the tab) so switching tabs neither loses
 * the conversation nor allows a second request while one is in flight.
 */
export function useChat(jobId) {
  const [messages, setMessages] = useState([]);
  const [pending, setPending] = useState(false);
  const live = useRef({ messages: [], pending: false });

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
        { role: "assistant", content: reply.answer, sources: reply.sources || [] },
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

function Sources({ sources }) {
  if (!sources?.length) return null;
  const cited = sources.filter((source) => source.cited).length;
  return (
    <details className="chat-sources">
      <summary>
        {sources.length} passage{sources.length === 1 ? "" : "s"} retrieved · {cited} cited
      </summary>
      <ol>
        {sources.map((source) => (
          <li key={source.id} className={source.cited ? "is-cited" : ""}>
            <span className="cite">[p.{source.page}]</span>
            {source.section ? <em> {source.section}</em> : null} — {source.text}
          </li>
        ))}
      </ol>
    </details>
  );
}

export default function ChatTab({ analysis, geminiEnabled, chat }) {
  const { messages, pending, send, clear } = chat;
  const [draft, setDraft] = useState("");
  const logRef = useRef(null);

  const jobId = analysis?.job_id || "";
  const isDemo = !jobId || jobId.startsWith("demo");
  // geminiEnabled is undefined when /api/config could not be read; the server still
  // answers with the same notice in that case, so only an explicit false blocks here.
  const notice = isDemo
    ? "Chat works on papers you upload. The demo analysis has no source document to search."
    : geminiEnabled === false
      ? NO_KEY_NOTICE
      : "";
  const disabled = Boolean(notice);

  useEffect(() => {
    const node = logRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, pending]);

  function submit(event) {
    event.preventDefault();
    if (disabled || pending || !draft.trim()) return;
    send(draft);
    setDraft("");
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) submit(event);
  }

  return (
    <div className="tab-stack">
      <section className="panel chat-panel">
        <div className="panel-head">
          <div>
            <p className="kicker">Grounded Q&amp;A · retrieval first, Gemini writes the answer</p>
            <h2>Ask the paper</h2>
          </div>
          {messages.length && !disabled ? (
            <button type="button" className="button secondary" onClick={clear} disabled={pending}>
              Clear chat
            </button>
          ) : null}
        </div>

        {notice ? (
          <div className="chat-notice" role="status">
            <strong>{isDemo ? "No paper to ask about" : "Gemini API key missing"}</strong>
            <span>{notice}</span>
          </div>
        ) : null}

        <div className="chat-log" ref={logRef} aria-live="polite">
          {!messages.length && !disabled ? (
            <div className="chat-empty">
              <p>Ask anything about this paper. Answers cite the pages they came from.</p>
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
            </div>
          ) : null}

          {messages.map((message, index) => (
            <div
              key={`msg-${index}`}
              className={`chat-msg ${message.role}${message.error ? " is-error" : ""}`}
            >
              <span className="chat-role">{message.role === "user" ? "You" : "Paper Q&A"}</span>
              {message.role === "assistant" && !message.error ? (
                <MarkdownLite text={message.content} />
              ) : (
                <p className="chat-plain">{message.content}</p>
              )}
              {message.role === "assistant" ? <Sources sources={message.sources} /> : null}
            </div>
          ))}

          {pending ? (
            <div className="chat-msg assistant is-pending" aria-label="Gemini is answering">
              <span className="chat-role">Paper Q&amp;A</span>
              <span className="chat-dots" aria-hidden="true"><i /><i /><i /></span>
            </div>
          ) : null}
        </div>

        <form className="chat-form" onSubmit={submit}>
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder={disabled ? "Chat is unavailable" : "Ask a question about the paper…"}
            rows={2}
            maxLength={1000}
            disabled={disabled}
            aria-label="Your question"
          />
          <button
            type="submit"
            className="button primary"
            disabled={disabled || pending || !draft.trim()}
          >
            <Icon name="chat" size={15} /> {pending ? "Thinking…" : "Ask"}
          </button>
        </form>
      </section>

      <p className="syllabus-note">
        <span>CSR322 link</span> RAG grounding (CO5): TF-IDF retrieves passages from the
        paper, only those passages reach Gemini, and any page citation that does not match a
        retrieved passage is removed before you see it.
      </p>
    </div>
  );
}
