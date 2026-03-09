import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from app.db import get_connection

app = FastAPI(title="Phase 2 API")

# Load embedding model once at startup
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Issue types that get a refund vs replacement
REFUND_TYPES = {"duplicate_charge", "refund_request", "late_delivery", "missing_item"}
REPLACEMENT_TYPES = {"warranty", "damaged_item", "defective_product", "wrong_item"}


# ---------- Request models ----------

class ClassifyRequest(BaseModel):
    ticket_text: str

class DraftRequest(BaseModel):
    issue_type: str
    order: dict

class KBSearchRequest(BaseModel):
    query: str
    top_k: int = 3

class RefundPreviewRequest(BaseModel):
    order_id: str
    issue_type: str
    citations: list[str] | None = None

class RefundCommitRequest(BaseModel):
    order_id: str
    amount: float
    issue_type: str

class ReplacementPreviewRequest(BaseModel):
    order_id: str
    issue_type: str
    citations: list[str] | None = None

class ReplacementCommitRequest(BaseModel):
    order_id: str
    issue_type: str


# ---------- Helper ----------

def fetch_order(order_id: str) -> dict | None:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT order_id, customer_name, email, items, order_date, "
        "status, delivery_date, total_amount, currency "
        "FROM orders WHERE order_id = %s",
        (order_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    cols = ["order_id", "customer_name", "email", "items", "order_date",
            "status", "delivery_date", "total_amount", "currency"]
    return dict(zip(cols, row))


# ---------- Health ----------

@app.get("/health")
def health():
    return {"status": "ok"}


# ---------- Orders ----------

@app.get("/orders/get")
def orders_get(order_id: str = Query(...)):
    order = fetch_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders/search")
def orders_search(customer_email: str | None = None, q: str | None = None):
    conn = get_connection()
    cur = conn.cursor()
    cols = ["order_id", "customer_name", "email", "items", "order_date",
            "status", "delivery_date", "total_amount", "currency"]

    if customer_email:
        cur.execute(
            "SELECT order_id, customer_name, email, items, order_date, "
            "status, delivery_date, total_amount, currency "
            "FROM orders WHERE email ILIKE %s",
            (customer_email,)
        )
    elif q:
        cur.execute(
            "SELECT order_id, customer_name, email, items, order_date, "
            "status, delivery_date, total_amount, currency "
            "FROM orders WHERE order_id ILIKE %s OR customer_name ILIKE %s",
            (f"%{q}%", f"%{q}%")
        )
    else:
        raise HTTPException(status_code=400, detail="Provide customer_email or q")

    results = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return {"results": results}


# ---------- Classify ----------

@app.post("/classify/issue")
def classify_issue(body: ClassifyRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT keyword, issue_type FROM issues")
    rules = cur.fetchall()
    cur.close()
    conn.close()

    text = body.ticket_text.lower()
    for keyword, issue_type in rules:
        if keyword.lower() in text:
            return {"issue_type": issue_type, "confidence": 0.85}

    return {"issue_type": "general_inquiry", "confidence": 0.1}


# ---------- Reply ----------

@app.post("/reply/draft")
def reply_draft(body: DraftRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT template FROM replies WHERE issue_type = %s", (body.issue_type,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    template = row[0] if row else "Hi {{customer_name}}, we are reviewing order {{order_id}}."
    reply = template.replace("{{customer_name}}", body.order.get("customer_name", "Customer"))
    reply = reply.replace("{{order_id}}", body.order.get("order_id", ""))
    return {"reply_text": reply}


# ---------- KB search (pgvector semantic search) ----------

@app.post("/kb/search")
def kb_search(body: KBSearchRequest):
    embedding = embedder.encode(body.query).tolist()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT doc_id, file, text,
               1 - (embedding <=> %s::vector) AS similarity
        FROM policy_chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (embedding, embedding, body.top_k)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = [
        {
            "doc_id": r[0],
            "file": r[1],
            "text": r[2],
            "similarity": round(float(r[3]), 4)
        }
        for r in rows
    ]
    citations = list({r["file"] for r in results})
    return {"results": results, "citations": citations}


# ---------- Payment stubs ----------

@app.post("/refund/preview")
def refund_preview(body: RefundPreviewRequest):
    order = fetch_order(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    amount = float(order["total_amount"])
    # Partial refund for late delivery per policy
    if body.issue_type == "late_delivery":
        amount = round(amount * 0.5, 2)

    return {
        "order_id": body.order_id,
        "customer_name": order["customer_name"],
        "issue_type": body.issue_type,
        "refund_amount": amount,
        "currency": order["currency"],
        "status": "pending_approval"
    }


@app.post("/refund/commit")
def refund_commit(body: RefundCommitRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO triage_log (order_id, issue_type, final_status) VALUES (%s, %s, %s)",
        (body.order_id, body.issue_type, "refund_committed")
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"order_id": body.order_id, "amount": body.amount, "status": "refund_committed"}


@app.post("/replacement/preview")
def replacement_preview(body: ReplacementPreviewRequest):
    order = fetch_order(body.order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    items = order.get("items") or []
    item_name = items[0]["name"] if items else "item"

    return {
        "order_id": body.order_id,
        "customer_name": order["customer_name"],
        "issue_type": body.issue_type,
        "replacement_item": item_name,
        "status": "pending_approval"
    }


@app.post("/replacement/commit")
def replacement_commit(body: ReplacementCommitRequest):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO triage_log (order_id, issue_type, final_status) VALUES (%s, %s, %s)",
        (body.order_id, body.issue_type, "replacement_authorized")
    )
    conn.commit()
    cur.close()
    conn.close()
    return {"order_id": body.order_id, "status": "replacement_authorized"}
