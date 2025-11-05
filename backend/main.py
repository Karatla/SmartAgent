from fastapi import FastAPI, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ollama import chat
import json
import asyncio
from fastapi.responses import StreamingResponse
from typing import Optional

from backend.history_store import HistoryStore

SYSTEM_PROMPT = (
    "You are a UI agent. Your job is to call tools to return layout JSON.\n"
    "DO NOT explain anything. Do NOT return markdown or freeform text.\n"
    "Only call tools or return layout as tool results."
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
    return {
        "type": "Page",
        "title": "Product List",
        "children": [
            {"type": "Table", "source": "products"}
        ]
    }

def get_sales_chart(period: str = "month") -> dict:
    """Return a sales chart layout for a specific period.

    Args:
        period: one of "today", "week", or "month"
    """
    return {
        "type": "Page",
        "title": f"Sales Chart ({period})",
        "children": [
            {
                "type": "Chart",
                "chartType": "bar",
                "source": "sales"
            }
        ]
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

    # Persist user message
    try:
        history.append(sid, "user", query.message)
    except Exception:
        pass

    # Build LLM messages from prior history (including just-saved user)
    messages = build_llm_messages(sid)

    # Tool-calling loop: support multiple tools/turns
    last_layout = None
    for step in range(1, MAX_TOOL_STEPS + 1):
        trace.append(f"Calling model: qwen3:8b with tool specs (step {step})")
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
                trace.append(f"Model requested tool: {tool_name} with args: {args_preview}")

                try:
                    tool_result = globals()[tool_name](**args)
                except Exception as e:
                    tool_result = {"type": "Text", "content": f"Tool {tool_name} error: {e}"}

                if isinstance(tool_result, dict):
                    last_layout = tool_result
                    title = tool_result.get("title") or tool_result.get("type")
                    if title:
                        trace.append(f"Executed tool → layout: {title}")

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
                    if isinstance(parsed, dict):
                        last_layout = parsed
                        title = parsed.get("title") or parsed.get("type")
                        if title:
                            trace.append(f"Parsed final layout: {title}")
                except Exception:
                    trace.append("Model returned non-JSON content; retaining last tool layout")
            break
    else:
        trace.append("Reached tool step limit; using last known layout")

    layout_result = last_layout or {"type": "Text", "content": "No layout generated"}

    # Collect main data source if present (first child)
    try:
        source_key = layout_result["children"][0].get("source")
    except Exception:
        source_key = None

    data_rows = db.get(source_key, []) if source_key else []
    if source_key:
        trace.append(f"Prepared dataset for source '{source_key}' ({len(data_rows)} rows)")
    else:
        trace.append("No data source detected in layout; returning empty dataset")

    result = {
        "layout": layout_result,
        "data": data_rows,
        "trace": trace,
    }

    # Persist assistant summary (+ thinking trace) and view snapshot
    try:
        title = layout_result.get("title") or layout_result.get("type")
        summary = f"Showing: {title}" if title else "Updated the view."
        history.append(sid, "assistant", summary, thinking=trace)
        history.append(sid, "view", "layout", meta={"layout": layout_result})
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
        # Initial status
        yield _sse("thinking", {"text": f"Received query: {message}"})
        trace_local.append(f"Received query: {message}")
        # Persist user message for this session
        try:
            history.append(sid, "user", message)
        except Exception:
            pass

        # Prepare LLM messages including history and the just-saved user
        messages = build_llm_messages(sid)

        last_layout = None
        for step_idx in range(1, MAX_TOOL_STEPS + 1):
            step_text = f"Calling model: qwen3:8b with tool specs (step {step_idx})"
            yield _sse("thinking", {"text": step_text})
            trace_local.append(step_text)

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
                    yield _sse("thinking", {"text": step})
                    trace_local.append(step)

                    try:
                        tool_result = globals()[tool_name](**args)
                    except Exception as e:
                        tool_result = {"type": "Text", "content": f"Tool {tool_name} error: {e}"}

                    if isinstance(tool_result, dict):
                        last_layout = tool_result
                        title = tool_result.get("title") or tool_result.get("type")
                        step = f"Executed tool → layout: {title}"
                        yield _sse("thinking", {"text": step})
                        trace_local.append(step)

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
                        if isinstance(parsed, dict):
                            last_layout = parsed
                            title = parsed.get("title") or parsed.get("type")
                            step = f"Parsed final layout: {title}"
                            yield _sse("thinking", {"text": step})
                            trace_local.append(step)
                    except Exception:
                        step = "Model returned non-JSON content; retaining last tool layout"
                        yield _sse("thinking", {"text": step})
                        trace_local.append(step)
                break
        else:
            step = "Reached tool step limit; using last known layout"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)

        layout_final = last_layout or {"type": "Text", "content": "No layout generated"}
        try:
            source_key = layout_final["children"][0].get("source")
        except Exception:
            source_key = None
        data_rows = db.get(source_key, []) if source_key else []
        if source_key:
            step = f"Prepared dataset for source '{source_key}' ({len(data_rows)} rows)"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)
        else:
            step = "No data source detected in layout; returning empty dataset"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)

        # Persist assistant message with collected trace and view snapshot
        try:
            title = layout_final.get("title") or layout_final.get("type")
            summary = f"Showing: {title}" if title else "Updated the view."
            history.append(sid, "assistant", summary, thinking=trace_local)
            history.append(sid, "view", "layout", meta={"layout": layout_final})
        except Exception:
            pass

        yield _sse("final", {"layout": layout_final, "data": data_rows})

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
        for rec in reversed(hist):
            meta = rec.get("meta") or {}
            if isinstance(meta, dict) and meta.get("layout"):
                layout = meta.get("layout")
                break
        if not layout:
            return {"layout": None, "data": []}

        # Compute primary data rows from first child source (if any)
        try:
            source_key = layout["children"][0].get("source")
        except Exception:
            source_key = None
        data_rows = db.get(source_key, []) if source_key else []
        return {"layout": layout, "data": data_rows}
    except Exception:
        return {"layout": None, "data": []}
