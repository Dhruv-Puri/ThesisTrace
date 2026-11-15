/**
 * Theme & UI Appearance Engine for ThesisTrace SaaS.
 * Supports independent Color Mode (Light/Dark), Interface Style (Professional/Bubbly),
 * and Coordinated Accent Palettes with live previews and local persistence.
 */

export const THEME_KEY = "thesistrace.theme.v1";

export const ACCENTS = [
  { id: "ocean", label: "Ocean Blue", color: "#2d5d8f", darkColor: "#4f88c6" },
  { id: "lavender", label: "Lavender", color: "#6355a4", darkColor: "#8c7ee0" },
  { id: "rose", label: "Rose Pink", color: "#b83b68", darkColor: "#e55f8f" },
  { id: "mint", label: "Mint Green", color: "#1f6b4f", darkColor: "#389e78" },
  { id: "peach", label: "Peach", color: "#b85b28", darkColor: "#e57e49" },
  { id: "slate", label: "Neutral Slate", color: "#475569", darkColor: "#94a3b8" },
];

export const DEFAULT_THEME = {
  mode: "light",          // "light" | "dark"
  style: "bubbly",        // "professional" | "bubbly"
  accent: "ocean",        // "ocean" | "lavender" | "rose" | "mint" | "peach" | "slate"
};

export function readStoredTheme() {
  try {
    const raw = window.localStorage.getItem(THEME_KEY);
    if (!raw) return DEFAULT_THEME;
    const parsed = JSON.parse(raw);
    return {
      mode: ["light", "dark"].includes(parsed.mode) ? parsed.mode : DEFAULT_THEME.mode,
      style: ["professional", "bubbly"].includes(parsed.style) ? parsed.style : DEFAULT_THEME.style,
      accent: ACCENTS.some((a) => a.id === parsed.accent) ? parsed.accent : DEFAULT_THEME.accent,
    };
  } catch {
    return DEFAULT_THEME;
  }
}

export function applyTheme(theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.setAttribute("data-theme", theme.mode || "light");
  root.setAttribute("data-style", theme.style || "bubbly");
  root.setAttribute("data-accent", theme.accent || "ocean");

  try {
    window.localStorage.setItem(THEME_KEY, JSON.stringify(theme));
  } catch {
    /* private browsing fallback */
  }
}
