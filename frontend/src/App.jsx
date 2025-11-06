import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import DynamicRenderer from "./DynamicRenderer";
import ChatSidebar from "./components/ChatSidebar";
import "./App.css";

const formatTime = (iso) => {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

const coerceArray = (value) => {
  if (Array.isArray(value)) return value;
  if (!value) return [];
  if (typeof value === "object") {
    const values = Object.values(value);
    const list = values.find((v) => Array.isArray(v));
    if (list) return list;
    return values;
  }
  return [];
};

const collectSources = (node, acc = new Set()) => {
  if (Array.isArray(node)) {
    node.forEach((item) => collectSources(item, acc));
    return acc;
  }
  if (node && typeof node === "object") {
    if (node.source) acc.add(node.source);
    if (Array.isArray(node.children)) {
      node.children.forEach((child) => collectSources(child, acc));
    }
  }
  return acc;
};

const normalizeDatasets = (layout, incoming, fallback) => {
  const normalized = {};
  if (Array.isArray(incoming)) {
    normalized.data = coerceArray(incoming);
  } else if (incoming && typeof incoming === "object") {
    Object.entries(incoming).forEach(([key, value]) => {
      normalized[key] = coerceArray(value);
    });
  }
  const sources = Array.from(collectSources(layout));
  const fallbackArray = coerceArray(fallback);
  if (normalized.data && sources.length === 1 && !normalized[sources[0]]) {
    normalized[sources[0]] = normalized.data;
  }
  if (fallbackArray.length) {
    if (!sources.length) {
      normalized.data = fallbackArray;
    } else if (sources.length === 1 && !normalized[sources[0]]) {
      normalized[sources[0]] = fallbackArray;
    } else if (!Object.keys(normalized).length) {
      normalized.data = fallbackArray;
    }
  }
  sources.forEach((src) => {
    if (!normalized[src]) normalized[src] = [];
  });
  if (!Object.keys(normalized).length) normalized.data = [];
  return normalized;
};

function App() {
  const [layout, setLayout] = useState(null);
  const [datasets, setDatasets] = useState({});
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const esRef = useRef(null);
  const [sessionId, setSessionId] = useState(null);
  const lastModelLog = useMemo(() => {
    for (let idx = messages.length - 1; idx >= 0; idx -= 1) {
      const entry = messages[idx];
      if (entry.role !== "assistant") continue;
      const modelLines =
        Array.isArray(entry.logs) && entry.logs.length > 0
          ? entry.logs.filter((log) => log.type === "model")
          : [];
      if (modelLines.length) {
        const last = modelLines[modelLines.length - 1];
        return {
          text: last.text || "",
          ts: last.ts || entry.timestamp,
        };
      }
    }
    return null;
  }, [messages]);

  // Initialize session and load chat history on first render
  useEffect(() => {
    let sid = localStorage.getItem("session_id");
    if (!sid) {
      try {
        sid = crypto?.randomUUID?.() || `s-${Math.random().toString(36).slice(2, 10)}`;
      } catch {
        sid = `s-${Math.random().toString(36).slice(2, 10)}`;
      }
      localStorage.setItem("session_id", sid);
    }
    setSessionId(sid);

    // Load history from backend
    fetch(`http://localhost:8000/chat_history?session_id=${encodeURIComponent(sid)}`)
      .then((r) => r.json())
      .then((json) => {
        const msgs = Array.isArray(json?.messages)
          ? json.messages
              .filter((m) => m.role === "user" || m.role === "assistant")
              .map((m) => ({
                role: m.role,
                content: m.content,
                timestamp: m.ts,
                thinking: Array.isArray(m.thinking) ? m.thinking : [],
                logs:
                  m.meta && Array.isArray(m.meta.logs)
                    ? m.meta.logs.map((log) => ({
                        ...log,
                        ts: log.ts || m.ts,
                      }))
                    : [],
              }))
          : [];
        setMessages(msgs);
      })
      .catch(() => {
        // ignore history load errors in UI
      });

    // Restore last view (layout + datasets)
    fetch(`http://localhost:8000/last_view?session_id=${encodeURIComponent(sid)}`)
      .then((r) => r.json())
      .then((json) => {
        if (json?.layout) {
          setLayout(json.layout);
          const datasetMap = normalizeDatasets(
            json.layout,
            json.datasets,
            json.data
          );
          setDatasets(datasetMap);
        }
      })
      .catch(() => {});
  }, []);

  const handleSend = async () => {
    const message = input.trim();
    if (!message) return;
    setError("");
    setLoading(true);
    setInput("");

    // Append user message to chat
    const userTimestamp = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      { role: "user", content: message, thinking: [], logs: [], timestamp: userTimestamp },
    ]);

    // Insert assistant skeleton to stream thinking lines
    const assistantTimestamp = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "Working…",
        thinking: [],
        logs: [],
        timestamp: assistantTimestamp,
      },
    ]);

    const updateLastAssistant = (updater) => {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "assistant") {
            next[i] = { ...next[i], ...updater(next[i]) };
            break;
          }
        }
        return next;
      });
    };

    const finalize = (nextLayout, normalizedDatasets) => {
      setLayout(nextLayout);
      setDatasets(normalizedDatasets);
      const title = nextLayout?.title || nextLayout?.type || "Updated the view.";
      updateLastAssistant(() => ({ content: `Showing: ${title}` }));
      setLoading(false);
    };

    const fallbackFetch = async () => {
      try {
        const res = await fetch("http://localhost:8000/ai_layout", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message, session_id: sessionId || "default" }),
        });
        const json = await res.json();
        const datasetMap = normalizeDatasets(
          json.layout,
          json.datasets,
          json.data
        );
        finalize(json.layout, datasetMap);
        // add any logs/trace we got
        const entries = Array.isArray(json?.logs)
          ? json.logs
          : Array.isArray(json?.trace)
          ? json.trace.map((t) => ({
              type: "thinking",
              text: t,
              ts: new Date().toISOString(),
            }))
          : [];
        entries.forEach((entry) => {
          updateLastAssistant((curr) => ({
            thinking:
              entry.type === "thinking"
                ? [...(curr.thinking || []), entry.text]
                : curr.thinking || [],
            logs: [
              ...(curr.logs || []),
              { ...entry, ts: entry.ts || new Date().toISOString() },
            ],
          }));
        });
      } catch (err) {
        console.error("Fallback fetch error:", err);
        setError("Streaming failed and fallback also failed. Please retry.");
        const errorSteps = [
          "Attempted streaming via /ai_layout_stream",
          "Falling back to /ai_layout",
          "Fallback failed",
        ];
        updateLastAssistant((curr) => ({
          content: "Sorry, streaming failed.",
          thinking: [...(curr.thinking || []), ...errorSteps],
          logs: [
            ...(curr.logs || []),
            ...errorSteps.map((text) => ({
              type: "thinking",
              text,
              ts: new Date().toISOString(),
            })),
          ],
        }));
        setLoading(false);
      }
    };

    try {
      // Close any previous stream
      if (esRef.current) {
        esRef.current.close();
        esRef.current = null;
      }

      const url = `http://localhost:8000/ai_layout_stream?message=${encodeURIComponent(message)}&session_id=${encodeURIComponent(sessionId || "default")}`;
      const es = new EventSource(url);
      esRef.current = es;

      es.addEventListener("thinking", (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          const line = typeof payload === "string" ? payload : payload.text || "";
          if (!line) return;
          updateLastAssistant((curr) => ({
            thinking: [...(curr.thinking || []), line],
            logs: [...(curr.logs || []), { type: "thinking", text: line, ts: new Date().toISOString() }],
          }));
        } catch (_) {
          // ignore bad lines
        }
      });
      es.addEventListener("tool", (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          const line = payload?.text || "";
          if (!line) return;
          updateLastAssistant((curr) => ({
            logs: [...(curr.logs || []), { type: "tool", text: line, ts: new Date().toISOString() }],
          }));
        } catch (_) {}
      });
      es.addEventListener("tool_result", (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          const line = payload?.text || "";
          if (!line) return;
          updateLastAssistant((curr) => ({
            logs: [...(curr.logs || []), { type: "tool_result", text: line, ts: new Date().toISOString() }],
          }));
        } catch (_) {}
      });
      es.addEventListener("model", (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          const line = payload?.text || "";
          if (!line) return;
          updateLastAssistant((curr) => ({
            logs: [...(curr.logs || []), { type: "model", text: line, ts: new Date().toISOString() }],
          }));
        } catch (_) {}
      });
      es.addEventListener("data", (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          const line = payload?.text || "";
          if (!line) return;
          updateLastAssistant((curr) => ({
            logs: [...(curr.logs || []), { type: "data", text: line, ts: new Date().toISOString() }],
          }));
        } catch (_) {}
      });

      es.addEventListener("final", (ev) => {
        try {
          const payload = JSON.parse(ev.data);
          const datasetMap = normalizeDatasets(
            payload.layout,
            payload.datasets,
            payload.data
          );
          finalize(payload.layout, datasetMap);
        } finally {
          es.close();
          esRef.current = null;
        }
      });

      es.onerror = () => {
        console.warn("EventSource error; closing and falling back.");
        try { es.close(); } catch {}
        esRef.current = null;
        // Fallback to regular fetch
        fallbackFetch();
      };
    } catch (err) {
      console.error("Stream init error:", err);
      // Fallback to regular fetch
      fallbackFetch();
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <main className="flex flex-1 justify-center px-4 py-6 lg:pr-[440px]">
        <div className="w-full max-w-6xl flex items-start">
          <div className="flex-1">
            {layout ? (
              <div className="rounded-2xl border border-slate-200 bg-white px-6 py-8 shadow-md">
                <DynamicRenderer layout={layout} datasets={datasets} />
              </div>
            ) : (
              <p className="text-base font-medium text-slate-500 text-center">
                Ask something to generate a layout.
              </p>
            )}
          </div>
        </div>
      </main>

      <footer className="px-4 pb-8 lg:pr-[440px]">
        <div className="mx-auto w-full max-w-6xl space-y-2">
          <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 shadow-sm">
            <div className="text-[11px] uppercase tracking-wide text-slate-500">
              Model Insight
            </div>
            {lastModelLog ? (
              <>
                <div className="prose prose-sm mt-1 max-w-none text-slate-800">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {lastModelLog.text}
                  </ReactMarkdown>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  {formatTime(lastModelLog.ts)}
                </p>
              </>
            ) : (
              <p className="mt-1 text-sm text-slate-500">
                No model output yet.
              </p>
            )}
          </div>
          {error && (
            <p className="text-sm font-medium text-rose-500">{error}</p>
          )}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your request..."
              className="flex-1 px-4 py-3 rounded-lg border border-gray-300 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button
              onClick={handleSend}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg transition font-medium"
            >
              {loading ? "Sending…" : "Send"}
            </button>
          </div>
        </div>
      </footer>

      {/* Fixed right sidebar */}
      <div className="hidden lg:block fixed right-0 top-0 bottom-0 w-[400px] p-4">
        <ChatSidebar messages={messages} loading={loading} />
      </div>
    </div>
  );
}

export default App;
