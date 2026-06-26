"use client";

import { KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import ThemeToggle from "./ThemeToggle";

type Role = "user" | "assistant";
type LlmProvider = "groq" | "ollama";
type HistoryTurn = { role: Role; content: string };
type SourceItem = { source: string; excerpt: string; date?: string; type?: string };
type LlmConfig = {
  default_provider: LlmProvider;
  groq_model: string;
  groq_available: boolean;
  default_ollama_model: string;
  ollama_base_url: string;
  ollama_available: boolean;
  ollama_models: string[];
};
type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  sources?: SourceItem[];
};

const PROVIDER_STORAGE_KEY = "practi:llm-provider";
const OLLAMA_MODEL_STORAGE_KEY = "practi:ollama-model";

const SUGGESTED = [
  "What documents do I need to prepare for pre-deployment?",
  "Where do I upload my weekly reports and timesheets?",
  "Do I submit my MOA for review on canvas or to BetterInternship?",
  "What do I do if the company has their own MOA template?",
];

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) throw new Error("NEXT_PUBLIC_API_URL is not set");
  return base.replace(/\/$/, "");
}

/* ── Icons ───────────────────────────────────────────────────────── */

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M15.98 1.804a1 1 0 0 0-1.96 0l-.24 1.192a1 1 0 0 1-.784.785l-1.192.238a1 1 0 0 0 0 1.962l1.192.238a1 1 0 0 1 .785.785l.238 1.192a1 1 0 0 0 1.962 0l.238-1.192a1 1 0 0 1 .785-.785l1.192-.238a1 1 0 0 0 0-1.962l-1.192-.238a1 1 0 0 1-.785-.785l-.238-1.192ZM6.949 5.684a1 1 0 0 0-1.898 0l-.683 2.051a1 1 0 0 1-.633.633l-2.051.683a1 1 0 0 0 0 1.898l2.051.684a1 1 0 0 1 .633.632l.683 2.051a1 1 0 0 0 1.898 0l.683-2.051a1 1 0 0 1 .633-.633l2.051-.683a1 1 0 0 0 0-1.898l-2.051-.683a1 1 0 0 1-.633-.633L6.95 5.684ZM13.949 13.684a1 1 0 0 0-1.898 0l-.184.551a1 1 0 0 1-.632.633l-.551.183a1 1 0 0 0 0 1.898l.551.183a1 1 0 0 1 .633.633l.183.551a1 1 0 0 0 1.898 0l.184-.551a1 1 0 0 1 .632-.633l.551-.183a1 1 0 0 0 0-1.898l-.551-.184a1 1 0 0 1-.633-.632l-.183-.551Z" />
    </svg>
  );
}

function SendIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={className}>
      <path d="M3.105 2.288a.75.75 0 0 0-.826.95l1.414 4.926A1.5 1.5 0 0 0 5.135 9.25h6.115a.75.75 0 0 1 0 1.5H5.135a1.5 1.5 0 0 0-1.442 1.086l-1.414 4.926a.75.75 0 0 0 .826.95 28.897 28.897 0 0 0 15.293-7.154.75.75 0 0 0 0-1.115A28.897 28.897 0 0 0 3.105 2.288Z" />
    </svg>
  );
}

function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={className}>
      <path fillRule="evenodd" d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
    </svg>
  );
}

function ChevronLeftIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className={className}>
      <path fillRule="evenodd" d="M12.79 5.23a.75.75 0 0 1 0 1.06L9.06 10l3.73 3.71a.75.75 0 1 1-1.06 1.06l-4.25-4.24a.75.75 0 0 1 0-1.06l4.25-4.24a.75.75 0 0 1 1.06 0Z" clipRule="evenodd" />
    </svg>
  );
}

/* ── Sub-components ──────────────────────────────────────────────── */

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 py-0.5">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-brand-400 animate-dot-bounce"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </div>
  );
}

