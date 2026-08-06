#!/usr/bin/env python3
"""
Round 5 — recover state-exclusion recall WITHOUT overfitting.

The round-4 v1 gate dropped OK HB3592 ("Medicaid; term; funds for abortions; exceptions")
because it has no RESTRICT verb ("term" != "terminate") and "funds for abortion(s)" was not
recognized as a defund construction.

Candidate fix (v2): treat "funds/funding for abortion" as an exclusionary funding hook.
Hypothesis: in bill TITLES this phrasing is a restriction construction (pro-access bills say
"coverage"/"access"/"insurance", not "funds for abortion; exceptions").

ANTI-OVERFIT TEST: apply v1 and v2 to ALL 1,931 cached bills (held-out — the gate was never
tuned on this full corpus), and print every bill v2 NEWLY accepts. If they are genuine defund
bills across many states -> generalizes. If v2 grabs pro-access bills -> overfit, reject.
Bill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.
"""
import json, os
from legiscan_ingest import state_exclusion_v1, _stance, REPRO_TOKENS

_HERE = os.path.dirname(os.path.abspath(__file__))
rows = json.load(open(os.path.join(_HERE, ".legiscan_data.json")))

# ---- v2 = v1 + generalizable "funds/funding for abortion" defund construction ----
_FUND = ["medicaid","reimburse","funds","funding","title x","taxpayer","public business","charitable organization"]
_PROVIDER = ["abortion provider","prohibited entity","planned parenthood","defund","abortion providers",
             "logistical support","abortion assistance"]
_OMNIBUS = ["enacts into law major components","implement","appropriation","state budget","omnibus",
            "major components of legislation"]
_RESTRICT = ["prohibit","defund","exclude","restrict","terminate","end taxpayer","no abortion",
             "no funding","prohibiting","ban"]
_PROACCESS = ["practical support","access to abortion","appreciation day","requires health",
              "coverage for family planning","remote monitoring","postpartum"]
# NEW: defund-funding constructions (guarded against pro-access phrasing)
_DEFUND_FUNDING = ["funds for abortion","funding for abortion","funds for abortions","funding for abortions",
                   "public funds for abortion","taxpayer funding of abortion","use of funds for abortion"]

def state_exclusion_v2(title, relevance=100):
    t = (title or "").lower()
    try: rel = int(relevance)
    except Exception: rel = 100
    hard = any(p in t for p in ["planned parenthood","prohibited entity","abortion provider","defund"])
    if rel < 50 and not hard:
        return False
    if any(p in t for p in _PROACCESS) and not any(r in t for r in ["prohibit","defund","exclude","ban"]):
        return False
    if any(o in t for o in _OMNIBUS) and not ("planned parenthood" in t or "abortion" in t):
        return False
    abortion = ("abortion" in t) or ("planned parenthood" in t)
    # NEW: a "funds/funding for abortion" construction counts as restrict intent,
    # but NOT if the title is pro-access (coverage/insurance/require/expand).
    proaccess_funding = any(x in t for x in ["coverage","insurance","require","expand","protect","access","freedom"])
    defund_funding = any(x in t for x in _DEFUND_FUNDING) and not proaccess_funding
    restrict = any(r in t for r in _RESTRICT) or defund_funding
    fund_or_provider = any(f in t for f in _FUND) or any(p in t for p in _PROVIDER) or "provider" in t
    if "defund planned parenthood" in t: return True
    if "planned parenthood" in t and restrict: return True
    return abortion and restrict and fund_or_provider

def state_exclusion_v3(title, relevance=100):
    """v3: recover OK HB3592 via a RESTRICT-context guard on the funding construction.
    'provides funding' / 'travel' / protect-stance = pro-access grant -> NOT a defund bill."""
    t = (title or "").lower()
    try: rel = int(relevance)
    except Exception: rel = 100
    if _stance(title) == "protect":                       # respect stance: pro-access is never exclusion
        return False
    hard = any(p in t for p in ["planned parenthood","prohibited entity","abortion provider","defund"])
    if rel < 50 and not hard:
        return False
    if any(p in t for p in _PROACCESS) and not any(r in t for r in ["prohibit","defund","exclude","ban"]):
        return False
    if any(o in t for o in _OMNIBUS) and not ("planned parenthood" in t or "abortion" in t):
        return False
    abortion = ("abortion" in t) or ("planned parenthood" in t)
    grant_verb = any(x in t for x in ["provides funding","provide funding","provides for","grant","travel",
                                      "coverage","insurance","require","expand","access","freedom"])
    defund_funding = any(x in t for x in _DEFUND_FUNDING) and not grant_verb
    restrict = any(r in t for r in _RESTRICT) or defund_funding
    fund_or_provider = any(f in t for f in _FUND) or any(p in t for p in _PROVIDER) or "provider" in t
    if "defund planned parenthood" in t: return True
    if "planned parenthood" in t and restrict: return True
    return abortion and restrict and fund_or_provider

def repro(t): return any(k in (t or "").lower() for k in REPRO_TOKENS)

# ---------------- held-out corpus scan ----------------
v1_pos, v2_pos, newly = [], [], []
for r in rows.values():
    title = r.get("title") or ""; st = r.get("state") or ""; rel = r.get("relevance",100)
    if not repro(title):
        continue
    a = state_exclusion_v1(title, rel)
    b = state_exclusion_v3(title, rel)
    if a: v1_pos.append((st,title))
    if b: v2_pos.append((st,title))
    if b and not a:
        newly.append((st, r.get("bill_number",""), rel, _stance(title), title))

print("="*90)
print(f"HELD-OUT CORPUS SCAN — {len(rows)} cached bills (gate never tuned on full corpus)")
print("="*90)
print(f"v1 accepts: {len(v1_pos)}    v2 accepts: {len(v2_pos)}    NEWLY accepted by v2: {len(newly)}")
print("\n--- every bill v2 NEWLY accepts (inspect for genuineness) ---")
for st,bn,rel,stance,title in sorted(newly):
    print(f"  [{st} {bn} rel={rel} stance={stance}] {title[:78]}")

print("\n"+"="*90)
print("GOLDEN SET RE-CHECK (26 bills) — did we recover OK HB3592 without new FPs?")
print("="*90)
from state_gate import GOLD
def score(fn):
    tp=fp=fn_=0; fps=[]; misses=[]
    for st,bill,rel,title,gold in GOLD:
        pred = 1 if fn(title, rel) else 0
        if pred and gold: tp+=1
        elif pred and not gold: fp+=1; fps.append(f"{st} {bill}")
        elif not pred and gold: fn_+=1; misses.append(f"{st} {bill}")
    prec=tp/(tp+fp) if tp+fp else 0; rec=tp/(tp+fn_) if tp+fn_ else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    return tp,fp,fn_,prec,rec,f1,fps,misses
for lbl,fn in (("v1 (round-4 production)",state_exclusion_v1),("v3 (round-5 guarded)",state_exclusion_v3)):
    tp,fp,fn_,prec,rec,f1,fps,misses=score(fn)
    print(f"\n{lbl}: TP={tp} FP={fp} FN={fn_}  precision={prec:.2f} recall={rec:.2f} F1={f1:.2f}")
    if fps: print(f"   FALSE POSITIVES: {', '.join(fps)}")
    if misses: print(f"   MISSES: {', '.join(misses)}")
print("\nBill data (c) LegiScan LLC (legiscan.com), CC BY 4.0.")
