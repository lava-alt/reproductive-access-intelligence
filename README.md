# Reproductive-Rights Policy Risk Engine

An early-warning system for reproductive-health policy threats. It fuses court dockets, federal
rulemaking, agency notices, DOJ enforcement, and 50-state legislation into **typed probabilities with
lead time** — not another bill tracker.

The market is full of horizontal, reactive trackers ($10k–$100k/yr) and free descriptive maps
(Guttmacher, KFF). Neither answers the question an organization actually needs answered: *is this
rising, and how long do we have?*

---

## How it works

A glass-box Bayesian evidence accumulator. A base-rate prior in log-odds; each signal adds a
log-likelihood ratio the moment it becomes **knowable** — a point-in-time gate that prevents
hindsight leaking into the score. Weights are set *a priori by mechanism reasoning*, not fitted to
outcomes, so every number can be read off the model and argued with.

```
ingesters → normalized signals → typed model → risk scores + deltas → { instant alert | weekly digest }
```

**Two lanes, because lead time is bounded by signal type.**

- **Foresight (slow)** — structural drivers: court composition, trifecta control, docket trajectories.
  These move months ahead of an event. Weekly rising-risk digest.
- **Sentinel (fast)** — event triggers: a cert grant, a signed reconciliation bill, an FDA/REMS
  notice. These fire close-in, so the honest goal is *detection latency*, not prediction.

---

## Validation

**20-event point-in-time backtest:** Brier **0.062**, AUC **0.99**, accuracy **95%**.

| Event | Outcome | Lead time |
|---|---|---|
| Dobbs | happened | 67% at Barrett's confirmation — **20 months out**, before cert was granted |
| Medina (state Medicaid defund) | happened | 40% → 67% across 2023, **24 months** before the ruling |
| An affiliate closure cascade | happened | 66% **15 months** out |
| Florida Amendment 4 | **failed** | Called **FAIL at 31%** despite 57% public support — the model encodes the 60% supermajority rule |
| Kansas "Value Them Both" | **failed** | Model said 60% pass. **A miss.** |

Two of these matter more than the headline number.

**Florida is the proof of value.** A naive model reads "57% support → passes." This one predicted
failure, for a mechanistic reason you can point at in the code. A non-obvious call that is right for
a legible reason is what separates a model from vibes.

**Kansas is the honest failure, and the more useful data point.** The post-Dobbs registration surge
was in the model as a negative signal but under-weighted — it pulled the number from 79% to 60%, not
below the line. The backtest caught my own weighting mistake. The correction was structural: ballot
and turnout events are a genuinely weak lane (**Brier 0.146**, versus 0.006 on court and 0.002 on
closures), so they are confined to an **advisory tier** rather than being reported as if they carried
the same confidence.

A confident false alarm is this tool's cardinal sin. Precision hardening on live data moved the
classifier from **0.91 → 1.00 precision** against a 22-document golden set of real documents and
adversarial decoys, at a cost of one recall miss — the correct trade for a trust product.

---

## Demographic module

Validated on ~225,000 Cooperative Election Study respondents across four cycles (logistic
regression). It corrected two of my own prior assumptions:

- **Party is the backbone** (pseudo-R² 0.208 alone; everything else adds 0.07).
- **Gender is a real independent predictor** (OR 1.43, p ≈ 3e-60) — I had previously dismissed it off
  aggregate crosstabs. The microdata earned its keep by proving me wrong.
- **Race is not a monolith.** Only the Black pro-choice advantage survives controls (OR 1.28); the
  Hispanic and Asian gaps are fully explained by party and religion composition. The Black pattern is
  specifically a *religiosity buffer* — the usual religiosity → anti-abortion link is far weaker
  (interaction OR 1.36, p ≈ 5e-20).

Encoded accordingly: party and religiosity as levers, a Black-distinct term, and no generic race
dummy.

---

## Feeds

| Feed | Covers | Status |
|---|---|---|
| Federal Register API | HHS/FDA/CMS rules — Title X, EMTALA, REMS, §1303 | live, keyless |
| CourtListener v4 | dockets, cert grants | live, keyless (verified — the docs claim otherwise) |
| DOJ OPA | enforcement actions | live, bounded recent-window only |
| LegiScan | all 50 states' bills | live, free key |
| Congress.gov | federal bills | key required |

Two findings worth recording, both from testing rather than documentation: CourtListener v4's search
endpoint **does** work without auth at 5,000 req/hr, and the DOJ API's `keyword` parameter is
**silently ignored** — the result count never changes — so keyless full-text DOJ search does not
exist and it can only serve as a recent-window sentinel.

---

## Running it

```bash
python3 backtest_panel20.py      # reproduce the 20-event backtest
python3 tracker2.py              # live run against the wide feed net
python3 precision_harness.py     # golden-set precision evaluation
python3 render_brief.py          # generate the executive brief
```

API keys are read from environment variables or gitignored key files — never committed. Raw CES
microdata (129–244MB per cycle) is excluded; download it from Harvard Dataverse under their terms.

---

## Honest limitations

- Weights are reasoned, not fitted. The backtest proves the architecture and ranks signal families;
  it is **not** a forward-validated forecaster.
- Positives saturate near 100% right before an event, which is trivially easy. The real result is the
  probability 15–24 months out. Calibration should be judged at a fixed decision horizon.
- Ballot and electoral events remain the weak lane, by construction.
- Narrow-TAM tooling for a handful of national organizations, not venture-scale SaaS.

Bill data © LegiScan LLC (legiscan.com), CC BY 4.0.
