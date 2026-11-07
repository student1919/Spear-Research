"""Empirically calibrated population sampler.

Draws a fully specified person for each profile (demographics, education, career,
online presence, work rhythm, phishing susceptibility) from the distributions in
config/empirical.py. The LLM then writes the narrative around this spec; it does
not choose any of the numbers. That keeps the dataset's statistics a property of
the sampler, which can be validated against the government/research sources.

Sampling order (each step conditions on the previous ones):
  industry -> firm-size class -> organization -> occupation role -> age -> sex ->
  race/ethnicity group (surname only) -> name -> education -> tenure -> career stage
  -> title -> online presence -> work rhythm -> phishing susceptibility
"""

from __future__ import annotations

import math
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from config import empirical as E  # noqa: E402

REF = ROOT / "data" / "reference"
CURRENT_YEAR = 2026
POPULATION_VERSION = "v2"

# --------------------------------------------------------------------------
# Synthetic company naming (larger pools than v1 so names/domains do not collide)
# --------------------------------------------------------------------------
_PREFIX = ["Meridian", "Cairnwell", "Haskett", "Brightmoor", "Talford", "Alderwood", "Vireo", "Northbay",
           "Calyx", "Everwell", "Lumat", "Fernstack", "Orbital", "Quillon", "Pinemark", "Sterling", "Harbor",
           "Westridge", "Lakeshore", "Fallon", "Ashgrove", "Brightland", "Kelmore", "Oakbridge", "Ridgeway",
           "Stonehaven", "Larkspur", "Coventry", "Marlowe", "Thornfield", "Windmere", "Elmhurst", "Granger",
           "Holloway", "Ironwood", "Juniper", "Keystone", "Linden", "Maplecrest", "Norwick", "Orchard",
           "Pemberton", "Quarry", "Redfern", "Silverline", "Tamarack", "Upland", "Valmont", "Whitcomb",
           "Yarrow", "Zephyr", "Ambrose", "Bellmont", "Corvane", "Dunmore", "Eastgate", "Fairhaven"]
_SUFFIX = {
    "Finance": ["Capital", "Financial", "Partners", "Trust", "Bancorp", "Credit Union", "Advisory", "Insurance",
                "Wealth Management"],
    "Healthcare": ["Health", "Care Systems", "Medical", "Clinics", "Diagnostics", "Health Partners",
                   "Medical Group", "Pharmacy Services"],
    "Tech": ["Labs", "Systems", "Software", "Technologies", "Analytics", "Networks", "Digital", "Cloud"],
    "Government": ["County Authority", "Agency", "Services Bureau", "Department", "Commission",
                   "Municipal Office", "Regional Authority", "Administration"],
    "Education": ["University", "Institute", "College", "Academy", "School District", "Community College",
                  "Research Institute"],
}
# Free-text variety seeds (assumption: no statistics behind them). Two are drawn per person so the model's
# "private" details do not collapse onto the same few habits.
DETAIL_THEMES = [
    "a hobby outside work", "where they grew up", "volunteer or community involvement",
    "family situation (do not name children)", "a professional certification or training course",
    "a sports team or league they follow", "a side project or business", "languages they speak",
    "a recent trip or conference", "an early-career mentor", "their commute or remote-work routine",
    "a recent milestone at work", "a weakness in their work routine", "a tool or app they rely on",
    "a recurring meeting or deadline in their week",
]
P_NEW_ORG = {"<20": 0.60, "20-99": 0.45, "100-499": 0.30, "500-4999": 0.15, "5000+": 0.08}


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def _logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def _weighted_choice(rng: random.Random, items, weights):
    return rng.choices(list(items), weights=list(weights), k=1)[0]


