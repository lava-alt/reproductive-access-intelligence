# Signal Expansion Plan — upstream of bills

*Goal: extend PP's eyes/ears earlier in the pipeline. Catch the campaign before the first bill and the reg before it publishes. Add these ONE AT A TIME; each new feed runs through the same discipline as the existing net (repro-relevance gate + precision check + attribution).*

## Status
- ✅ **Coverage recall fix DONE** (this pass): restrictive-bill recall 74% → 100%, catch-all `repro_watch` bucket added, new categories (telehealth, TRAP, contraception, dismemberment, fetal-remains), MT + NV re-harvested (50/50 states). This was the priority ("did we miss the Arizona bill").
- ⬜ Creative upstream feeds below, in priority order.

## Add in this order (highest early-warning value first)

### 1. Model-bill originators (the true early warning)
Catch the template *before* any state introduces it, then let the copycat detector watch it spread.
- **Americans United for Life (AUL)** — publishes model legislation ("Infants' Protection Act", drug-reporting bills). Watch their model-legislation / press pages.
- **ALEC** — model policy library.
- **Heritage / Project 2025** — the published FDA/EMTALA/Comstock playbook; a roadmap of intended federal moves.
- **How:** monitor these pages (RSS where available, else scheduled fetch of the model-legislation index) → new model bill = a Signal that pre-stages a threat; when matching bills appear in LegiScan, the copycat detector links origin → spread.
- **Payoff:** weeks-to-months lead over bill #1.

### 2. OIRA / reginfo.gov + Unified Agenda (reg before it publishes)
- **reginfo.gov** — rules **under OIRA review** (the step BEFORE Federal Register publication). Keyless; the earliest federal-rule signal.
- **Unified Agenda** (semiannual) — agencies telegraph planned rules months ahead.
- **How:** poll reginfo.gov for HHS/FDA/CMS entries with repro-relevant titles → escalate the matching threat (e.g. an FDA REMS rule under review lights mifepristone before it's public).

### 3. Anti-abortion org press feeds
- **SBA Pro-Life America, Alliance Defending Freedom (ADF), Students for Life** — announced campaigns and litigation intent, telegraphed in press releases.
- **How:** Google News RSS scoped to these orgs + their newsroom RSS → intent signal, feeds the news/gap lane.

### 4. White House executive-action feed
- **whitehouse.gov presidential-actions** (EOs, memoranda) + Federal Register presidential-documents.
- **How:** RSS; same-day structured signal for executive-branch moves (Mexico City Policy-style).

### 5. Republican AGs (RAGA) coordination
- Multistate AG letters, amicus briefs, enforcement threats (they coordinate before enforcement).
- **How:** monitor RAGA press + state-AG newsrooms for repro terms.

### 6. Follow-the-money (slowest, structural)
- **OpenSecrets / FollowTheMoney**, and **990s of anti-abortion orgs** (SBA, ADF, Susan B. Anthony) — funding precedes campaigns.
- **How:** periodic pull; a "pressure building" backdrop indicator, not a per-bill signal.

## Note on the "Trump trades app" idea
Politician stock-trade trackers (Capitol Trades, Unusual Whales) don't touch abortion policy — skip. The valuable reframe is **follow the model bills and the money, not the stocks** (items 1 and 6). Project 2025 is the literal playbook; watching the source orgs is the real early warning.

## The combination (why this compounds)
AUL publishes a model bill → copycat detector watches it appear across states → OIRA shows the matching federal rule under review → the threat lights up on the board **before it's news**. Origin + spread + pre-publication reg = the earliest possible warning.

## Discipline for each new feed
Same as the existing net: (1) repro-relevance gate to kill false positives, (2) route to a threat or the `repro_watch` bucket, (3) never silently drop a restrictive signal, (4) attribute the source. News/press feeds stay directional overlays; hard-signal feeds (bills, dockets, reg pipeline) are the trusted lane.
