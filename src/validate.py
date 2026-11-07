"""Statistical alignment checks: sampled population vs the calibration targets.

Two kinds of check, reported separately because they mean different things:

  1. Implementation checks (marginals): quantities the sampler draws directly from
     a source distribution (industry mix, firm-size shares, role mix, sex by role,
     education by role). A failure here is a bug; a pass shows the code reproduces
     the source numbers. These agree by construction.
  2. Held-out checks: quantities the sampler does NOT draw directly, compared with a
     source statistic it was not fit to (median tenure vs BLS 4.1 years, median age
     by role, LinkedIn use among college graduates vs Pew, mean phish-prone % vs
     KnowBe4). Agreement here is evidence the joint structure is realistic.

Each row has: quantity, observed, target, test statistic. Chi-square p-values are
for goodness of fit against the target distribution (large p = no evidence of
mismatch); total-variation (TV) distance is reported alongside because chi-square
loses power at small n and over-rejects at large n.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import empirical as E  # noqa: E402


def _norm(d: dict[str, float]) -> dict[str, float]:
    t = sum(d.values())
    return {k: v / t for k, v in d.items()}


def _gof(observed: Counter, target: dict[str, float]) -> dict[str, float]:
    keys = [k for k, v in target.items() if v > 0]
    n = sum(observed.get(k, 0) for k in keys)
    obs = np.array([observed.get(k, 0) for k in keys], dtype=float)
    exp = np.array([target[k] for k in keys]) * n
    tv = 0.5 * float(np.abs(obs / n - exp / n).sum()) if n else float("nan")
    mask = exp >= 1.0                       # drop near-empty cells that make chi-square unreliable
    if n and mask.sum() > 1:
        e = exp[mask]
        o = obs[mask]
        o = o * (e.sum() / o.sum()) if o.sum() > 0 else o
        p = float(stats.chisquare(o, e).pvalue)
    else:
        p = float("nan")
    return {"n": int(n), "tv": round(tv, 4), "chi2_p": round(p, 3)}


def validate(pop, orgs: list[dict[str, Any]], specs: list[dict[str, Any]]) -> dict[str, Any]:
    """`pop` is the Population (for its precomputed target tables)."""
    n = len(specs)
    out: dict[str, Any] = {"n": n, "implementation": [], "heldout": []}
    impl, held = out["implementation"], out["heldout"]

    # --- implementation: industry mix
    tgt = _norm({i: E.INDUSTRY_EMPLOYMENT_K[i] for i in E.INDUSTRIES})
    obs = Counter(s["industry"] for s in specs)
    impl.append({"quantity": "Industry mix (BLS CES)", "observed": {k: round(obs[k] / n, 3) for k in E.INDUSTRIES},
                 "target": {k: round(tgt[k], 3) for k in E.INDUSTRIES}, **_gof(obs, tgt)})

    # --- firm size class by industry (employee-weighted)
    for ind in E.INDUSTRIES:
        sub = [s for s in specs if s["industry"] == ind]
        if len(sub) < 20:
            continue
        t = _norm(E.SUSB_EMPLOYMENT[ind])
        ob = Counter(s["size_class"] for s in sub)
        impl.append({"quantity": f"Firm-size class, {ind} (Census SUSB, employee-weighted)"
                                 + (" [assumed targets]" if ind == "Government" else ""),
                     "observed": {k: round(ob[k] / len(sub), 3) for k in E.SIZE_CLASSES},
                     "target": {k: round(t[k], 3) for k in E.SIZE_CLASSES}, **_gof(ob, t)})

    # --- role mix by industry
    for ind in E.INDUSTRIES:
        sub = [s for s in specs if s["industry"] == ind]
        if len(sub) < 30:
            continue
        t = _norm(dict(zip(E.TARGET_ROLES, pop.role_w[ind])))
        ob = Counter(s["target_role"] for s in sub)
        impl.append({"quantity": f"Role mix, {ind} (BLS OEWS)",
                     "observed": {k: round(ob[k] / len(sub), 3) for k in E.TARGET_ROLES},
                     "target": {k: round(t[k], 3) for k in E.TARGET_ROLES}, **_gof(ob, t)})

    # --- sex by role
    rows = []
    for role in E.TARGET_ROLES:
        sub = [s for s in specs if s["target_role"] == role]
        if len(sub) < 15:
            continue
        w = sum(s["gender"] == "woman" for s in sub) / len(sub)
        tw = pop.role_demo[role]["women"]
        se = (tw * (1 - tw) / len(sub)) ** 0.5
        rows.append({"role": role, "n": len(sub), "observed": round(w, 3), "target": round(tw, 3),
                     "z": round((w - tw) / se, 2) if se else 0.0})
    out["sex_by_role"] = rows

    # --- education by role (age >= 26 so every level is feasible)
    rows = []
    for role in E.TARGET_ROLES:
        sub = [s for s in specs if s["target_role"] == role and s["age"] >= 26]
        if len(sub) < 25:
            continue
        t = dict(zip(E.EDU_LEVELS, pop.role_edu[role]))
        ob = Counter(s["highest_education"] for s in sub)
        rows.append({"role": role, **_gof(ob, t), "observed": {k: round(ob[k] / len(sub), 3) for k in E.EDU_LEVELS},
                     "target": {k: round(t[k], 3) for k in E.EDU_LEVELS}})
    out["education_by_role"] = rows

    # --- held-out: tenure
    ages = np.array([s["age"] for s in specs])
    ten = np.array([s["tenure_years"] for s in specs])
    adults = ages >= 25
    held.append({"quantity": "Median tenure, age 25+ (BLS Jan 2026: 4.9 yrs)", "observed": round(float(np.median(ten[adults])), 2),
                 "target": 4.9, "note": "Sampler uses medians by age band only; the overall median is not fit."})
    held.append({"quantity": "Median tenure, all (BLS: 4.1 yrs)", "observed": round(float(np.median(ten)), 2), "target": 4.1,
                 "note": "Prime-target occupations skew older than all workers; Students cap tenure at 2 yrs."})
    for lo, hi, med in E.TENURE_MEDIAN_BY_AGE:
        sel = (ages >= lo) & (ages <= hi)
        if sel.sum() >= 20:
            held.append({"quantity": f"Median tenure, age {lo}-{hi}", "observed": round(float(np.median(ten[sel])), 2),
                         "target": med, "note": f"n={int(sel.sum())}; tenure capped at time in labor force"})
    # --- held-out: age by role and by industry
    for role in E.TARGET_ROLES:
        sub = [s["age"] for s in specs if s["target_role"] == role]
        if len(sub) >= 60:
            held.append({"quantity": f"Median age, {role} (CPS 11b)", "observed": float(np.median(sub)),
                         "target": E.ROLE_MEDIAN_AGE[role], "note": f"n={len(sub)}; role medians are cross-industry"})
    held.append({"quantity": "Median age, all sampled (CPS all-employed: 42.1)", "observed": float(np.median(ages)),
                 "target": 42.1, "note": "Roles skew older than all workers"})
    # --- held-out: LinkedIn use among college graduates vs Pew 51%
    college = [s for s in specs if s["highest_education"] in ("bachelor", "master", "doctoral")]
    if college:
        li = sum("LinkedIn" in s["presence"]["platforms"] for s in college) / len(college)
        held.append({"quantity": "LinkedIn use, college graduates (Pew 2026: 51%)", "observed": round(li, 3),
                     "target": 0.51, "note": f"n={len(college)}; our sample skews 30-55, Pew averages all adults"})
    nocoll = [s for s in specs if s["highest_education"] in ("less_than_hs", "high_school") and s["age"] >= 25
              and not (s["career_stage"] == "Executive" and s["presence"]["p_platform"]["LinkedIn"] > 0.7)]
    if len(nocoll) >= 20:
        li = sum("LinkedIn" in s["presence"]["platforms"] for s in nocoll) / len(nocoll)
        held.append({"quantity": "LinkedIn use, HS or less (Pew 2026: 13%)", "observed": round(li, 3), "target": 0.13,
                     "note": f"n={len(nocoll)}; age 25+, excluding the 500+-firm executive override"})
    # --- held-out: phish-prone mean vs vendor benchmarks
    p = np.array([s["susceptibility"]["p_click_simulated_phish"] for s in specs])
    held.append({"quantity": "Mean simulated-phish click probability (KnowBe4: ~27% avg, 2025 baseline 33.1%)",
                 "observed": round(float(p.mean()), 3), "target": "0.27-0.33",
                 "note": "Inputs: industry x size baseline, training factor, new-hire factor"})
    held.append({"quantity": "Mean baseline phish-prone % before training factor (KnowBe4 older edition avg ~27%)",
                 "observed": round(float(np.mean([s["susceptibility"]["baseline_ppp"] for s in specs])), 3),
                 "target": 0.27, "note": "Industry x size matrix weighted by this sample's mix"})
    nh = [s for s in specs if s["is_new_hire"]]
    held.append({"quantity": "Share of new hires (tenure <= 90 days)", "observed": round(len(nh) / n, 3),
                 "target": "derived", "note": "Implied by exponential tenure model; no direct benchmark"})
    # --- held-out: work rhythm
    chk = np.array([s["rhythm"]["email_checks_per_day"] for s in specs])
    rcv = np.array([s["rhythm"]["emails_received_per_day"] for s in specs])
    held.append({"quantity": "Median email checks per day (Mark 2016: 77)", "observed": round(float(np.median(chk)), 1), "target": 77.0, "note": ""})
    held.append({"quantity": "Mean emails received per day (Microsoft 2025: 117)", "observed": round(float(rcv.mean()), 1), "target": 117.0,
                 "note": "Role factors raise it slightly"})
    late = sum(s["rhythm"]["late_night_inbox"] for s in specs) / n
    held.append({"quantity": "Share in inbox by 10 pm (Microsoft 2025: 29%)", "observed": round(late, 3), "target": 0.29, "note": ""})

    # --- descriptive: derived labels and cross-tabs (no benchmark; shown for review)
    out["distributions"] = {
        "career_stage": dict(Counter(s["career_stage"] for s in specs)),
        "security_awareness": dict(Counter(s["susceptibility"]["security_awareness"] for s in specs)),
        "busy_level": dict(Counter(s["rhythm"]["busy_level"] for s in specs)),
        "footprint_level": dict(Counter(s["presence"]["footprint_level"] for s in specs)),
        "company_size": dict(Counter(s["company_size"] for s in specs)),
        "gender": dict(Counter(s["gender"] for s in specs)),
        "platforms": dict(Counter(p for s in specs for p in s["presence"]["platforms"])),
        "highest_education": dict(Counter(s["highest_education"] for s in specs)),
        "n_orgs": len({s["org_id"] for s in specs}),
    }
    # distinctness
    out["distinctness"] = {
        "unique_names": len({s["full_name"] for s in specs}),
        "unique_first": len({s["full_name"].split()[0] for s in specs}),
        "unique_last": len({s["full_name"].split()[-1] for s in specs}),
        "unique_titles": len({s["title"] for s in specs}),
        "unique_schools": len({e["institution"]["name"] for s in specs for e in s["education"]}),
        "duplicate_org_domains": len(orgs) - len({o["domain"] for o in orgs}),
    }
    return out


def to_markdown(res: dict[str, Any]) -> str:
    L: list[str] = [f"n = {res['n']} sampled profiles\n"]
    L.append("### Implementation checks (marginals drawn directly from the sources)\n")
    L.append("| Quantity | n | TV distance | chi-square p |\n|---|---|---|---|")
    for r in res["implementation"]:
        L.append(f"| {r['quantity']} | {r['n']} | {r['tv']} | {r['chi2_p']} |")
    L.append("\n**Sex by role** (observed share of women vs CPS target; z = binomial z-score)\n")
    L.append("| Role | n | observed | target | z |\n|---|---|---|---|---|")
    for r in res["sex_by_role"]:
        L.append(f"| {r['role']} | {r['n']} | {r['observed']} | {r['target']} | {r['z']} |")
    L.append("\n**Highest education by role** (age 26+; BLS EP 5.3 target)\n")
    L.append("| Role | n | TV distance | chi-square p |\n|---|---|---|---|")
    for r in res["education_by_role"]:
        L.append(f"| {r['role']} | {r['n']} | {r['tv']} | {r['chi2_p']} |")
    L.append("\n### Held-out checks (not fit directly)\n")
    L.append("| Quantity | observed | target | note |\n|---|---|---|---|")
    for r in res["heldout"]:
        L.append(f"| {r['quantity']} | {r['observed']} | {r['target']} | {r['note']} |")
    L.append("\n### Distributions of derived labels (no benchmark)\n")
    for k, v in res["distributions"].items():
        L.append(f"- **{k}**: {v}")
    L.append("\n### Distinctness\n")
    for k, v in res["distinctness"].items():
        L.append(f"- {k}: {v}")
    return "\n".join(L)
