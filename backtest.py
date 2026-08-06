#!/usr/bin/env python3
"""
Defund War Room — Experiment 1: Glass-box backtest of a repro-rights early-warning model.

QUESTION (from the brief):
  Can a model that watches only *point-in-time* leading signals forecast known
  reproductive-rights events BEFORE they happen — with useful lead time and
  honest calibration (not a reverse-fit "hero number")?

METHOD:
  A transparent Bayesian evidence-accumulator. Each event starts at a base-rate
  prior (in log-odds). Every signal contributes a log-likelihood ratio (LLR) the
  moment it becomes *knowable* (a point-in-time gate = no lookahead leakage).
  Sum the log-odds -> logistic -> probability. Fully interpretable: you can read
  exactly which signal moved the number and by how much.

SCIENTIFIC DISCIPLINE (stated up front, enforced in code):
  - Point-in-time: a signal only contributes on/after its `active_from` date.
  - Weights are set a-priori by MECHANISM REASONING, not tuned to the outcomes.
    (Tuning 5 outcomes would be overfitting; the point is to test a reasoned model.)
  - Panel mixes 3 positives + 2 negatives so calibration is real, not "always high."
  - This is a PROOF-OF-METHOD on hand-reconstructed public-record data, NOT a
    validated production model. It shows (a) the architecture works, (b) which
    signal *families* carry the predictive load — that ranked list is the spec
    for which live feeds the forward War Room must wire in first.
"""

import math
from dataclasses import dataclass, field

def logistic(x): return 1.0 / (1.0 + math.exp(-x))
def logit(p):    return math.log(p / (1.0 - p))
def ym(s):       return s  # ISO 'YYYY-MM-DD' compares lexicographically = chronologically

# --------------------------------------------------------------------------------------
# Model primitives
# --------------------------------------------------------------------------------------
@dataclass
class Signal:
    name: str
    llr: float          # evidence strength in log-odds when active. + raises P, - lowers P.
    active_from: str    # ISO date the signal became KNOWABLE (point-in-time gate)
    family: str         # 'structural' | 'leading' | 'threshold' | 'sentiment'
    note: str = ""

@dataclass
class Event:
    key: str
    label: str
    target: str         # the proposition being predicted (P this is TRUE)
    outcome: int        # ground truth: 1 happened / passed, 0 did not
    event_date: str
    base_rate: float    # prior P before any event-specific signal
    signals: list = field(default_factory=list)
    cutoffs: list = field(default_factory=list)   # 'as of' evaluation dates

def prob_as_of(ev, asof):
    lo = logit(ev.base_rate)
    fired = []
    for s in ev.signals:
        if s.active_from <= asof:
            lo += s.llr
            fired.append(s)
    return logistic(lo), fired

# --------------------------------------------------------------------------------------
# THE PANEL  (weights reasoned a-priori; see notes)
# --------------------------------------------------------------------------------------
EVENTS = []

# 1) DOBBS — Roe overturned (June 24 2022).  OUTCOME = 1
EVENTS.append(Event(
    key="dobbs", label="Dobbs v. Jackson — Roe overturned",
    target="SCOTUS overturns Roe", outcome=1, event_date="2022-06-24",
    base_rate=0.03,   # base rate: a major precedent gets overturned in a given term ~ rare
    cutoffs=["2016-01-01","2018-10-06","2020-10-27","2021-05-17","2021-12-01","2022-06-01"],
    signals=[
        Signal("Court tilts 5-4 conservative (Gorsuch)", 0.8, "2017-04-07","structural"),
        Signal("Kavanaugh replaces Kennedy (median moves)", 1.2, "2018-10-06","structural",
               "Kennedy was the swing vote upholding Casey; his exit is the true inflection"),
        Signal("6-3 supermajority (Barrett)", 1.5, "2020-10-27","structural"),
        Signal("State trigger/6-wk bans stacking (>12 states)", 0.7, "2019-06-01","leading",
               "legislatures pricing in the outcome"),
        Signal("Cert GRANTED on a direct 15-wk challenge", 2.2, "2021-05-17","leading",
               "the court CHOOSING this case = intent; strongest single leading signal"),
        Signal("Oral-argument questioning hostile to Roe", 1.3, "2021-12-01","sentiment"),
        Signal("Draft opinion leak (Alito)", 3.0, "2022-05-02","leading",
               "near-certainty; included to show the curve saturating pre-event"),
    ]))

