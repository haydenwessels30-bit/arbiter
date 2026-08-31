"""
Arbiter Founder Mode — Customer signup + admin queue + negotiation playbooks
"""
import json
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CUSTOMERS_FILE = DATA_DIR / "customers.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
ADMIN_PASSWORD = os.environ.get("ARBITER_ADMIN_PASSWORD", "arbiter2026")


def _load(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default


def _save(path: Path, data):
    path.write_text(json.dumps(data, indent=2, default=str))


def add_customer(data: dict) -> str:
    """Create a customer record, returns customer_id."""
    customers = _load(CUSTOMERS_FILE, [])
    cid = f"cus_{secrets.token_hex(6)}"
    record = {
        "id": cid,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",  # pending → negotiating → won → lost → paid
        "name": data.get("name", "").strip(),
        "email": data.get("email", "").strip().lower(),
        "phone": data.get("phone", "").strip(),
        "provider_key": data.get("provider_key", ""),
        "provider_name": data.get("provider_name", ""),
        "monthly_amount": float(data.get("monthly_amount", 0)),
        "account_last4": data.get("account_last4", ""),
        "account_pin": data.get("account_pin", ""),
        "bill_filename": data.get("bill_filename", ""),
        "notes": data.get("notes", ""),
        "authorized": bool(data.get("authorized")),
        "agreed_at": datetime.now(timezone.utc).isoformat() if data.get("authorized") else None,
        "result": None,  # {"new_rate": float, "savings": float, "call_date": str, "notes": str}
    }
    customers.append(record)
    _save(CUSTOMERS_FILE, customers)
    return cid


def list_customers(status: Optional[str] = None) -> list:
    customers = _load(CUSTOMERS_FILE, [])
    if status:
        customers = [c for c in customers if c.get("status") == status]
    return sorted(customers, key=lambda c: c["created_at"], reverse=True)


def get_customer(cid: str) -> Optional[dict]:
    for c in list_customers():
        if c["id"] == cid:
            return c
    return None


def update_customer(cid: str, updates: dict):
    customers = _load(CUSTOMERS_FILE, [])
    for c in customers:
        if c["id"] == cid:
            c.update(updates)
            c["updated_at"] = datetime.now(timezone.utc).isoformat()
            break
    _save(CUSTOMERS_FILE, customers)


def stats() -> dict:
    customers = list_customers()
    won = [c for c in customers if c.get("status") == "paid" or (c.get("result") and c.get("status") == "won")]
    total_saved = sum((c.get("result") or {}).get("annual_savings", 0) for c in won)
    total_revenue = sum((c.get("result") or {}).get("our_fee", 0) for c in won)
    return {
        "total_customers": len(customers),
        "pending": len([c for c in customers if c["status"] == "pending"]),
        "negotiating": len([c for c in customers if c["status"] == "negotiating"]),
        "won": len(won),
        "lost": len([c for c in customers if c["status"] == "lost"]),
        "total_saved_customers": round(total_saved, 2),
        "total_revenue": round(total_revenue, 2),
    }
