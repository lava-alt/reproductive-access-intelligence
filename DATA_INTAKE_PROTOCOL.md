# Data Intake & Inclusion Protocol

*How we grow the model's evidence base **consistently across all six lanes** (not just ballot), and how every candidate feature / signal / data-type earns its way into the production model through a mini-experiment. This is the standing process, not a one-off.*

---

## Principle
Two separate growth tracks, run continuously:
1. **More labeled EVENTS** per lane → shrinks small-sample noise, tightens Venn-Abers intervals, stabilizes the calibration scale. Target: balanced growth across all lanes, since our weakest lanes (closure n=5, federal n=6, state n=7) gain the most per event.
2. **More candidate FEATURES / signals** → but each must pass the **inclusion gate** (`feature_gate.py`) before it enters the model. No feature ships on intuition; it ships on an out-of-sample win that harms no lane.

**Do-no-harm rule:** a change that helps the whole but quietly worsens one lane is rejected. Precision-first, same discipline as the round-5 state-gate work.

---

## Canonical event schema (all lanes)
Every labeled event, regardless of lane, is one row:

```
event_id | lane | state | direction(protective/restrictive) | outcome(0/1) | date
         | signals:[(name, sign, active_from)] | vote_share? | threshold? | source_url
```

`outcome` convention per lane: court=adverse ruling/upholds · ballot=measure passes · federal=bill enacted · admin=restriction imposed · closure=clinic closes · state=restrictive law effective. `active_from` on every signal enforces point-in-time (no leakage). `source_url` makes every label auditable.

Companion **state-year feature panel** (for candidate features): `state | year | trifecta | legislature_margin | governor_party | PRRI_attitude | guttmacher_tier | facilities | monthly_provision`.

---

## Where each lane's new EVENTS come from
Grow all six, not just ballot. Sources per lane (all already in our stack or free):

| Lane | Source of new labeled events | Cadence |
|---|---|---|
| **state** (legislation) | LegiScan enacted/failed × Guttmacher after-Roe changelog for dates | monthly |
| **court** | CourtListener (federal) + State Court Report + KFF litigation tracker → ruling + date | as decided |
| **federal** | GovTrack / Congress.gov enacted-vs-failed defund & repro bills (incl. historical Congresses) | per session |
| **admin** | Federal Register + agency newsrooms → rule/guidance imposed-or-not | as issued |
| **closure** | ANSIRH facility DB (annual) + #WeCount monthly volume → closures | quarterly |
| **ballot** | MEDSL dataset (1902–2016) + Ballotpedia (2017–26) + SOS certified results | per cycle + backfill |

**Backfill priority (biggest calibration win per hour):** ballot via MEDSL is the single largest labeled-count jump, but it only helps the ballot lane. To improve the model *overall*, pair it with **federal** (decades of failed/enacted defund attempts are well-documented) and **court** (state supreme court abortion rulings via State Court Report) so every lane grows, not just one.

---

## The inclusion gate (mini-experiment) — `feature_gate.py`
Any candidate feature/signal/new-data-type runs through this before adoption:

1. Express the candidate as `candidate(event) -> float`.
2. The gate fits **one** weight for it by leave-one-out CV (existing glass-box weights frozen), standardized so weights are comparable.
3. **INCLUDE only if:** LOO global log-loss improves by > margin (default 0.005) **AND** no single lane's Brier worsens by > tolerance (default 0.02). Else **REJECT**.

Worked results (on features derivable from current data):
- **net signal direction** → INCLUDE (LOO log-loss −0.047) — strongest.
- **signal count** → INCLUDE (−0.018).
- **post-Dobbs regime dummy** → REJECT (−0.004, below margin; Dobbs already encoded via dated signals).

New EVENT batches get the mirror test (already built as `backtest_panel60.py`): add them, confirm frozen-weight generalization (LOO log-loss / Brier / by-lane) holds and re-fit the global scale. If a batch tanks generalization, the labels or point-in-time signals are suspect — fix before adopting.

---

## Standing cadence
- **Monthly:** ingest new state/court/admin events from the live feeds into the event table; re-run `backtest_panel60`-style generalization + `calibration_fit` (re-fit the global scale γ, watch it stay modest ~1.2–1.4).
- **Per candidate feature:** run `feature_gate.py`; adopt only on INCLUDE.
- **Per election cycle:** backfill ballot (Ballotpedia + SOS) and re-decompose the ballot lane (E2) to check resolution.
- **Quarterly:** refresh Venn-Abers intervals (`venn_abers_bands.py`) so displayed bands track the growing data.

---

## Guardrails (from the calibration research)
- Keep the calibration scale a **single global** parameter — per-lane scales overfit at these sample sizes (LOO proved it: global 0.179 vs per-lane 0.243 log-loss).
- Keep it **modest** (~1.2–1.4). CV log-loss will tempt higher; the tail-risk study caps it (a confident-wrong call is catastrophic for a trust tool).
- The **ballot lane is a resolution problem** (E2: separation +0.29 vs +0.64 elsewhere), so its fix is *features* (measure direction, undecided share, turnout surge, spending asymmetry), never more scaling. Ballot stays advisory until those features pass the gate.
- **Never inherit candidate-race partisan priors** for abortion ballot measures (they run ahead of partisan lean).
- Everything validated **out-of-sample, time-ordered** (no shuffled CV, which would leak post-Dobbs into pre-Dobbs).