function SourceCard({ source, msgId }: { source: SourceItem; msgId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      key={`${msgId}-${source.source}`}
      onClick={() => setOpen((v) => !v)}
      className="w-full text-left rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-xs shadow-sm transition hover:border-brand-300 hover:bg-brand-50/60 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-brand-500 dark:hover:bg-slate-700"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-brand-100 text-brand-600">
            <svg viewBox="0 0 16 16" fill="currentColor" className="h-3 w-3">
              <path d="M7 3.5A1.5 1.5 0 0 1 8.5 2h1.879a1.5 1.5 0 0 1 1.06.44l1.122 1.12A1.5 1.5 0 0 1 13 4.622V12.5a1.5 1.5 0 0 1-1.5 1.5h-8A1.5 1.5 0 0 1 2 12.5v-9A1.5 1.5 0 0 1 3.5 2H5A1.5 1.5 0 0 1 6.5 3.5v.5H7v-.5Z" />
            </svg>
          </span>
          {source.type && (
            <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-500 dark:bg-slate-700 dark:text-slate-300">
              {source.type}
            </span>
          )}
          <span className="font-medium text-slate-700 truncate dark:text-slate-200">{source.source}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {source.date && (
            <span className="text-[10px] text-slate-400">{source.date}</span>
          )}
          <ChevronDownIcon
            className={`h-3.5 w-3.5 text-slate-400 transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          />
        </div>
      </div>
      {open && source.excerpt && (
        <p className="mt-2.5 border-t border-slate-100 pt-2.5 text-slate-500 leading-relaxed line-clamp-4 dark:border-slate-700 dark:text-slate-400">
          {source.excerpt}
        </p>
      )}
    </button>
  );
}

function BotAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-brand-500 to-brand-800 shadow-md shadow-brand-200 mt-0.5">
      <SparklesIcon className="h-4 w-4 text-white" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-700 text-white text-[11px] font-bold shadow-sm mt-0.5">
      You
    </div>
  );
}

function Message({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 animate-fade-up ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {isUser ? <UserAvatar /> : <BotAvatar />}

      <div className={`flex max-w-[78%] flex-col gap-2.5 ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
            isUser
              ? "rounded-tr-sm bg-gradient-to-br from-brand-600 to-brand-700 text-white"
              : "rounded-tl-sm border border-slate-100 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          }`}
        >
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>

        {!isUser && msg.sources && msg.sources.length > 0 && (
          <div className="w-full space-y-1.5">
            <p className="px-1 text-[10px] font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500">
              Sources
            </p>
            {msg.sources.map((s) => (
              <SourceCard key={`${msg.id}-${s.source}`} source={s} msgId={msg.id} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function LlmSettingsPanel({
  collapsed,
  llmConfig,
  llmProvider,
  ollamaModel,
  onProviderChange,
  onOllamaModelChange,
}: {
  collapsed: boolean;
  llmConfig: LlmConfig | null;
  llmProvider: LlmProvider;
  ollamaModel: string;
  onProviderChange: (provider: LlmProvider) => void;
  onOllamaModelChange: (model: string) => void;
}) {
  if (collapsed) return null;

  const groqLabel = llmConfig?.groq_model ?? "Groq";
  const modelOptions = llmConfig?.ollama_models.length
    ? llmConfig.ollama_models
    : llmConfig?.default_ollama_model
      ? [llmConfig.default_ollama_model]
      : [];

  return (
    <div className="space-y-3 border-t border-white/10 px-3 py-4">
      <p className="px-2 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        Model
      </p>

      <div className="grid grid-cols-2 gap-2">
        <button
          type="button"
          onClick={() => onProviderChange("groq")}
          disabled={llmConfig !== null && !llmConfig.groq_available}
          className={`rounded-lg px-2.5 py-2 text-[12px] font-medium transition ${
            llmProvider === "groq"
              ? "bg-white/15 text-white"
              : "text-slate-400 hover:bg-white/8 hover:text-white"
          } disabled:cursor-not-allowed disabled:opacity-40`}
        >
          Cloud
        </button>
        <button
          type="button"
          onClick={() => onProviderChange("ollama")}
          className={`rounded-lg px-2.5 py-2 text-[12px] font-medium transition ${
            llmProvider === "ollama"
              ? "bg-white/15 text-white"
              : "text-slate-400 hover:bg-white/8 hover:text-white"
          }`}
        >
          Local
        </button>
      </div>

      {llmProvider === "groq" ? (
        <p className="px-2 text-[11px] text-slate-400 leading-relaxed">
          Using <span className="text-slate-200">{groqLabel}</span> via Groq.
        </p>
      ) : (
        <div className="space-y-2">
          <label className="block px-2 text-[11px] text-slate-400" htmlFor="ollama-model">
            Ollama model
          </label>
          {modelOptions.length > 0 ? (
            <select
              id="ollama-model"
              value={ollamaModel}
              onChange={(e) => onOllamaModelChange(e.target.value)}
              className="w-full rounded-lg border border-white/10 bg-white/5 px-2.5 py-2 text-[12px] text-slate-100 outline-none transition focus:border-brand-400"
            >
              {modelOptions.map((model) => (
                <option key={model} value={model} className="text-slate-900">
                  {model}
                </option>
              ))}
            </select>
          ) : (
            <input
              id="ollama-model"
              value={ollamaModel}
              onChange={(e) => onOllamaModelChange(e.target.value)}
              placeholder="llama3.1:8b"
              className="w-full rounded-lg border border-white/10 bg-white/5 px-2.5 py-2 text-[12px] text-slate-100 placeholder:text-slate-500 outline-none transition focus:border-brand-400"
            />
          )}
          {llmConfig && !llmConfig.ollama_available && (
            <p className="px-2 text-[10px] text-amber-300/90 leading-relaxed">
              Ollama not detected. Start Ollama locally or enter a model name manually.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────── */

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [collapsed, setCollapsed] = useState(false);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [llmConfig, setLlmConfig] = useState<LlmConfig | null>(null);
  const [llmProvider, setLlmProvider] = useState<LlmProvider>("groq");
  const [ollamaModel, setOllamaModel] = useState("llama3.1:8b");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const storedProvider = localStorage.getItem(PROVIDER_STORAGE_KEY);
    const storedModel = localStorage.getItem(OLLAMA_MODEL_STORAGE_KEY);
    if (storedProvider === "groq" || storedProvider === "ollama") {
      setLlmProvider(storedProvider);
    }
    if (storedModel) {
      setOllamaModel(storedModel);
    }

    fetch(`${getApiBase()}/api/llm/config`)
      .then(async (res) => {
        if (!res.ok) throw new Error("Failed to load model config");
        return res.json() as Promise<LlmConfig>;
      })
      .then((config) => {
        setLlmConfig(config);
        const savedProvider = localStorage.getItem(PROVIDER_STORAGE_KEY) as LlmProvider | null;
        if (!savedProvider) {
          setLlmProvider(config.default_provider);
        } else if (savedProvider === "groq" && !config.groq_available) {
          setLlmProvider("ollama");
        }
        const savedModel = localStorage.getItem(OLLAMA_MODEL_STORAGE_KEY);
        if (!savedModel) {
          setOllamaModel(config.default_ollama_model);
        } else if (
          config.ollama_models.length > 0 &&
          !config.ollama_models.includes(savedModel)
        ) {
          setOllamaModel(config.default_ollama_model);
        }
      })
      .catch(() => {
        // Keep local defaults if config endpoint is unavailable.
      });
  }, []);

  const handleProviderChange = useCallback((provider: LlmProvider) => {
    setLlmProvider(provider);
    localStorage.setItem(PROVIDER_STORAGE_KEY, provider);
  }, []);

  const handleOllamaModelChange = useCallback((model: string) => {
    setOllamaModel(model);
    localStorage.setItem(OLLAMA_MODEL_STORAGE_KEY, model);
  }, []);

  const activeModelLabel =
    llmProvider === "ollama"
      ? ollamaModel
      : llmConfig?.groq_model ?? "Groq";

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const resetTextareaHeight = () => {
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;

      setError(null);
      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: trimmed,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      resetTextareaHeight();
      setLoading(true);
      requestAnimationFrame(scrollToBottom);

      const history: HistoryTurn[] = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      try {
        const res = await fetch(`${getApiBase()}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            history,
            query_date: new Date().toISOString().slice(0, 10),
            llm_provider: llmProvider,
            ollama_model: llmProvider === "ollama" ? ollamaModel : undefined,
          }),
        });
        if (!res.ok) {
          const t = await res.text();
          throw new Error(t || `Request failed (${res.status})`);
        }
        const data: { answer: string; sources: SourceItem[] } = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: data.answer,
            sources: data.sources ?? [],
          },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Something went wrong");
      } finally {
        setLoading(false);
        setTimeout(scrollToBottom, 50);
      }
    },
    [loading, messages, scrollToBottom, llmProvider, ollamaModel],
  );

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  };

  const handleTextareaInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  const isEmpty = messages.length === 0 && !loading;

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950">

      {/* ── Sidebar ── */}
      <aside
        className={`hidden md:flex flex-col bg-brand-800 text-white shrink-0 transition-[width] duration-200 ${
          collapsed ? "w-16" : "w-60"
        }`}
      >
        {/* Brand */}
        <div
          className={`flex items-center border-b border-white/10 py-5 ${
            collapsed ? "justify-center px-2" : "gap-3 px-5"
          }`}
        >
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-800 shadow-lg shadow-brand-900/40">
            <SparklesIcon className="h-5 w-5 text-white" />
          </div>
          {!collapsed && (
            <>
              <div className="leading-tight flex-1 min-w-0">
                <p className="font-semibold text-white text-sm tracking-tight">Practi</p>
                <p className="text-[11px] text-slate-400">Internship Assistant</p>
              </div>
              <button
                onClick={() => setCollapsed(true)}
                aria-label="Collapse sidebar"
                title="Collapse sidebar"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-slate-300 transition hover:bg-white/10 hover:text-white"
              >
                <ChevronLeftIcon className="h-4 w-4" />
              </button>
            </>
          )}
        </div>

        {/* Expand button (collapsed only) */}
        {collapsed && (
          <div className="flex justify-center border-b border-white/10 py-2">
            <button
              onClick={() => setCollapsed(false)}
              aria-label="Expand sidebar"
              title="Expand sidebar"
              className="flex h-7 w-7 items-center justify-center rounded-lg text-slate-300 transition hover:bg-white/10 hover:text-white"
            >
              <ChevronLeftIcon className="h-4 w-4 rotate-180" />
            </button>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto">
          <LlmSettingsPanel
            collapsed={collapsed}
            llmConfig={llmConfig}
            llmProvider={llmProvider}
            ollamaModel={ollamaModel}
            onProviderChange={handleProviderChange}
            onOllamaModelChange={handleOllamaModelChange}
          />
        </nav>

        {/* Footer */}
        {!collapsed && (
          <div className="border-t border-white/10 px-5 py-4 space-y-0.5">
            <p className="text-[11px] text-slate-500">Powered by</p>
            <p className="text-[12px] font-medium text-slate-300">
              {llmProvider === "ollama" ? "Ollama" : "Groq"} · {activeModelLabel} · ChromaDB
            </p>
          </div>
        )}
      </aside>

      {/* ── Main area ── */}
      <div className="flex flex-1 flex-col min-w-0">

        {/* Top bar */}
        <header className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3.5 shadow-sm shrink-0 dark:border-slate-800 dark:bg-slate-900">
          <div className="flex items-center gap-3">
            {/* Mobile logo */}
            <div className="md:hidden flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-brand-800 shrink-0">
              <SparklesIcon className="h-4 w-4 text-white" />
            </div>
            <div>
              <p className="font-semibold text-slate-800 text-sm leading-tight dark:text-slate-100">Practicum AI Assistant</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <span className="text-[11px] text-slate-500 dark:text-slate-400">Online · Knowledge base active</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="md:hidden">
              <select
                value={llmProvider}
                onChange={(e) => handleProviderChange(e.target.value as LlmProvider)}
                className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
              >
                <option value="groq">Cloud</option>
                <option value="ollama">Local</option>
              </select>
            </div>
            {llmProvider === "ollama" && (
              <div className="md:hidden">
                <select
                  value={ollamaModel}
                  onChange={(e) => handleOllamaModelChange(e.target.value)}
                  className="max-w-[9rem] rounded-lg border border-slate-200 bg-white px-2 py-1 text-[11px] text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
                >
                  {(llmConfig?.ollama_models.length
                    ? llmConfig.ollama_models
                    : [ollamaModel]
                  ).map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
              </div>
            )}
            <ThemeToggle />
          </div>
        </header>

        {/* Messages */}
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">

            {isEmpty ? (
              /* Empty state */
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-800 shadow-lg shadow-brand-200 mb-5">
                  <SparklesIcon className="h-8 w-8 text-white" />
                </div>
                <h2 className="text-xl font-semibold text-slate-800 mb-1.5 dark:text-slate-100">
                  Hi, I&apos;m Practi
                </h2>
                <p className="text-sm text-slate-500 max-w-xs leading-relaxed mb-8 dark:text-slate-400">
                  Ask me anything about practicum without having to contact your coordinator directly.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
                  {SUGGESTED.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="rounded-xl border border-slate-200 bg-white p-3.5 text-left text-sm text-slate-600 shadow-sm transition hover:border-brand-300 hover:bg-brand-50 hover:text-brand-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-brand-500 dark:hover:bg-slate-700 dark:hover:text-brand-200"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                {messages.map((m) => (
                  <Message key={m.id} msg={m} />
                ))}

                {loading && (
                  <div className="flex gap-3 animate-fade-up">
                    <BotAvatar />
                    <div className="rounded-2xl rounded-tl-sm border border-slate-100 bg-white px-4 py-3.5 shadow-sm dark:border-slate-700 dark:bg-slate-800">
                      <TypingDots />
                    </div>
                  </div>
                )}
              </>
            )}

            <div ref={bottomRef} />
          </div>
        </main>

        {/* Error bar */}
        {error && (
          <div className="flex items-center gap-2 border-t border-red-100 bg-red-50 px-5 py-2.5 text-sm text-red-700 shrink-0">
            <svg viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4 shrink-0 text-red-500">
              <path fillRule="evenodd" d="M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0zm-8-5a.75.75 0 0 1 .75.75v4.5a.75.75 0 0 1-1.5 0v-4.5A.75.75 0 0 1 10 5zm0 10a1 1 0 1 0 0-2 1 1 0 0 0 0 2z" clipRule="evenodd" />
            </svg>
            {error}
          </div>
        )}

        {/* Input bar */}
        <div className="border-t border-slate-200 bg-white px-4 py-4 sm:px-6 shrink-0 dark:border-slate-800 dark:bg-slate-900">
          <div className="mx-auto max-w-2xl">
            <div className="flex items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 shadow-sm transition focus-within:border-brand-400 focus-within:ring-2 focus-within:ring-brand-400/20 dark:border-slate-700 dark:bg-slate-800">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onInput={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your internship…"
                rows={1}
                disabled={loading}
                className="flex-1 resize-none bg-transparent text-sm text-slate-900 placeholder:text-slate-400 outline-none max-h-40 leading-relaxed dark:text-slate-100 dark:placeholder:text-slate-500"
              />
              <button
                onClick={() => send(input)}
                disabled={loading || !input.trim()}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-600 text-white shadow-sm transition hover:bg-brand-700 active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <SendIcon className="h-4 w-4" />
              </button>
            </div>
            <p className="mt-2 text-center text-[11px] text-slate-400 dark:text-slate-500">
              Enter to send &middot; Shift+Enter for new line
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
