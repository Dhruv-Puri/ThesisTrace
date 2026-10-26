function inline(text, keyPrefix) {
  const tokens = String(text).split(/(\*\*[^*]+\*\*|\[p\.\d+\]|_[^_]+_)/g);
  return tokens.filter(Boolean).map((token, index) => {
    const key = `${keyPrefix}-${index}`;
    if (token.startsWith("**") && token.endsWith("**")) {
      return <strong key={key}>{token.slice(2, -2)}</strong>;
    }
    if (/^\[p\.\d+\]$/.test(token)) {
      return <span className="cite" key={key}>{token}</span>;
    }
    if (token.startsWith("_") && token.endsWith("_") && token.length > 2) {
      return <em key={key}>{token.slice(1, -1)}</em>;
    }
    return <span key={key}>{token}</span>;
  });
}

export default function MarkdownLite({ text }) {
  const lines = String(text || "").split("\n");
  return (
    <div className="markdown">
      {lines.map((line, index) => {
        const key = `md-${index}`;
        if (!line.trim()) return <div className="md-gap" key={key} />;
        if (/^###\s+/.test(line)) return <h4 key={key}>{inline(line.replace(/^###\s+/, ""), key)}</h4>;
        if (/^##\s+/.test(line)) return <h3 key={key}>{inline(line.replace(/^##\s+/, ""), key)}</h3>;
        if (/^#\s+/.test(line)) return <h2 key={key}>{inline(line.replace(/^#\s+/, ""), key)}</h2>;
        if (/^---+$/.test(line.trim())) return <hr key={key} />;
        if (/^[-*]\s+/.test(line)) {
          return (
            <div className="md-li" key={key}>
              <span className="md-bullet" aria-hidden="true">•</span>
              <span>{inline(line.replace(/^[-*]\s+/, ""), key)}</span>
            </div>
          );
        }
        if (/^\d+\.\s+/.test(line)) {
          const [marker] = line.match(/^\d+\./);
          return (
            <div className="md-li" key={key}>
              <span className="md-number" aria-hidden="true">{marker}</span>
              <span>{inline(line.replace(/^\d+\.\s+/, ""), key)}</span>
            </div>
          );
        }
        return <p key={key}>{inline(line, key)}</p>;
      })}
    </div>
  );
}
