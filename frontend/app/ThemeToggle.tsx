"use client";

import { useEffect, useState } from "react";

function SunIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={className}>
      <path d="M10 2a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1A.75.75 0 0 1 10 2ZM10 15a.75.75 0 0 1 .75.75v1a.75.75 0 0 1-1.5 0v-1A.75.75 0 0 1 10 15ZM10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM15.657 4.343a.75.75 0 0 1 0 1.061l-.708.708a.75.75 0 1 1-1.06-1.06l.707-.709a.75.75 0 0 1 1.06 0ZM6.111 13.889a.75.75 0 0 1 0 1.06l-.707.708a.75.75 0 0 1-1.061-1.06l.707-.708a.75.75 0 0 1 1.061 0ZM18 10a.75.75 0 0 1-.75.75h-1a.75.75 0 0 1 0-1.5h1A.75.75 0 0 1 18 10ZM4.75 10a.75.75 0 0 1-.75.75H3a.75.75 0 0 1 0-1.5h1a.75.75 0 0 1 .75.75ZM15.657 15.657a.75.75 0 0 1-1.06 0l-.708-.708a.75.75 0 0 1 1.06-1.06l.708.707a.75.75 0 0 1 0 1.061ZM6.111 6.111a.75.75 0 0 1-1.06 0l-.708-.707a.75.75 0 0 1 1.06-1.061l.708.708a.75.75 0 0 1 0 1.06Z" />
    </svg>
  );
}

function MoonIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={className}>
      <path d="M7.455 2.004a.75.75 0 0 1 .26.77 7 7 0 0 0 9.958 7.967.75.75 0 0 1 1.067.853A8.5 8.5 0 1 1 6.647 1.921a.75.75 0 0 1 .808.083Z" />
    </svg>
  );
}

export default function ThemeToggle() {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* ignore storage errors */
    }
  };

  return (
    <button
      onClick={toggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50 hover:text-brand-600 active:scale-95 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-brand-300"
    >
      {dark ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
    </button>
  );
}
