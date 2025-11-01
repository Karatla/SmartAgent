
---

# ✅ TODO.md — AI Runtime Web Agent

### Project: AI Runtime Selling Management System

**Agent Name:** `runtime-ui-agent`
**Purpose:** Dynamically generate and render website layouts using AI at runtime (intent-driven UI).

---

## 🧩 PHASE 1 — Core Prototype (Base System)

**Goal:** Build the foundation that connects backend ↔ frontend via dynamic layout JSON.

### Tasks

* [x] Create `backend/main.py` using FastAPI.
* [x] Implement mock database (`backend/db.json`).
* [x] Build React frontend (Vite + Tailwind + Recharts).
* [x] Implement `DynamicRenderer.jsx` to render JSON-based UI.
* [x] Add `ProductTable` and `SalesChart` components.
* [x] Connect `/ai_layout` API endpoint to frontend.

### Deliverable

> A running prototype where JSON from backend changes the frontend layout instantly.

---

## 🤖 PHASE 2 — AI Integration (LLM Runtime)

**Goal:** Replace hardcoded logic with AI-driven reasoning.

### Tasks

* [ ] Integrate local Ollama into FastAPI.
* [ ] Define a prompt template for layout generation, e.g.:

  ```
  You are a UI runtime agent. Generate JSON layouts for a dashboard.
  ```
* [ ] Map database schema to natural-language queries.
* [ ] Generate layout dynamically based on user text intent.
* [ ] Add error fallback when AI layout is invalid.
* [ ] Log all generated layouts for debugging.

### Deliverable

> Natural language commands generate new layouts (table, chart, text) through AI.

---

## 🧠 PHASE 3 — Memory & Context

**Goal:** Give the agent persistent context for multi-turn conversations.

### Tasks

* [ ] Integrate Redis or a lightweight vector memory (e.g., LlamaIndex).
* [ ] Store current view state and previous intents.
* [ ] Add support for follow-ups:

  * “Now sort by price.”
  * “Compare to last month.”
* [ ] Implement context summarization every N turns.

### Deliverable

> AI remembers user session context and modifies layout accordingly.

---

## 🎙️ PHASE 4 — Voice Interface

**Goal:** Make the dashboard fully voice-interactive.

### Tasks

* [ ] Integrate Whisper for speech → text.
* [ ] Add VAD (Voice Activity Detection) for auto start/stop.
* [ ] Add TTS (Text-to-Speech) response playback.
* [ ] Connect voice commands directly to `/ai_layout`.

### Deliverable

> User can speak commands, AI updates dashboard, and responds verbally.

---

## 💾 PHASE 5 — Real Database Binding

**Goal:** Move from static JSON DB to real SQL data.

### Tasks

* [ ] Replace `db.json` with PostgreSQL / SQLite.
* [ ] Add ORM (SQLAlchemy or Prisma) with schema introspection.
* [ ] Let AI query data dynamically via ORM functions.
* [ ] Secure DB access and sanitize queries.
* [ ] Support CRUD operations (create/update/delete).

### Deliverable

> AI dynamically generates layouts *and* executes data queries live.

---

## 🎨 PHASE 6 — Advanced UI Runtime

**Goal:** Expand the runtime renderer with richer UI capabilities.

### Tasks

* [ ] Add components: Form, Modal, Card, FilterBar.
* [ ] Support layout grids and responsive sizing.
* [ ] Enable dynamic styling: themes, colors, chart modes.
* [ ] Add “stateful” components (inputs, toggles).

### Deliverable

> A more complete UI system with multiple view types and richer visuals.

---

## 🧩 PHASE 7 — Codex Agent Integration

**Goal:** Integrate this runtime system into Codex as an agent.

### Tasks

* [ ] Define agent manifest: `codex-agent.yaml`

  ```yaml
  name: runtime-ui-agent
  title: AI Runtime Web Agent
  version: 0.1.0
  entry: backend/main.py
  capabilities:
    - generate_ui
    - query_db
    - frontend_render
  ```
* [ ] Register in Codex CLI (`codex register`).
* [ ] Add interaction examples in `agent.md`.
* [ ] Test runtime UI change sessions via Codex API.
* [ ] Verify protocol handshake (MCP events, UI updates).

### Deliverable

> Agent runs in Codex environment and responds to user commands with live UI generation.

---

## 🧭 FUTURE IDEAS

| Idea                      | Description                                        |
| ------------------------- | -------------------------------------------------- |
| **Auto Schema Discovery** | AI reads DB schema and self-learns field meanings. |
| **Multi-Agent Mode**      | One agent for data, one for UI design.             |
| **AI Style Editor**       | “Make it dark theme” dynamically.                  |
| **Plugin Hooks**          | Extendable via Codex Tool API.                     |

---

## ✅ Final Deliverable

> A Codex-integrated **AI Runtime Agent** that allows the user to **talk to their web system**,
> while the interface **changes instantly** at runtime, powered by **AI-generated layouts** and **live database data**.

---

Would you like me to generate the **matching `codex-agent.yaml` file** next, so this agent is ready to register and run inside your Codex setup?
