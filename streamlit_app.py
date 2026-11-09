"""Real-time demo of synthetic profile generation (v2 pipeline).

    streamlit run streamlit_app.py

Each "Generate" click samples one person from the calibrated population
(src/population.py), has the selected backend write the narrative (src/profile_v2.py,
same validation and retries as the batch run) and optionally the targeting spear email
(src/emails_v2.py). The Local backend runs offline and instantly; the live backends make
real API calls. Everything is fictional and uses only reserved .example domains.
"""

from __future__ import annotations

import json
import random
import sys
import time
from dataclasses import asdict
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import empirical as E                                          # noqa: E402
from src.analyze import CAREER_STAGES                                      # noqa: E402
from src.emails_v2 import generate_emails_v2, profile_dict                 # noqa: E402
from src.llm import (AnthropicBackend, GeminiBackend, LiveHaikuBackend,    # noqa: E402
                     LocalBackend, GEMINI_PRIMARY, BULK_MODEL, SEED_MODEL)
from src.population import Population                                      # noqa: E402
from src.profile_v2 import generate_profiles_v2                            # noqa: E402

RANDOM = "— random —"
MAX_DRAWS = 5000   # rejection-sampling budget when dimensions are pinned

LOCAL_OPT = "Local (offline, instant)"
HAIKU_OPT = f"Live API — Claude Haiku ({BULK_MODEL})"
GEMINI_OPT = f"Live API — Gemini Flash-Lite ({GEMINI_PRIMARY})"
SONNET_OPT = f"Live API — Claude Sonnet ({SEED_MODEL})"
ANTHROPIC_OPTS = {HAIKU_OPT, SONNET_OPT}

st.set_page_config(page_title="Synthetic Profile Generator", page_icon="🪪", layout="wide")


