import json
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from ollama import chat
from pydantic import BaseModel

from backend.database import RuntimeDatabase
from backend.history_store import HistoryStore

SYSTEM_PROMPT = (
    "You are a UI runtime planner. Use the tools to inspect data sources, fetch datasets, and assemble layouts.\n"
    "Workflow: optionally call describe_sources, fetch_dataset for each requested source (adding SQL filters as needed), then call build_*_layout to create the Page.\n"
    "when you get data, should always check if data match what user want and fix it"
    # """
    # every time if you are going to update/delete/add database, please ask User permission and tell user what you gone do and what is consequence, and only do it after user give permission.
    # """
    """
    every time if you are going to update/delete/add database, after doing it please provide new updated data to layout again, such as after update data, keep showing table.
    """
)

MAX_TURNS = 100  # limit messages from history
MAX_TOOL_STEPS = 20  # prevent infinite tool loops


def build_llm_messages(session_id: str):
    msgs = [{"role": "system", "content": SYSTEM_PROMPT}]
    try:
        hist = history.get_session(session_id)
    except Exception:
        hist = []
    # take last MAX_TURNS items
    for rec in hist[-MAX_TURNS:]:
        role = rec.get("role")
        content = rec.get("content") or ""
        if role in ("user", "assistant") and content:
            msgs.append({"role": role, "content": content})
    return msgs


def _preview(text: str, max_len: int = 400) -> str:
    try:
        s = str(text)
    except Exception:
        return ""
    return s if len(s) <= max_len else s[: max_len - 1] + "…"


def _coerce_dataset(data):
    if data is None:
        return None
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                return value
        return list(data.values())
    if isinstance(data, tuple):
        return list(data)
    return data


def _extract_layout_payload(payload):
    layout = None
    datasets: dict[str, list] = {}
    if isinstance(payload, dict):
        if "layout" in payload:
            layout = payload.get("layout")
            raw_datasets = payload.get("datasets")
            if isinstance(raw_datasets, dict):
                for key, value in raw_datasets.items():
                    datasets[key] = _coerce_dataset(value)
            elif raw_datasets is not None:
                datasets["data"] = _coerce_dataset(raw_datasets)
            if "data" in payload:
                datasets.setdefault("data", _coerce_dataset(payload.get("data")))
        elif "datasets" in payload:
            raw_datasets = payload.get("datasets")
            if isinstance(raw_datasets, dict):
                for key, value in raw_datasets.items():
                    datasets[key] = _coerce_dataset(value)
            elif raw_datasets is not None:
                datasets["data"] = _coerce_dataset(raw_datasets)
        else:
            layout = payload
    return layout, datasets


def _collect_sources(node):
    sources = set()
    if isinstance(node, dict):
        source = node.get("source")
        if source:
            sources.add(source)
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                sources |= _collect_sources(child)
    elif isinstance(node, list):
        for item in node:
            sources |= _collect_sources(item)
    return sources


def _resolve_datasets(layout, candidate_datasets, logs, trace=None):
    normalized: dict[str, list] = {}
    if isinstance(candidate_datasets, dict):
        for key, value in candidate_datasets.items():
            normalized[key] = _coerce_dataset(value)

    sources = _collect_sources(layout)

    if "data" in normalized and len(sources) == 1:
        src = next(iter(sources))
        if src not in normalized:
            normalized[src] = normalized.pop("data")
            msg = f"Mapped generic 'data' dataset to source '{src}'"
            logs.append({"type": "data", "text": msg})
            if trace is not None:
                trace.append(msg)

    if not normalized and not sources:
        normalized["data"] = []

    for src in sources:
        if src not in normalized:
            rows = database.get_rows(src)
            normalized[src] = rows
            msg = f"Loaded dataset for '{src}' from DB ({len(rows)} rows)"
            logs.append({"type": "data", "text": msg})
            if trace is not None:
                trace.append(msg)

    if not normalized:
        normalized["data"] = []

    for key, rows in normalized.items():
        msg = f"Dataset '{key}' ready with {len(rows) if isinstance(rows, list) else '?'} rows"
        logs.append({"type": "data", "text": msg})
        if trace is not None:
            trace.append(msg)

    return normalized

app = FastAPI()

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite-backed dataset store
database = RuntimeDatabase()

# Chat history store (JSONL-backed)
history = HistoryStore("backend/chat_history.jsonl")

### -------- Tool Functions -------- ###

