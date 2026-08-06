"""
Hardened precision gates for the wide net (Experiment 2).

v0 problem (observed live): the Federal Register full-text term search "Title X
family planning" returned 40 docs, ZERO of which contained the literal program
token "Title X" in their visible title/abstract (Medicare OPPS rules, marine-mammal
takes, stablecoin CIP rules...). The v0 gate passed several because it accepted the
GENERIC token "family planning" as repro-evidence -> a soft false-positive that
surfaced a Medicare OPPS proposed rule as a 47% "Title X" threat.

v1 fixes:
  (a) Program-specific gate: the `titlex` threat requires the literal token "title x"
      (or "office of population affairs") in the visible title/abstract -- generic
      "family planning" is NOT sufficient (it appears in Medicare/Medicaid rules).
  (b) Agency scoping: FR repro threats are only credible from HHS/FDA/CMS/OPA (+DOJ
      for comstock). A "family planning" mention in a Commerce/Treasury/NRC doc is noise.
  (c) Hard NEG list for cross-domain homographs ("marine mammal", "stablecoin",
      "reduction in force", "public charge", "live nation", "in vitro fertilization").
"""

# repro evidence, split by strength. NOTE: bare "comstock" is deliberately NOT a
# strong token -- it is a common surname ("Jon Comstock v. Arkansas"). The Comstock
# *Act* is evidenced only with abortion/mailing/statute context (see PROGRAM_TOKEN).
REPRO_STRONG = ["mifepristone", "misoprostol", "abortion", "reproductive health",
                "planned parenthood", "emtala", "church amendment",
                "office of population affairs"]
REPRO_WEAK = ["family planning", "contracept", "pregnan"]   # necessary-not-sufficient alone

# program-specific required tokens (a threat only fires if its OWN program is named)
PROGRAM_TOKEN = {
    "titlex":   ["title x", "office of population affairs", "population affairs"],
    "fda_mife": ["mifepristone", "misoprostol", "abortion pill", "chemical abortion", "rems"],
    "comstock": ["comstock act", "18 u.s.c. 1461", "18 u.s.c. 1462", "1461",
                 "mailing of abortion", "abortion-inducing"],   # NOT bare "comstock"
    "emtala":   ["emtala", "emergency medical treatment", "stabilizing treatment", "church amendment"],
    "aca1303":  ["1303", "abortion coverage", "separate payment for abortion"],
    "fed_defund": ["planned parenthood", "prohibited entity", "defund"],
    "state_exclusion": ["planned parenthood", "qualified provider", "provider exclusion"],
}

# ---- court lane gate (mirrors feeds_wide.py): a case is repro-relevant only if its
# caseName carries a genuine repro token, OR it is a clean FDA-lane case ("X v. FDA").
COURT_REPRO_TOKENS = ["abortion", "reproduct", "mifepristone", "misoprostol",
                      "planned parenthood", "family planning", "population affairs",
                      "contracept", "danco", "emtala", "moyle"]

def court_ok(case_name):
    n = (case_name or "").lower()
    if any(t in n for t in COURT_REPRO_TOKENS):
        return True
    if ("v. fda" in n or "fda v" in n or "v fda" in n):   # trusted FDA lane
        return True
    return False

HHS_AGENCIES = ["health and human services", "food and drug administration",
                "centers for medicare", "population affairs", "children and families",
                "justice department", "office of the secretary"]

NEG_HOMOGRAPH = ["marine mammal", "stablecoin", "reduction in force", "public charge",
                 "live nation", "in vitro fertilization", "endangered", "radiation",
                 "student loan", "higher education", "workforce pell", "tobacco product",
                 "renal disease", "home health prospective", "outpatient prospective",
                 "inpatient prospective", "physician fee"]


def repro_relevant(title, abstract):
    """Universal gate: is the VISIBLE title/abstract actually about repro care?"""
    text = ((title or "") + " " + (abstract or "")).lower()
    if any(n in text for n in NEG_HOMOGRAPH) and not any(s in text for s in REPRO_STRONG):
        return False
    return any(s in text for s in REPRO_STRONG) or any(w in text for w in REPRO_WEAK)


def threat_ok(tid, title, abstract, agencies=None, hardened=True):
    """
    Does this doc credibly evidence THREAT `tid`?
      hardened=False -> v0 behavior (generic repro token is enough).
      hardened=True  -> v1: require the threat's OWN program token (+ agency scope).
    """
    text = ((title or "") + " " + (abstract or "")).lower()
    ag = " ".join(a.get("name", "").lower() if isinstance(a, dict) else str(a).lower()
                  for a in (agencies or []))

    if not repro_relevant(title, abstract):
        return False

    if not hardened:
        # v0: any repro token present -> accept (this is the bug that let OPPS through)
        return True

    # v1 (a) program-specific token required
    toks = PROGRAM_TOKEN.get(tid, [])
    if toks and not any(t in text for t in toks):
        return False
    # v1 (b) agency scope for the admin/FR lane (skip if no agency metadata, e.g. court)
    if agencies and ag and not any(h in ag for h in HHS_AGENCIES):
        return False
    # v1 (c) already handled by NEG_HOMOGRAPH inside repro_relevant
    return True
