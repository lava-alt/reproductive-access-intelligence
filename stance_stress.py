#!/usr/bin/env python3
"""
STRESS TEST — "only restrictive bills get through" filtering.
Two designs on a hand-labeled golden set of REAL bills (incl. the euphemism traps in both
directions that broke the naive filter):

  A = STRICT single guard   : routed AND _stance=='restrict' AND not in a pro-access blocklist.
                              (current production; high precision risk of low recall)
  B = BROAD + SECOND PASS    : cast wide (any repro-relevant, restrictive OR unclear), then a
                              NEGATION-AWARE directional verifier scores restrict-vs-protect signals
                              and passes only if net-restrictive. (recall recovered, precision kept)

Goal metric for a trust tool: PRECISION on restrictive (never pass a pro-access bill) first,
then recall. We report precision/recall/F1 for both, and list each design's errors.
"""
import legiscan_ingest as G
from map_data import PROACCESS_MAP

# ---------- GOLDEN SET: (title, gold)  gold=1 genuinely RESTRICTIVE (anti-access), 0 = not ----------
GOLD=[
 # ---- clear RESTRICTIVE ----
 ("Abortion-inducing drugs; trafficking; felony; exceptions; effective date.",1),
 ("Abortion; prohibiting manufacture or provision of abortion-inducing drugs; authorizing certain",1),
 ("Relating to certain prohibited transactions and logistical support between a governmental entity and an abortion provider",1),
 ("Defund Planned Parenthood & Cost Transparency",1),
 ("Abortion providers; prohibit public business with.",1),
 ('"Pain-Capable Unborn Child Protection Act"; bans abortion 20 weeks',1),
 ("PARTIAL BIRTH ABORTION BAN",1),
 ("Public Health - Abortion (Heartbeat Bill)",1),
 ("Criminal Law - Causing Ingestion of an Abortion-Inducing Drug - Prohibited",1),
 ('Enacts the "life appropriation act" prohibiting state funding for abortion',1),
 ("Prohibits the use of state funds for non-residents seeking an abortion",1),
 ("Prohibiting Medicaid from being used for abortions or gender reassignment",1),
 ("Defund Planned Parenthood Act of 2025",1),
 ('Creates the "Born-Alive Abortion Survivors Protection Act"',1),
 ("Use of public funds to cover abortions under MinnesotaCare prohibited",1),
 ("Abortions; public funding; prohibition",1),
 ("Abortion; Abolition of Abortion Act; purpose; enforcement",1),
 ("Fetal Heartbeat Act; prohibit abortion after detectable heartbeat",1),
 ("Relating to the definition of abortion.",1),
 ("Abortion; providers; waiting period; ultrasound",1),
 ("Telemedicine; abortion prohibition",1),
 ("Coercion of a pregnant minor female into seeking or obtaining an abortion",1),
 ("Title X Abortion Provider Prohibition Act",1),
 ("Establishing personhood at conception; equal protection for the unborn",1),
 ("End Taxpayer Funding for Abortion Providers Act",1),
 # ---- PRO-ACCESS euphemism traps (contain prohibit/requires but are PROTECTIVE) ----
 ("Prohibits hospital interference with patient care where the practitioner",0),
 ("Prohibits issuance of certain search warrants relating to out-of-state abortion",0),
 ("Secures protections for patients and providers accessing and providing abortion",0),
 ("Urging The Department Of Health To Coordinate The Stockpiling Of Mifepristone",0),
 ("Reproductive Health Emergency Preparedness Program.",0),
 ("Affirming And Supporting The Requirement That Hospitals Provide Emergency Abortion",0),
 ('Establishes the "safeguarding reproductive care act"',0),
 ("Provides that mifepristone or misoprostol may be dispensed without in-person",0),
 ("Requires health insurance and Medicaid coverage for family planning services",0),
 ("MinnesotaCare programs medical assistance coverage of abortion services",0),
 ("Abortion Medication Access on College Campuses",0),
 ("Requires limited services pregnancy centers to disclose to clients",0),
 ("Prohibits governmental entities from granting legal personhood to a fetus",0),
 ("Provides practical support for access to abortion care including funding",0),
 ("Expressing support for the recognition of Abortion Provider Appreciation Day",0),
 ("Prohibits the use of restraints on and the use of force against incarcerated pregnant",0),
 ("Provides that hospitals which offer medical residency training in abortion",0),
 ("Repealing provisions relating to abortion reporting requirements",0),
 # ---- neutral / off-target (not restrictive) ----
 ("Enacts into law major components of legislation necessary to implement the state budget",0),
 ("Pregnant and postpartum patients; reimbursement for remote monitoring services",0),
 ("Public university emergency contraception education program",0),
]

