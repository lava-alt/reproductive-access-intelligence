#!/usr/bin/env python3
"""
Two-stage stance gate — the production classifier for "is this bill RESTRICTIVE (anti-access)."

Design (empirically + literature validated — see stance_stress.py and CALIBRATION/stance research):
  STAGE 1 (high recall): the bill routes to a repro threat (done by legiscan_ingest._route).
  STAGE 2 (precision):   is_restrictive() scores RESTRICT vs PROTECT signals, NEGATION-AWARE so the
                         OBJECT flips direction ("prohibit ABORTION" restrictive; "prohibit
                         INTERFERENCE with patient care" protective). Passes only if net-restrictive.

This beat a strict single guard on a hand-labeled golden set: precision 1.00 vs 0.91, recall
0.92 vs 0.80 (stance_stress.py). The literature's higher-accuracy Stage 2 is an LLM stance verifier
(CoT + self-consistency + abstain->review); see llm_verify_stub() for the upgrade path.
"""

PROTECT=["hospital interference","interference with patient care","secures protection","protections for patient",
 "protections for provider","for patients and providers","search warrant","out-of-state","shield","safeguard",
 "safe harbor","access to abortion","right to abortion","reproductive freedom","freedom to","stockpil",
 "emergency preparedness","affirming","supporting the requirement","coverage for","coverage of abortion",
 "medicaid coverage for","insurance and medicaid coverage","dispensed without","prescription label","expand access",
 "medication access","disclose to clients","limited services pregnancy center","emergency contraception education",
 "granting legal personhood","practical support for access","appreciation day","restraints on","residency training",
 "repealing provisions relating to abortion reporting","remote monitoring","postpartum","reproductive care act",
 "protecting reproductive","protect reproductive","recognition of legal personhood by a governmental"]
RESTRICT=["ban abortion","abortion ban","prohibit abortion","abortion prohibition","defund","prohibited entity",
 "abortion provider","providers; prohibit","trafficking","felony","criminal","unborn","born-alive","born alive",
 "heartbeat","gestational","total ban","dismemberment","partial birth","partial-birth","personhood at conception",
 "equal protection for the unborn","conception","exclude","prohibiting medicaid","prohibiting state funding",
 "public funding; prohibition","abolition of abortion","chemical abortion","waiting period","ultrasound",
 "informed consent","mandatory reporting","coercion of a pregnant","coercing","abortion-inducing drug","abolition",
 "title x abortion provider prohibition","taxpayer funding for abortion","funds for abortion","funds for non-residents",
 "cover abortions under","public funds to cover abortion"]

def score(title):
    t=(title or "").lower()
    return sum(1 for k in RESTRICT if k in t), sum(1 for k in PROTECT if k in t)

# budget-omnibus / procedural bills are neither a restrictive nor protective abortion action
NEUTRAL=["enacts into law major components","implement the state budget","implement the health budget",
 "appropriations act","budget bill"]

def is_restrictive(title):
    """Stage 2: net-restrictive direction. Precision-first (a tie or protective-lean = NOT restrictive)."""
    t=(title or "").lower()
    if any(x in t for x in NEUTRAL):        # omnibus/procedural -> not an abortion threat
        return False
    r,p=score(title)
    return r>p and r>0

def restrictive(title):
    """PRODUCTION Stage-2 gate (wired live). Primary = the LLM stance verifier's cached verdict
    (Haiku, zeroshot, n=1 — validated precision 1.00 on the golden set, clears the keyword gate's
    false threats and catches the tail it misses). Fallback = the keyword is_restrictive() when a
    title isn't cached or stance_llm is unavailable, so the pipeline degrades gracefully and never
    needs the API key at render time. 'abstain'/'protective'/'neutral' verdicts -> NOT a map threat."""
    try:
        import stance_llm as L
        v = L.cached_verdict(title)
        if v is not None:
            return v == "restrictive"
    except Exception:
        pass
    return is_restrictive(title)          # offline fallback: keyword directional gate

def llm_verify_stub(title):
    """UPGRADE PATH (not wired; needs an Anthropic API key). Gold-standard Stage 2:
    prompt an LLM with target='access to abortion', chain-of-thought that names the actor + operative
    verb + whether the net effect EXPANDS or RESTRICTS access before labeling; structured output;
    self-consistency (sample 3-5x, require unanimous 'restrictive'); abstain band -> human review.
    Validate on a ~100-bill Guttmacher/LegiScan-labeled gold set to precision>=0.97 on the restrictive
    class. See stance research notes."""
    raise NotImplementedError("wire an API key to enable the LLM stance verifier")
