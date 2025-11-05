from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ollama import chat
import json
from fastapi.responses import StreamingResponse
from typing import Optional

from backend.history_store import HistoryStore

SYSTEM_PROMPT = (
    "You are a UI agent. Your job is to help user and call tools to return layout JSON.\n"
    #"DO NOT explain anything. Do NOT return markdown or freeform text.\n"
    #"Only call tools or return layout as tool results."
)

MAX_TURNS = 20  # limit messages from history
MAX_TOOL_STEPS = 8  # prevent infinite tool loops


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
    data = None
    if isinstance(payload, dict):
        if "layout" in payload:
            layout = payload.get("layout")
            if "data" in payload:
                data = payload.get("data")
            elif "datasets" in payload:
                datasets = payload.get("datasets")
                if isinstance(datasets, dict):
                    for value in datasets.values():
                        data = value
                        break
                elif isinstance(datasets, list) and datasets:
                    data = datasets[0]
        else:
            layout = payload
    return layout, _coerce_dataset(data)

app = FastAPI()

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mock database
with open("backend/db.json") as f:
    db = json.load(f)

# Chat history store (JSONL-backed)
history = HistoryStore("backend/chat_history.jsonl")

### -------- Tool Functions -------- ###

def get_product_table() -> dict:
    """Return a JSON layout for the product table."""
    layout = {
        "type": "Page",
        "title": "Product List",
        "children": [
            {"type": "Table", "source": "products"}
        ],
    }
    return {
        "layout": layout,
        "data": db.get("products", []),
    }

def get_sales_chart(period: str = "month") -> dict:
    """Return a sales chart layout for a specific period.

    Args:
        period: one of "today", "week", or "month"
    """
    layout = {
        "type": "Page",
        "title": f"Sales Chart ({period})",
        "children": [
            {
                "type": "Chart",
                "chartType": "bar",
                "source": "sales",
            }
        ],
    }
    data = db.get("sales", [])
    return {
        "layout": layout,
        "data": data,
    }

