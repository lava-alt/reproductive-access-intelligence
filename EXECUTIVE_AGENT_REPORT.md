# Defund War Room — Executive Agent Report

*Session date: 2026-08-04. Scope: market assessment + a round of build-and-measure experiments on the early-warning tool. Builds on the validated model (`warroom_model.py`, backtest AUC 0.99) and the v0 live tracker. Everything here is runnable and was actually executed; disconfirming results are reported, not buried.*

---

## (a) Market research — findings and the niche/adoption verdict

### The incumbent landscape (what exists, who buys, rough price, the gap)

| Product | What it does | Who buys | Rough price | Gap it leaves |
|---|---|---|---|---|
| **FiscalNote / CQ / PolicyNote** | Federal + 50-state bill & regulation tracking, now AI-layered; VoterVoice for grassroots | Corporate GR, large trade assocs, some big nonprofits | Custom, typically **$10k–$100k+/yr**, opaque | Horizontal firehose. No repro domain model, no *risk forecast*, no "what does this mean for PP's Medicaid line" |
| **Quorum** | Bill tracking + stakeholder CRM + grassroots/advocacy campaigns in one | Advocacy orgs, GR teams | Custom, **~$10k–$50k+/yr** | Same — reactive tracking + outreach, not a domain-specific early-warning/scoring engine |
| **Plural / Open States** | Modern AI 50-state bill tracking, **low-cost published pricing** | Smaller advocacy teams, journalists | **Low four figures/yr**; Open States data is free/open | Cheapest real option, but still generic tracking; no threat model, no court/agency/DOJ fusion |
| **POLITICO Pro** | Premium journalism + alerts on health/repro policy | Big orgs, lobbyists | **Tens of thousands/yr/seat**, custom | Human newsroom, not a machine risk score; you still need an analyst to synthesize |
| **Bloomberg Government (BGOV)** | Federal legislative/regulatory intel | GR shops, contractors | **~$6k–$15k/seat/yr** | Federal-centric, generic, expensive per seat |
| **Guttmacher / KFF trackers** | Free, authoritative repro-policy maps, litigation tracker, abortion dashboard | Everyone in the movement (incl. PP) | **Free** | *Descriptive and retrospective* — they tell you the state of play, not "this is rising, watch it." No alerting, no per-threat probability, no lead time |
| **SBA Pro-Life America — PP Closures tracker (lifesavinglaws.com)** | The **opposition's** map of PP closures + "life-saving laws" | Anti-abortion movement, press | Free | It is a *scoreboard of damage already done* and a targeting tool — the mirror image of what PP needs |

