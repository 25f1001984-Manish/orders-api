from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import time
import base64

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOTAL_ORDERS = 57
RATE_LIMIT = 15
WINDOW = 10

orders = [{"id": i} for i in range(1, TOTAL_ORDERS + 1)]

idempotency_store = {}
client_requests = {}


@app.post("/orders", status_code=201)
def create_order(
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    x_client_id: str = Header("default", alias="X-Client-Id"),
):
    now = time.time()

    history = client_requests.get(x_client_id, [])
    history = [t for t in history if now - t < WINDOW]

    if len(history) >= RATE_LIMIT:
        response.headers["Retry-After"] = "10"
        raise HTTPException(429, "Rate limit exceeded")

    history.append(now)
    client_requests[x_client_id] = history

    if idempotency_key in idempotency_store:
        return idempotency_store[idempotency_key]

    order = {"id": str(uuid4())}

    idempotency_store[idempotency_key] = order

    return order


@app.get("/orders")
def list_orders(limit: int = 10, cursor: str | None = None):

    start = 0

    if cursor:
        start = int(base64.b64decode(cursor).decode())

    end = min(start + limit, TOTAL_ORDERS)

    items = orders[start:end]

    next_cursor = None

    if end < TOTAL_ORDERS:
        next_cursor = base64.b64encode(str(end).encode()).decode()

    return {
        "items": items,
        "next_cursor": next_cursor
    }
