# State Trial-Court Monitoring — Standard Operating Procedure

*The gap: the War Room's court lane (CourtListener v4) covers **federal courts + some state appellate opinions**, but **not state TRIAL-court dockets** — where the bellwether shield-law case (Paxton v. **Carpenter**, Ulster County) and many post-Medina state-exclusion suits actually live. Ingesting all 50 states' trial dockets is infeasible (and impossible keyless). This SOP defines a tiered, curated approach and recommends the efficient path.*

---

## Design principle: curate cases, don't ingest dockets

We do **not** try to watch every state docket. We maintain a **bellwether case watchlist** (~12–25 cases: Carpenter shield-law, GenBioPro, Missouri/Louisiana v. FDA, post-Medina exclusion suits, SisterSong-GA, MO Amendment 3, WY/KS constitutional anchors, PA ERA Medicaid) and monitor *those* by the cheapest tier that meets the latency need.

---

## Tier 0 — KEYLESS (built, working today) → `feeds_statecourt.py`

| Source | Keyless? | What it gives | Latency |
|---|---|---|---|
| **Google News RSS on case names** | ✅ 200 | Case-level rulings/appeals/stays as headlines | ~1 day |
| **ACLU news RSS** (`aclu.org/news/feed`) | ✅ 200 | Movement-side case updates | ~1 day |
| **If/When/How RSS** (`ifwhenhow.org/feed`) | ✅ 200 | Criminalization / SMA case updates | ~days |
| **Georgetown Litigation Tracker** (HTML) | ✅ 200 (scrape) | Curated case status — fragile front-end | ~days |
| CourtListener v4 (state appellate) | ✅ 200 | State **supreme/appellate** opinions (WI/KS/MO rulings) — **not** trial dockets | ~days |
| CRR case-index | ❌ 404 (moved) | — | — |

**Prototype result (live):** the Google-News-on-case-name watchlist surfaced **24 case-level items across 12 cases**, correctly flagging events — *WV appeals court on abortion-pill access* (GenBioPro), *PA Medicaid abortion-coverage* ruling, *Amarillo travel-ban rejected*, *SisterSong v. Georgia*, *MO medication-abortion restored* (Amendment 3). Trigger heuristic fires on ruling/stay/appeal keywords in the headline.
**Verdict:** Tier 0 covers the **"a newsworthy thing happened in this case"** need at zero cost and ~1-day lag. It will **miss** routine docket entries (motions, filings, scheduling) that don't make news — acceptable for early warning, not for litigation ops.

**What is NOT keyless (verified 403):** NYSCEF (NY e-filing), re:SearchTX (Texas OCA). State e-filing portals are auth-walled/captcha'd; do **not** scrape them.

---

## Tier 1 — PAID docket APIs (drop-in when trial-docket granularity is needed)

| Service | Coverage | Rough pricing | Best for |
|---|---|---|---|
| **Docket Alarm** | Federal (PACER) + state dockets, tracking/alerts, API | **~$99/user/mo**; API custom | Cheapest real docket alerts; good first paid step |
| **Trellis.law** | **State TRIAL courts** — deep in CA/TX/IL, rulings, judge analytics, **webhooks** | Contact-sales (not public) | The strongest *state-trial* coverage — the exact gap |
| **UniCourt Enterprise API** | API-first, 140M+ federal+state records, real-time | Contact-sales | Highest-volume programmatic ingestion |

*(Pricing: Docket Alarm ~$99/user/mo per public listings; Trellis/UniCourt are sales-gated. Sources: GetApp/Slashdot comparisons, 2026.)*
Even Tier 1 has **thin state-trial coverage outside CA/TX/IL** — no vendor has all 50 states' trial dockets well. Scope any purchase to the states with live bellwether cases (NY for Carpenter, WV/LA/MO for mifepristone).

## Tier 2 — Enterprise (only if this becomes core infrastructure)

Bloomberg Law / Lexis CourtLink dockets — comprehensive, expensive (5-figure/yr), overkill for an early-warning augment.

---

## ⭐ The PP-specific shortcut (recommended primary path)

**PP is a *party* to the cases that matter most.** In Carpenter-adjacent, §71113, Medina-line, and most state-exclusion suits, **PP and its co-counsel (CRR, ACLU) already have PACER accounts and Bloomberg Law/docket access.** The efficient path is **not to buy a docket API** — it is a **1-page intake from co-counsel**: a shared calendar / email alias where CRR/ACLU paralegals drop docket events for the ~15 bellwether cases into the War Room. Zero incremental cost, authoritative, faster than any scraper.

---

## Recommendation (efficient path)

1. **Ship Tier 0 now** (`feeds_statecourt.py`) — keyless Google-News case watchlist, folded into the tracker as *context* (llr 0). Covers the shield-law/state-court gap for early warning at $0.
2. **Stand up the co-counsel intake** (the PP shortcut) for authoritative docket events on the ~15 bellwether cases — this is the real fix, and it's a process change, not a purchase.
3. **Buy Tier 1 only if** PP wants docket-level latency independent of co-counsel: start with **Docket Alarm (~$99/mo)** for alerts, add **Trellis.law** only for CA/TX/IL trial-docket depth.
4. **Skip Tier 2** unless this becomes owned infrastructure.

Net: the state-trial gap is closed for *early-warning* purposes by Tier 0 + the co-counsel intake, at ~zero cost. Paid docket APIs are a later optimization, not a prerequisite.
