"""War Room model core: threats, validated weights, keyword classifier, risk scoring."""
import math
def logistic(x): return 1/(1+math.exp(-x))
def logit(p):    return math.log(p/(1-p))

# base rates by event type (from the validated backtest panel)
BASE={"federal":0.15,"admin":0.30,"court":0.12,"closure":0.08,"ballot":0.50,"state":0.20}

THREATS={
 "fda_mife":       {"label":"FDA mifepristone REMS re-tightening",        "type":"admin"},
 "titlex":         {"label":"Title X withholding / restriction",          "type":"admin"},
 "emtala":         {"label":"EMTALA emergency-abortion rollback",         "type":"admin"},
 "comstock":       {"label":"Comstock enforcement (mailed-pill ban)",     "type":"admin"},
 "aca1303":        {"label":"ACA 1303 abortion-coverage friction",        "type":"admin"},
 "fed_defund":     {"label":"Federal Medicaid defund (71113 re-pass)",    "type":"federal"},
 "state_exclusion":{"label":"State Medicaid exclusion post-Medina",       "type":"state"},
 # added for the LegiScan 50-state lane (labels/types only; validated weights untouched)
 "personhood":     {"label":"Fetal personhood (state)",                   "type":"state"},
 "state_ban":      {"label":"State gestational/total ban",                "type":"state"},
 # coverage-audit fix: categories that were being silently dropped, plus the catch-all
 "telehealth_ban": {"label":"Telehealth medication-abortion ban",         "type":"state"},
 "dismemberment":  {"label":"Procedure ban (dismemberment/partial-birth)","type":"state"},
 "contraception":  {"label":"Contraception restriction",                  "type":"state"},
 "trap":           {"label":"TRAP / clinic burden (waiting period, ultrasound)","type":"state"},
 "fetal_remains":  {"label":"Fetal-remains / fetal-death provisions",     "type":"state"},
 "repro_watch":    {"label":"Other repro restriction (review)",           "type":"state"},
}

# keyword rules: (threat, any-of-keywords, base_llr, inherently_repro)
RULES=[
 ("fda_mife",  ["mifepristone","abortion pill","chemical abortion","rems","misoprostol"], 1.3, True),
 ("titlex",    ["title x","title 10 family planning","family planning services"],          1.2, True),
 ("comstock",  ["comstock","18 u.s.c. 1461","18 u.s.c. 1462","mailing of abortion"],        1.4, True),
 ("emtala",    ["emtala","emergency medical treatment","stabilizing treatment"],            1.1, False),
 ("aca1303",   ["1303","separate payment for abortion","abortion coverage","marketplace"],  0.9, False),
 ("fed_defund",["prohibited entity","planned parenthood","defund"],                         1.0, False),
 ("state_exclusion",["qualified provider","provider exclusion","terminate.*medicaid"],      0.9, False),
]
SIGNIF={"Rule":1.0,"Proposed Rule":0.6,"Notice":0.35,"Presidential Document":1.1}
REPRO=["abortion","reproductive","mifepristone","misoprostol","contracept","family planning","title x","emtala","pregnan"]

def classify(title, abstract, doctype):
    text=((title or "")+" "+(abstract or "")).lower()
    repro_present=any(t in text for t in REPRO)
    mult=SIGNIF.get(doctype,0.4)
    hits=[]
    for tid,kws,w,inh in RULES:
        if any(k in text for k in kws):
            if not inh and not repro_present:   # gate non-repro-inherent threats on repro relevance
                continue
            llr=round(w*mult,2)
            trigger = doctype in ("Rule","Presidential Document") and llr>=1.0
            hits.append((tid,llr,trigger))
    return hits

# Calibration gain from robustness_experiments.py (60-event out-of-sample study): the model was
# UNDER-confident (evidence too weak vs base rate). lambda=1.2 improved OOS Brier 0.098->0.079 and
# cut confident-wrong errors 9->7 without inflating tail risk. Higher lambda just games Brier, so held at 1.2.
GAIN=1.2
def risk(threat_id, acc, cap=3.5):
    t=THREATS[threat_id]["type"]
    return logistic(logit(BASE[t]) + min(GAIN*acc, cap))

def risk_band(threat_id, acc, feeds, cap=3.5):
    """Point risk plus an uncertainty band (from the weight-perturbation study, ~+-7-8 pts,
    wider when fewer independent feeds corroborate). Returns (point, lo, hi) as percentages."""
    p=round(risk(threat_id, acc, cap)*100)
    hw = 4 if feeds>=4 else 6 if feeds==3 else 9 if feeds==2 else 12
    return p, max(1, p-hw), min(97, p+hw)
