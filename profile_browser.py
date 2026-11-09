"""Profile browser + statistics dashboard for generated spear-email profile sets.

    streamlit run profile_browser.py

Reads any run folder under data/v2/ (or data/v1/) that holds profiles_core.jsonl, profiles_public.jsonl,
profiles_private.jsonl and profiles_behavior.jsonl (written by scripts/run_v2.py). When specs.jsonl is
present, the Statistics tab compares the generated people with the real-world targets from
config/empirical.py (BLS OEWS role mix, CPS sex/age, BLS education, ...), so drift is visible as the
set scales toward 5000 profiles.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import empirical as E  # noqa: E402

DATA = ROOT / "data"
GOAL = 5000
NEEDED = ("profiles_core.jsonl", "profiles_public.jsonl", "profiles_private.jsonl", "profiles_behavior.jsonl")

st.set_page_config(page_title="Profile Browser", page_icon="🗂️", layout="wide")


# ----------------------------------------------------------------------------- loading

def _read_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def find_runs() -> list[Path]:
    runs = [p.parent for p in DATA.rglob("profiles_core.jsonl") if all((p.parent / f).exists() for f in NEEDED)]
    return sorted(runs, key=lambda d: (d / "profiles_core.jsonl").stat().st_mtime, reverse=True)


@st.cache_data(show_spinner=False)
def load_run(path: str, stamp: float):
    d = Path(path)
    core = _read_jsonl(d / "profiles_core.jsonl")
    pub = {r["profile_id"]: r for r in _read_jsonl(d / "profiles_public.jsonl")}
    pri = {r["profile_id"]: r for r in _read_jsonl(d / "profiles_private.jsonl")}
    beh = {r["profile_id"]: r for r in _read_jsonl(d / "profiles_behavior.jsonl")}
    orgs = {o["org_id"]: o for o in _read_jsonl(d / "orgs.jsonl")}
    specs = _read_jsonl(d / "specs.jsonl")
    meta = json.loads((d / "run_meta.json").read_text()) if (d / "run_meta.json").exists() else {}
    profiles = []
    for c in core:
        pid = c["profile_id"]
        profiles.append({"core": c, "public": pub.get(pid, {}), "private": pri.get(pid, {}),
                         "behavior": beh.get(pid, {}), "org": orgs.get(c["org_id"], {})})
    return profiles, orgs, specs, meta


@st.cache_resource(show_spinner="Loading the reference population tables…")
def get_population():
    from src.population import Population
    return Population(seed=0)


@st.cache_data(show_spinner="Comparing with the real-world targets…")
def run_validation(path: str, stamp: float):
    from src.validate import validate
    profiles, orgs, specs, _ = load_run(path, stamp)
    ids = {int(p["core"]["profile_id"].split("_")[1]) for p in profiles}
    sub = [s for i, s in enumerate(specs) if i in ids]
    if not sub:
        return None, []
    return validate(get_population(), list(orgs.values()), sub), sub


def issue_words(meta: dict) -> dict[int, list[str]]:
    return {i["profile"]: i["errors"] for i in meta.get("narrative_issues", [])}


# ----------------------------------------------------------------------------- charts

def grouped_bar(df: pd.DataFrame, cat: str, title: str, pct: bool = True, height: int = 320, horizontal=False):
    """df has columns [cat, 'observed', 'target']."""
    long = df.melt(cat, ["observed", "target"], var_name="series", value_name="value")
    fmt = ".0%" if pct else ",.1f"
    q, n = ("value:Q", cat + ":N")
    enc = dict(
        x=alt.X(q, title=None, axis=alt.Axis(format=fmt)) if horizontal else alt.X(n, title=None, sort=list(df[cat])),
        y=alt.Y(n, title=None, sort=list(df[cat])) if horizontal else alt.Y(q, title=None, axis=alt.Axis(format=fmt)),
        color=alt.Color("series:N", scale=alt.Scale(domain=["observed", "target"], range=["#2563eb", "#9ca3af"]),
                        legend=alt.Legend(orient="top", title=None)),
        tooltip=[cat, "series", alt.Tooltip("value:Q", format=fmt)],
    )
    off = {"yOffset": "series:N"} if horizontal else {"xOffset": "series:N"}
    chart = alt.Chart(long, title=title).mark_bar().encode(**enc, **off).properties(height=height)
    st.altair_chart(chart, width="stretch")


def counts_bar(counter: dict, title: str, height: int = 240):
    df = pd.DataFrame({"label": list(counter), "count": list(counter.values())})
    st.altair_chart(alt.Chart(df, title=title).mark_bar(color="#2563eb").encode(
        x=alt.X("label:N", sort="-y", title=None), y=alt.Y("count:Q", title=None),
        tooltip=["label", "count"]).properties(height=height), width="stretch")


def zflag(z: float) -> str:
    return "✅" if abs(z) < 2 else "⚠️" if abs(z) < 3 else "❌"


# ----------------------------------------------------------------------------- sidebar

runs = find_runs()
st.sidebar.title("🗂️ Profile Browser")
if not runs:
    st.sidebar.error("No run folders with profiles_*.jsonl found under data/.")
    st.stop()
run_dir = st.sidebar.selectbox("Profile set", runs, format_func=lambda p: str(p.relative_to(ROOT)))
stamp = (run_dir / "profiles_core.jsonl").stat().st_mtime
if st.sidebar.button("Reload files"):
    st.cache_data.clear()
    st.rerun()

profiles, orgs, specs, meta = load_run(str(run_dir), stamp)
n = len(profiles)
st.sidebar.metric("Profiles in this set", f"{n:,}")
st.sidebar.progress(min(1.0, n / GOAL), text=f"{n:,} / {GOAL:,} toward the 5,000 goal")
if meta:
    st.sidebar.caption(f"backend: {meta.get('backend')} · model: {meta.get('model')} · prompt {meta.get('prompt_version')} "
                       f"· seed {meta.get('seed')}")

if n == 0:
    st.warning("This set has no profiles yet.")
    st.stop()

tab_stats, tab_browse = st.tabs(["📊 Statistics", "🔎 Browse profiles"])

# ============================================================================= STATISTICS
with tab_stats:
    cores = pd.DataFrame([p["core"] for p in profiles])
    words = pd.Series([p["public"].get("resume_word_count", 0) for p in profiles])
    issues = issue_words(meta)

    # --- company
    org_ids = sorted(cores["org_id"].unique())
    if len(org_ids) == 1:
        o = orgs[org_ids[0]]
        st.success(f"**One company:** {o['name']} · `{o['domain']}` · {o['industry']} · "
                   f"{o['headcount']:,} employees ({o['size_class']}) · {o['hq_city']}", icon="🏢")
    else:
        st.warning(f"This set spans **{len(org_ids)} companies**, not one.", icon="🏢")

    k = st.columns(5)
    k[0].metric("Profiles", f"{n:,}", f"{n / GOAL:.1%} of {GOAL:,}")
    k[1].metric("Companies", len(org_ids))
    k[2].metric("Median resume words", int(words.median()))
    k[3].metric("Resumes ≥ 450 words", f"{(words >= 450).mean():.0%}")
    k[4].metric("Kept with validation issues", f"{len(issues)}")

    res, sub_specs = run_validation(str(run_dir), stamp) if specs else (None, [])

    if res is None:
        st.info("No specs.jsonl in this folder, so only descriptive counts are shown (no real-world comparison).")
        counts_bar(dict(Counter(cores["target_role"])), "Profiles by role")
        counts_bar(dict(Counter(cores["gender"])), "Profiles by gender")
    else:
        sp = pd.DataFrame([{"role": s["target_role"], "gender": s["gender"], "age": s["age"],
                            "edu": s["highest_education"], "stage": s["career_stage"],
                            "industry": s["industry"]} for s in sub_specs])
        pop = get_population()
        ind = sp["industry"].iloc[0] if sp["industry"].nunique() == 1 else None

        s_role, s_demo, s_edu, s_held, s_other = st.tabs(
            ["Role mix", "Sex & age by role", "Education by role", "Other real-world checks", "Other distributions"])

        # ---------------- role mix
        with s_role:
            if ind:
                tgt = dict(zip(E.TARGET_ROLES, pop.role_w[ind]))
                tot = sum(tgt.values())
                tgt = {r: v / tot for r, v in tgt.items()}
                st.caption(f"Target: BLS OEWS employment share of each role **within {ind}** "
                           f"(the company's industry). Profiles are drawn from this mix.")
            else:
                w = np.array([sum(pop.role_w[i][j] * E.INDUSTRY_EMPLOYMENT_K[i] / sum(pop.role_w[i])
                                  for i in E.INDUSTRIES) for j in range(len(E.TARGET_ROLES))])
                tgt = dict(zip(E.TARGET_ROLES, w / w.sum()))
                st.caption("Target: BLS OEWS role shares blended over the industry mix.")
            obs = Counter(sp["role"])
            rows = []
            for r in E.TARGET_ROLES:
                t = tgt[r]
                se = (t * (1 - t) / n) ** 0.5
                z = ((obs[r] / n) - t) / se if se else 0.0
                rows.append({"role": r, "observed": obs[r] / n, "target": t, "count": obs[r],
                             "expected now": round(t * n, 1), "expected at 5,000": round(t * GOAL),
                             "z": round(z, 2), "": zflag(z)})
            df = pd.DataFrame(rows)
            grouped_bar(df, "role", "Share of profiles by role: observed vs real-world target", horizontal=True,
                        height=360)
            st.dataframe(df.assign(observed=df.observed.map("{:.1%}".format), target=df.target.map("{:.1%}".format)),
                         hide_index=True, width="stretch")
            st.caption("z = (observed − target) ÷ binomial standard error. ✅ |z|<2 · ⚠️ 2–3 · ❌ >3. "
                       "Small roles have few expected profiles at small n, so |z| is noisy until n grows.")

        # ---------------- sex and age by role
        with s_demo:
            c1, c2 = st.columns(2)
            rows = []
            for r in E.TARGET_ROLES:
                g = sp[sp.role == r]
                if len(g):
                    t = pop.role_demo[r]["women"]
                    se = (t * (1 - t) / len(g)) ** 0.5
                    z = ((g.gender == "woman").mean() - t) / se if se else 0.0
                    rows.append({"role": r, "n": len(g), "observed": (g.gender == "woman").mean(), "target": t,
                                 "z": round(z, 2), "": zflag(z) if len(g) >= 15 else "·"})
            d = pd.DataFrame(rows)
            with c1:
                grouped_bar(d, "role", "Share of women by role (CPS 11)", horizontal=True, height=340)
            with c2:
                st.dataframe(d.assign(observed=d.observed.map("{:.1%}".format), target=d.target.map("{:.1%}".format)),
                             hide_index=True, width="stretch")
                st.caption("· = fewer than 15 profiles in the role; not judged.")
            tot_w = (sp.gender == "woman").mean()
            st.metric("Overall share of women", f"{tot_w:.1%}",
                      help="Blend of the role-level CPS shares, weighted by the role mix of this set.")
            rows = []
            for r in E.TARGET_ROLES:
                g = sp[sp.role == r]
                if len(g):
                    rows.append({"role": r, "n": len(g), "observed": float(g.age.median()),
                                 "target": float(E.ROLE_MEDIAN_AGE[r])})
            d = pd.DataFrame(rows)
            grouped_bar(d, "role", "Median age by role (CPS 11b)", pct=False, horizontal=True, height=340)
            st.altair_chart(alt.Chart(sp, title="Age distribution").mark_bar(color="#2563eb").encode(
                x=alt.X("age:Q", bin=alt.Bin(step=2), title="age"), y=alt.Y("count()", title=None)).properties(height=220),
                width="stretch")

        # ---------------- education by role
        with s_edu:
            st.caption("Highest education among profiles aged 26+, vs BLS EP 5.3 for each role.")
            role = st.selectbox("Role", E.TARGET_ROLES)
            g = sp[(sp.role == role) & (sp.age >= 26)]
            if len(g) == 0:
                st.info("No profiles of this role aged 26+ yet.")
            else:
                t = dict(zip(E.EDU_LEVELS, pop.role_edu[role]))
                ob = Counter(g.edu)
                d = pd.DataFrame({"education": E.EDU_LEVELS, "observed": [ob[x] / len(g) for x in E.EDU_LEVELS],
                                  "target": [t[x] for x in E.EDU_LEVELS]})
                grouped_bar(d, "education", f"{role} (n = {len(g)})")
            rows = []
            for row in res["education_by_role"]:
                rows.append({"role": row["role"], "n": row["n"], "TV distance": row["tv"],
                             "chi-square p": row["chi2_p"]})
            st.markdown("**Fit by role** (TV distance: 0 = identical; chi-square p: large = no evidence of mismatch)")
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        # ---------------- held-out
        with s_held:
            st.caption("Quantities the sampler does not draw directly, compared with outside statistics. "
                       "Agreement is evidence the joint structure is realistic. Medians are noisy below ~100 profiles.")
            st.dataframe(pd.DataFrame(res["heldout"]).astype(str), hide_index=True, width="stretch")
            impl = [r for r in res["implementation"]
                    if ind is None or not r["quantity"].startswith(("Industry mix", "Firm-size"))]
            if ind:
                st.caption(f"Industry-mix and firm-size checks are omitted: this set is a single {ind} company by design.")
            if impl:
                st.markdown("**Implementation checks** (marginals drawn from the sources)")
                st.dataframe(pd.DataFrame([{"quantity": r["quantity"], "n": r["n"], "TV": r["tv"],
                                            "chi-square p": r["chi2_p"]} for r in impl]),
                             hide_index=True, width="stretch")

        # ---------------- other distributions
        with s_other:
            dist = res["distributions"]
            a, b, c = st.columns(3)
            with a:
                counts_bar(dist["career_stage"], "Career stage")
                counts_bar(dist["gender"], "Gender")
            with b:
                counts_bar(dist["security_awareness"], "Security awareness")
                counts_bar(dist["busy_level"], "Busy level")
            with c:
                counts_bar(dist["footprint_level"], "Public footprint")
                counts_bar(dist["platforms"], "Platform presence (profiles on each)")
            st.markdown("**Distinctness**")
            st.json(res["distinctness"], expanded=False)

    # --- resume length
    st.divider()
    st.subheader("Resume length")
    st.altair_chart(alt.Chart(pd.DataFrame({"words": words})).mark_bar(color="#2563eb").encode(
        x=alt.X("words:Q", bin=alt.Bin(step=25), title="resume words"), y=alt.Y("count()", title=None)
    ).properties(height=200), width="stretch")
    if issues:
        with st.expander(f"{len(issues)} profile(s) kept despite validation issues"):
            for i, errs in issues.items():
                st.markdown(f"**prof_{i:04d}** — " + "; ".join(e[:160] for e in errs))

# ============================================================================= BROWSE
with tab_browse:
    f = st.columns([2, 2, 2, 2])
    q = f[0].text_input("Search name / title / email")
    roles = f[1].multiselect("Role", sorted({p["core"]["target_role"] for p in profiles}))
    stages = f[2].multiselect("Career stage", sorted({p["core"]["career_stage"] for p in profiles}))
    genders = f[3].multiselect("Gender", sorted({p["core"]["gender"] for p in profiles}))
    ages = [p["core"]["age"] for p in profiles]
    g = st.columns([3, 2, 2])
    age_rng = g[0].slider("Age", min(ages), max(ages), (min(ages), max(ages))) if min(ages) < max(ages) else (min(ages), max(ages))
    edus = g[1].multiselect("Highest education", sorted({p["core"]["highest_education"] for p in profiles}))
    foot = g[2].multiselect("Public footprint", sorted({p["public"].get("footprint_level", "") for p in profiles} - {""}))

    def keep(p):
        c = p["core"]
        if q and q.lower() not in " ".join(str(c[k]) for k in ("full_name", "title", "email")).lower():
            return False
        return ((not roles or c["target_role"] in roles) and (not stages or c["career_stage"] in stages)
                and (not genders or c["gender"] in genders) and age_rng[0] <= c["age"] <= age_rng[1]
                and (not edus or c["highest_education"] in edus)
                and (not foot or p["public"].get("footprint_level") in foot))

    shown = [p for p in profiles if keep(p)]
    st.caption(f"{len(shown):,} of {n:,} profiles match")
    table = pd.DataFrame([{
        "id": p["core"]["profile_id"], "name": p["core"]["full_name"], "title": p["core"]["title"],
        "role": p["core"]["target_role"], "stage": p["core"]["career_stage"], "age": p["core"]["age"],
        "gender": p["core"]["gender"], "education": p["core"]["highest_education"],
        "tenure (yrs)": p["core"]["tenure_years"], "resume words": p["public"].get("resume_word_count"),
        "awareness": p["behavior"].get("security_awareness"), "footprint": p["public"].get("footprint_level"),
    } for p in shown])
    ev = st.dataframe(table, hide_index=True, width="stretch", height=300,
                      on_select="rerun", selection_mode="single-row")
    pick = ev.selection.rows[0] if ev.selection.rows else None
    if pick is None:
        st.info("Select a row to open the full profile.")
    else:
        P = shown[pick]
        c, pu, pr, be, org = P["core"], P["public"], P["private"], P["behavior"], P["org"]
        st.divider()
        st.subheader(f"{c['full_name']} — {c['title']}")
        st.caption(f"{c['profile_id']} · {c['email']} · {org.get('name', '')} · {c['location']}")
        m = st.columns(6)
        m[0].metric("Age", c["age"])
        m[1].metric("Gender", c["gender"])
        m[2].metric("Tenure", f"{c['tenure_years']} yrs")
        m[3].metric("Experience", f"{c['years_experience']} yrs")
        m[4].metric("Education", c["highest_education"])
        m[5].metric("Career stage", c["career_stage"])

        t1, t2, t3, t4, t5 = st.tabs(["Resume", "Public footprint", "Private ground truth", "Behavior", "Raw JSON"])
        with t1:
            res_ = pu.get("resume") or {}
            cur = res_.get("current_job") or {}
            st.markdown(f"**{cur.get('title', c['title'])}** · {org.get('name', '')} · current")
            for b in cur.get("bullets", []):
                st.markdown(f"- {b}")
            for j in res_.get("prior_jobs") or []:
                st.markdown(f"**{j.get('title', '')}** · {j.get('employer', '')} · {j.get('start_year')}–{j.get('end_year')}")
                for b in j.get("bullets", []):
                    st.markdown(f"- {b}")
            if res_.get("education"):
                st.markdown("**Education**")
                for b in res_["education"]:
                    st.markdown(f"- {b}")
            st.caption(f"{pu.get('resume_word_count')} words")
        with t2:
            st.markdown("**Handles**")
            st.json(pu.get("social_presence", {}), expanded=True)
            if pu.get("personal_website"):
                st.markdown(f"Website: `{pu['personal_website']}`")
            st.markdown(f"Footprint: **{pu.get('footprint_level')}** · {pu.get('public_posts_per_month')} posts/month")
            for post in pu.get("posts", []):
                st.markdown(f"> **{post['platform']}** · {post['date']}  \n> {post['text']}")
        with t3:
            for key, label in (("projects", "Projects"), ("real_details", "Real details"),
                               ("sensitive_access", "Sensitive access")):
                st.markdown(f"**{label}**")
                for x in pr.get(key, []):
                    st.markdown(f"- {x}")
            st.markdown("**Colleagues**")
            st.dataframe(pd.DataFrame(pr.get("colleagues", [])), hide_index=True, width="stretch")
        with t4:
            b1, b2 = st.columns(2)
            with b1:
                st.markdown("**Traits**")
                for x in be.get("traits", []):
                    st.markdown(f"- {x}")
                st.markdown("**Response tendencies**")
                for k_, v_ in (be.get("response_tendencies") or {}).items():
                    st.markdown(f"- *{k_}* → {v_}")
            with b2:
                for k_ in ("security_awareness", "p_click_simulated_phish", "received_security_training", "busy_level",
                           "email_checks_per_day", "emails_received_per_day", "late_night_inbox"):
                    st.markdown(f"**{k_.replace('_', ' ')}**: {be.get(k_)}")
        with t5:
            st.json(P, expanded=False)