# 2) MEDINA v. PPSA — states may exclude PP from Medicaid; no sec.1983 suit (June 26 2025). OUTCOME=1
EVENTS.append(Event(
    key="medina", label="Medina — states may defund PP from Medicaid",
    target="SCOTUS rules no private right to challenge state PP exclusion", outcome=1,
    event_date="2025-06-26", base_rate=0.20,   # sec.1983 provider-standing cases: court had been narrowing
    cutoffs=["2022-07-01","2023-06-01","2024-12-18","2025-04-02","2025-06-01"],
    signals=[
        Signal("6-3 conservative court (post-Dobbs posture)", 1.0, "2022-07-01","structural"),
        Signal("Circuit split on sec.1983 provider standing", 0.7, "2023-06-01","leading"),
        Signal("SCOTUS GRANTS cert on PPSA case", 1.8, "2024-12-18","leading",
               "choosing to hear it, post-Dobbs, signals appetite"),
        Signal("Oral-argument lean toward the state", 1.1, "2025-04-02","sentiment"),
        Signal("Trend of narrowing implied private rights (Talevski-aware)", 0.4, "2023-06-01","structural"),
    ]))

# 3) PP GULF COAST HOUSTON — largest US PP clinic closes (Sept 30 2025). OUTCOME=1
EVENTS.append(Event(
    key="closure_ppgc", label="PP Gulf Coast (Houston) closure",
    target="This affiliate closes/merges its flagship clinic", outcome=1,
    event_date="2025-09-30", base_rate=0.08,
    cutoffs=["2024-06-01","2025-01-01","2025-07-04","2025-09-01"],
    signals=[
        Signal("Texas total ban (no abortion revenue since 2022)", 0.9, "2022-08-01","structural"),
        Signal("Affiliate >$800k Medicaid + high Medicaid dependence", 1.0, "2024-06-01","structural"),
        Signal("Existential ~$1.8B False Claims clawback suit pending", 1.2, "2024-06-01","leading"),
        Signal("OBBBA sec.71113 federal Medicaid defund ENACTED", 2.0, "2025-07-04","leading",
               "the trigger event; flips solvency"),
        Signal("No state backfill (red state, hostile legislature)", 1.5, "2025-07-04","structural"),
        Signal("$45M system uncompensated care called 'unsustainable'", 0.8, "2025-09-01","leading"),
    ]))

# 4) KANSAS 'Value Them Both' (Aug 2 2022) — strip constitutional abortion protection. OUTCOME=0 (FAILED)
EVENTS.append(Event(
    key="ks_vtb", label="Kansas 'Value Them Both' amendment",
    target="Amendment PASSES (removes state constitutional protection)", outcome=0,
    event_date="2022-08-02", base_rate=0.50,   # FIRST post-Dobbs vote, no track record -> genuine coin-flip prior
    cutoffs=["2022-01-01","2022-05-01","2022-07-15","2022-08-01"],
    signals=[
        Signal("Deep-red state (Trump +15), GOP legislature referred it", 0.6, "2022-01-01","structural"),
        Signal("Aug primary timing (low-turnout, favors motivated base)", 0.5, "2022-01-01","structural",
               "GOP chose the date to help it pass"),
        Signal("Post-Dobbs backlash surge in registrations (esp. women)", -0.9, "2022-07-15","leading",
               "the countervailing leading signal a naive model would miss"),
        Signal("Confusing 'yes-to-restrict' ballot wording", 0.2, "2022-05-01","structural"),
        Signal("Polling within margin / high uncertainty", 0.0, "2022-05-01","sentiment",
               "honest: polling gave no clear edge -> contributes nothing"),
    ]))

# 5) FLORIDA Amendment 4 (Nov 5 2024) — establish right to abortion. OUTCOME=0 (FAILED: 57% < 60% rule)
EVENTS.append(Event(
    key="fl_a4", label="Florida Amendment 4 (right to abortion)",
    target="Amendment 4 PASSES", outcome=0, event_date="2024-11-05",
    base_rate=0.55,   # majority-support measures usually pass -> prior slightly >0.5
    cutoffs=["2024-01-01","2024-06-01","2024-10-01","2024-11-01"],
    signals=[
        Signal("Post-Dobbs ballot streak (abortion side 6/7 wins)", 0.8, "2024-01-01","structural",
               "the naive 'abortion wins at the ballot' signal"),
        Signal("Polling ~57-60% yes (majority, but near threshold)", 0.3, "2024-06-01","sentiment"),
        Signal("FLORIDA 60% SUPERMAJORITY RULE required", -1.7, "2024-01-01","threshold",
               "THE decisive signal: converts a clear majority into a loss. A model blind to the"
               " rule predicts PASS; a model that encodes the rule predicts FAIL."),
        Signal("State used agencies/ads against it (DeSantis)", -0.4, "2024-06-01","leading"),
    ]))

