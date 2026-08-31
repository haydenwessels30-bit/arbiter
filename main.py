"""
Arbiter — AI that negotiates your bills so you don't have to.
You only pay when we save you money: 25% of annual savings.
"""
import asyncio
import json
import os
import random
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

# Auto-load .env file so RESEND_API_KEY etc. are always available
def _load_env():
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
_load_env()

from fastapi import (
    FastAPI, File, Form, Request, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Response,
)
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from negotiation.simulator import run_simulated_negotiation
from negotiation import llm
from negotiation.providers import PROVIDERS, find_provider
from customers import (
    add_customer, list_customers, get_customer, update_customer,
    stats as customer_stats, ADMIN_PASSWORD,
)
from email_service import (
    send_customer_confirmation, send_customer_win, send_customer_lost, list_emails,
)

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)
WAITLIST_FILE = DATA_DIR / "waitlist.json"
BILLS_FILE = DATA_DIR / "bills.json"

# Render.com has ephemeral filesystem; ensure data dir is recreated on cold start
DATA_DIR.mkdir(exist_ok=True)
for f in [WAITLIST_FILE, BILLS_FILE]:
    if not f.exists():
        f.write_text("[]")

app = FastAPI(title="Arbiter")
templates = Jinja2Templates(directory=str(BASE / "templates"))
(BASE / "static").mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")

# ---------- Simple cookie auth for admin ----------
# Use a fixed token derived from ADMIN_PASSWORD so cookies survive cold starts.
# The token is HMAC(ADMIN_PASSWORD) — same password = same token every boot.
import hmac, hashlib
def _stable_token(secret: str) -> str:
    return hmac.new(secret.encode(), b"arbiter-admin-token", hashlib.sha256).hexdigest()
ADMIN_TOKEN = _stable_token(ADMIN_PASSWORD)


def _is_admin(request: Request) -> bool:
    token = request.cookies.get("arbiter_admin")
    return bool(token) and hmac.compare_digest(str(token), ADMIN_TOKEN)


def require_admin(request: Request):
    if not _is_admin(request):
        raise HTTPException(401, "Unauthorized")


# ---------- Storage helpers ----------
def load_json(path: Path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default


def save_json(path: Path, data):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, default=str))


# ---------- Bill parsing helpers ----------
def extract_amount(bill_text: str) -> float:
    matches = re.findall(r"\$?(\d{2,4}\.\d{2})", bill_text)
    if matches:
        return max(float(m) for m in matches)
    return 99.99


def extract_acct(bill_text: str) -> str:
    m = re.search(r"(?:account|acct)[^\d]{0,10}(\d{4,})", bill_text, re.IGNORECASE)
    if m:
        return m.group(1)[-4:]
    return str(random.randint(1000, 9999))


GENERIC_META = {
    "competitors": ["competitors at $49-59/mo in the area"],
    "retention_discount_range": (0.15, 0.30),
}


def parse_bill(bill_text: str) -> dict:
    provider = find_provider(bill_text)
    if provider is None:
        amount = extract_amount(bill_text)
        return {
            "provider_key": "generic", "provider": "your provider", "current_rate": amount,
            "acct_last4": extract_acct(bill_text), "tenure": random.randint(3, 12),
            "competitors": GENERIC_META["competitors"], "retention_number": "",
            "typical_discount": GENERIC_META["retention_discount_range"],
        }
    amount = extract_amount(bill_text)
    return {
        "provider_key": provider.key, "provider": provider.display_name,
        "current_rate": amount, "acct_last4": extract_acct(bill_text),
        "tenure": random.randint(3, 12), "competitors": provider.competitors_in_market,
        "retention_number": provider.retention_number,
        "typical_discount": provider.typical_retention_discount_pct,
        "tactics": provider.best_tactics, "fees_to_kill": provider.common_fees_to_kill,
    }


# ---------- Public pages ----------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html",
        context={"llm_mode": "llm" if llm.has_llm() else "scripted"},
    )


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse(request=request, name="signup.html", context={})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse(request=request, name="admin.html", context={})


# ---------- Public API ----------
@app.post("/api/signup")
async def signup(
    name: str = Form(...),
    email: str = Form(...),
    provider_key: str = Form(...),
    provider_name: str = Form(...),
    monthly_amount: float = Form(...),
    account_last4: str = Form(""),
    account_pin: str = Form(""),
    phone: str = Form(""),
    authorized: bool = Form(False),
):
    if not authorized:
        return JSONResponse(
            {"ok": False, "error": "You must authorize Arbiter to negotiate on your behalf"},
            status_code=400,
        )
    cid = add_customer({
        "name": name, "email": email, "phone": phone,
        "provider_key": provider_key, "provider_name": provider_name,
        "monthly_amount": monthly_amount, "account_last4": "", "account_pin": "",
        "authorized": True,
        "currency": PROVIDERS.get(provider_key).currency if PROVIDERS.get(provider_key) else "$",
    })
    try:
        customer = get_customer(cid)
        if customer:
            send_customer_confirmation(customer)
    except Exception as e:
        print(f"Email send error: {e}")
    return JSONResponse({"ok": True, "customer_id": cid})


