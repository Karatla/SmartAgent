from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ollama import chat
import json

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

### -------- AI Layout Endpoint -------- ###

@app.post("/ai_layout")
async def ai_layout(query: AIQuery):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a UI agent. Your job is to call tools to return layout JSON.\n"
                "DO NOT explain anything. Do NOT return markdown or freeform text.\n"
                "Only call tools or return layout as tool results."
            ),
        },
        {"role": "user", "content": query.message},
    ]

    # 1. Ask Qwen for what to do
    response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)

    messages.append(response.message)

    print(response)

    if response.message.tool_calls:
        call = response.message.tool_calls[0]
        tool_name = call.function.name
        args = call.function.arguments

        # 2. Execute the tool function
        layout_result = globals()[tool_name](**args)

        # 3. Send result back to Qwen to complete the flow (optional)
        messages.append({
            "role": "tool",
            "tool_name": tool_name,
            "content": json.dumps(layout_result)
        })

        final_response = chat(model="qwen3:8b", messages=messages, tools=tools, think=False)

        print(final_response)

        return {
            "layout": layout_result,
            "data": db.get(layout_result["children"][0]["source"], [])
        }

    else:
        # fallback if model replies with raw layout (no tool call)
        return {
            "layout": json.loads(response.message.content),
            "data": []
        }
