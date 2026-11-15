import { useState } from "react";
import { Icon } from "./ui.jsx";

export default function TabHelperBanner({
  emoji = "💡",
  title = "How to use this tab",
  children,
  defaultOpen = false,
  tips = [],
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div className={`bubbly-helper-banner ${open ? "is-open" : "is-collapsed"}`}>
      <button
        type="button"
        className="bubbly-helper-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <div className="bubbly-helper-label">
          <span className="bubbly-helper-emoji">{emoji}</span>
          <span className="bubbly-helper-title">{title}</span>
          <span className="bubbly-helper-pill">{open ? "Hide guide" : "How to use"}</span>
        </div>
        <span className="bubbly-helper-chevron">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="bubbly-helper-body">
          {children && <div className="bubbly-helper-content">{children}</div>}
          {tips.length > 0 && (
            <ul className="bubbly-tips-list">
              {tips.map((tip, idx) => (
                <li key={idx}>
                  <span className="bubbly-tip-dot">✨</span>
                  <span>{tip}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
