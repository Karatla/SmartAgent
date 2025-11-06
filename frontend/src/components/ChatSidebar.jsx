import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const collectProcessEntries = (message) => {
  if (Array.isArray(message.logs) && message.logs.length > 0) {
    return message.logs;
  }
  if (Array.isArray(message.thinking) && message.thinking.length > 0) {
    return message.thinking.map((text) => ({
      type: "thinking",
      text,
      ts: message.timestamp,
    }));
  }
  return [];
};

const formatTime = (iso) => {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
};

export default function ChatSidebar({ messages = [], loading = false }) {
  const scrollRef = useRef(null);
  const [openThreads, setOpenThreads] = useState(() =>
    messages.map(() => false)
  );

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    setOpenThreads((prev) =>
      messages.map((message, idx) => {
        if (prev[idx] !== undefined) {
          return prev[idx];
        }
        const hasProcess = collectProcessEntries(message).length > 0;
        return message.role !== "user" && hasProcess;
      })
    );
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
        <div
          ref={scrollRef}
          className="message-scroll max-h-[70vh] overflow-y-auto px-4 py-3 space-y-2"
        >
          {messages.length === 0 && (
            <p className="text-sm text-slate-500">No messages yet.</p>
          )}
          {messages.map((m, i) => {
            const processEntries = collectProcessEntries(m);
            const hasProcess = processEntries.length > 0;
            const isAssistant = m.role !== "user";
            const isOpen = openThreads[i] ?? (isAssistant && hasProcess);

            return (
              <div
                key={i}
                className={
                  (m.role === "user"
                    ? "bg-blue-50 text-blue-900"
                    : "bg-slate-100 text-slate-900") +
                  " rounded-lg px-3 py-2 text-sm"
                }
              >
                <div className="mb-0.5 flex items-center justify-between text-[11px] uppercase tracking-wide opacity-70">
                  <span>{m.role === "user" ? "You" : "Assistant"}</span>
                  <span className="text-[10px] normal-case">
                    {formatTime(m.timestamp)}
                  </span>
                </div>
                <div className="prose prose-sm max-w-none">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {m.content || ""}
                  </ReactMarkdown>
                </div>
                {hasProcess ? (
                  <details
                    className="mt-2 text-[11px] text-slate-700"
                    open={isOpen}
                    onClick={(event) => {
                      event.preventDefault();
                      toggleThread(i);
                    }}
                  >
                    <summary className="flex cursor-pointer list-none items-center justify-between rounded bg-slate-200 px-2 py-1 text-xs font-semibold text-slate-800">
                      <span>Process</span>
                      <span className="text-[10px] uppercase">
                        {isOpen ? "Collapse" : "Expand"}
                      </span>
                    </summary>
                    <ul className="mt-2 space-y-1">
                      {processEntries.map((entry, j) => {
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
                            <div className="mb-0.5 flex items-center justify-between text-[11px] font-semibold">
                              <span>{label}</span>
                              <span className="text-[10px] font-normal text-slate-500">
                                {formatTime(entry.ts)}
                              </span>
                            </div>
                            <div className="prose prose-xs max-w-none">
                              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {entry.text || ""}
                              </ReactMarkdown>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </details>
                ) : null}
              </div>
            );
          })}
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
