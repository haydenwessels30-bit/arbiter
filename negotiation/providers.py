"""
Arbiter Provider Knowledge Base
================================
Real data on major US telecom/bill providers — retention department numbers,
current new-customer pricing, competitor offers, typical discount ranges, and
tactics Arbiter uses to win. This is the data moat — it compounds as we run
real calls and learn what actually works.

All retention numbers below are publicly listed or commonly reported. We
verify numbers before live calls; if a number fails we fall back to the
main support line and ask for Retention.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Provider:
    key: str
    display_name: str
    category: str           # "internet", "mobile", "tv", "medical", "insurance"
    retention_number: str   # Direct retention line if known
    support_number: str     # Main support
    currency: str = "$"     # "$" for US, "R" for SA
    # Known levers / new customer offers we can reference
    new_customer_rates: list[str] = field(default_factory=list)
    competitors_in_market: list[str] = field(default_factory=list)
    typical_retention_discount_pct: tuple = (20, 40)  # (low, high)
    best_tactics: list[str] = field(default_factory=list)
    common_fees_to_kill: list[str] = field(default_factory=list)
    notes: str = ""


PROVIDERS: dict[str, Provider] = {
    "comcast": Provider(
        key="comcast",
        display_name="Comcast/Xfinity",
        category="internet",
        retention_number="1-800-934-6489",   # Xfinity main; press 4 for Cancel
        support_number="1-800-934-6489",
        new_customer_rates=[
            "Connect $19.99/mo (75Mbps) for 2 years",
            "Fast/Superfast $55/mo (800Mbps-1.2Gbps) for 2 years with 1-year agreement",
            "Gigabit $65/mo for 2 years",
        ],
        competitors_in_market=[
            "Verizon Fios starting at $49.99/mo",
            "Astound/RCN starting at $25-50/mo",
            "T-Mobile 5G Home Internet $50/mo (no contract, price lock)",
            "AT&T Fiber $55/mo",
        ],
        typical_retention_discount_pct=(25, 45),
        best_tactics=[
            "Mention you're switching to T-Mobile 5G Home specifically (Comcast hates T-Mobile most because it's no-contract)",
            "Ask for the 'Gigabit Promo' or 'Loyalty Rate' — retention reps have explicit codes",
            "Get equipment fee ($15/mo) waived — they almost always concede this if pushed",
            "Mention competitor pricing in your exact zip code",
            "Politely decline any 'free streaming bundles' — insist on bill credit instead",
            "Refuse 6-month promos; demand 12 months minimum",
        ],
        common_fees_to_kill=["xFi gateway/equipment rental ($15)", "Broadcast TV fee", "Regional sports fee"],
        notes="Xfinity retention is authorized up to ~40% off. Always ask for a supervisor if the first rep won't go below $15 off.",
    ),

    "spectrum": Provider(
        key="spectrum",
        display_name="Spectrum/Charter",
        category="internet",
        retention_number="1-833-267-6094",
        support_number="1-833-267-6094",
        new_customer_rates=[
            "Internet $49.99/mo for 12 months (300Mbps)",
            "Internet Ultra $69.99/mo for 12 months (500Mbps-1Gbps)",
        ],
        competitors_in_market=[
            "T-Mobile 5G Home Internet $50/mo (price-for-life)",
            "Verizon Fios $49.99/mo",
            "Astound $25-50/mo where available",
            "Starlink (for rural) $90/mo",
        ],
        typical_retention_discount_pct=(20, 40),
        best_tactics=[
            "Spectrum is highly vulnerable to T-Mobile 5G Home — lead with this",
            "Ask for the 'Spectrum One' promo rate",
            "Get WiFi equipment fee ($5/mo) waived — they will",
            "Push for 24-month lock (they can do it, but you have to ask)",
            "They offer 'existing customer promos' that don't require switching — ask directly",
        ],
        common_fees_to_kill=["WiFi equipment ($5)", "TV Broadcast surcharge"],
        notes="Spectrum doesn't do contracts, which gives them less leverage but also makes it easier to leave. Threaten cancellation hard.",
    ),

    "verizon": Provider(
        key="verizon",
        display_name="Verizon",
        category="internet",
        retention_number="1-800-922-0204",
        support_number="1-800-837-4966",
        new_customer_rates=[
            "Fios 300 $49.99/mo",
            "Fios 500 $69.99/mo",
            "Fios 1 Gig $89.99/mo",
            "5G Home $50/mo (with mobile), $70 standalone",
        ],
        competitors_in_market=[
            "Xfinity $55/mo",
            "T-Mobile 5G Home $50/mo",
            "Astound $25-50/mo",
        ],
        typical_retention_discount_pct=(15, 30),
        best_tactics=[
            "Lead with T-Mobile Home Internet ($50/mo price lock)",
            "If you have Verizon mobile, ask for the 'mobile + home' bundle discount ($25/mo)",
            "Ask for 'Loyalty Discount' (explicit code they can apply)",
            "Push for free router rental (they charge $15/mo otherwise)",
            "Verizon gives better deals if you have auto-pay and paperless — confirm you have both",
        ],
        common_fees_to_kill=["Router rental ($15)", "Fios TV surcharges"],
        notes="Verizon retention is generally less flexible than Comcast but their competitor T-Mobile is the biggest lever.",
    ),

    "att": Provider(
        key="att",
        display_name="AT&T",
        category="internet",
        retention_number="1-800-288-2020",
        support_number="1-800-288-2020",
        new_customer_rates=[
            "Internet 300 $55/mo",
            "Internet 500 $65/mo",
            "Internet 1000 $80/mo",
            "Internet 2000 $120/mo",
            "AirTies 5G $55/mo",
        ],
        competitors_in_market=[
            "Xfinity $55/mo",
            "Spectrum $49.99/mo",
            "T-Mobile 5G Home $50/mo",
            "Verizon Fios $49.99/mo",
        ],
        typical_retention_discount_pct=(15, 30),
        best_tactics=[
            "Ask for 'Retention Department' or 'Customer Loyalty' directly",
            "Reference the $55/mo fiber promo for new customers",
            "Push for free gateway rental ($10/mo)",
            "Ask about the $10/mo auto-pay + paperless discount",
            "Ask for a one-time $50+ credit on top of any monthly discount",
        ],
        common_fees_to_kill=["Equipment rental ($10)", "Internet infrastructure fee"],
        notes="AT&T retention is tougher; they often push 'call back later' or require multiple calls. Polite persistence wins.",
    ),

    # ===== MOBILE CARRIERS =====
    "verizon_mobile": Provider(
        key="verizon_mobile",
        display_name="Verizon Wireless",
        category="mobile",
        retention_number="1-800-922-0204",
        support_number="1-800-922-0204",
        new_customer_rates=[
            "Unlimited Welcome $65/mo/line (or $30 with 4+ lines)",
            "Unlimited Plus $80/mo/line",
        ],
        competitors_in_market=[
            "T-Mobile Go5G $75/mo with Netflix included",
            "Mint Mobile $15-30/mo (T-Mobile network)",
            "Visible $25-45/mo (Verizon network)",
            "AT&T Value Plus $50/mo single line",
            "Cricket $30/mo (AT&T network)",
        ],
        typical_retention_discount_pct=(15, 30),
        best_tactics=[
            "Lead with T-Mobile's Netflix/Apple TV+ included offer",
            "Ask for the 'loyalty plan' not advertised on website",
            "Reference that Visible uses Verizon's own network for half the price",
            "Push for device upgrade credits and free streaming bundle",
            "Threaten to port to T-Mobile (they can see the MNP pre-port request)",
            "If you have multiple lines, mention total account value",
        ],
        common_fees_to_kill=["Upgrade support fee ($35)", "Device insurance if unused"],
        notes="Verizon Wireless retention has authority to give up to 20-30% off + perks.",
    ),

    "tmobile": Provider(
        key="tmobile",
        display_name="T-Mobile",
        category="mobile",
        retention_number="1-800-937-8997",
        support_number="1-800-937-8997",
        new_customer_rates=[
            "Go5G $75/mo",
            "Go5G Plus $90/mo",
            "Essentials $60/mo",
        ],
        competitors_in_market=[
            "Mint Mobile $15/mo",
            "Visible $25/mo",
            "Verizon Welcome $65/mo",
            "AT&T Value Plus $50/mo",
        ],
        typical_retention_discount_pct=(10, 25),
        best_tactics=[
            "T-Mobile already positions itself as low-cost — harder to negotiate, but they have 'insider' promos",
            "Ask for the 'Insider Discount' (20% off for affiliated groups — almost anyone qualifies)",
            "Ask for free line promotions (they frequently offer BOGO free lines)",
            "Push for Netflix/Apple TV+/MLB.TV bundle activation if you don't have it",
        ],
        common_fees_to_kill=["Device protection if unused", "SIM card fees"],
        notes="T-Mobile's 'price lock' promise means once you have a rate they can't raise it, but existing customers miss out on new promos.",
    ),

    "att_mobile": Provider(
        key="att_mobile",
        display_name="AT&T Wireless",
        category="mobile",
        retention_number="1-800-331-0500",
        support_number="1-611 (from AT&T phone)",
        new_customer_rates=[
            "Value Plus $50/mo single line",
            "Unlimited Starter $65/mo",
            "Unlimited Extra $75/mo",
        ],
        competitors_in_market=[
            "T-Mobile Go5G $75/mo with Netflix",
            "Verizon Welcome $65/mo",
            "Mint Mobile $30/mo",
            "Cricket $30/mo (AT&T MVNO)",
        ],
        typical_retention_discount_pct=(15, 30),
        best_tactics=[
            "Ask for the 'Signature Program' discount (employees of many companies qualify for 15% off)",
            "Push for the $50 Value Plus plan if you're on a more expensive older plan",
            "Ask for 'loyalty credits' ($10-20/mo)",
            "Threaten to port to T-Mobile or switch to Cricket (their own MVNO)",
            "Get upgrade fees waived",
        ],
        common_fees_to_kill=["Upgrade fee ($45)", "Administrative fee ($1.99/mo)"],
        notes="AT&T Wireless retention has decent flexibility, especially for customers on older plans.",
    ),

    # ===== TV / CABLE =====
    "directv": Provider(
        key="directv",
        display_name="DirecTV/DirecTV Stream",
        category="tv",
        retention_number="1-800-531-5000",
        support_number="1-800-531-5000",
        new_customer_rates=["Entertainment $64.99/mo (promo)", "Choice $84.99/mo (promo)"],
        competitors_in_market=["YouTube TV $72.99/mo", "Hulu + Live TV $76.99/mo", "Sling $40/mo", "Fubo $79.99/mo"],
        typical_retention_discount_pct=(30, 60),
        best_tactics=[
            "Cable/satellite TV is the most negotiable category — threaten to cancel and switch to streaming",
            "Retention regularly offers $40-60/mo off to keep satellite customers",
            "Push for free NFL Sunday Ticket / premium channels (HBO/Max, Showtime) for 3-6 months",
            "Get free DVR / equipment upgrade",
        ],
        common_fees_to_kill=["Regional sports fee ($9-15)", "HD access fee", "Advanced receiver fee ($15)"],
        notes="TV retention is the easiest to win big. They know most customers are leaving for streaming.",
    ),

    "dish": Provider(
        key="dish",
        display_name="DISH Network",
        category="tv",
        retention_number="1-866-974-0781",
        support_number="1-800-333-3474",
        new_customer_rates=["Flex Pack $57.99/mo (promo)", "America's Top 120 $84.99/mo"],
        competitors_in_market=["DirecTV promotional rates", "YouTube TV $72.99/mo", "Hulu Live $76.99/mo"],
        typical_retention_discount_pct=(30, 50),
        best_tactics=[
            "Ask for the 'Customer Loyalty Department' specifically",
            "DISH retention has the most aggressive discounting in the industry",
            "Reference YouTube TV as your planned switch (no equipment, no contract)",
            "Ask for free premium channels + free Hopper upgrade",
        ],
        common_fees_to_kill=["Regional sports", "Whole-home DVR fee"],
        notes="",
    ),

    # ===== HOME SECURITY =====
    "adt": Provider(
        key="adt",
        display_name="ADT",
        category="home_security",
        retention_number="1-800-238-2727",
        support_number="1-800-238-2727",
        new_customer_rates=["Self-setup $24.99/mo", "Smart Home $49.99/mo"],
        competitors_in_market=["SimpliSafe $17.99/mo no contract", "Ring Alarm $20/mo", "Vivint $39.99/mo", "Cove $17.99/mo"],
        typical_retention_discount_pct=(20, 40),
        best_tactics=[
            "ADT is highly vulnerable to no-contract competitors (SimpliSafe, Ring)",
            "Push for equipment upgrade and free installation credits",
            "Demand removal of any auto-renewal contract",
            "Ask for monitoring rate match to SimpliSafe",
        ],
        common_fees_to_kill=["Cellular communicator fee", "Service fee increases at renewal"],
        notes="",
    ),

    # ===== SOUTH AFRICA — MOBILE =====
    "vodacom": Provider(
        key="vodacom",
        display_name="Vodacom",
        category="za_mobile",
        retention_number="082 135 (retentions)",
        support_number="082 111",
        currency="R",
        new_customer_rates=[
            "Smart Data+ 1GB R79/mo",
            "Smart Data+ 3GB R149/mo",
            "Smart Data+ 10GB R299/mo",
            "Red VIP R699/mo (unlimited)",
            "uChoose Flexi from R49/mo",
        ],
        competitors_in_market=[
            "MTN Mega Gigs from R59/mo (more data per rand)",
            "Cell C from R50/mo (often cheaper)",
            "Telkom Mobile data bundles up to 50% cheaper",
            "RAIN 5G from R299/mo (unlimited data)",
            "MVNOs like Mr Price Mobile, Me&You Mobile on Cell C/MTN network",
        ],
        typical_retention_discount_pct=(20, 35),
        best_tactics=[
            "Dial 082 135 and ask for 'Contract Cancellations / Retentions Department' directly",
            "Mention MTN's current deals — Vodacom hates losing to MTN",
            "Ask for the 'Loyalty Offer' or 'Customer Value Management (CVM)' discount — these are unadvertised",
            "Push for free data bundles added (they often give 1-5GB free per month rather than cut price)",
            "Mention you've been a paying customer for X years (tenure matters — they have access to this)",
            "If out of contract, say you're porting to MTN/Crain and they'll escalate",
            "Ask for any device payment settlement discount if upgrading",
            "Decline the first offer ('we can give you 500MB free data') — push harder",
        ],
        common_fees_to_kill=["Out-of-bundle rates (ask for Data Lock/stopper)", "SIM swap fees", "Admin/connection fee at renewal"],
        notes="Vodacom's Contract Cancellations dept (082 135) can give up to 30-35% off or massive free data bundles. Calling 082 111 gets normal support; ask for retentions.",
    ),

    "mtn": Provider(
        key="mtn",
        display_name="MTN",
        category="za_mobile",
        retention_number="083 135 (retentions/cancellations)",
        support_number="083 135 / 083 801 2373 (Cancellations)",
        currency="R",
        new_customer_rates=[
            "Mega Gigs 1GB R59/mo",
            "Mega Gigs 3GB R99/mo",
            "Mega Gigs 10GB R199/mo",
            "My MTN Choice from R90/mo",
            "MTN Sky Unlimited R799/mo",
        ],
        competitors_in_market=[
            "Vodacom Smart Data+ from R79/mo (sometimes bigger promos)",
            "Telkom Mobile data much cheaper (10GB R99)",
            "Cell C from R50/mo with aggressive data promos",
            "RAIN 5G from R299/mo",
        ],
        typical_retention_discount_pct=(15, 30),
        best_tactics=[
            "Call 083 801 2373 for Cancellations/Retention directly",
            "Mention Telkom's data prices for pure data users",
            "Ask for 'CVM team' (Customer Value Management) — they have the best deals",
            "MTN is aggressive on giving FREE data bundles (5GB-20GB) rather than price cuts",
            "Push for device upgrade credit or early upgrade eligibility",
            "Reference that Vodacom has network parity and better current promotions",
        ],
        common_fees_to_kill=["Out-of-bundle data (ask for Data Manager/Limit)", "SIM card fee", "Admin fee at upgrade"],
        notes="MTN retention flexibility is strong; they give big data bundles to keep customers. Price cuts are harder but possible with persistence.",
    ),

    "cellc": Provider(
        key="cellc",
        display_name="Cell C",
        category="za_mobile",
        retention_number="084 135",
        support_number="084 135 / 084 140",
        currency="R",
        new_customer_rates=[
            "Home Connecta Flexi from R50/mo",
            "Mega Data 5GB R99/mo",
            "Straight Up from R149/mo",
            "Supacharge 10GB R199/mo",
        ],
        competitors_in_market=[
            "Vodacom Smart Data+ from R79",
            "MTN Mega Gigs from R59",
            "Mr Price Mobile (MVNO, same network) cheaper",
            "Telkom Mobile data bundles cheaper",
        ],
        typical_retention_discount_pct=(25, 40),
        best_tactics=[
            "Cell C is the smallest of the big 3 and most desperate to keep customers",
            "Ask for 'Loyalty' or 'Retention' department",
            "Push hard for price cuts — they can undercut Vodacom/MTN",
            "Mention moving to MTN/Vodacom for better coverage",
            "Ask for free minutes + data bundles on top of any discount",
        ],
        common_fees_to_kill=["Out-of-bundle data", "Monthly admin fee"],
        notes="Cell C's smaller market share makes them highly negotiable.",
    ),

    "telkom_mobile": Provider(
        key="telkom_mobile",
        display_name="Telkom Mobile",
        category="za_mobile",
        retention_number="081 180 (support) → ask for Retentions",
        support_number="081 180",
        currency="R",
        new_customer_rates=[
            "FreeMe 500MB R39/mo",
            "FreeMe 2GB R79/mo",
            "FreeMe 10GB R139/mo",
            "FreeMe Unlimited R749/mo",
            "SmartBroadband wireless from R199",
        ],
        competitors_in_market=[
            "MTN Mega Gigs R99 for 3GB (better network)",
            "Vodacom Smart Data+ R79",
            "RAIN 5G R299 unlimited",
            "Cell C Home Connecta R50",
        ],
        typical_retention_discount_pct=(20, 35),
        best_tactics=[
            "Telkom is price-competitive already but struggles with network quality complaints",
            "Lead with MTN/Vodacom network quality",
            "Push for more data rather than price cuts — they give generous bundles",
            "Ask for free Mo'Nice/surprise bundles (Telkom's loyalty promos)",
            "If on a contract, push for contract buyout or free months",
        ],
        common_fees_to_kill=["Out-of-bundle rates", "SIM/connection fee"],
        notes="",
    ),

    # ===== SOUTH AFRICA — FIBRE/INTERNET =====
    "telkom_fibre": Provider(
        key="telkom_fibre",
        display_name="Telkom Fibre/LTE",
        category="za_internet",
        retention_number="081 180 → ask for Retentions/Cancellations",
        support_number="10210 (landline) / 081 180",
        currency="R",
        new_customer_rates=[
            "LTE 50GB R299/mo",
            "Fibre 10Mbps R399/mo",
            "Fibre 20Mbps R499/mo",
            "Fibre 50Mbps R699/mo",
            "Fibre 100Mbps R899/mo",
            "Uncapped 100Mbps promo R699/mo",
        ],
        competitors_in_market=[
            "Vumatel/Afrihost 50Mbps R497/mo uncapped",
            "Webafrica 50Mbps R499/mo",
            "Cool Ideas 50Mbps R499/mo",
            "RAIN 5G Standard R399/mo, Premium R699",
            "Supersonic (MTN) Fibre from R499/mo",
            "Openserve/Cybersmart 100Mbps R599/mo",
        ],
        typical_retention_discount_pct=(15, 30),
        best_tactics=[
            "Lead with Afrihost or Webafrica pricing — these ISPs are very aggressive",
            "If you're on Openserve/Vumatel network, you can actually switch ISPs without a re-install — mention this",
            "Ask for the 'current uncapped promotion' (they have rolling R699 100Mbps deals)",
            "Push for free installation/activation fee waiver",
            "Ask for a free router upgrade if you're on older hardware",
        ],
        common_fees_to_kill=["Wi-Fi router rental", "Line rental fee (if on DSL)", "Premium installation"],
        notes="Telkom fibre is on Openserve network in most areas — customer can literally switch ISPs in 24hrs. That's your biggest leverage.",
    ),

    "afrihost": Provider(
        key="afrihost",
        display_name="Afrihost",
        category="za_internet",
        retention_number="011 612 7200 → ask for Retentions",
        support_number="011 612 7200",
        currency="R",
        new_customer_rates=[
            "Fibre 10Mbps R347/mo",
            "Fibre 25Mbps R397/mo",
            "Fibre 50Mbps R497/mo",
            "Fibre 100Mbps R697/mo",
            "Fibre 200Mbps R897/mo",
            "Pure LTE 50GB+50GB R497/mo",
        ],
        competitors_in_market=[
            "Webafrica 50Mbps R499 (similar pricing, sometimes promos)",
            "Cool Ideas 50Mbps R499",
            "Supersonic 100Mbps R699",
            "RAIN 5G R399/R699",
            "Vox Telecom fibre deals",
        ],
        typical_retention_discount_pct=(10, 20),
        best_tactics=[
            "Afrihost is already one of the cheaper ISPs but they do run promos for existing customers",
            "Reference Webafrica/Cool Ideas equivalent pricing",
            "Ask for double data on LTE or a speed upgrade at same price",
            "Push for free months if you've had outages",
        ],
        common_fees_to_kill=["Account admin fee", "Cancellation notice period fees"],
        notes="Afrihost retention gives smaller discounts; better to push for speed upgrades or free months.",
    ),

    "webafrica": Provider(
        key="webafrica",
        display_name="Webafrica",
        category="za_internet",
        retention_number="021 464 9500 → Retentions",
        support_number="021 464 9500",
        currency="R",
        new_customer_rates=[
            "Fibre 25Mbps R399/mo",
            "Fibre 50Mbps R499/mo",
            "Fibre 100Mbps R699/mo",
            "Fibre 200Mbps R899/mo",
            "LTE 30GB+30GB R349/mo",
        ],
        competitors_in_market=[
            "Afrihost 50Mbps R497 (undercuts by R2)",
            "Cool Ideas 50Mbps R499",
            "Supersonic 100Mbps R699",
            "RAIN 5G R399/R699",
            "Axxess (sister company) cheaper on some packages",
        ],
        typical_retention_discount_pct=(10, 25),
        best_tactics=[
            "Mention Afrihost/Cool Ideas pricing (Afrihost is their main rival)",
            "Ask for a 'loyalty speed upgrade' — they'll bump from 50→100Mbps at same price",
            "Push for free router if renting",
            "Ask about any current new-customer promo applied to your account",
        ],
        common_fees_to_kill=["Router rental", "Pro-rata billing issues"],
        notes="",
    ),

    "rain": Provider(
        key="rain",
        display_name="RAIN (5G/LTE)",
        category="za_internet",
        retention_number="087 727 6000 → ask for Customer Retention",
        support_number="087 727 6000",
        currency="R",
        new_customer_rates=[
            "4G/LTE 19hrs unlimited R49-R250/mo (off-peak)",
            "5G Standard R399/mo (unlimited, speeds up to 30Mbps)",
            "5G Premium R699/mo (unlimited, up to 120Mbps)",
        ],
        competitors_in_market=[
            "Telkom LTE R299",
            "Afrihost LTE R497 (100GB)",
            "Fibre 50Mbps R497 (uncapped, more reliable)",
            "Cell C/Telkom data bundles for mobile",
            "Supersonic Air Fibre R399",
        ],
        typical_retention_discount_pct=(15, 25),
        best_tactics=[
            "RAIN is known for throttling/speed issues during peak hours — cite specific speed problems",
            "Mention fibre availability in your area (Afrihost/Webafrica)",
            "Push to be moved from Standard to Premium tier at Standard pricing if you have speed complaints",
            "Ask for a free month credit for any downtime",
        ],
        common_fees_to_kill=["Router/device payment plan (push for early settlement)"],
        notes="RAIN retention will give free months or upgrade tier if you complain about speed.",
    ),

    # ===== SOUTH AFRICA — TV =====
    "dstv": Provider(
        key="dstv",
        display_name="DStv / Multichoice",
        category="za_tv",
        retention_number="011 289 2222 → ask for Retentions / 'Loyalty'",
        support_number="011 289 2222",
        currency="R",
        new_customer_rates=[
            "EasyView R29/mo",
            "Access R129/mo",
            "Family R319/mo",
            "Compact R469/mo",
            "Compact+ R599/mo",
            "Premium R899/mo",
            "Add Showmax R39-R99",
        ],
        competitors_in_market=[
            "Netflix R49-R199/mo",
            "Disney+ R119/mo",
            "Showmax R39-R99/mo (including sports via Showmax Premier League)",
            "Amazon Prime Video R79/mo (with Prime shipping)",
            "Apple TV+ R84.99/mo",
            "DStv Stream (same content, cheaper, no decoder)",
            "Sling TV international / YouTube TV (if sports accessible)",
        ],
        typical_retention_discount_pct=(20, 50),
        best_tactics=[
            "DStv is the MOST negotiable SA bill. Multichoice loses thousands of subscribers monthly to streaming.",
            "Call 011 289 2222 → select option to DOWNGRADE or CANCEL (this routes to retentions)",
            "Open with: 'I want to cancel my DStv, I'm moving to streaming — Netflix + Showmax covers everything I watch.'",
            "They will offer: 2 months FREE (price holiday), or a permanent discount of 10-50%, or free Showmax, or Move to Compact at Family price.",
            "Don't accept the first offer (usually 10-20%). Push for 30-50%.",
            "If they only offer 2 months free, push for a permanent downgrade at discount rate.",
            "Mention you watch only 1-2 channels (e.g. Premier League) — note that Showmax now has PL for R99 vs DStv Compact R469.",
            "Ask for the decoder insurance / service fee to be removed (R65-R90/mo)",
            "If you don't watch sports, switch to streaming entirely — they'll counter-offer hard.",
        ],
        common_fees_to_kill=["Access fee/decoder rental (R90-R115)", "DStv Protect insurance (R25-R45)", "BoxOffice rentals billed to account"],
        notes="DStv retention has authority to give up to 50% off or multiple free months. Cancel gets you transferred to the loyalty/retentions team immediately. This is one of the easiest wins.",
    ),

    # ===== SOUTH AFRICA — SECURITY / OTHER =====
    "adt_za": Provider(
        key="adt_za",
        display_name="ADT South Africa",
        category="za_home_security",
        retention_number="086 12 12 300 → Retentions/Cancellations",
        support_number="086 12 12 300",
        currency="R",
        new_customer_rates=[
            "Indoor monitoring R280-R400/mo",
            "Outdoor/perimeter monitoring R450-R700/mo",
            "Full armed response R600-R1000/mo",
        ],
        competitors_in_market=[
            "Chubb Security (similar pricing)",
            "Fidelity ADT (different company, competitive)",
            "SMS Security / Blue Security (regional)",
            "Ring Alarm once-off purchase (no monthly fee)",
            "SimpliSafe / Ajax Systems DIY kits",
        ],
        typical_retention_discount_pct=(15, 25),
        best_tactics=[
            "Ask for retentions/cancellations department",
            "Reference Chubb/Fidelity quotes in your area",
            "Push for removal of annual escalation clauses (they raise 8-10% every year)",
            "Mention DIY systems (Ring/R5/month monitoring) as alternatives",
            "Ask for panic button/extra sensors added free to the package",
        ],
        common_fees_to_kill=["Annual price increase (ask for 0% increase year)", "Service call-out fees"],
        notes="Security companies in SA have high churn; they will negotiate to keep armed response clients.",
    ),
}


ZA_PROVIDER_KEYS = {"vodacom", "mtn", "cellc", "telkom_mobile", "telkom_fibre", "afrihost", "webafrica", "rain", "dstv", "adt_za"}


def _is_za(key: str) -> bool:
    return key in ZA_PROVIDER_KEYS


def find_provider(text: str) -> Optional[Provider]:
    """Try to detect provider from bill text."""
    t = text.lower()
    # SA providers (check first so "mtn" matches MTN SA before ambiguous US terms)
    if "vodacom" in t: return PROVIDERS["vodacom"]
    if "dstv" in t or "multichoice" in t: return PROVIDERS["dstv"]
    if "afrihost" in t: return PROVIDERS["afrihost"]
    if "webafrica" in t or "web africa" in t: return PROVIDERS["webafrica"]
    if "cell c" in t or "cellc" in t: return PROVIDERS["cellc"]
    if "rain" in t and ("5g" in t or "4g" in t or "internet" in t or "rain.co.za" in t): return PROVIDERS["rain"]
    if "telkom" in t and ("mobile" in t or "freeme" in t or "free me" in t): return PROVIDERS["telkom_mobile"]
    if "telkom" in t: return PROVIDERS["telkom_fibre"]  # default fibre/internet for Telkom
    if "mtn" in t and any(k in t for k in ("mobile", "data", "contract", "mega", "my mtn", "sim", "airtime")):
        return PROVIDERS["mtn"]
    if "adt" in t and any(k in t for k in ("086", "armed response", "chubb", "fidelity", "south africa")):
        return PROVIDERS["adt_za"]
    # US providers
    if "xfinity" in t or "comcast" in t: return PROVIDERS["comcast"]
    if "spectrum" in t or "charter" in t: return PROVIDERS["spectrum"]
    if "verizon" in t and ("wireless" in t or "mobile" in t or "cell" in t or ("fios" not in t and "internet" not in t)):
        return PROVIDERS["verizon_mobile"]
    if "verizon" in t: return PROVIDERS["verizon"]
    if "at&t" in t or "att " in t:
        if "wireless" in t or "mobile" in t: return PROVIDERS["att_mobile"]
        return PROVIDERS["att"]
    if "t-mobile" in t or "tmobile" in t or "t mobile" in t: return PROVIDERS["tmobile"]
    if "directv" in t: return PROVIDERS["directv"]
    if "dish" in t and "network" in t: return PROVIDERS["dish"]
    if "adt" in t: return PROVIDERS["adt"]
    return None


def list_providers():
    """Return all providers grouped by category for UI."""
    groups = {}
    for p in PROVIDERS.values():
        groups.setdefault(p.category, []).append(p)
    return groups
