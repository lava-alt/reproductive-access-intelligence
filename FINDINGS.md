# Defund War Room — Experiment 1: Findings

**Question:** Can a model watching only *point-in-time* leading signals forecast known repro-rights events *before* they happen — with useful lead time and honest calibration?

**Method:** Glass-box Bayesian evidence-accumulator. Base-rate prior in log-odds; each signal adds a log-likelihood ratio the moment it becomes *knowable* (point-in-time gate = no leakage). Weights set **a-priori by mechanism reasoning, not fitted to outcomes**. Panel = 3 positives + 2 negatives.

---

## Headline result

| Event | Outcome | Lead time (crossed 50%) | Call at a *real decision horizon* |
|---|---|---|---|
| Dobbs (Roe overturned) | 1 | **20 months** before | 67% at Barrett confirmation (Oct 2020), *before* cert was even granted |
| Medina (states defund PP) | 1 | **24 months** before | 40%→67% across 2023, well before the 2025 ruling |
| PP Gulf Coast closure | 1 | **15 months** before | 66% by mid-2024; 98% the day OBBBA passed |
| Kansas "Value Them Both" | 0 (failed) | — | **60% (model's honest miss)** |
| Florida Amendment 4 | 0 (failed) | — | **31% — correctly predicted FAIL despite 57% support** |

- **Brier score = 0.091** (0 = perfect; 0.25 = always guessing 50%; 1 = confidently wrong). Good.
- **Discrimination gap = +53%** — mean 99% on things that happened, 45% on things that didn't. Strong separation.

---

## The three things that matter

**1. It works, and the value is LEAD TIME, not the endpoint.**
The positives all saturate near 100% right before the event — that's *trivial* (of course it's ~100% after the draft leaks or after OBBBA is signed). The real result is that the probability was already **high 15–24 months out**, driven by *structural* + *leading* signals, long before it was obvious. That early window is the entire point of an early-warning tool.

**2. The Florida call is the proof the model adds value.**
A naive model reads "57% support → passes." Ours predicted **FAIL (31%)** — because it encodes the **60% supermajority rule** as a decisive negative signal. Getting a *non-obvious* answer right, for a mechanistic reason you can read off the model, is exactly what separates this from vibes.

**3. Kansas is the honest failure — and it's the most useful data point.**
Model said **60% pass; it failed.** The post-Dobbs registration surge (esp. women) was in the model as a −0.9 signal, but I **under-weighted it** — it pulled the number from 79%→60% but not below the line. Backtesting *caught my mistake*: **ballot/turnout events need enthusiasm/registration signals weighted much harder**, or the model should output wide uncertainty bands there instead of a false 60%. That's a concrete correction for the forward build, not a hand-wave.

---

## What carried the predictive load (→ what to wire first)

Feature importance (sum of |LLR| that fired across the panel):

| Family | Load | Examples |
|---|---|---|
| **Leading** | 13.7 | cert grants, bill *enactment*, court dockets, defund text |
| **Structural** | 10.4 | court composition, trigger-law stack, Medicaid dependence, no-backfill |
| **Sentiment** | 2.7 | oral-argument lean, polling |
| **Threshold** | 1.7 | supermajority rules (rare but decisive when present) |

**Read:** build the **leading-signal feeds first** — automated watchers on court dockets / cert grants, state bill filings, and federal bill/REMS/OLC text. Structural signals (court makeup, affiliate Medicaid exposure) are slow-moving and can be hand-maintained. Threshold rules are rare but flip outcomes, so they must be encoded as hard modifiers.

---

## Honest limitations (do not oversell)

- **n = 5, weights reasoned not fitted, data hand-reconstructed point-in-time.** This proves the *architecture* and *ranks the signal families*. It is **not** a validated forecaster.
- **Positives saturate** because I included near-certain late signals (Dobbs leak, OBBBA enacted). Calibration should really be judged at a fixed decision horizon (e.g., 12 months out) — a v2 improvement.
- **Ballot events are the weak spot** (the KS miss). The model is strong on court/legislative/administrative events (mechanistic, signal-rich) and weaker on electoral ones (turnout-driven, noisier).
- **All-positive court panel:** add court cases that were *denied cert* or ruled the other way, as negatives, to harden calibration.

---

## Verdict → the forward spec

The method is sound for exactly the events PP most needs warning on — **court, legislative, and administrative** moves (Medina, §71113, FDA/REMS, Comstock, state defund bills), where the signals are mechanistic and lead times are long (15–24 months). It is appropriately humble on ballots.

**Next experiment (v2):** fixed 12-month decision-horizon scoring, add cert-denied negatives, upweight ballot enthusiasm signals, and expand the panel to 12–15 events for a real reliability curve. Then — and only then — wire the top-ranked leading feeds into a live watcher.