class Population:
    def __init__(self, seed: int = 7, ref_dir: Path | None = None):
        self.rng = random.Random(seed)
        self.nprng = np.random.default_rng(seed)
        ref = Path(ref_dir) if ref_dir else REF
        self._load_reference(ref)
        self.orgs: list[dict[str, Any]] = []
        self._org_pool: dict[tuple[str, str], list[int]] = {}
        self._org_names: set[str] = set()
        self._emails: set[str] = set()
        self._names: set[str] = set()
        self._precompute()

    # ---------------------------------------------------------------- setup
    def _load_reference(self, ref: Path) -> None:
        self.inst = pd.read_csv(ref / "institutions.csv").set_index("unitid")
        comp = pd.read_csv(ref / "completions.csv")
        self._inst_weights: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
        for (level, field), g in comp.groupby(["level", "field"]):
            self._inst_weights[(level, field)] = (g.unitid.to_numpy(), g["count"].to_numpy(dtype=float))
        for level, g in comp.groupby("level"):
            t = g.groupby("unitid")["count"].sum()
            self._inst_weights[(level, "*")] = (t.index.to_numpy(), t.to_numpy(dtype=float))
        sn = pd.read_csv(ref / "surnames.csv")
        self.sur_names = sn["name"].str.title().to_numpy()
        base = sn["count"].to_numpy(dtype=float)
        pct = {c: sn[c].fillna(0).to_numpy(dtype=float) / 100.0 for c in
               ["pctwhite", "pctblack", "pctapi", "pctaian", "pct2prace", "pcthispanic"]}
        self.sur_w = {
            "white": base * (pct["pctwhite"] + pct["pctaian"] + pct["pct2prace"]),
            "black": base * pct["pctblack"],
            "asian": base * pct["pctapi"],
            "hispanic": base * pct["pcthispanic"],
        }
        gn = pd.read_csv(ref / "given_names.csv")
        self._given: dict[tuple[int, str], tuple[np.ndarray, np.ndarray]] = {}
        for (dec, sex), g in gn.groupby(["decade", "sex"]):
            self._given[(int(dec), sex)] = (g["name"].to_numpy(), g["weight"].to_numpy(dtype=float))

    def _precompute(self) -> None:
        self.industry_w = [E.INDUSTRY_EMPLOYMENT_K[i] for i in E.INDUSTRIES]
        # role weights per industry
        cols = {c: i for i, c in enumerate(E.OEWS_COLS)}
        self.role_w: dict[str, list[float]] = {}
        for ind in E.INDUSTRIES:
            ws = []
            for role in E.TARGET_ROLES:
                row = E.OEWS_ROLE_EMPLOYMENT[role]
                ws.append(float(sum(row[cols[c]] for c in E.INDUSTRY_OEWS_COLUMNS[ind])))
            self.role_w[ind] = ws
        # weighted CPS demographics per role
        def wavg(components: list[str], idx: int) -> float:
            num = sum(E.CPS11_ROWS[c][idx] * E.CPS11_ROWS[c][4] for c in components)
            den = sum(E.CPS11_ROWS[c][4] for c in components)
            return num / den
        self.role_demo = {r: {"women": wavg(comp, 0) / 100, "black": wavg(comp, 1) / 100,
                              "asian": wavg(comp, 2) / 100, "hispanic": wavg(comp, 3) / 100}
                          for r, comp in E.ROLE_CPS_COMPONENTS.items()}
        # education distribution per role (percent -> probability)
        self.role_edu: dict[str, np.ndarray] = {}
        for role, comp in E.ROLE_EDU_COMPONENTS.items():
            tot = sum(comp.values())
            v = sum(np.array(E.EP53_ROWS[k]) * w for k, w in comp.items()) / tot
            self.role_edu[role] = v / v.sum()
        self.metro_names = list(E.METRO_LABOR_FORCE)
        self.metro_w = [E.METRO_LABOR_FORCE[m] for m in self.metro_names]

    # ----------------------------------------------------------- organizations
    def _make_org(self, industry: str, size_class: str) -> dict[str, Any]:
        r = self.rng
        for _ in range(500):
            name = f"{r.choice(_PREFIX)} {r.choice(_SUFFIX[industry])}"
            if name not in self._org_names:
                break
        else:
            name = f"{r.choice(_PREFIX)} {r.choice(_PREFIX)} {r.choice(_SUFFIX[industry])}"
        self._org_names.add(name)
        slug = name.lower().replace(" ", "").replace(",", "")
        lo, hi = E.SIZE_CLASS_BOUNDS[size_class]
        headcount = int(round(math.exp(r.uniform(math.log(lo), math.log(hi)))))
        org = {
            "org_id": f"org_{len(self.orgs):04d}",
            "name": name,
            "domain": f"{slug}.example",
            "industry": industry,
            "size": E.SIZE_LABEL[size_class],
            "size_class": size_class,
            "headcount": headcount,
            "hq_city": _weighted_choice(r, self.metro_names, self.metro_w),
            "founded": r.randint(1950, 2021),
            "org_chart": [
                {"title": "Chief Executive", "reports_to": ""},
                {"title": "Director", "reports_to": "Chief Executive"},
                {"title": "Manager", "reports_to": "Director"},
            ],
            "synthetic": True,
        }
        self.orgs.append(org)
        self._org_pool.setdefault((industry, size_class), []).append(len(self.orgs) - 1)
        return org

    def _pick_org(self, industry: str, size_class: str) -> dict[str, Any]:
        pool = self._org_pool.get((industry, size_class), [])
        if not pool or self.rng.random() < P_NEW_ORG[size_class]:
            return self._make_org(industry, size_class)
        w = [self.orgs[i]["headcount"] for i in pool]
        return self.orgs[_weighted_choice(self.rng, pool, w)]

    # --------------------------------------------------------------- person
    def _age(self, industry: str, role: str) -> int:
        counts = E.INDUSTRY_AGE_COUNTS_K[industry]
        lo, hi = _weighted_choice(self.rng, E.AGE_BANDS, counts)
        age = self.rng.uniform(lo, hi + 1) + (E.ROLE_MEDIAN_AGE[role] - E.ALL_EMPLOYED_MEDIAN_AGE)
        return int(min(max(age, 18), 72))

    def _name(self, gender: str, role: str, birth_year: int) -> str:
        r, d = self.rng, self.role_demo[role]
        h, b, a = d["hispanic"], d["black"], d["asian"]
        grp = _weighted_choice(r, ["hispanic", "black", "asian", "white"],
                               [h, b, a, max(1 - h - b - a, 0.05)])
        w = self.sur_w[grp]
        decade = min(max(birth_year // 10 * 10, 1950), 2000)
        sex = "F" if gender == "woman" else "M"
        names, gw = self._given[(decade, sex)]
        for _ in range(200):
            first = names[self.nprng.choice(len(names), p=gw / gw.sum())]
            last = self.sur_names[self.nprng.choice(len(w), p=w / w.sum())]
            full = f"{first} {last}"
            if full not in self._names:
                self._names.add(full)
                return full
        return full

    def _pick_institution(self, level: str, field: str) -> dict[str, Any]:
        key = (level, field) if (level, field) in self._inst_weights else (level, "*")
        ids, w = self._inst_weights[key]
        uid = ids[self.nprng.choice(len(ids), p=w / w.sum())]
        row = self.inst.loc[uid]
        return {"name": row["name"], "city": row["city"], "state": row["state"], "control": row["control"]}

    def _field(self, role: str, level: str) -> str:
        dist = E.FIELD_OVERRIDE.get((role, level)) or E.FIELD_BY_ROLE[role]
        return _weighted_choice(self.rng, list(dist), list(dist.values()))

    def _sub(self, role: str, age: int) -> str:
        comp = E.ROLE_EDU_COMPONENTS[role]
        allowed = {k: w for k, w in comp.items() if age >= E.SUB_MIN_AGE.get(k, 0)} or comp
        return _weighted_choice(self.rng, list(allowed), list(allowed.values()))

    def _education(self, role: str, sub: str, age: int, birth_year: int) -> tuple[list[dict[str, Any]], str, bool]:
        """Returns (education records, highest completed level, currently enrolled)."""
        r = self.rng
        if age <= 22:   # still in school: working while completing a bachelor's (intern / co-op / part-time)
            field = self._field(role, "bachelor")
            exp_grad = CURRENT_YEAR + r.choice([0, 1, 1, 2, 3])
            rec = {"level": "bachelor", "status": "in progress", "field": field,
                   "institution": self._pick_institution("bachelor", field), "expected_grad_year": exp_grad}
            return [rec], "high_school", True
        probs = np.array(E.EP53_ROWS[sub], dtype=float)
        for i, lvl in enumerate(E.EDU_LEVELS):
            if age < E.EDU_MIN_AGE[lvl]:
                probs[i] = 0.0
        level = E.EDU_LEVELS[int(self.nprng.choice(len(probs), p=probs / probs.sum()))]
        recs: list[dict[str, Any]] = []
        if level in ("less_than_hs", "high_school"):
            return recs, level, False
        if level == "some_college":
            f = self._field(role, "bachelor")
            recs.append({"level": "some college", "status": "no degree", "field": f,
                         "institution": self._pick_institution("bachelor", f), "grad_year": None})
            return recs, level, False
        if level == "associate":
            f = self._field(role, "associate")
            recs.append({"level": "associate", "status": "completed", "field": f,
                         "institution": self._pick_institution("associate", f),
                         "grad_year": birth_year + E.EDU_TYPICAL_AGE["associate"] + r.choice([0, 0, 1, 2])})
            return recs, level, False
        # bachelor and above: record the bachelor's, then higher degrees
        bf = self._field(role, "bachelor")
        if level == "doctoral" and role == "Legal / compliance":
            bf = r.choice(["social_science", "humanities", "business"])
        by = birth_year + E.EDU_TYPICAL_AGE["bachelor"] + r.choice([0, 0, 0, 1, 1, 2])
        recs.append({"level": "bachelor", "status": "completed", "field": bf,
                     "institution": self._pick_institution("bachelor", bf), "grad_year": by})
        if level in ("master", "doctoral"):
            lv2 = "master" if level == "master" else "doctoral"
            f2 = self._field(role, lv2)
            gy = by + (2 if lv2 == "master" else (3 if f2 == "law" else r.choice([5, 6, 7]))) + r.choice([0, 0, 1])
            gy = min(gy, CURRENT_YEAR - (0 if age >= E.EDU_MIN_AGE[lv2] else 1))
            recs.append({"level": "juris doctor" if f2 == "law" else lv2, "status": "completed", "field": f2,
                         "institution": self._pick_institution(lv2, f2), "grad_year": gy})
        return recs, level, False

    def _tenure(self, age: int, experience: float, is_student: bool) -> float:
        for lo, hi, med in E.TENURE_MEDIAN_BY_AGE:
            if lo <= age <= hi:
                break
        cap = min(2.0, max(age - 16, 0.25)) if is_student else max(experience, 0.1)
        # Censor at time in the labor force: someone whose drawn tenure exceeds their career has spent it
        # all at one employer. (Rejection sampling would pull the median below the BLS value.)
        return round(min(self.rng.expovariate(math.log(2) / med), cap), 2)

    def _stage(self, role: str, age: int, experience: float, is_student: bool) -> str:
        if is_student:
            return "Student"
        if role == "Executive / senior leader" and age >= 35:
            return "Executive"
        if experience < 5:
            return "Entry Level"
        if experience >= E.MANAGER_MIN_EXPERIENCE and self.rng.random() < E.MANAGER_SHARE[role]:
            return "High Level"
        return "Mid Level"

    # ------------------------------------------------- relationships / career
    def _colleagues(self, stage: str, role: str, age: int, is_new_hire: bool) -> list[dict[str, str]]:
        r = self.rng
        rels = ["board chair"] if stage == "Executive" else ["manager"]
        pool = ["teammate", "teammate", "cross-team partner", "executive sponsor"]
        if not is_new_hire and stage in ("Mid Level", "High Level", "Executive"):
            pool += ["direct report", "direct report"]
        rels += r.sample(pool, k=r.choice([1, 2, 3]))
        out = []
        for rel in rels:
            g = "woman" if r.random() < 0.47 else "man"
            by = CURRENT_YEAR - max(22, min(68, int(r.gauss(age, 7))))
            out.append({"name": self._name(g, role, by), "relation": rel})
        return out

    def _career_skeleton(self, tenure: float, prior_years: float, prior_roles: int, industry: str) -> list[dict[str, Any]]:
        """Prior jobs before the current one: invented employers, contiguous whole-year spans."""
        r = self.rng
        n = min(prior_roles, int(prior_years))
        if n <= 0:
            return []
        start_current = int(round(CURRENT_YEAR + 0.83 - tenure))
        total = max(n, int(round(prior_years)))
        cuts = sorted(r.sample(range(1, total), n - 1)) if n > 1 else []
        spans = [b - a for a, b in zip([0] + cuts, cuts + [total])]
        jobs, end = [], start_current
        for span in reversed(spans):
            ind = r.choice(list(_SUFFIX))
            emp = f"{r.choice(_PREFIX)} {r.choice(_SUFFIX[ind])}"
            jobs.append({"employer": emp, "start_year": end - span, "end_year": end})
            end -= span
        return list(reversed(jobs))

    # ------------------------------------------------------------ presence
    def _presence(self, role: str, stage: str, industry: str, age: int, edu_level: str, size_class: str,
                  headcount: int) -> dict[str, Any]:
        r = self.rng
        edu_cat = ("hs_or_less" if edu_level in ("less_than_hs", "high_school")
                   else "some_college" if edu_level in ("some_college", "associate") else "college")
        if age <= 22:
            edu_cat = "some_college"
        band = next(i for i, (lo, hi) in enumerate(E.PEW_AGE_BANDS) if lo <= age <= hi)

        def p_logit(overall: float, p_age: float, p_edu: float) -> float:
            lo = _logit(overall)
            return _sigmoid(lo + (_logit(p_age) - lo) + (_logit(p_edu) - lo))

        p_li = p_logit(E.PEW_LINKEDIN_OVERALL, E.PEW_LINKEDIN_AGE[band], E.PEW_LINKEDIN_EDU[edu_cat])
        if stage == "Executive" and headcount >= 500:
            p_li = E.EXEC_LARGE_FIRM_LINKEDIN
        p_x = p_logit(E.PEW_X_OVERALL, E.PEW_X_AGE[band], E.PEW_X_EDU[edu_cat])
        academic = industry == "Education" and role == "Engineer / researcher"
        p_gh = E.GITHUB_BY_ROLE.get(role, E.GITHUB_DEFAULT)
        p_rg = (E.RESEARCHGATE_ACADEMIC if academic
                else E.RESEARCHGATE_OTHER_RESEARCHER if role == "Engineer / researcher" else 0.01)
        probs = {"LinkedIn": p_li, "X": p_x, "Facebook": E.PEW_FACEBOOK_AGE[band],
                 "Instagram": E.PEW_INSTAGRAM_AGE[band], "GitHub": p_gh, "ResearchGate": p_rg}
        have = [p for p, pr in probs.items() if r.random() < pr]
        mult = E.POSTER_ROLE_MULTIPLIER.get(role, 1.0)
        platforms: dict[str, float] = {}
        for p in have:
            u = r.random()
            if p in ("LinkedIn", "X") and u < min(E.WEEKLY_POSTER_SHARE * mult, 0.5):
                rate = math.exp(r.gauss(math.log(6.0), 0.5))           # weekly-or-more: ~26 posts/yr and up
            elif p in ("LinkedIn", "X", "Facebook", "Instagram") and \
                    u < min(E.WEEKLY_POSTER_SHARE * mult, 0.5) + min(E.OCCASIONAL_POSTER_SHARE * mult, 0.6):
                rate = r.uniform(0.1, 0.5)
            else:
                rate = 0.0
            platforms[p] = round(rate, 2)
        web_p = 0.25 if role in ("Engineer / researcher", "Journalist / communications") else E.PERSONAL_WEBSITE_SHARE
        website = r.random() < web_p
        total = sum(platforms.values())
        score = len(platforms) + math.log2(1 + total) + (1.0 if website else 0.0)
        level = "low" if score < 1.5 else "medium" if score < 3.0 else "high"
        return {"platforms": platforms, "public_posts_per_month": round(total, 2), "has_personal_website": website,
                "footprint_score": round(score, 2), "footprint_level": level,
                "p_platform": {k: round(v, 3) for k, v in probs.items()}}

    # -------------------------------------------------------------- rhythm
    def _rhythm(self, role: str) -> dict[str, Any]:
        r = self.rng
        checks = math.exp(r.gauss(math.log(E.EMAIL_CHECKS_PER_DAY_MEDIAN), E.EMAIL_CHECKS_SIGMA))
        factor = E.EMAIL_VOLUME_ROLE_FACTOR.get(role, 1.0)
        mean = E.EMAILS_RECEIVED_MEAN * factor
        median = mean / math.exp(E.EMAILS_RECEIVED_SIGMA ** 2 / 2)
        recv = math.exp(r.gauss(math.log(median), E.EMAILS_RECEIVED_SIGMA))
        lo, hi = E.BUSY_THRESHOLDS
        busy = "low" if recv < lo else "medium" if recv < hi else "high"
        return {"email_checks_per_day": round(checks, 1),
                "email_checks_per_computer_hour": round(checks / E.COMPUTER_HOURS_PER_DAY, 1),
                "emails_received_per_day": round(recv, 1),
                "late_night_inbox": r.random() < E.LATE_NIGHT_INBOX_SHARE,
                "busy_level": busy}

    def _susceptibility(self, industry: str, headcount: int, is_new_hire: bool) -> dict[str, Any]:
        r = self.rng
        col = 0 if headcount < E.PPP_SIZE_BREAKS[0] else 1 if headcount < E.PPP_SIZE_BREAKS[1] else 2
        base = E.PPP_BASELINE[industry][col] / 100.0
        p_train = next(p for cap, p in E.TRAINING_SHARE_BY_HEADCOUNT if headcount < cap)
        trained = r.random() < p_train
        mean = base * (E.TRAINING_FACTOR if trained else 1.0) * (E.NEW_HIRE_FACTOR if is_new_hire else 1.0)
        mean = min(mean, 0.9)
        k = E.PPP_HETEROGENEITY_KAPPA
        p = r.betavariate(mean * k, (1 - mean) * k)
        hi, lo = E.AWARENESS_THRESHOLDS[0], E.AWARENESS_THRESHOLDS[1]
        awareness = "high" if p < hi else "medium" if p < lo else "low"
        return {"p_click_simulated_phish": round(p, 3), "baseline_ppp": round(base, 4),
                "received_security_training": trained, "security_awareness": awareness}

    # ------------------------------------------------------------- one person
    def sample_person(self) -> dict[str, Any]:
        r = self.rng
        industry = _weighted_choice(r, E.INDUSTRIES, self.industry_w)
        size_class = _weighted_choice(r, E.SIZE_CLASSES, [E.SUSB_EMPLOYMENT[industry][c] for c in E.SIZE_CLASSES])
        org = self._pick_org(industry, size_class)
        role = _weighted_choice(r, E.TARGET_ROLES, self.role_w[industry])
        age = self._age(industry, role)
        birth_year = CURRENT_YEAR - age
        gender = "woman" if r.random() < self.role_demo[role]["women"] else "man"
        full_name = self._name(gender, role, birth_year)
        sub = self._sub(role, age)
        edu, edu_level, enrolled = self._education(role, sub, age, birth_year)
        is_student = enrolled
        entry_age = E.LABOR_ENTRY_AGE.get(edu_level, 18)
        experience = max(0.0, age - entry_age)
        tenure = self._tenure(age, experience, is_student)
        is_new_hire = tenure * 365 <= E.NEW_HIRE_DAYS
        stage = self._stage(role, age, experience, is_student)
        title = r.choice(E.titles_for(role, sub, stage))
        prior_years = max(0.0, experience - tenure)
        prior_roles = 0 if prior_years < 1 else min(5, max(1, int(round(prior_years / 4.1))))
        first, last = full_name.split(" ", 1)
        email = f"{first.lower()}.{last.lower().replace(' ', '').replace(chr(39), '')}@{org['domain']}"
        n = 2
        base_email = email
        while email in self._emails:
            email = base_email.replace("@", f"{n}@")
            n += 1
        self._emails.add(email)
        colleagues = self._colleagues(stage, role, age, is_new_hire)
        skeleton = self._career_skeleton(tenure, prior_years, prior_roles, industry)
        themes = r.sample(DETAIL_THEMES, k=2)
        return {
            "org_id": org["org_id"],
            "industry": industry,
            "company_size": org["size"],
            "size_class": size_class,
            "career_stage": stage,
            "target_role": role,
            "occupation": sub,
            "full_name": full_name,
            "email": email,
            "gender": gender,
            "age": age,
            "birth_year": birth_year,
            "title": title,
            "location": org["hq_city"],
            "tenure_years": tenure,
            "years_experience": round(experience, 1),
            "is_new_hire": is_new_hire,
            "prior_roles": len(skeleton),
            "prior_years": round(prior_years, 1),
            "career_skeleton": skeleton,
            "colleagues": colleagues,
            "detail_themes": themes,
            "highest_education": edu_level,
            "education": edu,
            "presence": self._presence(role, stage, industry, age, edu_level, size_class, org["headcount"]),
            "rhythm": self._rhythm(role),
            "susceptibility": self._susceptibility(industry, org["headcount"], is_new_hire),
        }

    def sample(self, n: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        specs = [self.sample_person() for _ in range(n)]
        return self.orgs, specs
