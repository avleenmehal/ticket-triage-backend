#!/usr/bin/env python3
"""
Seed script: loads mock JSON data into PostgreSQL and embeds policy chunks.
Run once before starting the server:
    python scripts/seed_db.py
"""

import json
import os
import psycopg2
from psycopg2.extras import Json
from sentence_transformers import SentenceTransformer

DB_URL = os.getenv("DATABASE_URL", "postgresql://localhost/viridien")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOCK_DIR = os.path.join(BASE_DIR, "mock_data")


def load_json(filename):
    with open(os.path.join(MOCK_DIR, filename), "r") as f:
        return json.load(f)


def seed(conn):
    cur = conn.cursor()

    # --- Customers (must be seeded before support_tickets due to FK) ---
    customers = load_json("customers.json")
    cur.execute("DELETE FROM support_tickets")
    cur.execute("DELETE FROM customers")
    for c in customers:
        cur.execute(
            "INSERT INTO customers (email, name, risk_tier) VALUES (%s, %s, %s)",
            (c["email"], c["name"], c["risk_tier"]),
        )
    print(f"Seeded {len(customers)} customers")

    # --- Orders ---
    orders = load_json("orders.json")
    cur.execute("DELETE FROM orders")
    for o in orders:
        cur.execute(
            """
            INSERT INTO orders (order_id, customer_name, email, items, order_date,
                                status, delivery_date, total_amount, currency)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                o["order_id"],
                o["customer_name"],
                o["email"],
                Json(o["items"]),
                o["order_date"],
                o["status"],
                o.get("delivery_date"),
                o["total_amount"],
                o.get("currency", "USD"),
            ),
        )
    print(f"Seeded {len(orders)} orders")

    # --- Issues ---
    issues = load_json("issues.json")
    cur.execute("DELETE FROM issues")
    for i in issues:
        cur.execute(
            "INSERT INTO issues (keyword, issue_type) VALUES (%s, %s)",
            (i["keyword"], i["issue_type"]),
        )
    print(f"Seeded {len(issues)} issues")

    # --- Replies ---
    replies = load_json("replies.json")
    cur.execute("DELETE FROM replies")
    for r in replies:
        cur.execute(
            "INSERT INTO replies (issue_type, template) VALUES (%s, %s)",
            (r["issue_type"], r["template"]),
        )
    print(f"Seeded {len(replies)} replies")

    # CHUNKING OF THE POLICY.md FILES AND EMBEDDING
    policy_index = load_json("policy_index.json")
    chunks = policy_index["docs"]

    print(f"Loading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    cur.execute("DELETE FROM policy_chunks")
    for chunk in chunks:
        embedding = model.encode(chunk["text"]).tolist()
        cur.execute(
            """
            INSERT INTO policy_chunks (doc_id, file, text, embedding)
            VALUES (%s, %s, %s, %s)
            """,
            (chunk["doc_id"], chunk["file"], chunk["text"], embedding),
        )
    print(f"Seeded {len(chunks)} policy chunks with embeddings")

    # --- Support Tickets ---
    tickets = load_json("support_tickets.json")
    for t in tickets:
        cur.execute(
            """
            INSERT INTO support_tickets
                (customer_email, order_id, ticket_text, ticket_type, issue_type,
                 requested_at, outcome, resolution, abuse_label)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                t["customer_email"],
                t["order_id"],
                t["ticket_text"],
                t["ticket_type"],
                t["issue_type"],
                t["requested_at"],
                t["outcome"],
                Json(t["resolution"]) if t.get("resolution") else None,
                t["abuse_label"],
            ),
        )
    print(f"Seeded {len(tickets)} support tickets")

    conn.commit()
    cur.close()
    print("Done.")


if __name__ == "__main__":
    conn = psycopg2.connect(DB_URL)
    try:
        seed(conn)
    finally:
        conn.close()