def fetch_dataset(
    source: str | None = None,
    query: str | None = None,
    params: dict | list | tuple | None = None,
    alias: str | None = None,
) -> dict:
    """
    Retrieve rows for the planner with either convenience lookups or direct SQL queries.

    Tips for the model:
    - Prefer the `source` argument when you just need one of the known datasets
      (`products`, `sales`, `customers`, `orders`, `order_items`). The response automatically returns
      the named dataset with all columns.
    - When you need filtered/aggregated data, submit a single SELECT statement via `query`.
      You may bind parameters safely using `params` (dict or list/tuple). INSERT/UPDATE/DELETE are also
      permitted when you need to mutate data; the tool will echo back how many rows were affected.
    - Use `alias` to choose the dataset key that downstream layout tools should reference. Otherwise the
      tool will fall back to the provided `source` or `query_results`.
    """

    if query:
        result = database.run_sql(query, params)
        if not result.get("ok"):
            message = result.get("message") or "Query failed."
            return {"type": "Text", "content": message}

        dataset_name = alias or source or "query_results"
        rows = result.get("rows", [])
        command = (result.get("command") or "").upper() or "STATEMENT"
        if rows:
            meta = {
                "source": dataset_name,
                "query": query,
                "params": params,
                "rows": len(rows),
                "columns": result.get("columns", []),
                "command": command,
            }
            if alias and source and alias != source:
                meta["requested_source"] = source
            return {
                "datasets": {dataset_name: rows},
                "meta": meta,
            }

        affected = result.get("rowcount", 0)
        message = f"{command} executed; {affected} row(s) affected."
        return {
            "type": "Text",
            "content": message,
        }

    if not source:
        return {
            "type": "Text",
            "content": "fetch_dataset requires either a source or a SELECT query.",
        }

    rows = database.get_rows(source)

    return {
        "datasets": {source: rows},
        "meta": {
            "source": source,
            "rows": len(rows),
        },
    }


def build_table_layout(source: str, title: str | None = None) -> dict:
    """
    Produce a simple page layout that renders a table for the given dataset.

    Tips for the model:
    - Ensure `source` matches a dataset key you already loaded (for example via `fetch_dataset`).
    - Provide an optional `title` to control the page heading; otherwise a friendly default is used.
    - The frontend expects the dataset to be available under the same name you reference here.
    """

    title = title or f"{source.title()} Table"
    return {
        "layout": {
            "type": "Page",
            "title": title,
            "children": [
                {
                    "type": "Table",
                    "source": source,
                }
            ],
        }
    }


def build_chart_layout(
    source: str,
    chart_type: str = "bar",
    metric: str = "total",
    title: str | None = None,
) -> dict:
    """
    Generate a page layout containing a single chart for a dataset.

    Tips for the model:
    - `source` should reference a dataset already prepared in the response payload.
    - `chart_type` can be `bar`, `line`, etc., mapped to known frontend chart primitives.
    - `metric` controls the numeric field plotted on the Y axis; default is `total`.
    - Use `title` to customize the page heading; otherwise the tool derives one automatically.
    """

    title = title or f"{source.title()} {chart_type.title()}"
    return {
        "layout": {
            "type": "Page",
            "title": title,
            "children": [
                {
                    "type": "Chart",
                    "chartType": chart_type,
                    "metric": metric,
                    "source": source,
                }
            ],
        }
    }


def describe_sources() -> dict:
    """
    Inspect available datasets and schema information.

    Tips for the model:
    - Call this when you need to understand field names, row counts, or to decide which tables to query.
    - The response places schema details inside `meta["sources"]`; datasets stay empty by design.
    - Pair this with subsequent `fetch_dataset` calls to retrieve actual rows.
    """

    summary = database.describe_sources()
    return {"datasets": {}, "meta": {"sources": summary}}


tools = [
    fetch_dataset,
    build_table_layout,
    build_chart_layout,
    describe_sources,
]

### -------- Request Model -------- ###

class AIQuery(BaseModel):
    message: str
    session_id: Optional[str] = None

### -------- AI Layout Endpoint -------- ###

