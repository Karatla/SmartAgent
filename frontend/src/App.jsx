import { useState } from "react";
import DynamicRenderer from "./DynamicRenderer";

function App() {
  const [layout, setLayout] = useState(null);
  const [data, setData] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSend = async () => {
    const message = input.trim();
    if (!message) return;
    setError("");
    setLoading(true);
    setInput("");

    try {
      const res = await fetch("http://localhost:8000/ai_layout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
      });
      const json = await res.json();
      setLayout(json.layout);
      setData(json.data);
    } catch (err) {
      console.error("Error fetching layout:", err);
      setError("I ran into an issue generating the layout. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <main className="flex flex-1 items-center justify-center px-4">
        <div className="w-full max-w-3xl text-center">
          {layout ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-6 py-8 shadow-md">
              <DynamicRenderer layout={layout} data={data} />
            </div>
          ) : (
            <p className="text-base font-medium text-slate-500">
              Ask something to generate a layout.
            </p>
          )}
        </div>
      </main>

      <footer className="px-4 pb-8">
        <div className="mx-auto w-full max-w-3xl space-y-2">
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
    </div>
  );
}

export default App;
