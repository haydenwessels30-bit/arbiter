# 💰 Founder Mode: How to Make Money This Week

You don't need AI voice agents to make your first $1,000.
You just need a phone and this playbook.

## The "Do Things That Don't Scale" Launch Plan

This is exactly how Airbnb, Uber, Stripe, and many billion-dollar companies started: founders did the work manually until they had cash to build the automation.

### Step 1: Launch today (right now)
- Arbiter is running on your machine.
- Deploy it to the internet using Render.com or Fly.io (both have free tiers, takes 10 minutes).
- You get a public URL like `https://arbiter.onrender.com`.
- Change the admin password first: set the `ARBITER_ADMIN_PASSWORD` environment variable to something secure.

### Step 2: Get your first 5 customers (today)
- Text 10 friends: "I built a thing that calls Comcast and negotiates your bill down. If I save you money I take 25%, if not you pay $0. Wanna try?"
- Post on your Facebook/Instagram: same message.
- Post on r/personalfinance or your local subreddit: "I built an AI that negotiates internet bills, beta-testing for free for the first 10 people (I just want feedback)".
- You will get signups within hours.

### Step 3: Call their billers for them (this week)
- Go to /admin, see who signed up.
- The dashboard gives you:
  - The phone number to call (retention line)
  - The customer's account last-4 and PIN
  - A step-by-step playbook of exactly what to say
  - The competitor rates to cite
- Call Comcast/Verizon/whoever using the playbook. It takes 8-10 minutes per call.
- When you get them a discount, enter the new rate in the dashboard.
- Email the customer: "Good news — I got your bill down to $X/mo, saving you $Y/yr. Your invoice for 25% ($Z) is attached."
- Send them a Stripe invoice (or Venmo/PayPal request). Collect the money.

### Step 4: Do the math
- Each 8-minute call saves ~$400/yr for the customer.
- Your fee: ~$100 per successful call.
- If you do 5 calls per hour, that's ~$500/hour.
- Win rate: 7 out of 10 calls (use the playbook, this is realistic).
- Even if you only do 5 customers in your first week, that's ~$500 cash in your pocket for ~1 hour of work.

### Step 5: Use the cash to build the AI
- Once you've done 20 manual calls and have $2,000 in the bank:
  1. Get free API keys for LiveKit, Deepgram, Gemini (see FREE_STARTER_GUIDE.md)
  2. Spend 1-2 weeks wiring real AI calls in voice_engine.py
  3. Deploy — now the AI calls for you
  4. You handle customer support and the AI does the work
- Keep doing manual calls for edge cases the AI can't handle yet.

### Step 6: Scale
- Post the demo video on TikTok/Reels/Shorts (just screen-record the AI negotiating). It's viral content — watching AI fight with Comcast is catnip for social media.
- Spend $50 on Facebook ads targeted at people who like "I Hate Comcast" pages. If you pay $10 per acquired customer and make $100 per win, that's 10x ROAS.
- Add categories: mobile, TV, medical, insurance.
- Build auto-renegotiation (call back every 12 months) — that's recurring revenue per customer with zero new acquisition cost.

## The Manual Call Script (What to Actually Say)

Don't overthink this. The person on the other end is a call center employee who does this 8 hours a day. Be polite, persistent, and use these exact lines:

### OPENING:
"Hi, my name is [your name], I'm calling on behalf of [customer name] regarding account ending in [last 4]. I'd like to discuss their monthly rate — they've noticed it's gone up recently and we'd like to review available promotions."

### WHEN THEY OFFER A TINY DISCOUNT ($5-10 off):
"I appreciate that, but I'm looking at new customer rates for [competitor] at $[X]/month in their area. As a [N]-year customer with zero late payments, can we get closer to the new customer rate?"

### IF THEY RESIST:
"I understand. At that rate we're going to have to switch to [competitor]. Before I do that, can you transfer me to your Retention or Cancellations department?"

### ONCE YOU'RE WITH RETENTION:
"Hi — I'm calling because [customer name] is ready to switch to [competitor] at $[X]/month today unless we can get their rate closer to new-customer pricing. What's the best you can do to keep them?"

### WHEN THEY OFFER MEDIUM DISCOUNT:
"That's a step. Can you also waive the equipment fee and lock this for 12 months? If we can get to $[target] with no equipment fee and no new contract, we'll stay."

### CLOSING:
"Great. Can you confirm: $[new rate]/month for 12 months, no new contract, and you'll send a confirmation email to the account? Perfect. Thank you."

### KEY RULES:
- Never be rude.
- Always ask for Retention — frontline reps have almost no discount authority.
- Mention a specific competitor by name (T-Mobile 5G Home is the most effective against Comcast/Spectrum/Verizon).
- Decline "free streaming" offers — insist on bill credit.
- Always confirm: new rate, months locked, no new contract, email confirmation.
- If one rep won't budge, hang up, call back in 10 minutes — different reps have different moods.

## How to Handle Payments

- Use Stripe to send invoices (takes 10 minutes to set up, 2.9%+30¢ per transaction).
- Or just use Venmo/PayPal for the first 10 customers.
- Invoice 25% of annual savings AFTER you confirm the rate landed.
- Give customers 7 days to pay (this is completely reasonable since they're saving money).

## What NOT to Do

- Don't pretend to BE the customer. Say "calling on behalf of [name]."
- Don't lie about having already canceled.
- Don't threaten legal action.
- Don't agree to new contracts, service changes, or additional equipment.
- Don't promise anything before you call — set expectations that you'll "try to lower their bill" not "guarantee X% off."

## What Happens After 50 Customers

Once you've done 50 real calls manually:
1. You know exactly what works against each provider (this is gold).
2. You have real testimonials and case studies to use in marketing.
3. You've made ~$3,000-5,000 to invest in automating.
4. You can train the AI on your own successful calls.
5. You have a repeatable sales pitch ("we've saved X customers $Y")
6. You can afford to hire a VA in the Philippines for $3/hr to make calls while you sleep.

The real AI comes last. First you prove that people will pay you, then you automate.
