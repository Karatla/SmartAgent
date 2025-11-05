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

    # 1. Ask Qwen for what to do
    trace.append("Calling model: qwen3:8b with tool specs")
    response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)

    messages.append(response.message)

    print(response)

    if response.message.tool_calls:
        call = response.message.tool_calls[0]
        tool_name = call.function.name
        args = call.function.arguments
        try:
            args_preview = json.dumps(args)
        except Exception:
            args_preview = str(args)
        trace.append(f"Model requested tool: {tool_name} with args: {args_preview}")

        # 2. Execute the tool function
        layout_result = globals()[tool_name](**(args or {}))
        title = layout_result.get("title") or layout_result.get("type")
        trace.append(f"Executed tool → layout: {title}")

        # 3. Send result back to Qwen to complete the flow (optional)
        messages.append({
            "role": "tool",
            "tool_name": tool_name,
            "content": json.dumps(layout_result)
        })

        final_response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)

        print(final_response)

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

        # Persist assistant summary (+ thinking trace)
        try:
            summary = f"Showing: {title}" if title else "Updated the view."
            history.append(sid, "assistant", summary, thinking=trace)
            # Persist view snapshot (layout)
            history.append(sid, "view", "layout", meta={"layout": layout_result})
        except Exception:
            pass

        return result

    else:
        # fallback if model replies with raw layout (no tool call)
        trace.append("Model returned raw layout without tool call")
        try:
            layout = json.loads(response.message.content)
            title = layout.get("title") or layout.get("type")
            trace.append(f"Parsed raw layout: {title}")
        except Exception:
            layout = {"type": "Text", "content": "Unable to parse layout"}
            trace.append("Failed to parse raw layout; using Text fallback")

        result = {
            "layout": layout,
            "data": [],
            "trace": trace,
        }

        try:
            title = layout.get("title") or layout.get("type")
            summary = f"Showing: {title}" if title else "Updated the view."
            history.append(sid, "assistant", summary, thinking=trace)
            history.append(sid, "view", "layout", meta={"layout": layout})
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
        yield _sse("thinking", {"text": "Calling model: qwen3:8b with tool specs"})
        trace_local.append("Calling model: qwen3:8b with tool specs")

        # Persist user message for this session
        try:
            history.append(sid, "user", message)
        except Exception:
            pass

        # Prepare LLM messages including history and the just-saved user
        messages = build_llm_messages(sid)

        # Ask model for tool selection / raw layout
        response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)
        messages.append(response.message)

        if response.message.tool_calls:
            call = response.message.tool_calls[0]
            tool_name = call.function.name
            args = call.function.arguments
            try:
                args_preview = json.dumps(args)
            except Exception:
                args_preview = str(args)
            step = f"Model requested tool: {tool_name} with args: {args_preview}"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)

            # Execute tool
            layout_result = globals()[tool_name](**(args or {}))
            title = layout_result.get("title") or layout_result.get("type")
            step = f"Executed tool → layout: {title}"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)

            # Optionally validate with model
            messages.append({
                "role": "tool",
                "tool_name": tool_name,
                "content": json.dumps(layout_result),
            })

            chat(model="qwen3:8b", messages=messages, tools=tools, think=False)
            yield _sse("thinking", {"text": "Validated layout with model"})
            trace_local.append("Validated layout with model")

            # Prepare data
            try:
                source_key = layout_result["children"][0].get("source")
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

            # Persist assistant message with collected trace
            try:
                summary = f"Showing: {title}" if title else "Updated the view."
                history.append(sid, "assistant", summary, thinking=trace_local)
                history.append(sid, "view", "layout", meta={"layout": layout_result})
            except Exception:
                pass

            yield _sse("final", {"layout": layout_result, "data": data_rows})
        else:
            # Raw layout path
            step = "Model returned raw layout without tool call"
            yield _sse("thinking", {"text": step})
            trace_local.append(step)
            try:
                layout = json.loads(response.message.content)
                title = layout.get("title") or layout.get("type")
                step = f"Parsed raw layout: {title}"
                yield _sse("thinking", {"text": step})
                trace_local.append(step)
            except Exception:
                layout = {"type": "Text", "content": "Unable to parse layout"}
                step = "Failed to parse raw layout; using Text fallback"
                yield _sse("thinking", {"text": step})
                trace_local.append(step)

            try:
                summary = f"Showing: {title}" if isinstance(layout, dict) and (title := (layout.get("title") or layout.get("type"))) else "Updated the view."
                history.append(sid, "assistant", summary, thinking=trace_local)
                history.append(sid, "view", "layout", meta={"layout": layout})
            except Exception:
                pass

            yield _sse("final", {"layout": layout, "data": []})

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
