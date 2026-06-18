"use client";

import { FormEvent, useCallback, useRef, useState } from "react";

type Role = "user" | "assistant";

type HistoryTurn = { role: Role; content: string };

type SourceItem = { source: string; excerpt: string; date?: string; type?: string };

type ChatMessage = {
  id: string;
  role: Role;
  content: string;
  sources?: SourceItem[];
};

function getApiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_URL;
  if (!base) {
    throw new Error("NEXT_PUBLIC_API_URL is not set");
  }
  return base.replace(/\/$/, "");
}

export default function HomePage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  const sendMessage = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
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
        body: JSON.stringify({ message: trimmed, history }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Request failed (${res.status})`);
      }

      const data: { answer: string; sources: SourceItem[] } = await res.json();
      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer,
        sources: data.sources ?? [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
      setTimeout(scrollToBottom, 50);
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-3xl flex-col px-4 pb-6 pt-8 sm:px-6">
      <header className="mb-6 border-b border-slate-200 pb-4">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          practi 🎓
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Ask questions about your practicum or internship. Answers use the
          knowledge base on the server.
        </p>
      </header>

      <main className="flex flex-1 flex-col gap-3 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
          {messages.length === 0 && (
            <p className="text-center text-sm text-slate-500">
              Start a conversation — for example: &ldquo;What should I do before
              day one?&rdquo;
            </p>
          )}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed shadow-sm sm:max-w-[75%] sm:text-[15px] ${
                  m.role === "user"
                    ? "bg-brand-600 text-white"
                    : "border border-slate-100 bg-slate-50 text-slate-800"
                }`}
              >
                <p className="whitespace-pre-wrap">{m.content}</p>
                {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                  <div className="mt-3 border-t border-slate-200 pt-3">
                    <p className="mb-1.5 text-xs font-medium uppercase tracking-wide text-slate-500">
                      Sources
                    </p>
                    <ul className="space-y-2">
                      {m.sources.map((s) => (
                        <li
                          key={`${m.id}-${s.source}-${s.excerpt.slice(0, 24)}`}
                          className="rounded-lg bg-white p-2 text-xs text-slate-600 ring-1 ring-slate-100"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <div className="flex min-w-0 items-center gap-2">
                              {s.type && (
                                <span className="shrink-0 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-500">
                                  {s.type}
                                </span>
                              )}
                              <span className="truncate font-medium text-slate-800">
                                {s.source}
                              </span>
                            </div>
                            {s.date && (
                              <span className="shrink-0 text-[10px] text-slate-400">
                                {s.date}
                              </span>
                            )}
                          </div>
                          {s.excerpt ? (
                            <p className="mt-1 line-clamp-3 text-slate-600">
                              {s.excerpt}
                            </p>
                          ) : null}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                <span
                  className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-brand-600"
                  aria-hidden
                />
                <span>Thinking…</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {error && (
          <div className="border-t border-red-100 bg-red-50 px-4 py-2 text-sm text-red-800">
            {error}
          </div>
        )}

        <form
          onSubmit={sendMessage}
          className="flex gap-2 border-t border-slate-100 bg-slate-50/80 p-3 sm:p-4"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your question…"
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 shadow-inner outline-none ring-brand-500/30 placeholder:text-slate-400 focus:border-brand-500 focus:ring-2"
            disabled={loading}
            autoComplete="off"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="shrink-0 rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </main>
    </div>
  );
}
