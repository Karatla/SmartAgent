import { useState } from "react";
import DynamicRenderer from "./DynamicRenderer";

function App() {
  const [layout, setLayout] = useState(null);
  const [data, setData] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      const res = await fetch("http://localhost:8000/ai_layout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: input }),
      });
      const json = await res.json();
      setLayout(json.layout);
      setData(json.data);
    } catch (err) {
      console.error("Error fetching layout:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-4 font-sans">
      <h1 className="text-2xl font-bold">AI Selling Dashboard</h1>
      <div className="flex space-x-2">
        <input
          className="border rounded p-2 w-80"
          placeholder="Ask something..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
        />
        <button
          onClick={handleSend}
          className="bg-blue-600 text-white px-4 py-2 rounded"
        >
          Send
        </button>
      </div>

      {loading && <p>Loading layout...</p>}

      {layout && <DynamicRenderer layout={layout} data={data} />}
    </div>
  );
}

export default App;