@app.post("/api/waitlist")
async def waitlist(email: str = Form(...)):
    emails = load_json(WAITLIST_FILE, [])
    if email not in [e.get("email") for e in emails]:
        emails.append({"email": email, "joined": datetime.now(timezone.utc).isoformat()})
        save_json(WAITLIST_FILE, emails)
    return JSONResponse({"ok": True, "position": len(emails)})


@app.get("/api/providers")
async def providers():
    groups = {}
    for p in PROVIDERS.values():
        groups.setdefault(p.category, []).append({
            "key": p.key, "name": p.display_name, "phone": p.retention_number,
            "avg_discount": f"{p.typical_retention_discount_pct[0]}-{p.typical_retention_discount_pct[1]}%",
            "fees": p.common_fees_to_kill,
        })
    return JSONResponse(groups)


@app.post("/api/parse-bill")
async def parse_bill_route(bill: UploadFile = File(...)):
    content = await bill.read()
    text = content.decode("utf-8", errors="ignore")
    return JSONResponse(parse_bill(text))


@app.websocket("/ws/negotiate")
async def websocket_negotiate(ws: WebSocket):
    await ws.accept()
    try:
        data = await ws.receive_json()
    except WebSocketDisconnect:
        return

    name = data.get("name", "Alex")
    provider_key = data.get("provider_key", "generic")
    provider = data.get("provider", "Comcast/Xfinity")
    amount = float(data.get("amount", 99.99))
    competitors = data.get("competitors") or ["Verizon Fios at $49/mo", "T-Mobile 5G Home at $50/mo"]
    tenure = int(data.get("tenure", 6))

    p = PROVIDERS.get(provider_key)
    if p:
        discount_range = (p.typical_retention_discount_pct[0] / 100.0,
                          p.typical_retention_discount_pct[1] / 100.0)
        competitors = p.competitors_in_market
    else:
        discount_range = (0.20, 0.38)

    bills = load_json(BILLS_FILE, [])
    bills.append({
        "name": name, "provider": provider, "amount": amount,
        "received": datetime.now(timezone.utc).isoformat(),
    })
    save_json(BILLS_FILE, bills)

    try:
        async for event in run_simulated_negotiation(
            customer_name=name, provider=provider, current_rate=amount,
            competitors=competitors, tenure=tenure, discount_range=discount_range,
        ):
            await ws.send_json(event)
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await ws.send_json({"type": "error", "text": str(e)})
    finally:
        try:
            await ws.close()
        except Exception:
            pass


@app.get("/api/stats")
async def stats():
    emails = load_json(WAITLIST_FILE, [])
    bills = load_json(BILLS_FILE, [])
    total_sim_savings = 41287.50 + len(bills) * 387.42
    return JSONResponse({
        "waitlist": len(emails), "bills_processed": len(bills),
        "simulated_savings": round(total_sim_savings, 2),
        "llm_enabled": llm.has_llm(),
        "live_calls_ready": bool(os.environ.get("LIVEKIT_API_KEY")),
    })


@app.get("/api/health")
async def health():
    return {"ok": True, "llm_enabled": llm.has_llm(), "live_calls_ready": bool(os.environ.get("LIVEKIT_API_KEY"))}


# ---------- Admin API ----------
@app.post("/api/admin/login")
async def admin_login(request: Request):
    body = await request.json()
    if body.get("password") == ADMIN_PASSWORD:
        resp = JSONResponse({"ok": True})
        resp.set_cookie("arbiter_admin", ADMIN_TOKEN, httponly=True, samesite="lax", max_age=86400 * 7)
        return resp
    return JSONResponse({"ok": False}, status_code=401)


@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    require_admin(request)
    return JSONResponse(customer_stats())


@app.get("/api/admin/customers")
async def admin_customers(request: Request, status: str = "pending"):
    require_admin(request)
    if status == "all":
        return JSONResponse(list_customers())
    return JSONResponse(list_customers(status))


@app.post("/api/admin/update")
async def admin_update(request: Request):
    require_admin(request)
    body = await request.json()
    cid = body.get("id")
    updates = body.get("updates", {})
    old_status = (get_customer(cid) or {}).get("status")
    update_customer(cid, updates)
    customer = get_customer(cid)
    if customer and updates.get("status") == "won" and customer.get("result"):
        r = customer["result"]
        try:
            send_customer_win(customer, float(r["new_rate"]), float(r["annual_savings"]), float(r["our_fee"]))
        except Exception as e:
            print(f"Win email error: {e}")
    elif customer and updates.get("status") == "lost" and old_status != "lost":
        try:
            send_customer_lost(customer)
        except Exception as e:
            print(f"Lost email error: {e}")
    return JSONResponse({"ok": True})


@app.get("/api/admin/emails")
async def admin_emails(request: Request):
    require_admin(request)
    return JSONResponse(list_emails(100))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
