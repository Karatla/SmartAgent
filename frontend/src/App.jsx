import { useState, useRef, useEffect } from "react";
import DynamicRenderer from "./DynamicRenderer";

function App() {
  const [layout, setLayout] = useState(null);
  const [data, setData] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setLoading(true);
    setInput("");

    try {
      const res = await fetch("http://localhost:8000/ai_layout", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: userMessage.content }),
      });
      const json = await res.json();
      setLayout(json.layout);
      setData(json.data);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Layout generated." },
      ]);
    } catch (err) {
      console.error("Error fetching layout:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="h-screen bg-gray-100 flex flex-col">
      <div className="flex-grow flex items-center justify-center px-4">
        {layout ? (
          <div className="bg-white rounded-xl shadow-md p-6 max-w-3xl w-full">
            <DynamicRenderer layout={layout} data={data} />
          </div>
        ) : (
          <p className="text-center text-gray-500">
            Ask something to generate a layout.
          </p>
        )}
      </div>

      <div className="w-full flex justify-center pb-6 px-4">
        <div className="flex w-full max-w-2xl gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your request..."
            className="flex-1 px-4 py-2 rounded-lg border border-gray-300 shadow-sm focus:outline-none focus:ring focus:ring-blue-200"
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
          />
          <button
            onClick={handleSend}
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition disabled:opacity-50"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
