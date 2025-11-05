import { useEffect, useRef } from "react";

export default function ChatSidebar({ messages = [], loading = false }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    // Always stick to bottom as content streams in
    el.scrollTop = el.scrollHeight;
  }, [messages, loading]);
  return (
    <aside className="w-full">
      <div className="rounded-2xl border border-slate-200 bg-white shadow-md">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">Chat History</h3>
        </div>
        <div ref={scrollRef} className="message-scroll max-h-[70vh] overflow-y-auto px-4 py-3 space-y-2">
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">No messages yet.</p>
          )}
          {messages.map((m, i) => (
            <div
              key={i}
              className={
                (m.role === "user"
                  ? "bg-blue-50 text-blue-900"
                  : "bg-slate-100 text-slate-900") +
                " rounded-lg px-3 py-2 text-sm"
              }
            >
              <div className="text-[11px] uppercase tracking-wide opacity-70 mb-0.5">
                {m.role === "user" ? "You" : "Assistant"}
              </div>
              <div className="whitespace-pre-wrap break-words">{m.content}</div>
              {Array.isArray(m.thinking) && m.thinking.length > 0 && (
                <div className="mt-2 text-[11px] text-slate-700">
                  <div className="font-semibold mb-1">Process</div>
                  <ul className="list-disc pl-4 space-y-1">
                    {m.thinking.map((t, j) => (
                      <li key={j} className="break-words">{t}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="bg-slate-50 text-slate-700 rounded-lg px-3 py-2 text-sm">
              <div className="text-[11px] uppercase tracking-wide opacity-70 mb-0.5">
                Assistant
              </div>
              <div>Thinking…</div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