# --------------------------------------------------------------------------------------
# BACKTEST + METRICS
# --------------------------------------------------------------------------------------
def months_between(a, b):
    ya,ma = int(a[:4]), int(a[5:7]); yb,mb = int(b[:4]), int(b[5:7])
    return (yb-ya)*12 + (mb-ma)

def run():
    print("="*90)
    print("DEFUND WAR ROOM — EXPERIMENT 1: point-in-time backtest (glass-box Bayesian accumulator)")
    print("="*90)
    final_forecasts = []   # (label, p_final_pre_event, outcome)
    importance = {}        # signal family -> summed |llr| that actually fired pre-event

    for ev in EVENTS:
        print(f"\n{'-'*90}\n{ev.label}   [target: {ev.target}]")
        print(f"  ground truth: {'HAPPENED/PASSED (1)' if ev.outcome else 'DID NOT (0)'}"
              f"   event date: {ev.event_date}   base rate: {ev.base_rate:.0%}")
        print(f"  {'as-of date':<12}{'P(event)':>10}   signals firing (llr)")
        p_pre = ev.base_rate
        first_cross_50 = None
        for c in ev.cutoffs:
            if c > ev.event_date: continue
            p, fired = prob_as_of(ev, c)
            p_pre = p
            names = ", ".join(f"{s.name.split('(')[0].strip()}({s.llr:+.1f})" for s in fired) or "(none)"
            flag = ""
            if first_cross_50 is None and p >= 0.50:
                first_cross_50 = c; flag = "  <-- crosses 50%"
            print(f"  {c:<12}{p:>9.0%}   {names[:70]}{flag}")
        # lead time (only meaningful for events that actually happened)
        if ev.outcome == 1 and first_cross_50:
            lt = months_between(first_cross_50, ev.event_date)
            print(f"  >> LEAD TIME: crossed 50% on {first_cross_50} = {lt} months before the event")
        elif ev.outcome == 1:
            print(f"  >> LEAD TIME: never crossed 50% pre-event (MISS on lead)")
        else:
            print(f"  >> negative control: final pre-event P = {p_pre:.0%} (outcome was 0)")
        final_forecasts.append((ev.label, p_pre, ev.outcome))
        for s in ev.signals:
            if s.active_from <= ev.event_date:
                importance[s.family] = importance.get(s.family, 0.0) + abs(s.llr)

    # ---- calibration ----
    print("\n"+"="*90); print("CALIBRATION  (final pre-event forecast vs. ground truth)"); print("="*90)
    brier = sum((p-o)**2 for _,p,o in final_forecasts)/len(final_forecasts)
    print(f"  {'event':<42}{'forecast':>10}{'actual':>9}{'sq.err':>9}")
    for lab,p,o in final_forecasts:
        print(f"  {lab[:41]:<42}{p:>9.0%}{o:>9}{(p-o)**2:>9.2f}")
    print(f"\n  Brier score = {brier:.3f}   (0=perfect, 0.25=always-guess-50%, 1=confidently wrong)")
    # discrimination
    pos = [p for _,p,o in final_forecasts if o==1]; neg=[p for _,p,o in final_forecasts if o==0]
    print(f"  mean P on things that HAPPENED (1): {sum(pos)/len(pos):.0%}")
    print(f"  mean P on things that DID NOT (0):  {sum(neg)/len(neg):.0%}")
    print(f"  discrimination gap: {sum(pos)/len(pos)-sum(neg)/len(neg):+.0%}  (bigger = better separation)")

    # ---- which signal families carry the load ----
    print("\n"+"="*90); print("FEATURE IMPORTANCE — which signal FAMILIES carried predictive load")
    print("(sum of |llr| that fired across the panel; = priority order for wiring live feeds)"); print("="*90)
    for fam,v in sorted(importance.items(), key=lambda kv:-kv[1]):
        print(f"  {fam:<12} {v:6.1f}  {'#'*int(v*3)}")

if __name__ == "__main__":
    run()
