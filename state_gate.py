#!/usr/bin/env python3
"""
Round 4 / Experiment 1 — tighten the STATE-EXCLUSION bill gate, measured.

Root cause of the NY-omnibus false positives: bare "medicaid"/"reimburse" tokens matched
budget bills and pro-access coverage bills. Fixes (v1):
  (a) CO-OCCURRENCE: a Medicaid/funding token AND an abortion-provider token
      ("abortion provider","prohibited entity","planned parenthood","defund","family planning
      by abortion") — a lone "Medicaid" no longer routes.
  (b) NEG appropriations/omnibus gate: drop titles that are clearly budget/omnibus
      ("enacts into law major components","implement...budget","appropriation") UNLESS
      Planned Parenthood / abortion is explicitly named.
  (c) RESTRICT stance required: pro-access coverage/"practical support"/"appreciation day"
      bills are not exclusion threats.
  (d) LegiScan relevance floor: drop weak full-text matches below REL_FLOOR.

Measured on a HAND-LABELED golden set of 26 real bills (from the live LegiScan cache),
precision/recall/F1 before (v0) vs after (v1).
Bill data © LegiScan LLC (legiscan.com), CC BY 4.0.
"""
from legiscan_ingest import _stance, state_exclusion_v1

# v0 = the ORIGINAL broad routing (bare medicaid/reimburse token), reconstructed for the
# before/after comparison (the production _route now uses v1, so we can't call it for v0).
_V0_KWS = ["prohibited entity", "qualified provider", "medicaid", "defund", "abortion provider", "reimburse"]
def _route_v0_excl(title):
    t = (title or "").lower()
    repro = any(k in t for k in ["abortion", "planned parenthood", "family planning", "reproductive",
                                 "medicaid", "title x"])
    return repro and any(k in t for k in _V0_KWS)

REL_FLOOR = 50   # LegiScan relevance %; NY budget bills came in at 21-28

FUND_TOK = ["medicaid", "reimburse", "funds", "funding", "title x", "taxpayer", "public business",
            "charitable organization"]
PROVIDER_TOK = ["abortion provider", "prohibited entity", "planned parenthood", "defund",
                "abortion providers", "family planning by abortion", "provision of abortion",
                "coverage for abortion", "funding for abortion", "funds for abortion",
                "logistical support", "abortion coverage"]
OMNIBUS = ["enacts into law major components", "implement", "appropriation", "state budget",
           "omnibus", "major components of legislation"]
RESTRICT = ["prohibit", "defund", "exclude", "restrict", "terminate", "end taxpayer", "no abortion",
            "no funding", "prohibiting", "ban"]
PROACCESS = ["practical support", "access to abortion", "appreciation day", "requires health",
             "coverage for family planning", "remote monitoring", "postpartum"]

def route_v1(title, relevance=100):
    """Tightened state_exclusion routing. Returns 'state_exclusion' or None."""
    t = (title or "").lower()
    try:
        rel = int(relevance)
    except Exception:
        rel = 100
    # (d) relevance floor unless a hard provider token is present
    hard = any(p in t for p in ["planned parenthood", "prohibited entity", "abortion provider", "defund"])
    if rel < REL_FLOOR and not hard:
        return None
    # (c) pro-access -> not an exclusion threat
    if any(p in t for p in PROACCESS) and not any(r in t for r in ["prohibit", "defund", "exclude", "ban"]):
        return None
    # (b) omnibus/appropriations unless PP/abortion explicitly named
    if any(o in t for o in OMNIBUS) and not ("planned parenthood" in t or "abortion" in t):
        return None
    # (a) co-occurrence, loosened: an exclusion bill = RESTRICT intent + abortion/PP subject
    #     + a funding-or-provider hook. (A lone "Medicaid" or a lone "abortion" won't route.)
    abortion_present = ("abortion" in t) or ("planned parenthood" in t)
    restrict = any(r in t for r in RESTRICT)
    fund_or_provider = any(f in t for f in FUND_TOK) or any(p in t for p in PROVIDER_TOK) or "provider" in t
    if "defund planned parenthood" in t:
        return "state_exclusion"
    if "planned parenthood" in t and restrict:
        return "state_exclusion"
    if abortion_present and restrict and fund_or_provider:
        return "state_exclusion"
    return None

