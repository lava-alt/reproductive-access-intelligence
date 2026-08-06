# CES 2020 microdata — individual-level validation (n = 55,843)

Source: Cooperative Election Study 2020 Common Content (Harvard Dataverse, 61k respondents; analytic sample 55,843 after dropping missing party/attitude and restricting to the 4 race groups with sufficient n). DV = `CC20_332a` "always allow abortion as a matter of choice" (Support=pro-choice). Logistic regression. Weights used for descriptives; models unweighted (tests association structure, not population point estimates). Large-n significance is robust; SEs approximate (no survey-design correction).

## Microdata self-check (vs PRRI/Pew) — passes
Weighted pro-choice by race: **Black 71.0% · Asian 65.9% · Hispanic 60.6% · White 52.0%.**
Rank order matches PRRI/Pew (Black highest, White lowest). Absolute levels are lower than Pew's "legal in all/most" because this is a stricter *absolutist* item — but the structure validates.

## Results

**Q1 — Party dominates. CONFIRMED.**
Party alone: pseudo-R² = **0.208**. Adding religion + gender + age + education + race lifts it only to **0.278**. Party is by far the single largest predictor. `pid7` OR = 0.58–0.62 per step toward Republican.

**Q2 — Gender: I WAS WRONG. It's a real independent predictor.**
`female` OR = **1.43**, p = 3.5e-60 — highly significant *net of party, religion, everything*. My earlier "gender is nearly noise once you know party" (read off aggregate within-party crosstabs) was **too strong**. At the individual level on this item, women have ~1.4× the odds of pro-choice support. The microdata earned its keep by catching this. *(Magnitude is item-dependent — larger on the absolutist item than on Pew's "legal all/most," which is why the aggregate looked smaller.)*

**Q3 — Race survives, but ONLY for Black respondents.**
Controlling for party + religiosity + gender + age + education:
| Race (vs White) | OR | p | verdict |
|---|---|---|---|
| **Black** | **1.28** | 3.7e-12 *** | **real, independent** |
| Hispanic | 1.02 | 0.56 ns | ≈ White once controlled |
| Asian | 1.10 | 0.15 ns | ≈ White once controlled |

The raw Hispanic-lower / Asian-higher gaps are **fully explained by party + religion composition** — no independent race effect. **"Race" is not a monolith.** Only the Black pro-choice advantage is real net of covariates. Predicted probs at sample means: **White 65.2 · Black 70.6 · Hispanic 65.7 · Asian 67.3** — Black ~5pts above, others ~1pt.

**Q4 — WHERE the Black effect lives: a religiosity buffer.**
Race × religiosity interaction:
- Main `relig` effect strongly negative (OR 0.50 — more religious = less pro-choice), as expected.
- **Black × relig OR = 1.36, p = 5e-20*** ** — religiosity depresses Black pro-choice support **far less** than it does White. Black Americans hold high support *despite* high religiosity.
- Asian × relig OR 1.20 ** (weaker version); Hispanic × relig ns (behaves like White).

So the Black pattern isn't a generic "race" effect — it's that **the usual religiosity→anti-abortion link is much weaker among Black respondents** (a validated cross-pressure). p = 5e-20 is not a fluke.

## Conclusions → how to (and not) encode race

1. **Party is the backbone** (confirmed). Religion is the second lever (OR 0.50).
2. **Gender is a genuine independent signal** (OR 1.43) — revise my earlier dismissal; keep it, but item-scale it.
3. **Race matters — but specifically as a Black-distinct, religiosity-independent pattern**, NOT a generic race term. Hispanic and Asian effects are **party/religion-mediated** — capture them through party + religiosity, not a race dummy.
4. **The 2024 Latino→Trump shift is therefore a PARTY-term movement**, not a race-attitude change — it flows into the model through `party`, and would lower Hispanic pro-access ballot support *via party*, exactly as observed. Race-as-such stays stable; party moved.
5. **Behavior ≥ attitude:** on 2024 *ballots* (VoteCast) Black support was even higher (AZ 80%, FL 83%) — consistent with, and stronger than, the CES attitude signal.

**Net:** the user was right to keep race open. The validated encoding is a **Black-share / Black-mobilization signal (religiosity-independent)** for ballot events — and treating Hispanic/Asian variation as captured by the party + religiosity terms, not by race. Monitoring "race" generically would have been the loaded assumption; monitoring the *Black-specific, religiosity-buffered* pattern is what the data supports.

**Caveats:** 2020 data (pre-2024 realignment; re-run on CES 2022/2024 for drift). Absolutist DV item. Unweighted models for structure. Next: replicate on CES 2022, and test the same structure on *ballot-vote* microdata where available.
