"""
Arbiter Email Service
=====================
Two modes:
1. **Local/founder mode** (no API keys needed): saves emails to data/emails.json
   and displays them in the admin "mailbox" so you can see everything.
2. **Production mode**: if RESEND_API_KEY is set, sends real emails via Resend
   (3,000 emails/day free at resend.com — no credit card required).

All emails are logged regardless of mode so you have a record.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import httpx

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
EMAILS_FILE = DATA_DIR / "emails.json"

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FOUNDER_EMAIL = os.environ.get("ARBITER_FOUNDER_EMAIL", "")  # your email for new signup alerts
FROM_EMAIL = os.environ.get("ARBITER_FROM_EMAIL", "Arbiter <onboarding@resend.dev>")  # set in Resend

# ---- Email templates ----

def customer_confirmation_email(name: str, provider: str, amount: float, cid: str, cur: str = "$") -> dict:
    return {
        "to_name": name,
        "subject": f"Arbiter received your {provider} bill — we're on it",
        "html": f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;">
          <div style="font-size:22px;font-weight:800;margin-bottom:20px;">⚖️ Arbiter</div>
          <h2 style="margin:0 0 12px;">Hi {name},</h2>
          <p style="line-height:1.6;color:#333;">
            We've received your <strong>{provider}</strong> bill ({cur}{amount:.2f}/mo) and added it to our queue.
            Our team will negotiate a lower rate on your behalf within <strong>48 hours</strong>.
          </p>
          <p style="line-height:1.6;color:#333;">
            Here's how it works:
          </p>
          <ul style="line-height:1.8;color:#333;">
            <li>We call {provider} and negotiate with their retention department</li>
            <li>If we need you for identity verification, we'll text you briefly during the call (takes 10 seconds)</li>
            <li>If we succeed, you'll get an email with your new rate and a simple invoice for 25% of your annual savings</li>
            <li><strong>If we don't lower your bill, you pay {cur}0. No catch.</strong></li>
          </ul>
          <p style="line-height:1.6;color:#333;">
            Your confirmation ID: <strong>{cid}</strong>
          </p>
          <p style="line-height:1.6;color:#333;">
            Sit back — we'll be in touch soon.
          </p>
          <p style="color:#888;font-size:13px;margin-top:32px;">
            © 2026 Arbiter · We work for you, not the billers
          </p>
        </div>""",
        "text": f"Hi {name},\n\nWe've received your {provider} bill ({cur}{amount:.2f}/mo) and will negotiate within 48 hours.\nIf we need you for verification, we'll text you during the call.\nIf we don't lower your bill, you pay {cur}0.\n\nConfirmation ID: {cid}\n\n— Arbiter",
    }


