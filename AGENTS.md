
---

# 🧠 AI Runtime Web Agent

### Overview

This agent powers a **natural-language controlled web interface**, where users can talk or type to change what they see on a website — instantly, without editing code.

Instead of traditional hard-coded pages, the website’s frontend acts as a **runtime renderer** that displays layouts described in **AI-generated JSON**.
The backend AI agent interprets user intent, queries data, and returns a layout that the frontend immediately renders.

This makes the web experience **intent-driven**, not code-driven.

---

## 🎯 Core Idea

> “AI dynamically generates the website’s UI and data views at runtime.”

* The **frontend** is static and knows how to render generic layouts (`Table`, `Chart`, `Text`, etc.).
* The **AI backend** creates a layout JSON describing what to show.
* The **database** remains the source of truth for data.
* The **user** interacts via natural language or voice.
* The **UI changes in real-time** without rebuilding or deploying new code.

---

## 🏗️ System Architecture

```
User → (Chat or Voice)
      ↓
[AI Runtime Server]
 ├── Intent Parser (LLM)
 ├── Action Planner
 ├── Database Access Layer
 └── UI Generator → JSON Layout
      ↓
[Frontend React Runtime]
 ├── Renders JSON instantly
 ├── Components: Table, Chart, etc.
 └── Updates on new layout
      ↓
[Database]
 └── Real product, sales, user data
```

---

## 🧩 Example Flow

**User:**

> “Show me product list.”

**AI Runtime Server:**

* Parses intent → “Display products.”
* Fetches data from DB.
* Returns layout JSON:

  ```json
  {
    "type": "Page",
    "title": "Product List",
    "children": [{ "type": "Table", "source": "products" }]
  }
  ```

**Frontend:**

* Receives JSON.
* Renders the `Table` component with real data.

---

## ⚙️ Prototype Components

| Component                      | Description                                                     |
| ------------------------------ | --------------------------------------------------------------- |
| `backend/main.py`              | FastAPI server that simulates AI responses (or integrates GPT). |
| `backend/database.py`          | SQLite data layer with seeded datasets and CRUD helpers.        |
| `frontend/App.jsx`             | Main UI where user types requests.                              |
| `frontend/DynamicRenderer.jsx` | Renders UI from layout JSON.                                    |
| `frontend/components/*`        | Table and Chart React components.                               |

---

## 🚀 Future Vision

Eventually, this will evolve into a **self-adapting AI runtime framework** that:

* Connects to any database automatically.
* Understands user intent from natural conversation.
* Generates and updates the web UI on demand.
* Supports real-time voice, multi-modal input, and auto-context memory.


## 🧭 Notes

* The **frontend stays constant** — it never changes code dynamically.
  The **AI backend changes the JSON layout**, and the frontend re-renders.
* JSON acts as a **universal bridge** between AI and UI.
* This structure allows future **live code generation** if desired (Codex SDK supports that).

---


# Repository Guidelines

## Project Structure & Module Organization
The FastAPI service lives in `backend/`; its entry point is `backend/main.py`, backed by the SQLite data layer in `backend/database.py` (which materialises `runtime.db` on first run). Expand Python modules inside `backend/` (e.g., `backend/services/`, `backend/routes/`) and mirror them under `backend/tests/` when you add coverage. The React client resides in `frontend/`, with source files under `frontend/src/` and static assets inside `frontend/public/`. Keep shared UI primitives in `frontend/src/components/` and colocate feature-specific helpers beside their calling components. The root `main.py` is reserved for quick CLI experiments—avoid mixing application logic there.

## Build, Test, and Development Commands
Install backend dependencies once with `uv sync`, then launch an auto-reloading API via `uv run uvicorn backend.main:app --reload`. The frontend uses Vite; run `npm install` inside `frontend/` on first setup, `npm run dev` for local development, `npm run build` for production bundles, and `npm run preview` to validate the optimized build. When iterating on both tiers, run the API first so the UI can proxy to `/ai_layout`.

## Coding Style & Naming Conventions
Follow PEP 8 in Python: 4-space indentation, snake_case for functions, PascalCase for classes, and module-level constants in UPPER_SNAKE. Annotate new FastAPI endpoints with type hints for request/response models. Prefer small, dependency-injected services over module-level state. In React, keep components as PascalCase files (`DynamicRenderer.jsx`) and favor hooks for shared state. Run `uv run ruff check backend` and `uv run black backend` (add both as dev dependencies if missing) alongside `npm run lint` to keep code style consistent.

## Testing Guidelines
Use `pytest` for backend coverage; place files under `backend/tests/test_*.py` and isolate API contracts with `TestClient`. Target regression tests around the layout inference rules that read from the SQLite `RuntimeDatabase`. For the frontend, add Vitest plus React Testing Library to exercise rendering logic, storing specs under `frontend/src/__tests__/`. Mark slower integration suites with `@pytest.mark.integration` or `describe.skip` so CI remains fast.

## Commit & Pull Request Guidelines
Write commits in the imperative mood and scope them tightly (e.g., `Add product layout endpoint`). Squash noisy WIP commits before opening a PR. PR descriptions should explain the user-facing impact, link tracking issues, and attach screenshots or JSON samples when updating generated layouts. Verify `uv run uvicorn backend.main:app --reload` and `npm run dev` both start cleanly, and include test or lint output in the summary before requesting review.
