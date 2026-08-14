#!/usr/bin/env python3
"""
LLM stance verifier (Stage 2, gold-standard). Classifies a bill title as RESTRICTIVE / PROTECTIVE /
NEUTRAL toward access to abortion & reproductive care, using chain-of-thought (actor -> operative
verb -> expand/restrict) + self-consistency + an abstain band. This is the precision layer the
research recommends; keyword stance_gate.is_restrictive is the offline fallback.

SECURITY: key read from .anthropic_key (or ANTHROPIC_API_KEY env). NEVER printed, NEVER logged,
NEVER committed (gitignored). The x-api-key header is never echoed, even on error.
"""
import os, json, hashlib, atexit, urllib.request, urllib.error

_HERE=os.path.dirname(os.path.abspath(__file__))
_KEYFILE=os.path.join(_HERE,".anthropic_key")
_CACHEFILE=os.path.join(_HERE,".stance_cache.json")
API="https://api.anthropic.com/v1/messages"

def _key():
    k=os.environ.get("ANTHROPIC_API_KEY")
    if k: return k.strip()
    with open(_KEYFILE) as f: return f.read().strip()

# ---- prompt builders (a SUB-DECISION under test: zeroshot vs cot vs fewshot) ----
TASK=('Classify whether this US legislative bill RESTRICTS or PROTECTS access to abortion and '
      'reproductive care. "restrictive" = limits/bans/criminalizes/defunds access. "protective" = '
      'expands/safeguards/funds access. "neutral" = neither (procedural, budget, off-target).')
FEWSHOT=[
 ('Prohibits hospital interference with patient care where the practitioner provides abortion','protective'),
 ('Creates the "Born-Alive Abortion Survivors Protection Act"','restrictive'),
 ('Requires health insurance and Medicaid coverage for family planning services','protective'),
 ('Abortion-inducing drugs; trafficking; felony; exceptions','restrictive'),
 ('Enacts into law major components of legislation necessary to implement the health budget','neutral'),
]
def _prompt(title, style):
    j='Output ONLY a JSON object: {"direction":"restrictive|protective|neutral","confidence":0-1}.'
    if style=="zeroshot":
        return f'{TASK}\n{j}\nBill title: "{title}"'
    cot=('Reason briefly: (1) who is the actor and what does the operative verb DO; (2) does the net '
         'effect EXPAND access (protective) or RESTRICT access (restrictive) or neither (neutral). '
         'Watch negation/euphemism: "prohibits hospital INTERFERENCE" PROTECTS; "prohibits ABORTION" '
         'RESTRICTS; "requires COVERAGE for abortion" PROTECTS; "born-alive protection" RESTRICTS.')
    if style=="fewshot":
        ex="\n".join(f'Title: "{t}" -> {{"direction":"{d}"}}' for t,d in FEWSHOT)
        return f'{TASK}\n{cot}\nExamples:\n{ex}\n{j} (JSON on the last line)\nBill title: "{title}"'
    return f'{TASK}\n{cot}\n{j} (put the JSON on the last line)\nBill title: "{title}"'

def _call(model, prompt, temperature, max_tokens=300):
    body=json.dumps({"model":model,"max_tokens":max_tokens,"temperature":temperature,
                     "messages":[{"role":"user","content":prompt}]}).encode()
    req=urllib.request.Request(API, data=body, headers={
        "x-api-key":_key(), "anthropic-version":"2023-06-01", "content-type":"application/json"})
    try:
        d=json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Anthropic HTTP {e.code} (key/header not shown)")   # never leak key
    except Exception as e:
        raise RuntimeError(f"Anthropic call failed: {type(e).__name__}")
    return "".join(b.get("text","") for b in d.get("content",[]) if b.get("type")=="text")

def _parse(txt):
    i=txt.rfind("{"); j=txt.rfind("}")
    if i<0 or j<0: return None
    try: return json.loads(txt[i:j+1])
    except Exception: return None

def classify(title, model="claude-haiku-4-5-20251001", style="cot", temperature=0.0):
    out=_parse(_call(model,_prompt(title,style),temperature))
    return (out or {}).get("direction","neutral")

def verify(title, model="claude-haiku-4-5-20251001", style="cot", n=3, temperature=1.0):
    """Self-consistency + abstain. Returns 'restrictive' only if ALL n samples say restrictive
    (precision-first). Unanimous protective/neutral -> that. Any disagreement -> 'abstain' (review)."""
    if n==1:
        return classify(title, model, style, 0.0)
    votes=[classify(title, model, style, temperature) for _ in range(n)]
    if all(v=="restrictive" for v in votes): return "restrictive"
    if all(v=="protective" for v in votes):  return "protective"
    if all(v=="neutral" for v in votes):     return "neutral"
    return "abstain"

# ---- verdict cache (keeps API cost in the cents/week band) --------------------------------------
# Keyed by (title, model, style, n): only NEW or config-changed titles hit the API; everything
# else is served from disk. Cache stores the verdict string only (no key, no bill data blobs).
# Rebuildable at any time -> gitignored. Experiment harness bypasses this (calls verify() directly)
# so its call-count cost proxy stays honest.
_CACHE=None; _DIRTY=[False]

def _cache():
    global _CACHE
    if _CACHE is None:
        try:
            with open(_CACHEFILE) as f: _CACHE=json.load(f)
        except Exception: _CACHE={}
    return _CACHE

def _ck(title, model, style, n):
    sig=f"{model}|{style}|n{n}|{(title or '').strip().lower()}"
    return hashlib.sha1(sig.encode()).hexdigest()

def flush():
    """Atomically persist the cache (temp file + rename) if anything changed."""
    if not _DIRTY[0] or _CACHE is None: return
    tmp=_CACHEFILE+".tmp"
    with open(tmp,"w") as f: json.dump(_CACHE, f)
    os.replace(tmp, _CACHEFILE); _DIRTY[0]=False
atexit.register(flush)

def verify_cached(title, model="claude-haiku-4-5-20251001", style="cot", n=3):
    """Production entry point. Cache hit -> instant, no API call. Miss -> verify() then store.
    Changing model/style/n changes the key, so a config change safely re-verifies (no stale verdicts)."""
    c=_cache(); k=_ck(title, model, style, n)
    if k in c: return c[k]
    v=verify(title, model=model, style=style, n=n)
    c[k]=v; _DIRTY[0]=True
    return v

def cached_verdict(title, model="claude-haiku-4-5-20251001", style="zeroshot", n=1):
    """CACHE-ONLY lookup — returns the stored verdict or None, NEVER calls the API. This is what
    production render uses: deterministic, instant, $0, no key needed at deploy time. Warm the cache
    offline with verify_cached; misses fall back to the keyword gate."""
    return _cache().get(_ck(title, model, style, n))

def cache_stats():
    c=_cache()
    return {"entries":len(c), "file":_CACHEFILE, "exists":os.path.exists(_CACHEFILE)}

if __name__=="__main__":
    for t in ['Prohibits hospital interference with patient care where the practitioner provides abortion',
              'Abortion-inducing drugs; trafficking; felony','Relating to the definition of abortion.']:
        try: print(f'{verify_cached(t)!r:14} <- {t[:56]}')   # 1st run hits API, 2nd run all cache
        except Exception as e: print("ERROR:", e, "(is .anthropic_key set?)"); break
    flush(); print("cache:", cache_stats())