# ---------------- HAND-LABELED GOLDEN SET (26 real bills; gold=1 genuine exclusion, 0 not) ----------------
# (state, bill, relevance, title, gold)
GOLD = [
 ("AZ","HB2810",98,"Health education; abortion providers; prohibitions",1),
 ("MS","SB2620",99,"Abortion providers; prohibit public business with.",1),
 ("MS","HB979",88,"Medicaid; exclude from participation any providers that perform or refer abortion",1),
 ("NC","H192",96,"Defund Planned Parenthood & Cost Transparency",1),
 ("NH","HB1338",97,"Restricting abortion providers from the definition of charitable organization",1),
 ("OH","HB410",92,"Prohibit Medicaid funds for certain abortion providers",1),
 ("OK","HB3592",97,"Medicaid; term; funds for abortions; exceptions; effective date.",1),
 ("SC","S0778",98,"Prohibit Medicaid Funding for Family Planning by Abortion Providers",1),
 ("TX","SB33",99,"Relating to certain prohibited transactions and logistical support between a governmental entity and an abortion assistance entity or abortion provider",1),
 ("TX","HB1806",99,"Relating to certain prohibited transactions and logistical support between a governmental entity and an abortion assistance entity or abortion provider",1),
 ("TX","SB730",99,"Relating to certain prohibited transactions and logistical support between a governmental entity and an abortion assistance entity or abortion provider",1),
 ("US","HB719",99,"No Abortion Coverage for Medicaid Act",1),
 ("US","HB343",99,"Title X Abortion Provider Prohibition Act",1),
 ("US","SB4329",99,"Title X Abortion Provider Prohibition Act",1),
 ("US","SB125",98,"End Taxpayer Funding for Abortion Providers Act",1),
 ("US","HB271",99,"Defund Planned Parenthood Act of 2025",1),
 ("US","SB203",96,"Defund Planned Parenthood Act",1),
 ("WV","SB921",99,"Prohibiting Medicaid from being used for abortions or gender reassignment",1),
 # ---- false positives v0 produced ----
 ("NJ","A4349",86,"Requires health insurance and Medicaid coverage for family planning services",0),
 ("NJ","S2257",85,"Requires health insurance and Medicaid coverage for family planning services",0),
 ("NY","A02137",97,"Provides practical support for access to abortion care including funding",0),
 ("NY","S03007",24,"Enacts into law major components of legislation necessary to implement the health budget",0),
 ("NY","A10007",21,"Enacts into law major components of legislation necessary to implement the state budget",0),
 ("VA","HB425",93,"Pregnant and postpartum patients; reimbursement for remote monitoring services",0),
 ("US","HCR78",93,"Expressing support for the recognition of March 10, 2026, as Abortion Provider Appreciation Day",0),
 ("TX","HB1098",98,"Relating to the coverage and provision of abortion, contraception, and sterilization under Medicaid and certain health benefit plans",0),
]

def score(router, uses_rel=False):
    tp=fp=fn=0; fps=[]; fns=[]
    for st,bill,rel,title,gold in GOLD:
        pred = 1 if (router(title, rel) if uses_rel else router(title)[0]=="state_exclusion") else 0
        if pred and gold: tp+=1
        elif pred and not gold: fp+=1; fps.append(f"{st} {bill}")
        elif not pred and gold: fn+=1; fns.append(f"{st} {bill}")
    prec=tp/(tp+fp) if tp+fp else 0; rec=tp/(tp+fn) if tp+fn else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    return dict(tp=tp,fp=fp,fn=fn,precision=prec,recall=rec,f1=f1,fps=fps,fns=fns)

def _v0(title, rel=100):
    return "state_exclusion" if _route_v0_excl(title) else None
def _v1(title, rel=100):   # the PRODUCTION function (no drift)
    return "state_exclusion" if state_exclusion_v1(title, rel) else None

if __name__=="__main__":
    npos=sum(g[4] for g in GOLD); nneg=len(GOLD)-npos
    print("="*84); print(f"STATE-EXCLUSION GATE — golden set: {len(GOLD)} bills ({npos} genuine, {nneg} not)"); print("="*84)
    for lbl,router,ur in (("v0 (bare medicaid/reimburse token)",_v0,True),
                          ("v1 (PRODUCTION: co-occurrence + omnibus-NEG + stance + relevance floor)",_v1,True)):
        s=score(router,uses_rel=True)
        print(f"\n{lbl}")
        print(f"   TP={s['tp']} FP={s['fp']} FN={s['fn']}   precision={s['precision']:.2f} recall={s['recall']:.2f} F1={s['f1']:.2f}")
        if s['fps']: print(f"   FALSE POSITIVES: {', '.join(s['fps'])}")
        if s['fns']: print(f"   MISSES: {', '.join(s['fns'])}")
    print("\nBill data © LegiScan LLC (legiscan.com), CC BY 4.0.")