def customer_win_email(name: str, provider: str, old_rate: float, new_rate: float, annual_savings: float, our_fee: float, cur: str = "$") -> dict:
    return {
        "to_name": name,
        "subject": f"🎉 We saved you {cur}{annual_savings:.0f}/year on your {provider} bill!",
        "html": f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;">
          <div style="font-size:22px;font-weight:800;margin-bottom:20px;">⚖️ Arbiter</div>
          <div style="background:linear-gradient(135deg,rgba(0,212,168,0.1),rgba(108,92,231,0.1));border:1px solid rgba(0,212,168,0.3);border-radius:12px;padding:20px;margin-bottom:20px;">
            <h2 style="margin:0 0 8px;color:#00b894;">Good news, {name}!</h2>
            <p style="margin:0;font-size:16px;">We just negotiated your {provider} bill down from <strong>{cur}{old_rate:.2f}/mo</strong> to <strong style="color:#00b894;">{cur}{new_rate:.2f}/mo</strong>.</p>
          </div>
          <table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
            <tr><td style="padding:8px 0;color:#666;">Old rate</td><td style="padding:8px 0;text-align:right;">{cur}{old_rate:.2f}/mo</td></tr>
            <tr><td style="padding:8px 0;color:#666;">New rate</td><td style="padding:8px 0;text-align:right;color:#00b894;font-weight:700;">{cur}{new_rate:.2f}/mo</td></tr>
            <tr><td style="padding:8px 0;border-top:1px solid #eee;color:#666;">Annual savings</td><td style="padding:8px 0;border-top:1px solid #eee;text-align:right;color:#00b894;font-weight:700;">{cur}{annual_savings:.2f}</td></tr>
            <tr><td style="padding:8px 0;color:#666;">Our fee (25%)</td><td style="padding:8px 0;text-align:right;">{cur}{our_fee:.2f}</td></tr>
            <tr><td style="padding:8px 0;border-top:2px solid #333;color:#333;font-weight:700;">You keep</td><td style="padding:8px 0;border-top:2px solid #333;text-align:right;color:#6c5ce7;font-weight:800;font-size:18px;">{cur}{annual_savings-our_fee:.2f}</td></tr>
          </table>
          <p style="line-height:1.6;color:#333;">
            The new rate is confirmed for 12 months with no new contract. We'll automatically check back in 11 months to renegotiate before the promo expires.
          </p>
          <p style="line-height:1.6;color:#333;">
            We'll send an invoice for <strong>{cur}{our_fee:.2f}</strong> separately — payable by card, Venmo, or PayPal.
          </p>
          <p style="color:#888;font-size:13px;margin-top:32px;">
            © 2026 Arbiter · We work for you, not the billers
          </p>
        </div>""",
        "text": f"Good news {name}! We negotiated your {provider} bill from {cur}{old_rate:.2f}/mo down to {cur}{new_rate:.2f}/mo — saving you {cur}{annual_savings:.2f}/year. Our 25% fee is {cur}{our_fee:.2f}, you keep {cur}{annual_savings-our_fee:.2f}. We'll send an invoice shortly. — Arbiter",
    }


def customer_lost_email(name: str, provider: str, amount: float, cur: str = "$") -> dict:
    return {
        "to_name": name,
        "subject": f"Update on your {provider} bill negotiation",
        "html": f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;">
          <div style="font-size:22px;font-weight:800;margin-bottom:20px;">⚖️ Arbiter</div>
          <h2 style="margin:0 0 12px;">Hi {name},</h2>
          <p style="line-height:1.6;color:#333;">
            We called {provider} to negotiate your {cur}{amount:.2f}/mo bill but unfortunately weren't able to secure a lower rate this time. Their retention team wouldn't budge today.
          </p>
          <p style="line-height:1.6;color:#333;">
            The good news: <strong>you owe us {cur}0.</strong> We only get paid when we save you money.
          </p>
          <p style="line-height:1.6;color:#333;">
            We'd like to try again in 30 days when a different promotion might be available. Let us know if that's okay.
          </p>
          <p style="color:#888;font-size:13px;margin-top:32px;">© 2026 Arbiter</p>
        </div>""",
        "text": f"Hi {name}, we called {provider} about your {cur}{amount:.2f}/mo bill but couldn't get it lowered this time. You owe us {cur}0. We'll try again in 30 days if that's okay. — Arbiter",
    }