# ---------- A: strict single guard (current production) ----------
def guard_A(title):
    tid,_=G._route(title,100)
    if not tid: return False
    if G._stance(title)!="restrict": return False
    if any(p in title.lower() for p in PROACCESS_MAP): return False
    return True

# ---------- B: broad first pass + negation-aware directional second pass ----------
# strong PROTECTIVE markers (object of a prohibit/require that flips direction to pro-access)
PROTECT=["hospital interference","interference with patient care","secures protection","protections for patient",
 "protections for provider","for patients and providers","search warrant","out-of-state","shield","safeguard",
 "safe harbor","access to abortion","right to abortion","reproductive freedom","freedom to","stockpil",
 "emergency preparedness","affirming","supporting the requirement","coverage for","coverage of abortion",
 "medicaid coverage for","insurance and medicaid coverage","dispensed without","prescription label","expand access",
 "medication access","disclose to clients","limited services pregnancy center","emergency contraception education",
 "granting legal personhood","practical support for access","appreciation day","restraints on","residency training",
 "repealing provisions relating to abortion reporting","remote monitoring","postpartum","reproductive care act"]
RESTRICT=["ban abortion","abortion ban","prohibit abortion","abortion prohibition","defund","prohibited entity",
 "abortion provider","providers; prohibit","trafficking","felony","criminal","unborn","born-alive","born alive",
 "heartbeat","gestational","total ban","dismemberment","partial birth","partial-birth","personhood at conception",
 "equal protection for the unborn","conception","exclude","prohibiting medicaid","prohibiting state funding",
 "public funding; prohibition","abolition of abortion","chemical abortion","waiting period","ultrasound",
 "informed consent","mandatory reporting","coercion of a pregnant","coercing","abortion-inducing drug","abolition",
 "title x abortion provider prohibition","taxpayer funding for abortion","funds for abortion","funds for non-residents"]
def _score(title):
    t=title.lower()
    r=sum(1 for k in RESTRICT if k in t); p=sum(1 for k in PROTECT if k in t)
    return r,p
def guard_B(title):
    tid,_=G._route(title,100)                       # broad first pass: repro-relevant + routable
    if not tid: return False
    r,p=_score(title)                               # negation-aware directional second pass
    return r>p and r>0

def evalg(guard):
    tp=fp=fn=tn=0; fps=[]; fns=[]
    for title,gold in GOLD:
        pred=1 if guard(title) else 0
        if pred and gold: tp+=1
        elif pred and not gold: fp+=1; fps.append(title[:52])
        elif not pred and gold: fn+=1; fns.append(title[:52])
        else: tn+=1
    prec=tp/(tp+fp) if tp+fp else 0; rec=tp/(tp+fn) if tp+fn else 0
    f1=2*prec*rec/(prec+rec) if prec+rec else 0
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,precision=prec,recall=rec,f1=f1,fps=fps,fns=fns)

if __name__=="__main__":
    npos=sum(g for _,g in GOLD)
    print("="*82); print(f"STANCE STRESS TEST — golden set: {len(GOLD)} bills ({npos} restrictive, {len(GOLD)-npos} not)"); print("="*82)
    for lab,gu in (("A  strict single guard (current)",guard_A),("B  broad + directional 2nd pass",guard_B)):
        s=evalg(gu)
        print(f"\n{lab}")
        print(f"   TP={s['tp']} FP={s['fp']} FN={s['fn']} TN={s['tn']}   precision={s['precision']:.2f}  recall={s['recall']:.2f}  F1={s['f1']:.2f}")
        if s['fps']: print("   FALSE POSITIVES (pro-access shown as threat - the cardinal sin):"); [print("     -",x) for x in s['fps']]
        if s['fns']: print("   FALSE NEGATIVES (real restrictive bill dropped):"); [print("     -",x) for x in s['fns']]
    print("\nGoal: precision=1.00 (never a pro-access false positive) with the higher recall.")
