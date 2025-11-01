import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# fake database
db_path = Path(__file__).resolve().parent / "db.json"
with db_path.open("r") as f:
    db = json.load(f)

@app.get("/ai_layout")
def ai_layout(query: str = Query(...)):
    """
    Simulates an AI agent that generates UI JSON
    based on user intent.
    """
    q = query.lower()
    if "product" in q:
        layout = {
            "type": "Page",
            "title": "Product List",
            "children": [{"type": "Table", "source": "products"}],
        }
        data = db["products"]

    elif "sale" in q or "chart" in q:
        layout = {
            "type": "Page",
            "title": "Sales Chart",
            "children": [{
                "type": "Chart",
                "chartType": "bar",
                "source": "sales"
            }],
        }
        data = db["sales"]

    else:
        layout = {"type": "Text", "content": "I didn’t understand that."}
        data = {}

    return {"layout": layout, "data": data}
