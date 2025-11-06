import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

export default function ChatSidebar({ messages = [], loading = false }) {
  const scrollRef = useRef(null);
  const [openThreads, setOpenThreads] = useState(() =>
    messages.map(() => false)
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    // Always stick to bottom as content streams in
    el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    setOpenThreads((prev) => {
      if (prev.length === messages.length) return prev;
      return messages.map((m, idx) => prev[idx] ?? false);
    });
  }, [messages]);

  const toggleThread = useCallback((index) => {
    setOpenThreads((prev) => {
      const next = prev.map((isOpen, idx) =>
        idx === index ? !isOpen : isOpen
      );
      if (!prev[index] && next[index]) {
        requestAnimationFrame(() => {
          const el = scrollRef.current;
          if (el) el.scrollTop = el.scrollHeight;
        });
      }
      return next;
    });
  }, []);

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
              <div className="prose prose-sm max-w-none">
                <ReactMarkdown>{m.content || ""}</ReactMarkdown>
              </div>
              {(Array.isArray(m.logs) && m.logs.length > 0) ||
              (Array.isArray(m.thinking) && m.thinking.length > 0) ? (
                <details
                  className="mt-2 text-[11px] text-slate-700"
                  open={openThreads[i]}
                  onClick={(event) => {
                    event.preventDefault();
                    toggleThread(i);
                  }}
                >
                  <summary className="flex cursor-pointer list-none items-center justify-between rounded bg-slate-200 px-2 py-1 text-xs font-semibold text-slate-800">
                    <span>Process</span>
                    <span className="text-[10px] uppercase">
                      {openThreads[i] ? "Collapse" : "Expand"}
                    </span>
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {(Array.isArray(m.logs) && m.logs.length > 0
                      ? m.logs
                      : (m.thinking || []).map((t) => ({ type: "thinking", text: t }))
                    ).map((entry, j) => {
                      const label =
                        entry.type === "tool"
                          ? "Tools"
                          : entry.type === "tool_result"
                          ? "Tool Result"
                          : entry.type === "model"
                          ? "Model"
                          : entry.type === "data"
                          ? "Data"
                          : "Thinking";
                      return (
                        <li key={j} className="rounded bg-slate-100 p-2">
                          <div className="font-semibold mb-0.5">{label}</div>
                          <div className="break-words">{entry.text}</div>
                        </li>
                      );
                    })}
                  </ul>
                </details>
              ) : null}
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