@app.post("/ai_layout")
async def ai_layout(query: AIQuery):
    sid = query.session_id or "default"
    trace = [f"Received query: {query.message}"]
    logs = [{"type": "thinking", "text": f"Received query: {query.message}"}]

    # Persist user message
    try:
        history.append(sid, "user", query.message)
    except Exception:
        pass

    # Build LLM messages from prior history (including just-saved user)
    messages = build_llm_messages(sid)

    # Tool-calling loop: support multiple tools/turns
    last_layout = None
    candidate_datasets: dict[str, list] = {}
    for step in range(1, MAX_TOOL_STEPS + 1):
        step_txt = f"Calling model: qwen3:8b with tool specs (step {step})"
        trace.append(step_txt)
        logs.append({"type": "thinking", "text": step_txt})
        response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)
        messages.append(response.message)

        if response.message.tool_calls:
            for call in response.message.tool_calls:
                tool_name = call.function.name
                args = call.function.arguments or {}
                try:
                    args_preview = json.dumps(args)
                except Exception:
                    args_preview = str(args)
                msg = f"Model requested tool: {tool_name} with args: {args_preview}"
                trace.append(msg)
                logs.append({"type": "tool", "text": msg})

                try:
                    tool_result = globals()[tool_name](**args)
                except Exception as e:
                    tool_result = {"type": "Text", "content": f"Tool {tool_name} error: {e}"}

                layout_candidate, datasets_candidate = _extract_layout_payload(tool_result)
                if layout_candidate:
                    last_layout = layout_candidate
                    title = layout_candidate.get("title") or layout_candidate.get("type")
                    if title:
                        step_log = f"Executed tool → layout: {title}"
                        trace.append(step_log)
                        logs.append({"type": "tool_result", "text": step_log})
                if datasets_candidate:
                    candidate_datasets.update(datasets_candidate)
                    keys = ", ".join(sorted(datasets_candidate.keys())) or "data"
                    logs.append({"type": "data", "text": f"Tool provided datasets: {keys}"})

                messages.append({
                    "role": "tool",
                    "tool_name": tool_name,
                    "content": json.dumps(tool_result),
                })
            continue
        else:
            content = getattr(response.message, "content", None)
            if content:
                try:
                    parsed = json.loads(content)
                    layout_candidate, datasets_candidate = _extract_layout_payload(parsed)
                    if layout_candidate:
                        last_layout = layout_candidate
                        title = layout_candidate.get("title") or layout_candidate.get("type")
                        if title:
                            fin = f"Parsed final layout: {title}"
                            trace.append(fin)
                            logs.append({"type": "thinking", "text": fin})
                    if datasets_candidate:
                        candidate_datasets.update(datasets_candidate)
                        keys = ", ".join(sorted(datasets_candidate.keys())) or "data"
                        logs.append({"type": "data", "text": f"Model response included datasets: {keys}"})
                    logs.append({"type": "model", "text": _preview(content)})
                except Exception:
                    warn = "Model returned non-JSON content; retaining last tool layout"
                    trace.append(warn)
                    logs.append({"type": "model", "text": _preview(content)})
                    logs.append({"type": "thinking", "text": warn})
            break
    else:
        txt = "Reached tool step limit; using last known layout"
        trace.append(txt)
        logs.append({"type": "thinking", "text": txt})

    layout_result = last_layout or {"type": "Text", "content": "No layout generated"}
    datasets_final = _resolve_datasets(layout_result, candidate_datasets, logs, trace)
    primary_data = next(iter(datasets_final.values()), [])

    result = {
        "layout": layout_result,
        "datasets": datasets_final,
        "data": primary_data,
        "trace": trace,
        "logs": logs,
    }

    # Persist assistant summary (+ thinking trace) and view snapshot
    try:
        title = layout_result.get("title") or layout_result.get("type")
        summary = f"Showing: {title}" if title else "Updated the view."
        history.append(
            sid,
            "assistant",
            summary,
            thinking=trace,
            meta={"logs": logs, "datasets": datasets_final},
        )
        history.append(
            sid,
            "view",
            "layout",
            meta={"layout": layout_result, "datasets": datasets_final},
        )
    except Exception:
        pass

    return result


def _sse(event: str, data) -> str:
    """Format a Server-Sent Event string for the given event and data."""
    try:
        payload = json.dumps(data)
    except Exception:
        payload = json.dumps({"text": str(data)})
    return f"event: {event}\ndata: {payload}\n\n"


