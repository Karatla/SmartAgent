# Terminal 1
uvicorn backend.main:app --reload
# Terminal 2
cd frontend && npm run dev
sudo systemctl status ollama

---

This repo hosts the AI Runtime Web Agent prototype: a FastAPI backend and Vite React frontend where layouts, data queries, and UI rendering all happen at runtime via natural-language prompts. Launch the backend and frontend with the commands above, then talk to the agent to watch it inspect data sources, run SQL, and generate new dashboards on the fly.