def founder_new_customer_email(customer: dict, cur: str = "$") -> dict:
    return {
        "to_name": "Founder",
        "subject": f"🆕 New customer: {customer['name']} — {customer['provider_name']} ({cur}{customer['monthly_amount']}/mo)",
        "html": f"""
        <div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;padding:24px;">
          <h2>New customer signed up!</h2>
          <table style="width:100%;border-collapse:collapse;">
            <tr><td style="padding:6px 0;color:#666;">Name</td><td style="padding:6px 0;"><strong>{customer['name']}</strong></td></tr>
            <tr><td style="padding:6px 0;color:#666;">Email</td><td style="padding:6px 0;">{customer['email']}</td></tr>
            <tr><td style="padding:6px 0;color:#666;">Phone</td><td style="padding:6px 0;">{customer.get('phone','(not provided)')}</td></tr>
            <tr><td style="padding:6px 0;color:#666;">Provider</td><td style="padding:6px 0;"><strong>{customer['provider_name']}</strong></td></tr>
            <tr><td style="padding:6px 0;color:#666;">Monthly bill</td><td style="padding:6px 0;"><strong>{cur}{customer['monthly_amount']}</strong></td></tr>
            <tr><td style="padding:6px 0;color:#666;">Customer ID</td><td style="padding:6px 0;"><code>{customer['id']}</code></td></tr>
            <tr><td style="padding:6px 0;color:#666;">Signed up</td><td style="padding:6px 0;">{customer['created_at']}</td></tr>
          </table>
          <p style="margin-top:16px;">
            Expected fee if won (at 30% savings, 25% cut): <strong style="color:#00b894;">~${customer['monthly_amount']*0.30*12*0.25:.0f}</strong>
          </p>
          <p><a href="/admin" style="background:#6c5ce7;color:white;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:700;">Open dashboard →</a></p>
        </div>""",
        "text": f"New customer: {customer['name']} ({customer['email']})\nProvider: {customer['provider_name']}\nBill: {cur}{customer['monthly_amount']}/mo\nID: {customer['id']}\nExpected fee: ~${customer['monthly_amount']*0.30*12*0.25:.0f}",
    }


# ---- Send logic ----

def _log_email(to_email: str, subject: str, body_html: str, body_text: str, category: str, sent: bool):
    emails = _load_emails()
    emails.append({
        "to": to_email,
        "subject": subject,
        "html": body_html,
        "text": body_text,
        "category": category,  # "customer_confirmation", "customer_win", "customer_lost", "founder_alert"
        "sent": sent,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_emails(emails)


def _load_emails() -> list:
    if EMAILS_FILE.exists():
        try:
            return json.loads(EMAILS_FILE.read_text())
        except:
            return []
    return []


def _save_emails(emails: list):
    EMAILS_FILE.write_text(json.dumps(emails, indent=2, default=str))


def send_email(to_email: str, subject: str, html: str, text: str, category: str = "general") -> bool:
    """
    Send an email. Logs to mailbox always. Actually sends via Resend if API key is set.
    Returns True if email was actually sent, False if logged only.
    """
    _log_email(to_email, subject, html, text, category, sent=False)

    if RESEND_API_KEY and to_email and "@" in to_email:
        try:
            with httpx.Client(timeout=10) as client:
                r = client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": FROM_EMAIL,
                        "to": [to_email],
                        "subject": subject,
                        "html": html,
                        "text": text,
                    },
                )
                if r.status_code == 200 or r.status_code == 201:
                    # Mark as sent
                    emails = _load_emails()
                    emails[-1]["sent"] = True
                    _save_emails(emails)
                    return True
        except Exception as e:
            print(f"Email send failed: {e}")

    return False


# ---- Convenience functions ----

def send_customer_confirmation(customer: dict):
    cur = customer.get("currency", "$")
    t = customer_confirmation_email(
        customer["name"], customer["provider_name"], float(customer["monthly_amount"]), customer["id"], cur
    )
    send_email(customer["email"], t["subject"], t["html"], t["text"], "customer_confirmation")
    # Also notify founder
    if FOUNDER_EMAIL:
        ft = founder_new_customer_email(customer, customer.get("currency", "$"))
        send_email(FOUNDER_EMAIL, ft["subject"], ft["html"], ft["text"], "founder_alert")


def send_customer_win(customer: dict, new_rate: float, annual_savings: float, our_fee: float):
    cur = customer.get("currency", "$")
    t = customer_win_email(
        customer["name"], customer["provider_name"], float(customer["monthly_amount"]),
        new_rate, annual_savings, our_fee, cur,
    )
    send_email(customer["email"], t["subject"], t["html"], t["text"], "customer_win")


def send_customer_lost(customer: dict):
    cur = customer.get("currency", "$")
    t = customer_lost_email(customer["name"], customer["provider_name"], float(customer["monthly_amount"]), cur)
    send_email(customer["email"], t["subject"], t["html"], t["text"], "customer_lost")


def list_emails(limit: int = 50) -> list:
    return list(reversed(_load_emails()))[:limit]