@app.get("/ai_layout_stream")
async def ai_layout_stream(message: str, session_id: Optional[str] = Query(None)):
    async def event_generator():
        sid = session_id or "default"
        trace_local = []
        logs_local = []
        # Initial status
        yield _sse("thinking", {"text": f"Received query: {message}"})
        trace_local.append(f"Received query: {message}")
        logs_local.append({"type": "thinking", "text": f"Received query: {message}"})
        # Persist user message for this session
        try:
            history.append(sid, "user", message)
        except Exception:
            pass

        # Prepare LLM messages including history and the just-saved user
        messages = build_llm_messages(sid)

        last_layout = None
        candidate_datasets: dict[str, list] = {}
        for step_idx in range(1, MAX_TOOL_STEPS + 1):
            step_text = f"Calling model: qwen3:8b with tool specs (step {step_idx})"
            yield _sse("thinking", {"text": step_text})
            trace_local.append(step_text)
            logs_local.append({"type": "thinking", "text": step_text})

            response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)
            messages.append(response.message)

            if response.message.tool_calls:
                # Handle possibly multiple tool calls
                for call in response.message.tool_calls:
                    tool_name = call.function.name
                    args = call.function.arguments or {}
                    try:
                        args_preview = json.dumps(args)
                    except Exception:
                        args_preview = str(args)
                    step = f"Model requested tool: {tool_name} with args: {args_preview}"
                    yield _sse("tool", {"text": step, "name": tool_name, "args": args})
                    trace_local.append(step)
                    logs_local.append({"type": "tool", "text": step})

                    try:
                        tool_result = globals()[tool_name](**args)
                    except Exception as e:
                        tool_result = {"type": "Text", "content": f"Tool {tool_name} error: {e}"}

                    layout_candidate, datasets_candidate = _extract_layout_payload(tool_result)
                    if layout_candidate:
                        last_layout = layout_candidate
                        title = layout_candidate.get("title") or layout_candidate.get("type")
                        step = f"Executed tool → layout: {title}"
                        yield _sse("tool_result", {"text": step, "title": title})
                        trace_local.append(step)
                        logs_local.append({"type": "tool_result", "text": step})
                    if datasets_candidate:
                        candidate_datasets.update(datasets_candidate)
                        keys = ", ".join(sorted(datasets_candidate.keys())) or "data"
                        data_msg = f"Tool provided datasets: {keys}"
                        yield _sse("data", {"text": data_msg})
                        trace_local.append(data_msg)
                        logs_local.append({"type": "data", "text": data_msg})

                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": json.dumps(tool_result),
                    })

                continue
            else:
                # Try final layout parse
                content = getattr(response.message, "content", None)
                if content:
                    try:
                        parsed = json.loads(content)
                        layout_candidate, datasets_candidate = _extract_layout_payload(parsed)
                        if layout_candidate:
                            last_layout = layout_candidate
                            title = layout_candidate.get("title") or layout_candidate.get("type")
                            step = f"Parsed final layout: {title}"
                            yield _sse("model", {"text": _preview(content)})
                            yield _sse("thinking", {"text": step})
                            trace_local.append(step)
                            logs_local.append({"type": "model", "text": _preview(content)})
                            logs_local.append({"type": "thinking", "text": step})
                        if datasets_candidate:
                            candidate_datasets.update(datasets_candidate)
                            keys = ", ".join(sorted(datasets_candidate.keys())) or "data"
                            data_msg = f"Model response included datasets: {keys}"
                            yield _sse("data", {"text": data_msg})
                            trace_local.append(data_msg)
                            logs_local.append({"type": "data", "text": data_msg})
                    except Exception:
                        step = "Model returned non-JSON content; retaining last tool layout"
                        yield _sse("model", {"text": _preview(content)})
                        yield _sse("thinking", {"text": step})
                        trace_local.append(step)
                        logs_local.append({"type": "model", "text": _preview(content)})
                        logs_local.append({"type": "thinking", "text": step})
                break
        else:
            step = "Reached tool step limit; using last known layout"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)
            logs_local.append({"type": "thinking", "text": step})

        layout_final = last_layout or {"type": "Text", "content": "No layout generated"}
        datasets_final = _resolve_datasets(layout_final, candidate_datasets, logs_local, trace_local)

        # Persist assistant message with collected trace and view snapshot
        try:
            title = layout_final.get("title") or layout_final.get("type")
            summary = f"Showing: {title}" if title else "Updated the view."
            history.append(
                sid,
                "assistant",
                summary,
                thinking=trace_local,
                meta={"logs": logs_local, "datasets": datasets_final},
            )
            history.append(
                sid,
                "view",
                "layout",
                meta={"layout": layout_final, "datasets": datasets_final},
            )
        except Exception:
            pass

        primary_data = next(iter(datasets_final.values()), [])
        yield _sse("final", {"layout": layout_final, "datasets": datasets_final, "data": primary_data})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/chat_history")
async def chat_history(session_id: Optional[str] = Query(None)):
    """Return saved chat history for a session (or 'default')."""
    sid = session_id or "default"
    try:
        return {"session_id": sid, "messages": history.get_session(sid)}
    except Exception:
        return {"session_id": sid, "messages": []}


@app.get("/last_view")
async def last_view(session_id: Optional[str] = Query(None)):
    """Return the most recent saved layout and data for a session."""
    sid = session_id or "default"
    try:
        hist = history.get_session(sid)
        layout = None
        datasets = None
        for rec in reversed(hist):
            meta = rec.get("meta") or {}
            if isinstance(meta, dict) and meta.get("layout"):
                layout = meta.get("layout")
                if "datasets" in meta and isinstance(meta["datasets"], dict):
                    datasets = {
                        key: _coerce_dataset(value)
                        for key, value in meta["datasets"].items()
                    }
                elif "data" in meta:
                    datasets = {"data": _coerce_dataset(meta.get("data"))}
                break
        if not layout:
            return {"layout": None, "datasets": {}, "data": []}

        datasets = _resolve_datasets(layout, datasets, [], None)
        primary = next(iter(datasets.values()), [])
        return {"layout": layout, "datasets": datasets, "data": primary}
    except Exception:
        return {"layout": None, "datasets": {}, "data": []}
