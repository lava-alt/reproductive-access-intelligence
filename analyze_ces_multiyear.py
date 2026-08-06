#!/usr/bin/env python3
"""
Multi-year drift check on CES 2016 / 2018 / 2020 / 2022 (n ~ 60k each).
Same model every year -> do the demographic effects HOLD, or drift (populations/values/coalitions shift)?
DV: 'always allow abortion as a matter of choice' (Support=pro-choice), first item of each year's battery.
Reports, per year: weighted pro-choice by race + logit ORs for party/female/relig/Black(net)/Black x relig.
"""
import pandas as pd, numpy as np, statsmodels.formula.api as smf, warnings
warnings.filterwarnings("ignore")

YEARS={
 2016:{"f":"ces16.tab","sep":"\t","ab":"CC16_332a","g":"gender"},
 2018:{"f":"ces18.csv","sep":",","ab":"CC18_321a","g":"gender"},
 2020:{"f":"ces20.csv","sep":",","ab":"CC20_332a","g":"gender"},
 2022:{"f":"ces22.csv","sep":",","ab":"CC22_332a","g":"gender4"},
}
RACEMAP={1:"White",2:"Black",3:"Hispanic",4:"Asian"}

# label->code maps (some years, e.g. 2018 csv, ship value LABELS not codes)
MAPS={
 "ab":{"support":1,"oppose":2},
 "gender":{"male":1,"female":2,"man":1,"woman":2},
 "pid7":{"strong democrat":1,"not very strong democrat":2,"lean democrat":3,"independent":4,
         "lean republican":5,"not very strong republican":6,"strong republican":7,"not sure":8},
 "relig_imp":{"very important":1,"somewhat important":2,"not too important":3,"not at all important":4},
 "educ":{"no hs":1,"high school graduate":2,"some college":3,"2-year":4,"4-year":5,"post-grad":6},
 "race":{"white":1,"black":2,"hispanic":3,"asian":4,"native american":5,"mixed":6,"other":7,"middle eastern":8},
}
def norm(s, role):
    v=pd.to_numeric(s, errors="coerce")
    if v.notna().mean()>0.5: return v          # already numeric
    m=MAPS[role]
    return s.astype(str).str.strip().str.lower().map(m)

def load(year,c):
    cols=[c["ab"],"pid7",c["g"],"birthyr","educ","race","pew_religimp","commonweight"]
    df=pd.read_csv(c["f"],sep=c["sep"],usecols=lambda x:x.strip().strip('"') in cols,
                   encoding="latin-1",low_memory=False)
    df.columns=[x.strip().strip('"') for x in df.columns]
    df[c["ab"]]=norm(df[c["ab"]],"ab")
    df["pid7"]=norm(df["pid7"],"pid7")
    df[c["g"]]=norm(df[c["g"]],"gender")
    df["pew_religimp"]=norm(df["pew_religimp"],"relig_imp")
    df["educ"]=norm(df["educ"],"educ")
    df["race"]=norm(df["race"],"race")
    df["birthyr"]=pd.to_numeric(df["birthyr"],errors="coerce")
    df["commonweight"]=pd.to_numeric(df["commonweight"],errors="coerce")
    df["pro_choice"]=np.where(df[c["ab"]]==1,1,np.where(df[c["ab"]]==2,0,np.nan))
    g=df[c["g"]]
    df["female"]=np.where(g==2,1,np.where(g==1,0,np.nan))   # 1=male,2=female (gender & gender4)
    df["age"]=year-df["birthyr"]
    df=df[(df.pid7>=1)&(df.pid7<=7)]
    df["relig"]=5-df["pew_religimp"]; df=df[(df.relig>=1)&(df.relig<=4)]
    df=df[(df.educ>=1)&(df.educ<=6)]
    df["racecat"]=df["race"].map(RACEMAP).astype("object")
    df=df.dropna(subset=["pro_choice","female","age","pid7","relig","educ","racecat","commonweight"])
    df["racecat"]=pd.Categorical(df["racecat"],categories=["White","Black","Hispanic","Asian"])
    for col in ["pro_choice","female","age","pid7","relig","educ","commonweight"]:
        df[col]=df[col].astype(float)
    return df

def OR(m,term):
    for t in m.params.index:
        if t==term or t.endswith(term):
            return np.exp(m.params[t]), m.pvalues[t]
    return None,None

rows=[]
racepct={}
for year,c in YEARS.items():
    df=load(year,c)
    print(f"[debug] {year}: rows={len(df)}  racecat={dict(df.racecat.value_counts())}  pro_choice_mean={df.pro_choice.mean():.3f}")
    # weighted pro-choice by race (robust: drop nonpositive weights, fallback to unweighted)
    def wpct(sub):
        v=sub.pro_choice.to_numpy(dtype=float); w=sub.commonweight.to_numpy(dtype=float)
        ok=np.isfinite(v)&np.isfinite(w)&(w>0)
        if ok.sum()==0: return float("nan")
        if w[ok].sum()<=0: return round(v[ok].mean()*100,1)
        return round(np.average(v[ok],weights=w[ok])*100,1)
    rp={r: wpct(df[df.racecat==r]) for r in ["White","Black","Hispanic","Asian"]}
    racepct[year]=rp
    m=smf.logit("pro_choice ~ pid7 + relig + female + age + educ + C(racecat, Treatment('White'))",data=df).fit(disp=0)
    mi=smf.logit("pro_choice ~ pid7 + female + age + educ + C(racecat, Treatment('White'))*relig",data=df).fit(disp=0)
    or_party,_=OR(m,"pid7"); or_fem,pf=OR(m,"female"); or_rel,_=OR(m,"relig")
    or_blk,pb=OR(m,"[T.Black]"); or_bxr,pbx=OR(mi,"[T.Black]:relig")
    rows.append(dict(year=year,n=int(m.nobs),R2=round(m.prsquared,3),
        OR_party=round(or_party,2),OR_female=round(or_fem,2),OR_relig=round(or_rel,2),
        OR_Black_net=round(or_blk,2),pBlack=f"{pb:.0e}",
        OR_BlackXrelig=round(or_bxr,2),pBxR=f"{pbx:.0e}"))

print("="*94)
print("WEIGHTED pro-choice % by race, by year  (drift in levels)")
print("="*94)
print(f"  {'year':<6}{'White':>8}{'Black':>8}{'Hispanic':>10}{'Asian':>8}")
for y in YEARS:
    rp=racepct[y]; print(f"  {y:<6}{rp['White']:>8}{rp['Black']:>8}{rp['Hispanic']:>10}{rp['Asian']:>8}")

print("\n"+"="*94)
print("MODEL COEFFICIENTS by year  (drift in structure). OR>1 = more pro-choice.")
print("  party: OR<1 per step toward GOP.  female OR>1.  relig OR<1.  Black_net = Black vs White net of controls.")
print("  BlackXrelig OR>1 = religiosity suppresses Black support LESS (the buffer).")
print("="*94)
t=pd.DataFrame(rows)
print(t.to_string(index=False))

print("\nREAD: are party-dominance / female / Black-net / Black-buffer STABLE across 2016->2022?")
