# Reproductive Access Intelligence — Architecture (v0)

*An always-on wide net. A PP insider already follows the space; this covers what no single human can watch continuously — 50 legislatures + every federal docket + agency registers + affiliate signals, 24/7. Augment bandwidth, don't duplicate the expert.*

## What the experiments already taught us (folded in)
- **Trust the mechanistic domains.** 20-event backtest Brier by type: court 0.006 · closure 0.002 · federal 0.016 · admin 0.043 · **ballot 0.146**. The model is near-perfect on court/legislative/administrative/closure — *exactly PP's existential threats* — and weak on elections.
- **Ballots = advisory, wide bands.** The single miss + all near-misses were ballots. Registration-surge-by-demographic + mobilization data is a real input but noisy → **📌 bookmarked** for later integration; kept out of the trusted lane.
- **Leading signals carry the load** (feature importance: leading 13.7 ≫ structural 10.4 ≫ sentiment 2.7). Wire leading feeds first.
- **Lead time is bounded by signal type.** Structural drivers show months early (Dobbs 79% a year out); event-triggers fire close-in (Medina 45%, §71113 15% at 12mo). → two lanes, below.
- **Demographic block validated on 4 CES cycles (~225k):** party = backbone (stable, strengthening); gender real + growing (OR 1.28→1.50); Black-distinct + religiosity-buffer robust all years. Party-registration *undercounts* pro-access on ballots (cross-party defection ~38–40%). All of this lives in the **advisory ballot module**, not the trusted lane.

## Two lanes, one system
**🐢 Slow lane — Foresight (prediction, long lead).** Structural drivers (court composition, trifecta control, docket/bill trajectories) → the validated typed model → *rising-risk* forecasts weeks–months out. Weekly digest.

**⚡ Fast lane — Sentinel (detection, low latency).** Sudden triggers (cert grant, signed reconciliation bill, FDA/REMS notice, OLC memo). The moment it hits a docket/register → alert. Detection, not prediction — because these fire close-in.

## Pipeline
`ingesters → normalize to Signals → typed model (per-threat evidence accumulator) → risk scores + deltas → { ⚡ instant alert | 🐢 weekly rising-risk digest }`

## Threats tracked (v0)
| id | threat | type | lane |
|---|---|---|---|
| fed_defund | Multi-year federal Medicaid defund (§71113 re-pass) | federal | slow+fast |
| state_exclusion | State Medicaid exclusions post-Medina | court/state | slow+fast |
| fda_mife | FDA mifepristone REMS re-tightening | admin | fast |
| titlex | Title X withholding/restriction | admin | fast |
| comstock | Comstock enforcement (mailed-pill ban) | admin | fast |
| emtala | EMTALA emergency-abortion rollback | admin | fast |
| aca1303 | ACA §1303 abortion-coverage friction | admin | fast |
| closures | Affiliate closure cascade | closure | slow |
| *ballot_** | *state ballot measures* | ballot | **advisory only** |

## Feeds (all free)
| feed | covers | key? | status |
|---|---|---|---|
| **Federal Register API** | HHS/FDA/CMS rules (Title X, EMTALA, REMS, §1303) | none | **LIVE v0** |
| LegiScan API | all 50 states' bills | free key | stub |
| Congress.gov API | federal bills / reconciliation | free key | stub |
| CourtListener/RECAP | court dockets, cert grants | token | stub |
| ProPublica Nonprofit | affiliate 990s | none | later |
| TargetSmart / state SoS | registration surge (advisory ballots) | mixed | 📌 bookmarked |

## Model weights
Reused verbatim from the validated backtest (`backtest_panel20.py` MAG table, shared per type). Live docs are scored by (threat-keyword match) × (doc significance: Final Rule ≫ Proposed Rule ≫ Notice).

## Honest status
v0 proves the pipeline on **live Federal Register data** end-to-end. Classifier is keyword-based (iterative). Not yet validated forward — that's the next phase.
