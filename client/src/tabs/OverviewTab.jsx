import { useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { StatCard, Tag, formatNumber } from "../components/ui.jsx";

const PART_LABELS = {
  term_density: "Technical terms",
  sentence_length: "Sentence length",
  pos_mix: "Noun / adjective mix",
  references: "Reference density",
  structure: "Section structure",
  lexical_variety: "Lexical variety",
};

function SummaryPanel({ summary }) {
  const [showEli5, setShowEli5] = useState(false);
  const bullets = summary?.bullets || [];
  return (
    <section className="panel summary-panel">
      <div className="panel-head">
        <div>
          <p className="kicker">Practical 4 · summarization</p>
          <h2>Paper in three bullets</h2>
        </div>
        <Tag tone={summary?.method === "abstractive" ? "accent" : "neutral"}>
          {summary?.method || "extractive"} summary
        </Tag>
      </div>
      <ol className="bullet-list">
        {bullets.map((bullet, index) => (
          <li key={`bullet-${index}`}>
            <span className="bullet-index" aria-hidden="true">{index + 1}</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ol>
      {summary?.abstractive_supported === false ? (
        <p className="fine-print">
          The numeric check removed a generated bullet that introduced a number not present in
          the source. That is the anti-hallucination rule working, not a failure.
        </p>
      ) : null}
      {summary?.eli5 ? (
        <div className="eli5-box">
          <button
            type="button"
            className="text-button"
            onClick={() => setShowEli5((value) => !value)}
            aria-expanded={showEli5}
          >
            {showEli5 ? "Hide beginner explanation" : "Explain like I'm a beginner"}
          </button>
          {showEli5 ? <p className="eli5-text">{summary.eli5}</p> : null}
        </div>
      ) : null}
    </section>
  );
}

function ComplexityPanel({ parts }) {
  const data = Object.entries(parts || {}).map(([key, value]) => ({
    key,
    label: PART_LABELS[key] || key,
    value: Number(value) || 0,
  }));
  if (!data.length) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="kicker">Classical NLP · feature blend</p>
          <h2>Complexity profile</h2>
        </div>
        <Tag tone="neutral">0–10</Tag>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={270}>
          <RadarChart data={data} outerRadius="72%">
            <PolarGrid stroke="#ded7c9" />
            <PolarAngleAxis dataKey="label" tick={{ fill: "#5e6675", fontSize: 11 }} />
            <Radar dataKey="value" stroke="#0d6b5f" fill="#0d6b5f" fillOpacity={0.18} />
            <Tooltip
              contentStyle={{
                background: "#fffdf8",
                border: "1px solid #ddd6c8",
                borderRadius: 10,
                fontSize: 12,
              }}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <p className="fine-print">
        A transparent weighted blend of term density, sentence length, POS mix, reference
        density, section structure and lexical variety. No black box.
      </p>
    </section>
  );
}

function TokenizerPanel({ tokenization }) {
  const rows = tokenization?.tokenizers || [];
  const splits = tokenization?.term_splits || [];
  if (!rows.length) {
    return (
      <section className="panel">
        <div className="panel-head">
          <div>
            <p className="kicker">Practical 1 · tokenization study</p>
            <h2>Tokenizer comparison</h2>
          </div>
        </div>
        <p className="fine-print">
          {tokenization?.note || "Tokenizer study is disabled for this run."}
        </p>
      </section>
    );
  }
  const columns = rows.filter((row) => row.available).map((row) => row.name);
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="kicker">Practical 1 · tokenization study</p>
          <h2>How the paper shatters into tokens</h2>
        </div>
        <Tag tone="accent">BPE · WordPiece · SentencePiece</Tag>
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">Tokenizer</th>
              <th scope="col">Vocab</th>
              <th scope="col">Tokens</th>
              <th scope="col">Tokens / word</th>
              <th scope="col">OOV</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name} className={row.available ? "" : "row-muted"}>
                <td>
                  <strong>{row.name}</strong>
                  {row.model !== "builtin" ? <code className="model-id">{row.model}</code> : null}
                </td>
                <td>{row.available ? formatNumber(row.vocab_size) : "—"}</td>
                <td>{row.available ? formatNumber(row.tokens) : "—"}</td>
                <td>{row.available ? row.tokens_per_word : "—"}</td>
                <td>{row.available ? `${((row.unk_rate || 0) * 100).toFixed(1)}%` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {splits.length ? (
        <details className="inline-details">
          <summary>Technical terms per tokenizer</summary>
          <div className="table-wrap">
            <table className="data-table compact">
              <thead>
                <tr>
                  <th scope="col">Term</th>
                  {columns.slice(1).map((name) => (
                    <th scope="col" key={name}>{name}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {splits.map((row) => (
                  <tr key={row.term}>
                    <td><strong>{row.term}</strong></td>
                    {columns.slice(1).map((name) => (
                      <td key={`${row.term}-${name}`}>{row[name] ?? "—"}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
      <p className="fine-print">{tokenization.note}</p>
    </section>
  );
}

function SignalsPanel({ signals, keyTerms }) {
  const percentages = signals?.percentages || [];
  const pValues = signals?.p_values || [];
  const metrics = signals?.metric_mentions || [];
  const links = signals?.links || [];
  if (!percentages.length && !pValues.length && !metrics.length && !links.length) {
    return null;
  }
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <p className="kicker">Regex + classical extraction</p>
          <h2>What the text actually reports</h2>
        </div>
        <Tag tone="neutral">page-cited</Tag>
      </div>
      <div className="signal-grid">
        {percentages.slice(0, 4).map((item) => (
          <div className="signal" key={`pct-${item.value}-${item.page}`}>
            <strong>{item.value}</strong>
            <span className="cite">[p.{item.page}]</span>
            <p>{item.context}</p>
          </div>
        ))}
        {pValues.slice(0, 2).map((item) => (
          <div className="signal" key={`p-${item.value}-${item.page}`}>
            <strong>{item.value}</strong>
            <span className="cite">[p.{item.page}]</span>
            <p>{item.context}</p>
          </div>
        ))}
        {metrics.slice(0, 4).map((item) => (
          <div className="signal" key={`metric-${item.metric}-${item.value}-${item.page}`}>
            <strong>{item.metric} {item.value}</strong>
            <span className="cite">[p.{item.page}]</span>
            <p>{item.context}</p>
          </div>
        ))}
      </div>
      <div className="signal-footer">
        {keyTerms?.length ? (
          <p>
            <span className="inline-label">TF-IDF key terms:</span>{" "}
            {keyTerms.slice(0, 8).map((term) => term.term).join(" · ")}
          </p>
        ) : null}
        {links.length ? (
          <p>
            <span className="inline-label">Links found:</span>{" "}
            {links.slice(0, 4).map((link) => (
              <a key={link.url} href={link.url} target="_blank" rel="noreferrer">
                p.{link.page}
              </a>
            ))}
          </p>
        ) : null}
      </div>
    </section>
  );
}

export default function OverviewTab({ analysis }) {
  const stats = analysis?.stats || {};
  const summary = analysis?.summary || {};
  return (
    <div className="tab-stack">
      <div className="stat-grid">
        <StatCard
          label="Words"
          value={formatNumber(stats.words)}
          detail={`${stats.unique_words ? `${formatNumber(stats.unique_words)} unique` : "extracted text"}`}
        />
        <StatCard
          label="Reading time"
          value={`${stats.reading_minutes || 0} min`}
          detail="at 220 words / minute"
        />
        <StatCard
          label="Sections"
          value={stats.sections ?? "—"}
          detail={`${stats.figures || 0} figures · ${stats.tables || 0} tables`}
        />
        <StatCard
          label="References"
          value={stats.references ?? "—"}
          detail={`complexity ${stats.complexity_score ?? "—"}/10`}
        />
      </div>

      <SummaryPanel summary={summary} />

      <div className="grid-2">
        <ComplexityPanel parts={stats.complexity_parts} />
        <TokenizerPanel tokenization={analysis?.tokenization} />
      </div>

      <SignalsPanel signals={analysis?.signals} keyTerms={analysis?.key_terms} />

      <p className="syllabus-note">
        <span>CSR322 link</span> Practical 4 (summarization pipeline), Practical 1
        (tokenization comparison), and the Word Level / Text Classification blocks for
        TF-IDF and POS features.
      </p>
    </div>
  );
}