tools = [get_product_table, get_sales_chart]

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
    last_data = None
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

                layout_candidate, data_candidate = _extract_layout_payload(tool_result)
                if layout_candidate:
                    last_layout = layout_candidate
                    title = layout_candidate.get("title") or layout_candidate.get("type")
                    if title:
                        step_log = f"Executed tool → layout: {title}"
                        trace.append(step_log)
                        logs.append({"type": "tool_result", "text": step_log})
                if data_candidate is not None:
                    last_data = data_candidate
                    if isinstance(last_data, list):
                        logs.append({"type": "data", "text": f"Tool provided dataset with {len(last_data)} rows"})
                    else:
                        logs.append({"type": "data", "text": "Tool provided dataset"})

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
                    layout_candidate, data_candidate = _extract_layout_payload(parsed)
                    if layout_candidate:
                        last_layout = layout_candidate
                        title = layout_candidate.get("title") or layout_candidate.get("type")
                        if title:
                            fin = f"Parsed final layout: {title}"
                            trace.append(fin)
                            logs.append({"type": "thinking", "text": fin})
                    if data_candidate is not None:
                        last_data = data_candidate
                        if isinstance(last_data, list):
                            logs.append({"type": "data", "text": f"Model response included dataset with {len(last_data)} rows"})
                        else:
                            logs.append({"type": "data", "text": "Model response included dataset"})
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

    if last_data is None:
        try:
            source_key = layout_result["children"][0].get("source")
        except Exception:
            source_key = None

        if source_key:
            last_data = db.get(source_key, [])
            info = f"Prepared dataset for source '{source_key}' ({len(last_data)} rows)"
            trace.append(info)
            logs.append({"type": "data", "text": info})
        else:
            last_data = []
            info = "No data source detected in layout; returning empty dataset"
            trace.append(info)
            logs.append({"type": "thinking", "text": info})
    else:
        if isinstance(last_data, list):
            info = f"Using dataset with {len(last_data)} rows from tool chain"
        else:
            info = "Using dataset returned by tool chain"
        trace.append(info)
        logs.append({"type": "data", "text": info})

    result = {
        "layout": layout_result,
        "data": last_data,
        "trace": trace,
        "logs": logs,
    }

    # Persist assistant summary (+ thinking trace) and view snapshot
    try:
        title = layout_result.get("title") or layout_result.get("type")
        summary = f"Showing: {title}" if title else "Updated the view."
        history.append(sid, "assistant", summary, thinking=trace, meta={"logs": logs, "data": last_data})
        history.append(sid, "view", "layout", meta={"layout": layout_result, "data": last_data})
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
        last_data = None
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

                    layout_candidate, data_candidate = _extract_layout_payload(tool_result)
                    if layout_candidate:
                        last_layout = layout_candidate
                        title = layout_candidate.get("title") or layout_candidate.get("type")
                        step = f"Executed tool → layout: {title}"
                        yield _sse("tool_result", {"text": step, "title": title})
                        trace_local.append(step)
                        logs_local.append({"type": "tool_result", "text": step})
                    if data_candidate is not None:
                        last_data = data_candidate
                        if isinstance(last_data, list):
                            data_msg = f"Tool provided dataset with {len(last_data)} rows"
                            rows = len(last_data)
                        else:
                            data_msg = "Tool provided dataset"
                            rows = None
                        yield _sse("data", {"text": data_msg, "rows": rows})
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
                        layout_candidate, data_candidate = _extract_layout_payload(parsed)
                        if layout_candidate:
                            last_layout = layout_candidate
                            title = layout_candidate.get("title") or layout_candidate.get("type")
                            step = f"Parsed final layout: {title}"
                            yield _sse("model", {"text": _preview(content)})
                            yield _sse("thinking", {"text": step})
                            trace_local.append(step)
                            logs_local.append({"type": "model", "text": _preview(content)})
                            logs_local.append({"type": "thinking", "text": step})
                        if data_candidate is not None:
                            last_data = data_candidate
                            if isinstance(last_data, list):
                                data_msg = f"Model response included dataset with {len(last_data)} rows"
                                rows = len(last_data)
                            else:
                                data_msg = "Model response included dataset"
                                rows = None
                            yield _sse("data", {"text": data_msg, "rows": rows})
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
        if last_data is None:
            try:
                source_key = layout_final["children"][0].get("source")
            except Exception:
                source_key = None
            if source_key:
                last_data = db.get(source_key, [])
                step = f"Prepared dataset for source '{source_key}' ({len(last_data)} rows)"
                yield _sse("data", {"text": step, "rows": len(last_data)})
                trace_local.append(step)
                logs_local.append({"type": "data", "text": step})
            else:
                last_data = []
                step = "No data source detected in layout; returning empty dataset"
                yield _sse("thinking", {"text": step})
                trace_local.append(step)
                logs_local.append({"type": "thinking", "text": step})
        else:
            if isinstance(last_data, list):
                step = f"Using dataset with {len(last_data)} rows from tool chain"
                rows = len(last_data)
            else:
                step = "Using dataset returned by tool chain"
                rows = None
            yield _sse("data", {"text": step, "rows": rows})
            trace_local.append(step)
            logs_local.append({"type": "data", "text": step})

        # Persist assistant message with collected trace and view snapshot
        try:
            title = layout_final.get("title") or layout_final.get("type")
            summary = f"Showing: {title}" if title else "Updated the view."
            history.append(sid, "assistant", summary, thinking=trace_local, meta={"logs": logs_local, "data": last_data})
            history.append(sid, "view", "layout", meta={"layout": layout_final, "data": last_data})
        except Exception:
            pass

        yield _sse("final", {"layout": layout_final, "data": last_data})

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
        data_rows = None
        for rec in reversed(hist):
            meta = rec.get("meta") or {}
            if isinstance(meta, dict) and meta.get("layout"):
                layout = meta.get("layout")
                if "data" in meta:
                    data_rows = meta.get("data")
                break
        if not layout:
            return {"layout": None, "data": []}

        if data_rows is None:
            # Compute primary data rows from first child source (if any)
            try:
                source_key = layout["children"][0].get("source")
            except Exception:
                source_key = None
            data_rows = db.get(source_key, []) if source_key else []
        return {"layout": layout, "data": data_rows}
    except Exception:
        return {"layout": None, "data": []}
