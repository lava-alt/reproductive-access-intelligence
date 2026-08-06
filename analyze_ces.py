#!/usr/bin/env python3
"""
Individual-level validation on CES 2020 microdata (n~61k, Harvard Dataverse).
Question set (pre-registered, neutral):
  Q1 does PARTY dominate abortion attitude?
  Q2 does GENDER survive controlling for party+religion? (aggregate said ~3pt within party)
  Q3 does RACE survive controlling for party+religion?   <-- the open question
  Q4 is RACE mediated by / interacting with religiosity? (e.g. Black support 'despite' religiosity)
DV: pro_choice = CC20_332a==1  ("Always allow abortion as a matter of choice": 1=Support)
Weights: commonweight used for DESCRIPTIVES; models run unweighted (association structure),
         weighting caveat noted. This tests structure/effect-sizes, not population point estimates.
"""
import pandas as pd, numpy as np, statsmodels.formula.api as smf

COLS=["commonweight","birthyr","gender","educ","CC20_332a","pid7","pew_religimp","pew_churatd","race"]
df=pd.read_csv("ces20.csv", usecols=COLS, low_memory=False)
print(f"loaded {len(df):,} rows")

# ---- recode ----
df["pro_choice"]=np.where(df.CC20_332a==1,1,np.where(df.CC20_332a==2,0,np.nan))
df["female"]=np.where(df.gender==2,1,np.where(df.gender==1,0,np.nan))
df["age"]=2020-df.birthyr
df=df[(df.pid7>=1)&(df.pid7<=7)]                       # drop 'not sure'/missing party
df["relig"]=5-df.pew_religimp                          # 4=very religious ... 1=not at all
df=df[(df.relig>=1)&(df.relig<=4)]
df=df[(df.educ>=1)&(df.educ<=6)]
RACEMAP={1:"White",2:"Black",3:"Hispanic",4:"Asian",5:"Native",6:"Mixed",7:"Other",8:"MiddleEast"}
df["racecat"]=df.race.map(RACEMAP)
df=df.dropna(subset=["pro_choice","female","age","pid7","relig","educ","racecat"])
df=df[df.racecat.isin(["White","Black","Hispanic","Asian"])]   # 4 groups w/ enough n
print(f"analytic sample: {len(df):,}")

# ---- (0) cross-validate the microdata itself vs PRRI/Pew: weighted pro-choice by race ----
print("\n=== WEIGHTED pro-choice % by race (validate microdata vs PRRI/Pew) ===")
for r in ["Asian","Black","White","Hispanic"]:
    s=df[df.racecat==r]; w=s.commonweight
    pct=np.average(s.pro_choice, weights=w)*100
    print(f"  {r:<9} {pct:5.1f}%   (n={len(s):,})")

def report(name, formula):
    m=smf.logit(formula, data=df).fit(disp=0)
    print(f"\n--- {name} ---  (pseudo-R2={m.prsquared:.3f}, n={int(m.nobs):,})")
    for term in m.params.index:
        if term=="Intercept": continue
        coef=m.params[term]; p=m.pvalues[term]; orr=np.exp(coef)
        star="***" if p<.001 else "**" if p<.01 else "*" if p<.05 else "ns"
        print(f"    {term:<34} beta={coef:+.3f}  OR={orr:4.2f}  p={p:.1e} {star}")
    return m

print("\n"+"="*80)
print("Q1  PARTY alone")
report("M1: pro_choice ~ party", "pro_choice ~ pid7")

print("\n"+"="*80)
print("Q2/Q3  full controls (race = C(racecat), White reference)")
m3=report("M3: ~ party + relig + female + age + educ + RACE",
    "pro_choice ~ pid7 + relig + female + age + educ + C(racecat, Treatment('White'))")

print("\n"+"="*80)
print("Q4  RACE x RELIGIOSITY interaction (does race effect live in religiosity?)")
report("M4: + race*relig",
    "pro_choice ~ pid7 + female + age + educ + C(racecat, Treatment('White'))*relig")

# ---- predicted probabilities: race effect holding party+relig at sample means ----
print("\n"+"="*80)
print("PREDICTED pro-choice prob by race, holding party/relig/age/educ/gender at MEANS")
base=dict(pid7=df.pid7.mean(), relig=df.relig.mean(), female=df.female.mean(),
          age=df.age.mean(), educ=df.educ.mean())
import itertools
grid=pd.DataFrame([{**base,"racecat":r} for r in ["White","Black","Hispanic","Asian"]])
grid["pred"]=m3.predict(grid)
for _,row in grid.iterrows():
    print(f"  {row.racecat:<9} {row.pred*100:5.1f}%")