def _installed(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


@st.cache_resource(show_spinner=False)
def get_live_backend(choice: str):
    if choice == HAIKU_OPT:
        return LiveHaikuBackend()
    if choice == GEMINI_OPT:
        return GeminiBackend()
    return AnthropicBackend()


# --- sidebar controls -------------------------------------------------------

st.sidebar.header("Generation controls")

backend_choice = st.sidebar.radio(
    "Backend", [LOCAL_OPT, HAIKU_OPT, GEMINI_OPT, SONNET_OPT], index=0,
    help="Local composes offline from src/pools.py (not model text). The live options make one real "
         "call per narrative/email, plus retries when the output fails validation.",
)
if backend_choice in ANTHROPIC_OPTS and not _installed("anthropic"):
    st.sidebar.warning("`anthropic` SDK not installed — `pip install anthropic`, then set "
                       "`ANTHROPIC_API_KEY` (or run `ant auth login`).")
if backend_choice == GEMINI_OPT and not _installed("google.genai"):
    st.sidebar.warning("`google-genai` not installed — `pip install google-genai`. "
                       "`GEMINI_API_KEY` is loaded from `cred.env`.")

st.sidebar.markdown("**Pin dimensions** — or leave random (calibrated distribution)")
industry = st.sidebar.selectbox("Industry", [RANDOM] + E.INDUSTRIES)
size_class = st.sidebar.selectbox("Employer size (employees)", [RANDOM] + E.SIZE_CLASSES)
role = st.sidebar.selectbox("Target role", [RANDOM] + E.TARGET_ROLES)
stage = st.sidebar.selectbox("Career stage", [RANDOM] + CAREER_STAGES)

st.sidebar.markdown("---")
lock_seed = st.sidebar.checkbox("Lock seed (reproducible)", value=False)
seed_val = st.sidebar.number_input("Seed", value=7, step=1, disabled=not lock_seed)
also_email = st.sidebar.checkbox("Also generate targeting spear email", value=False)

generate = st.sidebar.button("⚡ Generate profile", type="primary", use_container_width=True)


# --- generation -------------------------------------------------------------

def _matches(spec: dict) -> bool:
    want = {"industry": industry, "size_class": size_class, "target_role": role, "career_stage": stage}
    return all(v == RANDOM or spec[k] == v for k, v in want.items())


def sample_spec(seed: int) -> tuple[dict, dict]:
    """Draw from the calibrated population until the pinned dimensions match."""
    pop = Population(seed=seed)
    for _ in range(MAX_DRAWS):
        spec = pop.sample_person()
        if _matches(spec):
            org = next(o for o in pop.orgs if o["org_id"] == spec["org_id"])
            return spec, org
    raise RuntimeError(f"No sampled person matched the pinned dimensions in {MAX_DRAWS:,} draws; "
                       "that combination is rare or absent in the calibrated population.")


def run_generation():
    seed = int(seed_val) if lock_seed else random.randrange(1_000_000)
    is_local = backend_choice == LOCAL_OPT
    backend = LocalBackend(random.Random(seed)) if is_local else get_live_backend(backend_choice)
    label = "LocalBackend" if is_local else backend_choice.split("(")[-1].rstrip(")") + " (live)"
    usage, notes = [], []

    with st.status("Generating…", expanded=True) as status:
        status.write("Sampling a person from the calibrated population")
        spec, org = sample_spec(seed)
        status.write(f"Writing the narrative with {label}")
        t0 = time.perf_counter()
        bundles, issues = generate_profiles_v2(backend, [org], [spec], random.Random(seed + 1),
                                               log=notes.append)
        if not bundles:
            raise RuntimeError("The backend returned no parseable profile: " + "; ".join(notes))
        if getattr(backend, "last_usage", None):
            usage.append({"stage": "profile", **backend.last_usage})

        email, email_issues = None, []
        if also_email:
            status.write("Writing the targeting spear email")
            emails, email_issues = generate_emails_v2(backend, bundles, [org], log=notes.append)
            email = asdict(emails[0]) if emails else None
            if getattr(backend, "last_usage", None):
                usage.append({"stage": "email", **backend.last_usage})

        elapsed = (time.perf_counter() - t0) * 1000
        status.update(label=f"Done in {elapsed:,.0f} ms", state="complete", expanded=False)

    st.session_state["result"] = {
        "org": org, "spec": spec, "profile": profile_dict(bundles[0]), "email": email,
        "issues": [e for i in issues for e in i["errors"]] + [e for i in email_issues for e in i["errors"]],
        "backend": label, "seed": seed, "ms": round(elapsed), "usage": usage,
    }


if generate:
    try:
        run_generation()
    except Exception as e:  # e.g. live backend selected with no credentials
        st.session_state.pop("result", None)
        msg = str(e).lower()
        auth_like = any(k in msg for k in (
            "authentication", "api_key", "api key", "credential", "x-api-key",
            "permission", "unauthenticated", "invalid key"))
        if auth_like and backend_choice == GEMINI_OPT:
            st.error("Gemini couldn't authenticate. Ensure `GEMINI_API_KEY` is set in "
                     "`cred.env`, then Generate again.", icon="🔑")
        elif auth_like:
            st.error("Live backend couldn't authenticate. Set `ANTHROPIC_API_KEY` "
                     "(or run `ant auth login`), then Generate again.", icon="🔑")
        else:
            st.error(f"Generation failed: {e}")


# --- header -----------------------------------------------------------------

st.title("🪪 Synthetic Profile Generator")
st.caption("Live demo of the spear-phishing **detector-research** profile generator "
           "(v2: calibrated sampler + model-written narrative). Pin dimensions, click **Generate**.")
st.info("All people, companies, and addresses are **fictional** and use reserved "
        "`.example` domains. Nothing here describes or targets a real person.", icon="🛡️")


def kv(label, value):
    st.markdown(f"**{label}**  \n{value}")


def render(result: dict):
    org, profile, email = result["org"], result["profile"], result["email"]
    core, pub, pri, beh = profile["core"], profile["public"], profile["private"], profile["behavior"]

    st.success(f"Generated via **{result['backend']}** in {result['ms']:,} ms (seed {result['seed']})", icon="✅")
    usage = result.get("usage") or []
    if usage:
        tin = sum((u.get("input_tokens") or 0) for u in usage)
        tout = sum((u.get("output_tokens") or 0) for u in usage)
        st.caption(f"🔌 Live call to `{usage[0].get('model', '')}` — {tin:,} input / {tout:,} output tokens "
                   f"(last call of each stage).")
    if result.get("issues"):
        st.warning("Kept after retries with validation issues: " + "; ".join(result["issues"]))

    with st.container(border=True):
        st.subheader(f"🏢 {org['name']}")
        c = st.columns(5)
        c[0].metric("Industry", org["industry"])
        c[1].metric("Size class", org["size_class"])
        c[2].metric("Headcount", f"{org['headcount']:,}")
        c[3].metric("HQ", org["hq_city"])
        c[4].metric("Domain", org["domain"])

    with st.container(border=True):
        st.subheader(f"👤 {core['full_name']} — {core['title']}")
        c = st.columns(5)
        with c[0]:
            kv("Email", f"`{core['email']}`")
        with c[1]:
            kv("Career stage", core["career_stage"])
        with c[2]:
            kv("Target role", core["target_role"])
        with c[3]:
            kv("Age / tenure", f"{core['age']} / {core['tenure_years']} y")
        with c[4]:
            kv("Education", core["highest_education"])

    tabs = st.tabs(["📄 Résumé", "🌐 Public footprint", "🔒 Private (ground truth)", "🧠 Behavior", "🧾 Raw JSON"])
    res = pub.get("resume") or {}

    with tabs[0]:
        st.caption(f"{pub.get('resume_word_count', 0)} words across {len(pub.get('resume_bullets', []))} bullets")
        cur = res.get("current_job") or {}
        st.markdown(f"**{cur.get('title', core['title'])}** — {org['name']} (current)")
        for b in cur.get("bullets", []):
            st.markdown(f"- {b}")
        for job in res.get("prior_jobs", []):
            st.markdown(f"**{job.get('title')}** — {job.get('employer')} ({job.get('start_year')}–{job.get('end_year')})")
            for b in job.get("bullets", []):
                st.markdown(f"- {b}")
        if res.get("education"):
            st.markdown("**Education**")
            for b in res["education"]:
                st.markdown(f"- {b}")

    with tabs[1]:
        st.markdown(f"**Footprint level:** {pub.get('footprint_level')} (score {pub.get('footprint_score')})")
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Social presence**")
            st.json(pub.get("social_presence", {}))
            if pub.get("personal_website"):
                st.markdown(f"**Website:** {pub['personal_website']}")
        with cols[1]:
            st.markdown("**Posts**")
            for p in pub.get("posts", []):
                st.markdown(f"- *{p.get('date')} · {p.get('platform')}* — {p.get('text')}")

    with tabs[2]:
        st.caption("The ground truth the public footprint only hints at — the baseline for "
                   "under-knowledge comparison.")
        st.markdown("**Projects:** " + ", ".join(pri.get("projects", [])))
        st.markdown("**Sensitive access**")
        for a in pri.get("sensitive_access", []):
            st.markdown(f"- {a}")
        st.markdown("**Colleagues**")
        for col in pri.get("colleagues", []):
            st.markdown(f"- {col.get('name')} — *{col.get('relation')}*")
        st.markdown("**Real details**")
        for d in pri.get("real_details", []):
            st.markdown(f"- {d}")

    with tabs[3]:
        c = st.columns(4)
        c[0].metric("Security awareness", beh.get("security_awareness"))
        c[1].metric("Busy level", beh.get("busy_level"))
        c[2].metric("p(click simulated phish)", beh.get("p_click_simulated_phish"))
        c[3].metric("Emails / day", beh.get("emails_received_per_day"))
        st.markdown("**Traits:** " + ", ".join(beh.get("traits", [])))
        st.markdown("**Response tendencies**")
        st.json(beh.get("response_tendencies", {}))

    with tabs[4]:
        st.json({"spec": result["spec"], **profile})

    st.download_button(
        "⬇️ Download profile JSON",
        json.dumps({"org": org, **profile}, ensure_ascii=False, indent=2),
        file_name=f"{core['full_name'].replace(' ', '_').lower()}.json",
        mime="application/json",
    )

    if email:
        st.markdown("---")
        st.subheader("✉️ Targeting spear email")
        st.warning("Synthetic attack email for detector research — sender is a `.example` "
                   "look-alike; this is not sendable.", icon="🛡️")
        c = st.columns(3)
        c[0].metric("Scenario", email["scenario"])
        c[1].metric("Urgency", email["urgency"])
        c[2].metric("Impersonates", email["impersonated_role"])
        st.markdown(f"**From:** `{email['sender_display']} <{email['sender_address']}>`")
        st.markdown(f"**Subject:** {email['subject']}")
        st.code(email["body"], language="text")
        st.caption("Personalization used: " + ", ".join(map(str, email.get("personalization_fields", []))))


if "result" in st.session_state:
    render(st.session_state["result"])
else:
    st.markdown("> Pin dimensions in the sidebar (or leave them random) and press **⚡ Generate profile**.")
