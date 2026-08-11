# Reproductive Access Intelligence

**Live tracker** (same data, pick your screen):
[Desktop view](https://repro-access-intel.vercel.app) · [Mobile view](https://repro-access-intel-mobile.vercel.app)

**An always-on reproductive-access threat tracker** that fuses 50-state legislation, federal courts,
and agency actions into one evergreen early-warning feed — with a calibrated risk model under the
hood.

The market is full of horizontal, reactive bill trackers ($10k–$100k/yr) and free descriptive maps
(Guttmacher, KFF). Neither answers the question an organization actually needs answered: *what is
rising right now, what is nobody covering, and how long do we have?*

---

## What it does

**1. Watches continuously, across every route.** A threat to reproductive access can arrive through a
court docket, a federal rule, an agency notice, a DOJ action, or any of 50 state legislatures. No
person can watch all of them; this does, and normalizes everything into one comparable stream.

**2. Flags what nobody is covering** — the marquee capability. The **signal-vs-coverage gap analysis**
compares real legislative and legal activity against how much press a threat is getting. A high gap
means genuine movement with no national attention: the threats you find out about too late.

> On the live run, **fetal personhood** scored the highest gap in the system (**+0.45**) — ~40
> verified bills across ~21 states, but the *lowest* media coverage of any tracked threat. That is
> the kind of finding the tracker exists to surface.

**3. Drills through to the source.** Every number resolves to the underlying bills, dockets, and
rules — state, bill number, last action, and a direct link. A risk score you cannot audit is a rumor,
so nothing in the product is a dead end.

**4. Scores each threat with lead time.** Each threat carries a calibrated probability and a
trajectory, so a rising threat is visible months out rather than on the morning it lands.

---

## The layers

| Layer | What it is | Role |
|---|---|---|
| **Product** | Reproductive Access Intelligence | The always-on tracker — this is the deliverable |
| **Capability** | Signal-vs-coverage gap analysis | The marquee feature: finds under-covered threats |
| **Drill-down** | Source bills, dockets, rules | Every score is auditable to its evidence |
| **Engine** | Bayesian glass-box accumulator | Produces the calibrated risk % — a component, not the product |
| **Feeds** | Federal Register, CourtListener, GovTrack, LegiScan, DOJ, news | The raw wide net |

The engine is the interesting machinery, but the tracker is the value. A probability is one number
the product displays, not the reason to use it.

---

## Under the hood: the risk engine

A glass-box Bayesian evidence accumulator. A base-rate prior in log-odds; each signal adds a
log-likelihood ratio the moment it becomes **knowable** — a point-in-time gate that keeps hindsight
from leaking into the score. Weights are set *a priori by mechanism reasoning*, not fitted to
outcomes, so every number can be read off the model and argued with.

Two lanes, because lead time is bounded by signal type:

- **Foresight (slow)** — structural drivers (court composition, trifecta control, docket
  trajectories) move months ahead of an event. Weekly rising-risk digest.
- **Sentinel (fast)** — event triggers (cert grant, signed reconciliation bill, FDA/REMS notice) fire
  close-in, so the honest goal is *detection latency*, not prediction.

### Validation

**20-event point-in-time backtest:** Brier **0.062**, AUC **0.99**, accuracy **95%**.

| Event | Outcome | Lead time |
|---|---|---|
| Dobbs | happened | 67% at Barrett's confirmation — **20 months out**, before cert was granted |
| Medina (state Medicaid defund) | happened | 40% → 67% across 2023, **24 months** before the ruling |
| An affiliate closure cascade | happened | 66% **15 months** out |
| Florida Amendment 4 | **failed** | Called **FAIL at 31%** despite 57% public support — encodes the 60% supermajority rule |
| Kansas "Value Them Both" | **failed** | Model said 60% pass. **A miss.** |

**Florida is the proof of value.** A naive model reads "57% support → passes." This one predicted
failure, for a mechanistic reason you can point at in the code.

**Kansas is the honest failure, and the more useful data point.** The post-Dobbs registration surge
was in the model as a negative signal but under-weighted — it pulled the number from 79% to 60%, not
below the line. The backtest caught my own weighting mistake, and the correction was structural:
ballot and turnout events are a genuinely weak lane (**Brier 0.146**, versus 0.006 on court and 0.002
on closures), so they are confined to an **advisory tier** rather than reported with the same
confidence as the mechanistic lanes.

A confident false alarm is this product's cardinal sin — it destroys the trust that is the entire
value. Precision hardening on live data moved the classifier from **0.91 → 1.00** against a
22-document golden set of real documents and adversarial decoys, at a cost of one recall miss. The
correct trade for a trust tool.

### Demographic module

Validated on ~225,000 Cooperative Election Study respondents across four cycles (logistic
regression). It corrected two of my own prior assumptions: **gender is a real independent predictor**
(OR 1.43, p ≈ 3e-60) after I had dismissed it off aggregate crosstabs, and **race is not a monolith** —
only the Black pro-choice advantage survives controls (OR 1.28), specifically as a *religiosity
buffer* (interaction OR 1.36, p ≈ 5e-20). Hispanic and Asian gaps are fully explained by party and
religion composition, so they are captured through those terms rather than a race dummy.

---

## Feeds

| Feed | Covers | Status |
|---|---|---|
| LegiScan | all 50 states' bills | live, free key |
| CourtListener v4 | dockets, cert grants | live, keyless (verified — the docs claim otherwise) |
| Federal Register API | HHS/FDA/CMS rules — Title X, EMTALA, REMS, §1303 | live, keyless |
| GovTrack / Congress.gov | federal bills | live |
| DOJ OPA | enforcement actions | live, bounded recent-window only |
| News / RSS | corroboration + the coverage side of the gap analysis | live |

Two findings from testing rather than documentation: CourtListener v4's search endpoint **does** work
without auth at 5,000 req/hr, and the DOJ API's `keyword` parameter is **silently ignored** — the
result count never changes — so keyless full-text DOJ search does not exist, and DOJ can only serve
as a recent-window sentinel.

---

## Running it

```bash
python3 tracker2.py              # the tracker — live run across the full feed net
python3 gap_analysis.py          # signal-vs-coverage gap
python3 render_brief.py          # generate the executive brief
python3 backtest_panel20.py      # reproduce the 20-event backtest
python3 precision_harness.py     # golden-set precision evaluation
```

`PP_EXEC_BRIEF.md` is real output from a live run.

API keys are read from environment variables or gitignored key files — never committed. Raw CES
microdata (129–244MB per cycle) is excluded; download it from Harvard Dataverse under their terms.

---

## Honest limitations

- Engine weights are reasoned, not fitted. The backtest proves the architecture and ranks signal
  families; it is **not** a forward-validated forecaster.
- Positives saturate near 100% right before an event, which is trivially easy. The real result is the
  probability 15–24 months out.
- Ballot and electoral events remain the weak lane, by construction.
- Narrow-TAM tooling for a handful of national organizations, not venture-scale SaaS.

Bill data © LegiScan LLC (legiscan.com), CC BY 4.0.
