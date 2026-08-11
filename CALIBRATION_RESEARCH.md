# Calibration Research — Reproductive Access Intelligence risk engine

*Synthesis of four independent literature sweeps (post-hoc calibration, judgmental-forecasting, Bayesian uncertainty quantification, and ingestible datasets), mapped to our specific engine: a glass-box Bayesian log-odds accumulator, ~60 labeled events across 6 event types (some lanes only 5–7 examples), strong discrimination (AUC ~0.97) but poor calibration (ECE ~0.19), systematically **under-confident**, with a persistent weak **ballot** lane, on a domain that **shifted after Dobbs (Jun 2022)**.*

---

## 0. The headline: three fields, one answer

Three independent sweeps arrived at the **same** fix from different vocabularies:

| Field | Name for it | Prescription |
|---|---|---|
| ML calibration | **Temperature scaling** (T<1) | divide the log-odds by T<1 to sharpen an under-confident model |
| Judgmental forecasting | **Extremizing** the log-odds (γ>1) | GJP's documented remedy for under-confident aggregates |
| Bayesian UQ | posterior sharpening / informative prior | flat-prior MLE at small n is under-confident; fix the prior |

All three are **the same one-parameter transform on our accumulated log-odds** — which is exactly what our adopted **λ=1.2 evidence gain** already does. The research validates the move and sharpens *how* to set it:

> **Fit the scale by leave-one-out cross-validated log-loss, PER LANE, with a shrinkage prior centered at 1.0.** Keep it modest (a single correlated model wants the low end of the range, not a crowd's 1.7+). Log the loss-vs-scale *plateau width* as the safety check.

This is why our Brier had no interior optimum: **Brier-chasing is the wrong selector.** Use CV log-loss + the Brier reliability/resolution decomposition instead, and distrust ECE at n=60 (it's a biased, binning-sensitive estimator).

---

## 1. Methods menu, ranked by fit to n≈60

### Recalibration / fixing under-confidence (do first, cheap, glass-box-preserving)
- **Temperature scaling (1 param).** `p = σ(logit / T)`, T<1 sharpens. Best-in-class at tiny n; leaves AUC untouched (monotone). *Guo et al. 2017* [arxiv 1706.04599](https://arxiv.org/abs/1706.04599). **This is the principled version of our λ.**
- **Extremizing (1 param, γ on log-odds).** Empirically optimal range [1.16, 3.92] for diverse crowds; **modest for a single correlated model**. Fit per-lane, horizon matters (distant events want more). *Satopää et al. 2014* [IJF](https://www.sciencedirect.com/science/article/abs/pii/S0169207013001635); *Baron et al.* [PDF](https://sjdm.org/~baron/journal/21/210914/jdm210914.pdf).
- **Platt / logistic (2 params).** Adds an intercept if under-confidence has a base-rate *bias* too. sklearn: "most effective for small samples or under-confident models." [sklearn calibration](https://scikit-learn.org/stable/modules/calibration.html).
- **Beta calibration (3 params).** For *skewed* rare-event scores; includes identity so it won't over-correct. Only if a reliability diagram shows asymmetric distortion. *Kull et al. 2017* [AISTATS](https://proceedings.mlr.press/v54/kull17a.html), `pip install betacal`.
- **AVOID at n=60:** isotonic, histogram binning, spline — all overfit below ~1000 samples and can damage our AUC. (Unanimous across sweeps.)

### Honest uncertainty intervals (the principled version of our jitter bands)
- **Venn-Abers predictors** — *best for finite-sample-calibrated intervals at tiny n.* Outputs a probability **interval** [p0,p1] per prediction, guaranteed calibrated in finite samples; interval width auto-widens where data is thin (our 5-example ballot lane → honestly wide). `pip install venn-abers`. *Vovk & Petej* [arxiv 1211.0025](https://arxiv.org/pdf/1211.0025).
- **Bayesian bootstrap (Dirichlet weights)** — the principled sibling of our current weight-perturbation MC. Draw observation weights from Dirichlet(1,…,1), refit, take percentiles. *Rubin 1981* [PDF](https://statisticspg.scss.tcd.ie/wp-content/uploads/2020/11/Bayes_Bootstrap.pdf).
- **Conformal prediction** — distribution-free coverage, but only *marginal* at n=60; per-lane guarantees fail on sparse lanes. Use as a secondary check. *Angelopoulos & Bates* [arxiv 2107.07511](https://arxiv.org/abs/2107.07511).

### Sparse-lane fix (the ballot problem, structurally)
- **Bayesian hierarchical partial pooling** — *best for helping sparse event types.* Model lanes as exchangeable groups `(1 | lane)`; a 5-example lane borrows from the global mean by an amount the data dictates. Reframes our glass-box as a hierarchical logistic model, keeps interpretability, yields posterior-predictive intervals for free. *rstanarm pooling* [mc-stan](https://mc-stan.org/rstanarm/articles/pooling.html); Eight Schools template.
- **Beta-Binomial base-rate shrinkage** — closed-form conjugate version; stops rare-event base rates degenerating to 0/1. *Robinson empirical-Bayes* [varianceexplained](http://varianceexplained.org/r/empirical_bayes_baseball/).

### Distribution shift (post-Dobbs)
- **Time-decay / regime weighting** — down-weight pre-Dobbs events when fitting calibration (simple, defensible). Rigorous form: **weighted conformal under covariate shift** *Tibshirani et al. 2019* [arxiv 1904.06019](https://arxiv.org/pdf/1904.06019).
- **Adaptive Conformal Inference (ACI)** — rolling recalibration under arbitrary drift; fits our time-ordered event stream. *Gibbs & Candès 2021* [arxiv 2106.00170](https://arxiv.org/pdf/2106.00170).

### Validation protocol (mandatory given the shift)
- **Expanding-window walk-forward CV with an embargo/purge** — never shuffle (leaks future→past); gap train/test to kill autocorrelation leakage. Aggregate probability-outcome pairs across folds before the reliability diagram (positives are rare). *López de Prado 2018* purged K-fold; sklearn `TimeSeriesSplit`.

### Diagnostics
- **Brier = Reliability − Resolution + Uncertainty** (Murphy). Tells us *what kind* of broken each lane is: under-confidence is a **reliability** defect (fix with the scale param); low **resolution** needs better features. *Ferro & Fricker 2012* (bias-corrected).
- **Distrust ECE at n=60** — biased, binning-sensitive; report Brier decomposition + CV log-loss + a reliability diagram with confidence bands instead.

---

## 2. Recommendations (stacked, in order)

1. **Replace the fixed λ=1.2 with a CV-fit, per-lane scale.** Fit γ per lane by leave-one-out CV log-loss over the 60 events, shrinkage prior at γ=1, grid ~[1.0, 2.5]. Log plateau width. Expect a modest global γ (~1.1–1.3) and possibly γ≈1 for ballot (see #3). *This is the single highest-value, immediately runnable upgrade.*
2. **Decompose ballot-lane Brier before touching it.** If it's *reliability*, the per-lane γ fixes it. If it's *resolution/bias* (the 2022–24 abortion evidence strongly suggests bias — measures systematically over-performed partisan lean and were under-polled), extremizing won't help — add referendum features instead.
3. **Add referendum-specific features to the ballot lane:** measure direction (does "Yes" = change or status-quo), undecided share, turnout/registration-surge proxy, campaign-spending asymmetry. **Do not inherit candidate-race partisan-lean priors for abortion measures** (Kansas 2022 was an 18-pt polling miss; AZ/NV measures ran ahead of Harris).
4. **Upgrade the uncertainty bands** from ad-hoc jitter to **Venn-Abers intervals** (finite-sample calibrated) or a Dirichlet Bayesian bootstrap. Widest exactly where data is thinnest, honestly.
5. **Long-term architecture:** re-cast the glass box as a **Bayesian hierarchical logistic model** with a Beta-Binomial base-rate layer — one model that does pooling (sparse lanes), calibration, and posterior-predictive intervals coherently. Keeps interpretability.
6. **Handle Dobbs drift** with time-decay weighting + rolling recalibration; validate everything with expanding-window walk-forward CV + embargo.

---

## 3. Concrete experiments (prioritized, runnable)

| # | Experiment | What it answers | Effort |
|---|---|---|---|
| **E1** | **Per-lane LOO-CV scale fit** (γ grid + shrinkage prior; report CV log-loss, plateau width, per-lane γ) | Is λ=1.2 right? Per-lane? Safe (flat plateau) or fragile (sharp min)? | **Low, do now** |
| **E2** | **Brier reliability/resolution decomposition per lane** | Is each lane mis-*calibrated* or mis-*resolved*? Where extremizing helps vs where features are needed | Low, do now |
| **E3** | **Venn-Abers intervals** over the 60 events; LOO coverage check by lane | Replace jitter bands with finite-sample-calibrated intervals | Medium (`venn-abers`) |
| **E4** | **Ballot feature ablation** (add direction / undecided / turnout-surge / spending one at a time; LOO resolution gain) | Which referendum features actually raise ballot resolution | Medium (needs data, §4) |
| **E5** | **Expanding-window walk-forward backtest**, calibration pre/post-Dobbs | Quantify the drift; confirm recalibration fixes it | Medium |
| **E6** | **Hierarchical partial-pooling model** (`(1\|lane)` + Beta-Binomial base rate) vs current | Does pooling beat the flat model on sparse-lane log-loss? | High (Stan/PyMC) |

E1 and E2 need nothing new — just the 60-event panel we already have. Recommended immediate next step.

---

## 4. Data to ingest (grow past 60 events + add features)

**Phase 1 — explode the ballot lane + dated statute labels (biggest calibration win):**
1. **MEDSL/NCSL Ballot Measures Dataset** (Harvard Dataverse, CSV, 1902–2016; pass/fail + yes-share + type). Filter to abortion → multi-decade labeled ballot base. [dataverse](https://dataverse.harvard.edu/dataverse/medsl)
2. **Ballotpedia abortion-measure tables** (2017–2026; adds the **sponsor-direction** label MEDSL lacks). Verify vote shares vs **state SOS** certified results. [Ballotpedia history](https://ballotpedia.org/History_of_abortion_ballot_measures) *(copyrighted — extract, don't mass-scrape)*
3. **Guttmacher after-Roe tiers + tri-annual policy updates** × our **LegiScan** enactment dates → dated enacted-vs-failed restriction labels. [states.guttmacher](https://states.guttmacher.org/policies/)

**Phase 2 — features:** Ballotpedia **trifecta** + NCSL **legislature margins** (structural, likely strongest predictor), **PRRI** state abortion attitudes (opinion), **ANSIRH facilities** / **#WeCount** monthly volume (access shocks), **Metaculus** probabilities (external calibration benchmark). [KFF State Health Facts](https://www.kff.org/state-health-facts/) is the cleanest CSV export.

**Target schema — unified `event` table:** `event_id | state | lane | direction (protective/restrictive) | outcome | date | vote_share | threshold | source_url`, plus a **state-year feature panel**: `state | year | trifecta | legislature_margin | governor_party | PRRI_attitude | guttmacher_tier | facilities | monthly_provision`.

**Access caveats:** MEDSL (CC, cite); KFF/Guttmacher/NCSL/PRRI/CRR (reuse w/ attribution); Ballotpedia (extract only); ANSIRH microdata + ICPSR/Roper (free registration/approval, budget lead time). Brennan/CRR state-court tracker is **frozen (Jan 2024)** — use KFF + State Court Report for live court labels.

---

## 5. Honest caveats (flagged across all sweeps)
- **Extremizing is contested** — GJP tournament gains may be partly overfit ("small wins often, big losses sometimes"); it *theoretically assumes independence*, and a single glass-box model is the correlated case. Keep γ modest and empirically fit, not the crowd's 1.73.
- **6 groups is few** for estimating the hierarchical variance τ — use an informative prior on τ + sensitivity analysis; don't over-read the pooled result.
- **Per-lane coverage guarantees are weak at 5–7 examples** for any method — plain conformal gives marginal coverage only; be explicit that per-lane intervals are model-informed, not distribution-free-guaranteed.
- **ECE at n=60 is unreliable** — the 0.19 number is binning-sensitive; treat as rough.
- **No single machine-readable API spans 2017–2026 ballot results** — plan a manual/semi-automated MEDSL+Ballotpedia+SOS merge.

---

## 6. Key sources
Post-hoc calibration: [sklearn](https://scikit-learn.org/stable/modules/calibration.html), Guo 2017 [1706.04599](https://arxiv.org/abs/1706.04599), Kull 2017 [AISTATS](https://proceedings.mlr.press/v54/kull17a.html), Niculescu-Mizil & Caruana 2005. Uncertainty: Vovk & Petej Venn-Abers [1211.0025](https://arxiv.org/pdf/1211.0025), Angelopoulos & Bates [2107.07511](https://arxiv.org/abs/2107.07511), Rubin 1981 Bayesian bootstrap, rstanarm pooling [mc-stan](https://mc-stan.org/rstanarm/articles/pooling.html), Tibshirani 2019 [1904.06019](https://arxiv.org/pdf/1904.06019), Gibbs & Candès [2106.00170](https://arxiv.org/pdf/2106.00170). Forecasting: Satopää 2014 [IJF](https://www.sciencedirect.com/science/article/abs/pii/S0169207013001635), Baron/Han-Budescu [PDF](https://sjdm.org/~baron/journal/21/210914/jdm210914.pdf), GJP evidence [AI Impacts](https://aiimpacts.org/evidence-on-good-forecasting-practices-from-the-good-judgment-project/), Kansas-2022 miss / Guttmacher 2024. Data: [MEDSL](https://dataverse.harvard.edu/dataverse/medsl), [Guttmacher](https://states.guttmacher.org/policies/), [KFF](https://www.kff.org/state-health-facts/), [Ballotpedia trifectas](https://ballotpedia.org/State_government_trifectas), [NCSL](https://www.ncsl.org/about-state-legislatures/state-partisan-composition), [PRRI](https://prri.org/research/abortion-views-in-all-50-states-findings-from-prris-2023-american-values-atlas/), [ANSIRH](https://www.ansirh.org/abortion-facility-database), [#WeCount](https://societyfp.org/research/wecount/).
