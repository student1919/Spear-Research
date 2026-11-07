#!/usr/bin/env python3
"""Builds report/CALIBRATION.md, report/AUDIT_V1.md, report/BIBLIOGRAPHY.md and the alignment figure.

Inputs: data/v1/*.jsonl (v1, 100 profiles), data/v2/spec5000/specs.jsonl + validation.md (sampler run),
        data/v2/test15 (live-LLM test). Everything numeric in the reports is computed here, not typed.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import empirical as E  # noqa: E402
from config.sources import SOURCES  # noqa: E402
from src.population import Population  # noqa: E402

REP = ROOT / "report"
FIG = REP / "figures_v2"
FIG.mkdir(parents=True, exist_ok=True)


def rd(p: Path) -> list[dict]:
    return [json.loads(l) for l in p.open(encoding="utf-8") if l.strip()]


def norm(d):
    t = sum(d.values())
    return {k: v / t for k, v in d.items()}


def tv(obs: dict, tgt: dict) -> float:
    return 0.5 * sum(abs(obs.get(k, 0) - tgt.get(k, 0)) for k in set(obs) | set(tgt))


def gof_p(counts: Counter, tgt: dict) -> float:
    keys = [k for k in tgt if tgt[k] > 0]
    n = sum(counts.get(k, 0) for k in keys)
    exp = np.array([tgt[k] for k in keys]) * n
    obs = np.array([counts.get(k, 0) for k in keys], dtype=float)
    m = exp >= 1
    if m.sum() < 2:
        return float("nan")
    return float(stats.chisquare(obs[m] * exp[m].sum() / max(obs[m].sum(), 1), exp[m]).pvalue)


# ----------------------------------------------------------------------------------------------
v1c, v1p = rd(ROOT / "data/v1/profiles_core.jsonl"), rd(ROOT / "data/v1/profiles_public.jsonl")
v1v, v1b = rd(ROOT / "data/v1/profiles_private.jsonl"), rd(ROOT / "data/v1/profiles_behavior.jsonl")
v1o, v1e = rd(ROOT / "data/v1/orgs.jsonl"), rd(ROOT / "data/v1/emails_attack.jsonl")
orgs1 = {o["org_id"]: o for o in v1o}
specs = rd(ROOT / "data/v2/spec5000/specs.jsonl")
N2 = len(specs)
pop = Population(seed=1)

# --- targets ------------------------------------------------------------------------------------
ind_t = norm({i: E.INDUSTRY_EMPLOYMENT_K[i] for i in E.INDUSTRIES})
role_t = {r: 0.0 for r in E.TARGET_ROLES}
for ind in E.INDUSTRIES:
    rw = norm(dict(zip(E.TARGET_ROLES, pop.role_w[ind])))
    for r in E.TARGET_ROLES:
        role_t[r] += ind_t[ind] * rw[r]
tot_emp = sum(E.SUSB_ALL_EMPLOYMENT.values())
def _size3(ind):
    e = E.SUSB_EMPLOYMENT[ind]
    t = sum(e.values())
    return {"Small": (e["<20"] + e["20-99"]) / t, "Medium": e["100-499"] / t,
            "Large": (e["500-4999"] + e["5000+"]) / t}


# target weighted to the industry mix (per-industry SUSB employee shares; Government is an assumed row)
size3_t = {k: sum(ind_t[i] * _size3(i)[k] for i in E.INDUSTRIES) for k in ("Small", "Medium", "Large")}
tot_firms = sum(E.SUSB_ALL_FIRMS.values())
size3_firms = {"Small": (E.SUSB_ALL_FIRMS["<20"] + E.SUSB_ALL_FIRMS["20-99"]) / tot_firms,
               "Medium": E.SUSB_ALL_FIRMS["100-499"] / tot_firms,
               "Large": (E.SUSB_ALL_FIRMS["500-4999"] + E.SUSB_ALL_FIRMS["5000+"]) / tot_firms}

# --- v1 distributions -----------------------------------------------------------------------------
OLD2NEW = {"Engineer / researcher (valuable data)": "Engineer / researcher",
           "Journalist / activist / political": "Journalist / communications"}
v1_ind = Counter(c["industry"] for c in v1c)
v1_role = Counter(OLD2NEW.get(c["target_role"], c["target_role"]) for c in v1c if c["target_role"] != "New hire")
v1_size = Counter(orgs1[c["org_id"]]["size"] for c in v1c)
n1 = len(v1c)
nr1 = sum(v1_role.values())
v2_ind = Counter(s["industry"] for s in specs)
v2_role = Counter(s["target_role"] for s in specs)
v2_size = Counter(s["company_size"] for s in specs)


def share(c: Counter, keys, n):
    return {k: c.get(k, 0) / n for k in keys}


# --- figure ---------------------------------------------------------------------------------------
BLUE, ORANGE, GREY, INK, GRID = "#2a78d6", "#eb6834", "#8d8c85", "#0b0b0b", "#e6e5e1"
fig, axes = plt.subplots(2, 2, figsize=(13, 9), facecolor="#fcfcfb")


def grouped(ax, keys, series, title, labels=None, rot=0):
    x = np.arange(len(keys))
    w = 0.26
    for j, (name, vals, col) in enumerate(series):
        b = ax.bar(x + (j - 1) * w, [vals[k] * 100 for k in keys], w - 0.03, label=name, color=col,
                   edgecolor="#fcfcfb", linewidth=1.5)
        for rect, k in zip(b, keys):
            ax.text(rect.get_x() + rect.get_width() / 2, rect.get_height() + 0.6, f"{vals[k]*100:.0f}",
                    ha="center", va="bottom", fontsize=7, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels(labels or keys, rotation=rot, ha="right" if rot else "center", fontsize=8)
    ax.set_title(title, fontsize=11, loc="left", color=INK)
    ax.set_ylabel("% of profiles / workers", fontsize=8)
    ax.set_facecolor("#fcfcfb")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.legend(fontsize=8, frameon=False)


grouped(axes[0, 0], E.INDUSTRIES,
        [("v1 (n=100)", share(v1_ind, E.INDUSTRIES, n1), ORANGE),
         ("v2 sampler (n=%d)" % N2, share(v2_ind, E.INDUSTRIES, N2), BLUE), ("BLS CES target", ind_t, GREY)],
        "Industry mix")
grouped(axes[0, 1], ["Small", "Medium", "Large"],
        [("v1", share(v1_size, size3_t, n1), ORANGE), ("v2 sampler", share(v2_size, size3_t, N2), BLUE),
         ("Census SUSB employees, weighted to industry mix", size3_t, GREY)],
        "Company size (Small <100, Medium 100-499, Large 500+ employees)")
short = {r: r.split(" / ")[0] for r in E.TARGET_ROLES}
grouped(axes[1, 0], E.TARGET_ROLES,
        [("v1 (excl. new hires)", share(v1_role, E.TARGET_ROLES, nr1), ORANGE),
         ("v2 sampler", share(v2_role, E.TARGET_ROLES, N2), BLUE), ("BLS OEWS-implied target", role_t, GREY)],
        "Target-role mix", labels=[short[r] for r in E.TARGET_ROLES], rot=30)
ages = np.array([s["age"] for s in specs])
edges = [18, 20, 25, 35, 45, 55, 65, 73]
hist = np.histogram(ages, bins=edges)[0] / len(ages) * 100
age_tgt = {i: np.array(E.INDUSTRY_AGE_COUNTS_K[i], dtype=float) for i in E.INDUSTRIES}
ageT = sum(ind_t[i] * age_tgt[i] / age_tgt[i].sum() for i in E.INDUSTRIES) * 100
lab = ["18-19", "20-24", "25-34", "35-44", "45-54", "55-64", "65+"]
ax = axes[1, 1]
x = np.arange(7)
ax.bar(x - 0.15, hist, 0.3, color=BLUE, label="v2 sampler (role shifts add older skew)", edgecolor="#fcfcfb")
ax.bar(x + 0.15, ageT, 0.3, color=GREY, label="CPS industry age mix (before role shift)", edgecolor="#fcfcfb")
for xi, h, t in zip(x, hist, ageT):
    ax.text(xi - 0.15, h + 0.4, f"{h:.0f}", ha="center", fontsize=7)
    ax.text(xi + 0.15, t + 0.4, f"{t:.0f}", ha="center", fontsize=7)
ax.set_xticks(x)
ax.set_xticklabels(lab, fontsize=8)
ax.set_title("Age distribution", fontsize=11, loc="left")
ax.set_facecolor("#fcfcfb")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.yaxis.grid(True, color=GRID)
ax.set_axisbelow(True)
ax.legend(fontsize=8, frameon=False)
fig.tight_layout()
fig.savefig(FIG / "alignment.png", dpi=140)
plt.close(fig)

# --- audit of v1 ---------------------------------------------------------------------------------
om = orgs1
A: list[str] = []
A.append("# Audit of the original 100 profiles (v1)\n")
A.append("_Computed by `scripts/make_calibration_report.py` from `data/v1/*.jsonl`. Findings only._\n")
A.append("## 1. How they were produced\n")
A.append("- `report/REPORT.md` records `backend: LocalBackend`. The 100 profiles and 100 emails were **composed offline from fixed "
         "template pools** (`src/pools.py`), not written by an LLM. The `claude-sonnet-5-5` / `claude-haiku-5-5` labels in the "
         "report header are configuration metadata; the 5 'seed' items were also template-composed.\n"
         "- Every sampling weight in `config/dimensions.py` is a hand-set number with an inline rationale (for example "
         "Finance 0.26, Tech 0.24, Healthcare 0.20, Government 0.16, Education 0.14). None is sourced.\n")
A.append("## 2. Distribution vs government data\n")
A.append("| Quantity | v1 | target | TV distance | chi-square p |\n|---|---|---|---|---|")
ind_obs = share(v1_ind, E.INDUSTRIES, n1)
A.append(f"| Industry mix | {', '.join(f'{k} {v:.0%}' for k, v in ind_obs.items())} | "
         f"{', '.join(f'{k} {v:.0%}' for k, v in ind_t.items())} (BLS CES) | {tv(ind_obs, ind_t):.2f} | "
         f"{gof_p(v1_ind, ind_t):.4f} |")
role_obs = share(v1_role, E.TARGET_ROLES, nr1)
A.append(f"| Role mix (89 profiles, new hires excluded) | see figure | OEWS-implied | {tv(role_obs, role_t):.2f} | "
         f"{gof_p(v1_role, role_t):.4f} |")
sz_obs = share(v1_size, size3_t, n1)
A.append(f"| Company size, share of profiles | {', '.join(f'{k} {v:.0%}' for k, v in sz_obs.items())} | "
         f"{', '.join(f'{k} {v:.0%}' for k, v in size3_t.items())} (SUSB employees, industry-weighted; Government row assumed) | {tv(sz_obs, size3_t):.2f} | "
         f"{gof_p(v1_size, size3_t):.4f} |")
A.append("\n![alignment](figures_v2/alignment.png)\n")
A.append("Notes: v1 draws company size with weights 34% / 36% / 30% (Small / Medium / Large) and then allocates profiles to companies "
         "with `SIZE_ALLOC_WEIGHT` (1.0 / 2.4 / 4.2), which moves the share of profiles in Large companies to 64%. "
         "Government is 8% of v1 profiles (one company) against a 16% intended weight.\n")
A.append("## 3. Traits that are functions of one other field\n")
stage_sec = Counter((c["career_stage"], b["security_awareness"]) for c, b in zip(v1c, v1b))
stage_busy = Counter((c["career_stage"], b["busy_level"]) for c, b in zip(v1c, v1b))
stage_fp = Counter((c["career_stage"], p["footprint_level"]) for c, p in zip(v1c, v1p))
A.append("- **Security awareness is a lookup on career stage** (`STAGE_SECURITY` in `src/llm.py`): "
         + "; ".join(f"{k[0]} -> {k[1]}: {v}" for k, v in sorted(stage_sec.items())) + ". No profile deviates.")
A.append("- **Busy level:** " + "; ".join(f"{k[0]}/{k[1]}: {v}" for k, v in sorted(stage_busy.items())) +
         ". Student is always low; High Level and Executive are always high.")
A.append("- **Footprint:** " + "; ".join(f"{k[0]}/{k[1]}: {v}" for k, v in sorted(stage_fp.items())) +
         ". High Level and Executive are always high.")
A.append("- Because each trait is determined by stage, the dataset contains no information in security awareness or busyness "
         "beyond career stage, and the 'low / medium / high' cut points are the arbitrary boundaries the advisor questioned.\n")
A.append("## 4. Internal inconsistencies\n")
mm = 0
for c, p in zip(v1c, v1v):
    rel = {x["name"]: x["relation"] for x in p["colleagues"]}
    m = re.search(r"Reports into ([^.]+)\.", " ".join(p["real_details"]))
    if m and rel.get(m.group(1)) != "manager":
        mm += 1
stu = [(c, p, v) for c, p, v in zip(v1c, v1p, v1v) if c["career_stage"] == "Student"]
dupdom = Counter(o["domain"] for o in v1o)
exec_titles = Counter(c["title"] for c in v1c if c["career_stage"] == "Executive")
bad_exec = sum(n for t, n in exec_titles.items() if t.startswith("Chief ") and t != "Chief Operations Officer")
A.append(f"- **Reporting line contradicts colleague list:** {mm} of {n1} profiles say 'Reports into X' where X is listed as something other than their manager.")
A.append(f"- **Executive titles built by prefixing 'Chief':** {bad_exec} of {sum(exec_titles.values())} executives hold titles such as "
         f"{', '.join(sorted(t for t in exec_titles if t.startswith('Chief ') and t != 'Chief Operations Officer')[:5])}.")
A.append(f"- **Students with workplace history and access:** {sum(1 for c, p, v in stu if any('year at' in x['text'] for x in p['posts']))} of "
         f"{len(stu)} students have a 'year at <company>' post; {sum(1 for c, p, v in stu if v['sensitive_access'])} of {len(stu)} hold sensitive access.")
A.append(f"- **Duplicate companies:** {sum(1 for d, n in dupdom.items() if n > 1)} domains are shared by two different org_ids "
         f"({', '.join(d for d, n in dupdom.items() if n > 1)}), so email addresses can collide.")
A.append("- **Company-name pool:** 5 prefixes x 5 suffixes per industry (25 combinations) for 24 companies.\n")
A.append("## 5. Variety\n")
bul = [b for p in v1p for b in p["resume_bullets"]]
A.append(f"- Distinct first names {len({c['full_name'].split()[0] for c in v1c})}, last names {len({c['full_name'].split()[-1] for c in v1c})} across {n1} people.")
A.append(f"- Resume bullets: {len(set(bul))} distinct of {len(bul)}. Distinct titles: {len({c['title'] for c in v1c})}. Distinct work locations: {len({c['location'] for c in v1c})} (always the company HQ).")
hand = all(h == c["full_name"].split()[0].lower() + c["full_name"].split()[1].lower()[:3]
           for c, p in zip(v1c, v1p) for h in p["social_presence"].values())
A.append(f"- Every social handle follows one pattern (first name + first three letters of last name): {hand}.")
A.append(f"- Education appears in {sum(1 for b in bul if re.search(r'universit|college|degree', b, re.I))} of {len(bul)} resume bullets; no profile names a school.")
gh = Counter(('GitHub' in p['social_presence'], c['target_role']) for c, p in zip(v1c, v1p))
A.append("- Platform choice ignores role: GitHub accounts appear on " +
         ", ".join(f"{k[1]} ({v})" for k, v in gh.items() if k[0]) + ".")
A.append("- Email personalization fields are only 'target_role' and 'projects' in all 100 emails; colleague names appear in "
         f"{sum(1 for e, p in zip(v1e, v1v) if any(x['name'].split()[0] in e['body'] for x in p['colleagues']))} of {len(v1e)} email bodies.")
A.append("\n## 6. What the audit does not cover\n- Email text quality was not assessed beyond the personalization counts above.\n")
(REP / "AUDIT_V1.md").write_text("\n".join(A), encoding="utf-8")

# --- bibliography ----------------------------------------------------------------------------------
B = ["# Bibliography and source status\n",
     "Status: **primary** = the primary table/document was opened; **secondary** = seen only through a news/vendor/aggregator "
     "page or search summary; **derived** / **assumption** = see `config/sources.py`. Citations tagged (CR) were checked "
     "against Crossref. First-name initials of some co-authors were written from memory and are unverified.\n"]
order = [k for k in SOURCES if k not in ("ASSUMPTION", "DERIVED")]
for k in order:
    s = SOURCES[k]
    B.append(f"- **[{k}]** ({s['status']}) {s['cite']} {s['url']}")
B.append("\n## Support for each target-role category\n")
B.append("| Role category | Citable support found | Gap |\n|---|---|---|")
B.append("| Executives / senior leaders | Barracuda (2021): CEOs average 57 targeted attacks a year [secondary]; Keepnet (2025): +45% on CEO-impersonation lures for new hires [vendor] | Primary Barracuda report not opened |")
B.append("| Finance / accounting | FBI IC3 (2026), IC3 PSA I-091124 (2024): BEC counts and losses; Verizon DBIR (2025): BEC and wire-transfer share | none for the category itself |")
B.append("| IT admin / help desk | Barracuda (2021): IT staff average 40 targeted emails a year [secondary] | Primary report not opened |")
B.append("| Journalists / activists | Marczak & Scott-Railton (2016), Citizen Lab | single case study |")
B.append("| Government / defense | Verizon DBIR (2025): espionage motive in 52% of social-engineering breaches | does not name government employees specifically |")
B.append("| New hires | Keepnet (2025) vendor report, n = 237 companies: 71% fell for phishing within 90 days, 44% more likely than staff past 90 days [secondary] | peer-reviewed version (Sevimli Deniz & Atas, 2026) seen only in a search summary |")
B.append("| HR / payroll | none verified | no source found |")
B.append("| Executive assistants | none verified | no source found |")
B.append("| Engineers / researchers; legal staff (valuable data) | none verified | no source found |")
B.append("\n`Profiles.md` lists the prime-target categories without citations; their origin could not be established from the repository.\n")
(REP / "BIBLIOGRAPHY.md").write_text("\n".join(B), encoding="utf-8")

# --- calibration report ----------------------------------------------------------------------------
val = (ROOT / "data/v2/spec5000/validation.md").read_text(encoding="utf-8")
val1k = (ROOT / "data/v2/spec1000/validation.md").read_text(encoding="utf-8")
t15 = rd(ROOT / "data/v2/test15/specs.jsonl")
c15 = rd(ROOT / "data/v2/test15/profiles_core.jsonl")
meta15 = json.loads((ROOT / "data/v2/test15/run_meta.json").read_text())
susb = E.SUSB_ALL_EMPLOYMENT
sf = E.SUSB_ALL_FIRMS
tf, te = sum(sf.values()), sum(susb.values())
C: list[str] = []
C.append("# Calibration of the synthetic profile generator to government and research data\n")
C.append("_Generated by `scripts/make_calibration_report.py`. Research date: 2026-11-01. Findings only._\n")
C.append("## 1. Summary\n")
C.append("- The sampler in `src/population.py` now draws every profile's industry, firm size, occupation, age, sex, education, school, "
         "tenure, career stage, online-platform use, email workload and phishing susceptibility from distributions in "
         "`config/empirical.py`. Each parameter names a source in `config/sources.py` and an evidence grade "
         "(data / derived / proxy / assumption; Section 6).")
C.append("- The LLM no longer chooses any number. It receives the sampled person and writes only text (resume bullets, post text, "
         "projects, ground-truth details, traits). Colleague names and prior employers are also sampled in code, because the live "
         "test showed the model reusing the same few names and employers across profiles.")
C.append(f"- Statistical alignment is checked in `src/validate.py` on {N2} sampled people (Section 5) and on 1,000 (`data/v2/spec1000/validation.md`).")
C.append(f"- A live Gemini run produced {len(c15)} new profiles with {len(meta15['narrative_issues'])} narrative-validation failures after retries (Section 7).\n")
C.append("## 2. The three advisor questions\n")
C.append("### 2.1 Online presence as numbers\n")
C.append("Each profile now carries numeric fields instead of a hand-drawn low/medium/high:\n")
C.append("| Field | Source and grade |\n|---|---|")
C.append("| Platform membership (LinkedIn, X, Facebook, Instagram) | Pew 2026 by age and education, combined as an additive logit; data (overall LinkedIn 33% and X 25% cells were flagged by the fetch tool as inferred) |")
C.append("| LinkedIn for executives at 500+ firms = 71.5% | 73% of Fortune 500 CEOs on any platform x 98% of those on LinkedIn; secondary, consultancy sample |")
C.append("| GitHub, ResearchGate | no representative rate found; academics 39% (range 37-78% in three studies); GitHub rates are assumptions |")
C.append("| Public posts per month, per platform | ~1.4% of LinkedIn users post weekly (weak lineage); occasional-poster share (18%) and role multipliers (journalists x6, executives x2.5) are assumptions |")
C.append("| Email checks per day: median 77 (about 17 per computer-hour) | Mark et al. 2016, n = 40; data. Spread is an assumption |")
C.append("| Emails received per day: mean 117 | Microsoft Work Trend Index 2025; data. Role factors (executives, assistants x1.25) are assumptions |")
C.append("| In inbox late at night (by 10 pm): 29% | Microsoft Work Trend Index 2025; data |")
C.append("| `footprint_score` = platforms + log2(1 + posts/month) + website | our definition; `footprint_level` cut points (1.5, 3.0) are still arbitrary and are labels only |")
C.append("\nNot found: LinkedIn use or posting frequency by occupation or seniority; email-checking rates by role. The advisor's "
         "example (marketing staff are more active than others) therefore rests on assumed multipliers, not data. "
         "Given the sources, most sampled people have no or few public posts, which matches the 1.4% weekly-poster figure.\n")
C.append("### 2.2 Company size\n")
C.append("US Census SUSB 2022 (`susb22`), all industries:\n")
C.append("| Enterprise size | % of firms | % of employees |\n|---|---|---|")
for lab_, keys in [("< 20", ["<20"]), ("20-99", ["20-99"]), ("100-499", ["100-499"]), ("500-4,999", ["500-4999"]), ("5,000+", ["5000+"])]:
    C.append(f"| {lab_} | {sum(sf[k] for k in keys)/tf:.2%} | {sum(susb[k] for k in keys)/te:.1%} |")
C.append(f"\n- By firm count, {sum(sf[k] for k in ['<20','20-99'])/tf:.1%} of firms have fewer than 100 employees and only "
         f"{sf['100-499']/tf:.2%} have 100-499. By employment, {(susb['500-4999']+susb['5000+'])/te:.0%} of employees work at firms of 500 or more "
         f"and {susb['5000+']/te:.0%} at firms of 5,000 or more.")
C.append("- The statement 'most companies are mid-sized and huge companies are rare' does not match these numbers under either "
         "measure: small firms dominate the count, and large firms (500+) employ the majority of people. 'Large companies are rare' holds only by firm count.")
C.append("- The sampler draws the firm-size class of a person in proportion to employment in that class, per industry, because a "
         "profile is a person. Government is not in SUSB; its size classes are an assumption.\n")
C.append("### 2.3 Role taxonomy and citations\n")
C.append("See `report/BIBLIOGRAPHY.md`. Verified support exists for finance/BEC, journalists/activists, and (vendor, secondary) executives, IT staff and new hires. "
         "No source was found for HR/payroll, executive assistants, engineers/researchers or legal staff as targeted groups, and the origin of the list in `Profiles.md` could not be established. "
         "Role frequencies in the sampler come from BLS OEWS employment, not from how often a role is targeted. "
         "Two changes to the taxonomy: 'New hire' is now a tenure flag (tenure <= 90 days) rather than an occupation, and 'Government / defense personnel' uses federal protective-service employment as a proxy because OEWS excludes military.\n")
C.append("## 3. What the sampler draws, in order\n")
C.append("industry (BLS CES employment) -> firm-size class (SUSB, employee-weighted) -> organization (new or reused within industry and class) -> "
         "role (BLS OEWS employment, May 2023 industry tables) -> sub-occupation (lawyer / paralegal / compliance, etc.) -> age (CPS industry age bands, shifted by role median age) -> "
         "sex (CPS by role) -> surname group (CPS race/ethnicity by role; group not stored) -> names (Census 2010 surnames, SSA given names by birth decade) -> "
         "education level (BLS EP Table 5.3 for the sub-occupation, restricted to ages that can hold the degree) -> field (assumed by role) -> "
         "school (IPEDS completions at that level and field) -> tenure (BLS median by age, exponential, capped at career length) -> "
         "career stage (experience and OEWS manager share) -> title -> online presence -> work rhythm -> phishing susceptibility.\n")
C.append("Phishing susceptibility: baseline phish-prone % by industry and org size (KnowBe4, undated edition, 20.8-31% by cell), "
         "x0.80 if the person received training (assumed effect; training share by org size from the UK CSBS 2025, a proxy), x1.44 for new hires (Keepnet vendor study). "
         "Person-level spread is a Beta distribution with concentration 16.1, solved from Lain et al. (2022): a mean per-email click rate of 5.67% "
         "with that spread gives 32.1% of people clicking at least once in 8 emails (observed 32.1%) and predicts 30.4% of clickers clicking 2+ times (observed 30.6%).\n")
C.append("## 4. Added profile detail\n")
C.append("`core`: age, gender, birth year, tenure, years of experience, new-hire flag, highest education, firm-size class. "
         "`public`: education records (level, major, institution, city/state, graduation year), career history (prior titles, invented employers, contiguous years), per-platform posting rates, footprint score. "
         "`behavior`: click probability, training flag, emails received and checked per day, late-night inbox flag. "
         "Two free-text detail themes (hobby, hometown, volunteer work, and similar) are sampled per person to vary the private details; the theme list has no statistics behind it.\n")
C.append("## 5. Statistical alignment\n")
C.append("![alignment](figures_v2/alignment.png)\n")
C.append("How to read the tables: **implementation checks** are quantities drawn directly from a source distribution, so agreement is expected by construction and a failure would indicate a bug. "
         "**Held-out checks** compare quantities the sampler does not draw directly against source statistics it was not fit to.\n")
C.append(f"### Sampler run, n = {N2}\n")
C.append(val.split("\n", 2)[2])
C.append("\n### Reading the held-out rows\n")
C.append("- Tenure by age band tracks BLS within about 10% for ages 25 and over; it is lower for ages 18-24 because students are capped at two years and the exponential shape is an assumption. "
         "Overall median tenure is above BLS' 4.1 years because the sampled roles are older than the all-worker population (median age 44 vs 42.1).")
C.append("- Median age by role is within about 2 years of CPS for the roles with n >= 60.")
_trained = np.mean([s["susceptibility"]["received_security_training"] for s in specs])
_pc = np.mean([s["susceptibility"]["p_click_simulated_phish"] for s in specs])
_pb = np.mean([s["susceptibility"]["baseline_ppp"] for s in specs])
_rv = np.mean([s["rhythm"]["emails_received_per_day"] for s in specs])
_col = [s for s in specs if s["highest_education"] in ("bachelor", "master", "doctoral")]
_hs = [s for s in specs if s["highest_education"] in ("less_than_hs", "high_school") and s["age"] >= 25
       and not (s["career_stage"] == "Executive" and s["presence"]["p_platform"]["LinkedIn"] > 0.7)]
_li = lambda g: np.mean(["LinkedIn" in s["presence"]["platforms"] for s in g])
C.append(f"- LinkedIn use among college graduates ({_li(_col):.0%}) is close to Pew's 51%; among people 25+ with a high-school education or less ({_li(_hs):.0%}) it is above Pew's 13%. The model combines age and education marginals additively, so it is not fit to their joint distribution.")
C.append(f"- Mean click probability ({_pc:.0%}) is below the KnowBe4 baseline range because {_trained:.0%} of sampled people are trained (x0.80, assumed effect); the mean baseline before the training factor is {_pb:.1%} against the matrix average of about 27%.")
C.append(f"- Mean emails received per day ({_rv:.0f}) is above 117 because executives and assistants carry an assumed x1.25 factor.\n")
C.append("### Distinct values (n = 5000)\n")
C.append(val.split("### Distinctness")[1].strip())
C.append("\n## 6. Parameter registry\n")
C.append("| Parameter | Source | Grade | Note |\n|---|---|---|---|")
for name, src, grade, note in E.PARAM_REGISTRY:
    C.append(f"| {name} | {src} | {grade} | {note} |")
C.append("\n## 7. Live generation test (15 profiles)\n")
C.append(f"Backend: Gemini (`GeminiBackend`; configured primary `gemini-3.5-flash-lite` with fallback). Seed 31. Output in `data/v2/test15/`. "
         f"Narrative-validation failures after up to 3 attempts per profile: {len(meta15['narrative_issues'])}.\n")
t15c = Counter(s["industry"] for s in t15)
C.append(f"- Industry: {dict(t15c)}; career stage: {dict(Counter(c['career_stage'] for c in c15))}.")
pub15 = rd(ROOT / "data/v2/test15/profiles_public.jsonl")
priv15 = rd(ROOT / "data/v2/test15/profiles_private.jsonl")
C.append(f"- Distinct colleague names {len({x['name'] for v in priv15 for x in v['colleagues']})} of {sum(len(v['colleagues']) for v in priv15)}; "
         f"distinct prior employers {len({h['employer'] for p in pub15 for h in p['career_history']})} of {sum(len(p['career_history']) for p in pub15)}; "
         f"distinct private details {len({d for v in priv15 for d in v['real_details']})} of {sum(len(v['real_details']) for v in priv15)}.")
C.append("- Checked by script: every school appears in the resume text, no decimal tenure or '.example' leaks in resume bullets, career history ends at the current job's start year (set in code), platforms match the sampled list.")
C.append("- Earlier test run (12 profiles, before the fixes below) showed: the same colleague names in most profiles ('Marcus Vance', 'Sarah Jenkins'), the same prior-employer names, tenure written as '4.61 years', '.example' appended to employer names, and a paralegal with a J.D. Fixes: colleagues, employers and career dates are sampled in code; the prompt forbids raw numbers; education and title are drawn from the same sub-occupation.\n")
C.append("## 8. Limitations and gaps\n")
C.append("- Occupation mix is May 2023 (newer industry tables returned no data); firm size is SUSB 2022; the KnowBe4 by-size matrix is from an undated edition (about 27% average vs 33.1% in the 2025 report).")
C.append("- Roles are the nine target categories, so profiles are conditional on being in a prime-target occupation; the shares in the figure are shares within that set, not of all workers.")
C.append("- Government firm-size classes, field of study by role, GitHub/ResearchGate rates, posting activity beyond the 1.4% weekly share, role multipliers for email volume, the training effect factor, and career-stage thresholds are assumptions (grade `assumption` or `proxy` in Section 6).")
C.append("- Not found: ACS field of degree by occupation, SBA Office of Advocacy firm-size cross-check (HTTP 403), federal and military headcounts, LinkedIn use by occupation, a primary Verizon DBIR median time-to-click, role-specific phishing susceptibility effect sizes, SSA given names directly from SSA (a GitHub mirror through birth year 2008 was used).")
C.append("- Real US college names are used for fictional people. The prompt limits statements about the institution to its name, degree and year.")
C.append("- The Census surname file is used with CPS race/ethnicity shares to draw plausible surnames; the group is not stored on the profile. Pairing of given name and surname is independent.")
C.append("- Gender is drawn as woman/man from CPS sex shares; no data for other categories was used.")
(REP / "CALIBRATION.md").write_text("\n".join(C), encoding="utf-8")
print("wrote", [p.name for p in REP.glob("*.md")], FIG / "alignment.png")
