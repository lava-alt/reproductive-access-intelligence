# Demographic Validation — before we encode any assumption

**Mandate:** don't hard-code "young women register → blue → pro-access win." Validate each link against verified sources, cross-validate, run cuts neutrally (no cherry-pick), report surprises honestly — including disconfirming evidence.

**Sources cross-validated (3 independent, well-regarded):**
- **Pew Research Center**, "Broad public support for legal abortion persists 2 years after Dobbs" (May 2024) — *attitudes*
- **AP VoteCast** (via KFF analysis, 2024; AP analysis of KS 2022) — *actual ballot behavior*, >100k sample
- **TargetSmart** (Tom Bonier, 2022) — *voter-registration* behavior

**Caveat on level:** these are published aggregate crosstabs, not individual-level microdata (CES/ANES). Cross-source agreement is strong, but a v2 rigor step is voter-file-matched microdata to confirm effect sizes hold at the individual level.

---

## Pre-registered cuts, reported in full (no selection)

### Link 1 — demographic → abortion *attitude* (Pew 2024, 63% overall "legal in all/most")

| Cut | Support "legal all/most" | Gap |
|---|---|---|
| **Party** | Dem 85% vs **Rep 36%** | **≈49 pts — dominant** |
| **Religion** | Unaffiliated 86%, Catholic 59%, (evangelical much lower) | large |
| **Gender** | Women 66% vs Men 61% | **only 5 pts** |
| **Age** | younger higher, but see below | small once party held |

**The decisive control — gender/age *within* party (this is the test that matters):**
- Dem women 87% vs Dem men 84% = **3 pts**
- Rep women 40% vs Rep men 37% = **3 pts**
- Dem *young* women 87% vs Dem young men 82% = 5 pts; Rep young women 36% vs young men 31% = 5 pts

> **Finding 1 (overturns my prior):** once you know party, **gender and age add almost nothing to attitude** (~3–5 pts). "Women are pro-choice" as an independent *attitude* driver is far weaker than assumed. Party and religiosity dominate. **Do NOT encode "female → pro-access attitude" as an independent model term — it double-counts party and is nearly noise.**

### Link 2 — demographic → *ballot behavior* (AP VoteCast) — where it gets surprising

- **38% of Trump voters nationally** say abortion should be legal in all/most cases.
- **~3 in 10** voters who backed abortion-rights measures in AZ/MO/NV **also voted Trump**.
- **~4 in 10 Republicans/Trump voters** voted *for* abortion measures in some states.

> **Finding 2 (the big one, data-driven not assumed):** on abortion **ballot measures**, party breaks down — there is **massive cross-party defection toward pro-access.** A model that infers ballot outcome from **party registration systematically UNDERCOUNTS the pro-access side by 30–40% of Republicans.** This — not demographics — is the core reason party-weighted polls missed Kansas.

### The registration surge (TargetSmart, validated)
- Kansas: **70% of post-Dobbs new registrants were women**; women = **56% of ballots cast** (largest gender gap Bonier had ever measured; 53% in 2020).
- National: in **41 of 45** states women's share of new registrants rose post-Dobbs; 9 states women out-registered men by 10+ pts.
- Wisconsin: women +15 pts; new registrants **52% Dem vs <17% Rep**.

> **Finding 3 — reinterpret the surge correctly:** given Finding 1, the surge matters **NOT** because women hold different views (they barely do, within party), but because it is an observable proxy for **issue salience + asymmetric mobilization** — one side got activated. Encode the surge as a **turnout/mobilization signal, not an attitude signal.**

---

## The "blue flip" assumption — tested, and partly FALSE

The user's caution was right. **Registration surge ≠ "state flipping blue."** Kansas is deep red (Trump +15) and voted **59% pro-access.** The pro-access *ballot* coalition is **broader than the Democratic coalition** (Findings 2 + 3 stack: mobilization asymmetry + cross-party defection). Inferring "blue" from the surge is the **wrong frame** — it's an **issue coalition**, not a party one. Encoding it as "blue" would itself be the loaded assumption we were told to avoid.

## Disconfirming evidence (reported, not buried)
- **Florida, South Dakota, Nebraska ballot measures FAILED in 2024** despite the general pattern. Mobilization + cross-party defection are **necessary, not sufficient** — a 60% supermajority rule (FL), competing/decoy measures (NE), and a deep-red ceiling (SD) still beat them.
- **2024 Latino shift toward Trump** complicates any race-based term; many still voted pro-access on measures (issue≠party held), so **race is a weak, unstable predictor — don't lean on it.**

---

## What this means for the model (concrete, de-assumption-ed)

**Ballot-event signals to encode:**
1. **Registration-surge asymmetry** (behavioral mobilization proxy) — from state SoS / TargetSmart. Strong, leading, hard-to-fake. *This is the KS signal.*
2. **Cross-party defection correction** — a structural term that widens pro-access support ~30–40% beyond the party baseline on abortion measures. *This is what actually fixes the KS miss.*
3. **Threshold rule** (supermajority) — decisive hard modifier (already in v1; it's what got Florida right).
4. **Polls** — discounted, wide bands.
5. **Do NOT** add "female %" or "young %" as independent attitude terms — Finding 1 says they're ~noise once party + mobilization are in.

**Net correction to my earlier "add a demographic-skewed registration signal":** the signal is right, but the *reason* is mobilization, not attitude — and it must be paired with the cross-party-defection term, or it still under-predicts pro-access. The single most important, most-validated, least-obvious lever is **Finding 2**.