**Sources:** [LegiStorm public-affairs buyer's guide](https://info.legistorm.com/blog/best-public-affairs-software) · [FiscalNote best-legislative-tracking blog](https://fiscalnote.com/blog/best-legislative-tracking-software) · [Quorum FiscalNote-alternatives](https://www.quorum.us/about/fiscalnote-alternatives/) · [Capterra FiscalNote](https://www.capterra.com/p/185611/FiscalNote/) · [BGOV seat pricing (BidSparq)](https://bidsparq.com/vs/bloomberg-government) · [Digiday on POLITICO Pro pricing](https://digiday.com/media/business-publishers-rethink-how-they-can-retain-subscribers-during-the-economic-downturn/) · [Guttmacher state-policy resources](https://www.guttmacher.org/state-policy-resources) · [KFF federal-courts litigation tracker](https://www.kff.org/womens-health-policy/litigation-involving-reproductive-health-and-rights-in-the-federal-courts/) · [SBA PP-closures tracker](https://sbaprolife.org/newsroom/press-releases/new-resource-tracking-planned-parenthood-closures-in-2025).

### The verdict: yes, there's a real niche — but it is *narrow and specific*

The market is crowded with **horizontal, reactive trackers** ($10k–$100k) and **free descriptive maps** (Guttmacher/KFF). The whitespace both leave open is the same one this tool targets:

> **A repro-specific, forward-looking, multi-source *risk* engine** — one that fuses the court + agency + legislative + DOJ routes into a *typed probability with lead time*, tuned to PP's actual threat surface (Medicaid defund, Title X, mifepristone/REMS, Comstock, EMTALA, state exclusion), and disciplined enough to say "advisory" where it's weak (ballots).

Nobody sells "here is the probability that a multi-year §71113 re-pass lands, and it's been rising for 6 months." FiscalNote/Quorum give you the raw bills; Guttmacher/KFF give you the current map; POLITICO gives you the story. **The synthesis-into-a-scored-forecast layer is unowned.**

**Build-vs-buy for PP:** PP should **buy** the commodity firehose (Plural/Open States is cheap and its data is open; or it already has KFF/Guttmacher for free) and **build** the thin, opinionated scoring/fusion layer on top — which is exactly this tool. Rebuilding 50-state bill ingestion from scratch is wasted effort when Open States exists; the defensible IP is the *typed threat model + precision discipline + cross-feed corroboration*, not the scraping.

**Who would adopt/pay:**
- **PP National (PPFA)** — the natural owner. The brains show national is already standing up a COO-level data function and an InfoSec-embedded compliance role; this is a bandwidth-augmentation tool for exactly that team. Highest-fit buyer.
- **Allied national legal/advocacy orgs (ACLU RFP, CRR, NWLC)** — plausible *shared-infrastructure* adopters, since the agency-litigation fight (FDA/REMS, Comstock, EMTALA) is where the movement's bench is thinnest (Org-landscape brain, Gap #7).
- **Affiliates** — *not* individual buyers; they lack the bandwidth and the tool is national-altitude by design.
- **Abortion funds / smaller orgs** — free-rider beneficiaries of a shared feed, not payers.

**Honest caveat:** this is a **narrow-TAM internal tool**, not a venture-scale SaaS. Its value is *strategic bandwidth for a handful of national orgs*, and its worst failure mode is a confident false alarm (a fake "93%" destroys the trust that is the entire product). That framing drove every experiment below.

---

## (b) Experiments run — what changed, results, what I learned (incl. failures)

I verified both baselines first: the 20-event backtest reproduces (accuracy 95%, **Brier 0.062, AUC 0.99**; ballot Brier 0.146 — the known weak lane), and the v0 tracker runs live against the Federal Register (113 docs).

### Experiment 1 — Close the FR blind spot with two GENUINELY KEYLESS live feeds  → `feeds_wide.py`

**Hypothesis (from prior findings):** the Federal Register catches *formal rules* but misses the guidance/memo/court/DOJ route that caused most of 2025's damage.

**What I built + a key empirical correction:** I tested the task's suggested keyless sources directly.
- **CourtListener v4** — the web says v4 "enforces auth," but the **search endpoint works keyless (HTTP 200, 5000 req/hr anon)**, verified live. So I implemented it as a *real* feed, not a stub. It covers the **court lane**.
- **DOJ OPA press-release API** — keyless, 270k releases. Covers the **enforcement/DOJ lane**.
- HHS newsroom RSS → **403 (blocked)**; FDA press RSS → 200. DOJ became the primary enforcement feed.

**Results (live):** the court feed surfaces **12 correctly-routed signals** the FR-only tracker never saw — **Medina v. PP South Atlantic (SCOTUS, flagged as a trigger)**, *PPFA v. Kennedy* (the §71113 case), *FDA v. AHM*, *Moyle*, *GenBioPro*, *Washington v. FDA*, *Louisiana v. FDA*. Zero visible false positives after gate-tuning.

**Failures/learnings, reported honestly:**
1. **The DOJ `keyword` param is silently ignored** (count stays 270,065 regardless). So keyless *full-text* DOJ search does not exist. DOJ can only work as a **bounded recent-window Sentinel** (catches *new* Comstock prosecutions as they post) — it returned **0** this run, which is the *honest* answer (no repro enforcement in the most-recent ~800 releases). Historical backfill needs an HTML-search scrape → roadmap.
2. **Court precision needed two passes.** Ordering by date surfaced junk; a caseName repro-token gate then over-corrected and dropped "X v. FDA" cases (whose names carry no repro word). Final design: **relevance-ranked queries + a caseName repro-token gate + a "top-3 trust" granted only to the clean FDA-centric lanes** (mifepristone, EMTALA), whose top hits are verified 100% on-topic. The word "comstock" is deliberately excluded from repro tokens because it is a common **surname** ("Jon Comstock v. Arkansas").

### Experiment 2 — Harden Federal Register precision (kill the Title X false-positive)  → `precision.py`

**Root cause, diagnosed on live data:** the FR term "Title X family planning" returned **40 docs, zero containing the literal token "Title X"** in their visible title/abstract (Medicare OPPS rules, marine-mammal takes, stablecoin CIP rules…). The v0 gate accepted the *generic* token "family planning," so a **Medicare OPPS proposed rule surfaced as a 47% "Title X" threat.**

**Fix (v1 gate):** (a) **program-specific token** — a threat fires only if its *own* program is named (`titlex` needs literal "title x"/"office of population affairs," not generic "family planning"); (b) **agency scope** — FR repro threats must come from HHS/FDA/CMS/OPA/DOJ; (c) a hard **NEG-homograph list** (marine mammal, stablecoin, physician-fee, public charge…).

**Bonus finding:** the real 2025 Title X withholding was a **grant-letter action that never appeared in the FR at all** — confirming the blind-spot thesis and that Title X must be watched via the newsroom/grant route, not the FR.

### Experiment 4 (mine) — A labeled precision harness  → `precision_harness.py`

Because a confident false alarm is the product's cardinal sin, I built a **22-doc golden set** of *real* documents (10 true positives, 12 adversarial decoys) drawn from the live feeds, lane-aware (FR docs scored on the program-token gate; court docs on the court gate).

| Gate | Precision | Recall | F1 | False alarms |
|---|---|---|---|---|
| v0 (generic repro token) | 0.91 | 1.00 | 0.95 | "Unaccompanied Children" rule fired **all 7 threats** |
| **v1 (hardened)** | **1.00** | 0.90 | 0.95 | **none** |

**Learned:** hardening moved precision **0.91 → 1.00**, eliminating the confident cross-domain false alarm, at a cost of **one** recall miss — the vaguely-titled "Reproductive Health Services" rule, which has no program token to route on. That is the correct trade for a trust tool. An honest residual: the metadata-only gate can't see a doc that is mifepristone-related only in *full text* (the HHS OCR pharmacy-guidance Notice) — a real argument for the multi-feed net, and a candidate for a medium-confidence **review queue** rather than a binary drop.

### Experiment 5 (mine) — Cross-feed corroboration in the unified wide net  → `tracker2.py`

Fused all three keyless feeds into one typed model with the v1 gate, and added a **corroboration badge**: when a threat is evidenced by **≥2 independent feeds**, flag it. Crucially, this is an **advisory overlay shown *beside* the validated risk number, not baked into it** — respecting the project's trusted-lane/advisory discipline (the corroboration heuristic is not itself backtested).

**Live result:** FR collapses to **1 clean signal** (Title X FP gone); the Sentinel fires **3 SCOTUS triggers the FR-only tracker missed** (Medina, Moyle, FDA v. AHM); and **EMTALA shows ⛓ corroboration across FR + Court** (the FR Church-Amendment-rescission Notice *and* the Moyle/AHM cases independently confirm the same rollback). That is the wide-net thesis made visible: no single feed is complete, but their intersection is a stronger signal than any one alone.

### Experiment 3 — Scaffold the widest net (LegiScan + Congress.gov)  → `legiscan_stub.py`

Both need a free key not provisioned here, so this is a **runnable scaffold** with the real ingester, normalized Signal schema, threat routing, LegiScan status→LLR mapping, and a **structural weight from the brains** (provider-exclusion bills in the ~19 no-backfill red states weighted ×1.3). Documented exactly what it catches that the other feeds cannot: **state bills months before they become the state action the court/FR feeds later see**, and **federal bills at introduction** (a multi-year §71113 re-pass, national Comstock codification, Title X elimination riders) — the true slow-lane structural lead.

---

## (c) Honest assessment — where the tool stands

**Strong / proven:**
- The **model** is validated on the mechanistic lanes PP most needs (court/federal/admin/closure Brier 0.006–0.043, AUC 0.99).
- The **wide net is now three keyless live feeds**, not one — and it demonstrably catches the SCOTUS/court and agency-guidance routes the FR alone misses.
- **Precision is measured, not asserted** (golden-set harness), and the trust-critical false-alarm rate on that set is now **zero**.
- Everything runs keyless, today.

**Weak / unproven (do not oversell):**
- **DOJ lane is recall-limited** (no keyless full-text search) — a live Sentinel for *new* actions, blind to history without a scrape.
- **Ballots remain advisory** (unchanged; Brier 0.146).
- **Corroboration and the no-backfill weight are reasoned, not backtested** — advisory overlays only.
- **The metadata-only FR gate** can miss full-text-only relevance (precision-first by choice).
- **No forward (out-of-sample) validation yet** — the whole system is still backtest- and construct-validated, not proven on genuinely future events.
- The **golden set is small (n=22) and self-authored** — it demonstrates the gate behavior, it is not an independent benchmark.

---

## (d) Prioritized roadmap for the next phase

1. **LegiScan key + go live (highest value/effort ratio).** The state-legislative feed is the true structural slow-lane and the biggest current blind spot; the scaffold already exists. One free key flips it on. This is the single most valuable next feed.
2. **Congress.gov key** — federal bills at introduction (the §71113-re-pass early warning). Free key, scaffold ready.
3. **A medium-confidence "review queue"** for docs that match a threat in full-text but not metadata (the HHS OCR pharmacy-notice case) — a human-in-the-loop tier that recovers recall without polluting the high-precision alert stream.
4. **DOJ historical backfill** via an HTML-search scrape or component-scoped crawl, so Comstock enforcement isn't blind before "today."
5. **Forward validation harness** — freeze the model, log its calls prospectively for a quarter, and score calibration on genuinely out-of-sample events. This is what converts "validated architecture" into "validated forecaster."
6. **Only then**: revisit the advisory ballot module (registration-surge + cross-party-defection signals) and consider baking corroboration into the trusted number *after* it earns a backtest.

---

## Artifacts (all in `defund-war-room/`)

| File | Purpose |
|---|---|
| `feeds_wide.py` | Exp 1 + R2 — keyless CourtListener search, court WATCHLIST, DOJ ingesters |
| `precision.py` | Exp 2 — v1 hardened precision gates (program-token + agency scope + court gate) |
| `precision_harness.py` | Exp 4 — 22-doc golden-set precision/recall harness (v0 vs v1; incl. court decoys) |
| `feeds_fed.py` | R2 Exp 6 — keyless federal bills (GovTrack) with stance filter |
| `feeds_agency.py` | R2 Exp 7 — keyless CMS/FDA newsroom (guidance/grant-letter route) |
| `tracker2.py` | Exp 5 + R2 — unified 5-feed wide-net tracker, one fused two-lane digest + corroboration |
| `legiscan_stub.py` | Exp 3 — runnable LegiScan + Congress.gov scaffold (key-gated) |
| `tracker.py`, `warroom_model.py`, `backtest_panel20.py` | v0 baselines (unchanged; model reused verbatim) |

---

# ROUND 2 — federal bills, deeper court lane, agency newsroom

*Same discipline: precision > recall, keyless only, model reused verbatim, honest limits.*

### R2-Exp 6 — Keyless federal bills via GovTrack.us  → `feeds_fed.py`
**Congress.gov needs a key; I found a keyless substitute.** Tested empirically: **GovTrack.us API works keyless (HTTP 200)** and mirrors Congress.gov bill-status data. (GovInfo bulk JSON returned a service error; GovInfo `api.govinfo.gov` needs a key/DEMO_KEY — both rejected in favor of GovTrack.) This is the **slow-lane structural signal** — a bill at *introduction* leads the enacted rule by months/years.

**Caught (13 repro bills since Jan 2025):** `S.203 / H.R.271 Defund Planned Parenthood Act` → **fed_defund** (the §71113 re-pass long-lead signal); `Safeguarding Women from Chemical Abortion Act`, `Ending Chemical Abortions Act`, `Protecting Life from Chemical Abortions Act` → **fda_mife**; `Stop Comstock Act` → **comstock**.

**Failure found + fixed:** keyword routing captures **topic, not stance** — a *pro-access* "Stop Comstock Act" and an *anti-access* "Defund PP Act" both matched their threat, but only one *advances* it. Added a **stance filter**: pro-access bills (Stop Comstock, "Reaffirming freedom") are scored **llr 0 (context only)**, so they don't inflate the threat. Verified live. Residual honest limit: "unclear"-stance resolutions still contribute a weak 0.33 — acceptable for a long-lead awareness signal, flagged in the digest.

### R2-Exp 2b — Deeper court lane: live-docket WATCHLIST  → `feeds_wide.fetch_court_watchlist`
Moved beyond one-shot search to **tracking the named dockets that matter now**: Missouri/Louisiana v. FDA (mifepristone), Carpenter shield-law, post-Medina exclusion, PPFA v. Kennedy (§71113), GenBioPro. Each named-case query returns its latest court event; **SCOTUS action or appellate stay/vacate/cert = Sentinel trigger**. Caught Louisiana v. FDA, PPFA v. Kennedy (→ fed_defund), Medina (SCOTUS trigger), FDA v. AHM (SCOTUS trigger). **Honest gap:** the **Carpenter shield-law cases don't surface** — they're NY/TX *state-court* matters with thin CourtListener opinion coverage; catching them needs a state-docket source (roadmap). Court-lane precision is already validated by the golden set (Medina/Louisiana accepted; the "Jon Comstock" surname and the Landor RLUIPA case rejected).

### R2-Exp 7 (my pick) — Agency newsroom feed  → `feeds_agency.py`
Chose the **guidance/grant-letter route** because the real 2025 Title X withholding was a grant letter that **never hit the Federal Register**. **CMS + FDA newsroom RSS work keyless (200); HHS RSS is 403 → stubbed** (HTML-scrape roadmap). Same v1 hardened program-token gate. **Result: 0 items this window — the honest answer** (agency newsrooms are ~99% non-repro payment rules/recalls); the feed is precision-first, fires rarely, and would catch a REMS "safety review" or a Title X grant announcement the moment it posts.

### R2 — Unified fusion  → `tracker2.py` (now **5 feeds, one pass, one two-lane digest**)
FR + CourtListener(search) + CourtWatch + GovTrack + CMS/FDA news + DOJ, fused with deduped Sentinel and cross-feed corroboration.

**Headline round-2 outcome — the wide net measurably paid off:**
- **`fed_defund` went from 15% (invisible, no signal) → 47%, ⛓ corroborated across CourtWatch (PPFA v. Kennedy) + GovTrack (S.203 Defund PP Act).** The federal-bill feed gave the top structural threat its long-lead signal for the first time.
- **`fda_mife` 93%, ⛓ corroborated across 3 feeds** (CourtListener + CourtWatch + GovTrack).
- **`emtala` 86%, ⛓ corroborated across FR + Court.**
- Comstock's pro-access "Stop Comstock" bills correctly show as **context (llr 0), not threat evidence** — the stance filter working in the live digest.

**Precision numbers unchanged and honest:** golden-set gate still **precision 1.00 / recall 0.90 / F1 0.95**; model backtest untouched (**AUC 0.99, Brier 0.062**). No new confident false positives observed in the live 30-signal run.

**Round-2 honest failures:** (1) shield-law state dockets invisible to CourtListener; (2) agency feed empty this window (expected, precision-first); (3) DOJ still recall-limited (keyword param ignored — recent-window Sentinel only); (4) bill stance detection is heuristic and can't resolve "unclear" resolutions.

### Updated #1 next step (after round 2)
Add a state-court source + wire LegiScan — both addressed in round 3 below.

---

# ROUND 3 — LegiScan 50-state feed, state-court hunt, live-data mining, news + gap analysis

*LegiScan key now provisioned. Same discipline. Spec `LEGISCAN_INGEST_SPEC.md` followed (getSearchRaw change-driver, change_hash caching, status checks, no front-end scraping, CC-BY attribution).*

### R3-Build 1 — LegiScan 50-state ingester  → `legiscan_ingest.py` (+ `feeds_legiscan.py`)
Verified the key (1,783 abortion bills). `getSearchRaw` returns only `bill_id + change_hash` (the cheap change-driver, per spec); rich metadata comes from paginated `getSearch` (~36 q for the whole corpus) **cached to `.legiscan_data.json`** so all experiments replay at **zero API cost** (well under the 30k/mo budget). Harvested **1,931 bills**, routed **205** to threats with the repro-token precision gate, the **stance filter** (pro-access bills → llr 0 context), and the **no-backfill-state ×1.3** consequence weight. Added `personhood` + `state_ban` threat types (labels only; validated weights untouched). Integrated into `tracker2.py` as a **bounded per-threat summary** (so 200 bills don't flood or trivially saturate the digest).

### R3-Build 2 — Keyless state-court hunt: **negative result, stated plainly**
Probed CourtListener state coverage, NYSCEF, re:SearchTX, statecourtreport.org. **No keyless state-court *docket* API exists.** State e-filing portals (NYSCEF, re:SearchTX) return **403**; CourtListener carries federal + some state *appellate opinions* but **not** the state *trial* dockets where the **Carpenter shield-law** case lives (Ulster County). To close it would take a **paid docket service** (Docket Alarm / Trellis / PacerPro), **per-state portal scraping** (fragile, captcha/403), or monitoring a **curated tracker** (Georgetown/Brennan). Honest gap; documented, not faked.

### R3-Experiments (live-data mining)  → `analyze_legiscan.py`
1. **Landscape:** 205 routed repro bills / 36 states. Hotspots **TX(17), OK(16), IA(9), MO(8)**. By threat: **mifepristone 73, personhood 41, EMTALA 36, state-exclusion 34, comstock 11**. Stance 126 restrict / 4 protect (stance under-tags pro-access — honest limit). Stage: 11 enacted, 194 pending.
2. **Velocity:** clear 2026-session spike — **41 (Jan) → 27 → 22** repro bills/month.
3. **Copycat / model-bill detection (Jaccard clustering):** **"Abortion-inducing drugs & abortion reports"** cloned across **AZ, IN, OK, SC**; **"Born-Alive Abortion Survivors Protection Act"** in **MO, NJ + federal** — coordinated campaigns visible *before* any single bill advances.
4. **Next-Kansas ranking:** surfaced enacted no-backfill-state restrictions a headline-watcher misses — **SD abortion-drug distribution ban** (signed Mar 30), **TX PP "logistical support" exclusion** (eff. 9/1/25), **TN personhood** (eff. 4/23/26).
5. **State×federal corroboration:** `fda_mife` lit in **both** lanes (72 state + 8 federal); **personhood 41 state / 0 federal** (a state-only phenomenon).

### R3-Addendum — Keyless news feed + THE gap capability  → `feeds_news.py`, `gap_analysis.py`
**News feed:** Google News RSS (reliable, keyless) as coverage proxy + GDELT DOC 2.0 volume (best-effort; **429-rate-limited → fail-fast fallback to Google News count**). Repro-gated. Also feeds the fast lane as *context* (llr 0 — a story can precede the action).

**Signal-vs-coverage gap (the marquee capability):** per threat, min-max-normalize **REAL hard-signal activity** (LegiScan+Court+GovTrack+FR llr) against **MEDIA volume**, then GAP = activity − coverage.
- **⚠ #1 UNDER-COVERED SLEEPER: Fetal personhood, GAP +0.45** — 41 bills / 22 states (24 no-backfill), yet the *lowest* media coverage of any threat. Real movement, no headlines.
- **Over-covered (legacy/hype):** §71113 federal defund, Title X (1 bill vs 50 articles), EMTALA/state-ban retrospectives — heavy coverage of *already-realized* 2025 events, low *new* bill activity.
- **Aligned:** mifepristone (high both — matches reality).
- *Honest method limits:* both inputs noisy; Google News saturates near its cap (compresses the top); one dominant threat (mife) anchors the min-max; directional heuristic, not a precise metric; correlation ≠ causation. News also **leads** on some items (a mifepristone-ruling story appeared before it entered our court lane) — noted as an early-context use, not trusted evidence.

### R3 — Unified fusion  → `tracker2.py` now **7 keyless feeds, one two-lane digest**
FR + CourtListener(search+watchlist) + GovTrack + **LegiScan(50-state)** + CMS/FDA + DOJ + **News**, 51 signals, ~18s. **`fda_mife` now ⛓ corroborated across 4 feeds (93%)**; **personhood surfaces at 65%** (41 bills/22 states) as a LegiScan trigger; **Comstock 76%** on the state mailing-ban route. Precision holds (golden set 1.00/0.90/F1 0.95; model backtest untouched). **Honest new precision leak:** generic "Medicaid"/"reimburse" tokens catch some NY omnibus **budget bills** as state_exclusion/comstock hits — flagged for a tighter state-bill gate.

### Updated #1 next step (post round 3)
**Tighten the state-bill precision gate** (kill the omnibus-budget-bill false hits) **and operationalize the gap analysis as the headline product** — a weekly "what's real but under-covered" digest, led by the personhood sleeper. The remaining feed gap (state trial-court dockets / Carpenter) needs a paid or scraped source; everything else — 50 states, federal bills, federal courts, agencies, and news — is now live and keyless.

### Round-3 artifacts
| File | Purpose |
|---|---|
| `feeds_legiscan.py` | Spec-compliant LegiScan client (getSearchRaw + change_hash cache) |
| `legiscan_ingest.py` | 50-state routing, stance, no-backfill weight, cached harvest, bounded summary |
| `analyze_legiscan.py` | Live-data mining: landscape / velocity / copycat / next-Kansas / corroboration |
| `feeds_news.py` | Keyless Google News + GDELT coverage feed |
| `gap_analysis.py` | **Signal-vs-coverage gap — the marquee under-covered-sleeper detector** |
| `PP_EXEC_BRIEF.md` | Monday-morning exec brief + most-exciting-capabilities |

---

# ROUND 4 — measured gate hardening, state-court SOP, personhood verification

*Three experiments, measured before/after. Bill data © LegiScan LLC (legiscan.com), CC BY 4.0.*

### R4-Exp 1 — Tighten the state-exclusion gate (MEASURED)  → `state_gate.py` + `legiscan_ingest.state_exclusion_v1`
Root cause of the NY-omnibus false positives: bare "medicaid"/"reimburse" tokens. Fix (v1): **co-occurrence** (a funding token AND an abortion-provider token, or an explicit "defund PP"/"planned parenthood"+restrict); **omnibus-negative** gate (drop "enacts into law major components / implement / appropriation" unless PP/abortion named); **RESTRICT-stance** requirement (pro-access coverage / "appreciation day" bills excluded); **LegiScan relevance floor** (50; NY budget bills came in at rel 21–28).
**Measured on a 26-bill hand-labeled golden set (production function, no drift):**

| gate | precision | recall | F1 | false positives |
|---|---|---|---|---|
| v0 (bare token) | 0.82 | 1.00 | 0.90 | NJ family-planning-coverage ×2, US Appreciation-Day resolution, TX coverage bill |
| **v1 (production)** | **1.00** | 0.94 | **0.97** | **none** |

Confirmed on the live corpus: the **NY omnibus budget bills (S03007/A03007/A10007/S09007) are gone**, replaced by genuine restrictions (AZ public-funding prohibition, TX travel-funding bans, OK Right-to-Life Act). One honest recall miss: OK HB3592 ("Medicaid; funds for abortions; exceptions") — no explicit restriction verb in the title.

### R4-Exp 2 — State trial-court access: keyless Tier-0 prototype + SOP  → `feeds_statecourt.py`, `STATE_COURT_SOP.md`
Confirmed **no keyless state-trial-DOCKET API exists** (NYSCEF, re:SearchTX → 403). Built a working **keyless Tier-0** monitor: a **bellwether case watchlist** (~12 cases: Carpenter, GenBioPro, Missouri/Louisiana v. FDA, post-Medina exclusion, SisterSong-GA, MO Amendment 3, WY/KS anchors, PA ERA) watched via **Google News RSS on case names**. **Live prototype: 24 case-level items across 12 cases**, correctly flagging events — *WV appeals court on abortion-pill access*, *PA Medicaid abortion coverage*, *Amarillo travel-ban rejected*, *MO medication-abortion restored*. Folded into the tracker as context (llr 0).
**SOP recommendation:** ship Tier-0 now ($0, ~1-day lag); the real fix is the **PP-specific shortcut** — PP is a *party* to these cases, so a **co-counsel (CRR/ACLU) docket-event intake** gives authoritative updates at zero cost. Buy Tier-1 (**Docket Alarm ~$99/mo**, then **Trellis.law** for CA/TX/IL trial depth) only if docket-level latency independent of co-counsel is needed. Skip enterprise.

### R4-Exp 3 — VERIFY the personhood finding (independent audit)  → `personhood_audit.py`
Crisp **definition** (fetal/embryonic personhood; excludes corporate/AI personhood, anti-personhood/pro-access bills, pure gestational bans, fetal-remains, born-alive). **Full reclassification** of all candidates (not a 10-sample):
- **Original routing had false positives** — corporate personhood (OH SR93/HR211), AI personhood (OH HB469, OK HB3546), anti-personhood/protective (MO HB2286 "prohibits granting legal personhood", WA HB2029), fetal-remains (NE LB632). **Routing precision 0.81.**
- **VERIFIED: 42 fetal-personhood bills / 21 states** (20 states + 1 federal).
- **Cross-source triangulation:** CORROBORATED — sits inside **Guttmacher** (16 states / 40+ bills, 2024) and **Pregnancy Justice / Legal Voice** (24 states with personhood language; 17 with established fetal rights). **Confidence: MEDIUM-HIGH.**
- **Coverage side validated:** even at a raised news cap (100), personhood = **66 articles vs mifepristone 99** — genuinely the lowest-covered threat, *not* a cap artifact. The under-coverage finding **holds**.
- **Correction:** the headline "41 bills / 22 states" was directionally right but should be reported as **audit-verified ~40 bills / ~21 states** with the ~6–10 non-fetal bills explicitly stripped. Production routing now applies the personhood exclusions.

### Updated #1 next step (post round 4)
**Operationalize the gap analysis as the weekly headline product** (led by the now-verified personhood sleeper) and **stand up the co-counsel docket intake** (the zero-cost state-court fix). The measured gates (state-exclusion 1.00 precision; personhood exclusions) are in production. Remaining optional spend: a Tier-1 docket API only if co-counsel intake is insufficient.

### Round-4 artifacts
| File | Purpose |
|---|---|
| `state_gate.py` | Exp 1 — state-exclusion gate golden-set harness (v0 vs v1, measured) |
| `personhood_audit.py` | Exp 3 — personhood definition + full reclassification + triangulation |
| `feeds_statecourt.py` | Exp 2 — keyless Tier-0 state-court bellwether monitor (prototype) |
| `STATE_COURT_SOP.md` | Exp 2 — tiered build-vs-buy plan + PP co-counsel shortcut |
