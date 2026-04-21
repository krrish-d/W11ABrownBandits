"use client";

import { useEffect, useState } from "react";

const THEMES = [
  { id: "lavender", label: "Lavender", swatch: ["#e6d9f7", "#f5ede0", "#d4e8c8"] },
  { id: "ocean",    label: "Ocean",    swatch: ["#7ec8e3", "#b2e8e0", "#d6eef7"] },
  { id: "forest",   label: "Forest",   swatch: ["#6dbd8a", "#e8c97a", "#c8e8c8"] },
  { id: "slate",    label: "Slate",    swatch: ["#6b8cce", "#c4cce0", "#e0e4ee"] },
  { id: "sunset",   label: "Sunset",   swatch: ["#f4874b", "#e8778c", "#fde0d0"] },
] as const;

type ThemeId = (typeof THEMES)[number]["id"];

const STORAGE_KEY = "invoiceflow_theme";

export function ThemeSwitcher() {
  const [current, setCurrent] = useState<ThemeId>("lavender");

  useEffect(() => {
    const saved = (localStorage.getItem(STORAGE_KEY) ?? "lavender") as ThemeId;
    setCurrent(saved);
    applyTheme(saved);
  }, []);

  function applyTheme(id: ThemeId) {
    const root = document.documentElement;
    if (id === "lavender") {
      root.removeAttribute("data-theme");
    } else {
      root.setAttribute("data-theme", id);
    }
    localStorage.setItem(STORAGE_KEY, id);
  }

  function select(id: ThemeId) {
    setCurrent(id);
    applyTheme(id);
  }

  return (
    <div className="mt-4 border-t border-border pt-4">
      <p className="mb-2 px-1 text-xs font-medium text-muted-foreground uppercase tracking-wide">Theme</p>
      <div className="flex flex-wrap gap-2 px-1">
        {THEMES.map((t) => (
          <button
            key={t.id}
            type="button"
            title={t.label}
            onClick={() => select(t.id)}
            className={`group flex flex-col items-center gap-1 rounded-lg p-1 transition-all ${
              current === t.id
                ? "ring-2 ring-primary ring-offset-1"
                : "opacity-70 hover:opacity-100"
            }`}
          >
            <div className="flex overflow-hidden rounded-md">
              {t.swatch.map((color, i) => (
                <span
                  key={i}
                  style={{ background: color, width: 14, height: 14 }}
                />
              ))}
            </div>
            <span className="text-[10px] text-muted-foreground">{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
