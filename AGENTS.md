# Repository Guidelines

## Project Structure & Module Organization
The FastAPI service lives in `backend/`; its entry point is `backend/main.py`, backed by the JSON fixture in `backend/db.json`. Expand Python modules inside `backend/` (e.g., `backend/services/`, `backend/routes/`) and mirror them under `backend/tests/` when you add coverage. The React client resides in `frontend/`, with source files under `frontend/src/` and static assets inside `frontend/public/`. Keep shared UI primitives in `frontend/src/components/` and colocate feature-specific helpers beside their calling components. The root `main.py` is reserved for quick CLI experiments—avoid mixing application logic there.

## Build, Test, and Development Commands
Install backend dependencies once with `uv sync`, then launch an auto-reloading API via `uv run uvicorn backend.main:app --reload`. The frontend uses Vite; run `npm install` inside `frontend/` on first setup, `npm run dev` for local development, `npm run build` for production bundles, and `npm run preview` to validate the optimized build. When iterating on both tiers, run the API first so the UI can proxy to `/ai_layout`.

## Coding Style & Naming Conventions
Follow PEP 8 in Python: 4-space indentation, snake_case for functions, PascalCase for classes, and module-level constants in UPPER_SNAKE. Annotate new FastAPI endpoints with type hints for request/response models. Prefer small, dependency-injected services over module-level state. In React, keep components as PascalCase files (`DynamicRenderer.jsx`) and favor hooks for shared state. Run `uv run ruff check backend` and `uv run black backend` (add both as dev dependencies if missing) alongside `npm run lint` to keep code style consistent.

## Testing Guidelines
Use `pytest` for backend coverage; place files under `backend/tests/test_*.py` and isolate API contracts with `TestClient`. Target regression tests around the layout inference rules that read `db.json`. For the frontend, add Vitest plus React Testing Library to exercise rendering logic, storing specs under `frontend/src/__tests__/`. Mark slower integration suites with `@pytest.mark.integration` or `describe.skip` so CI remains fast.

## Commit & Pull Request Guidelines
Write commits in the imperative mood and scope them tightly (e.g., `Add product layout endpoint`). Squash noisy WIP commits before opening a PR. PR descriptions should explain the user-facing impact, link tracking issues, and attach screenshots or JSON samples when updating generated layouts. Verify `uv run uvicorn backend.main:app --reload` and `npm run dev` both start cleanly, and include test or lint output in the summary before requesting review.
