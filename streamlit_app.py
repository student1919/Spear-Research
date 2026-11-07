"""Real-time demo of synthetic profile generation.

    streamlit run streamlit_app.py

Each "Generate" click produces a fresh synthetic profile live by calling the same
pipeline the batch run uses (src/sample.py + src/llm.py backends + src/prompts.py).
Local backend runs offline and instantly; the Anthropic backend calls Haiku/Sonnet
live when the SDK + credentials are present. Everything is fictional and uses only
reserved .example domains.
"""

from __future__ import annotations

import os
import sys
import json
import random
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config import dimensions as D                      # noqa: E402
from src.llm import (                                   # noqa: E402
    LocalBackend, AnthropicBackend, LiveHaikuBackend, GeminiBackend,
    SEED_MODEL, BULK_MODEL, GEMINI_PRIMARY,
)
from src.sample import make_org, _coherent_role, _coherent_stage           # noqa: E402

RANDOM = "— random —"

LOCAL_OPT = "Local (offline, instant)"
HAIKU_OPT = "Live API — Claude Haiku (true call)"
GEMINI_OPT = "Live API — Gemini Flash-Lite (true call)"
TWOPASS_OPT = "Anthropic — Sonnet seed + Haiku bulk (SDK)"

ANTHROPIC_OPTS = {HAIKU_OPT, TWOPASS_OPT}

st.set_page_config(page_title="Synthetic Profile Generator", page_icon="🪪", layout="wide")


def _installed(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:
        return False


def anthropic_installed() -> bool:
    return _installed("anthropic")


def genai_installed() -> bool:
    return _installed("google.genai")


@st.cache_resource(show_spinner=False)
def get_anthropic_backend():
    return AnthropicBackend()


@st.cache_resource(show_spinner=False)
def get_haiku_backend():
    return LiveHaikuBackend()


@st.cache_resource(show_spinner=False)
def get_gemini_backend():
    return GeminiBackend()


# --- sidebar controls -------------------------------------------------------

st.sidebar.header("Generation controls")

backend_choice = st.sidebar.radio(
    "Backend",
    [LOCAL_OPT, HAIKU_OPT, GEMINI_OPT, TWOPASS_OPT],
    index=0,
    help="Local composes offline from Claude-authored pools. "
         "'Claude Haiku' makes one real `claude-haiku-5-5` call per generation. "
         "'Gemini Flash-Lite' makes one real Gemini call (3.5-flash-lite, falling back "
         "to 3.1-flash-lite). 'Sonnet seed + Haiku bulk' is the two-pass batch design.",
)
if backend_choice in ANTHROPIC_OPTS and not anthropic_installed():
    st.sidebar.warning("`anthropic` SDK not installed — `pip install anthropic`, then set "
                       "`ANTHROPIC_API_KEY` (or run `ant auth login`).")
if backend_choice == GEMINI_OPT and not genai_installed():
    st.sidebar.warning("`google-genai` not installed — `pip install google-genai`. "
                       "`GEMINI_API_KEY` is loaded from `cred.env`.")

st.sidebar.markdown("**Target dimensions** — pick or leave random")
industry = st.sidebar.selectbox("Industry", [RANDOM] + D.INDUSTRIES)
stage = st.sidebar.selectbox("Career stage", [RANDOM] + D.CAREER_STAGES)
size = st.sidebar.selectbox("Company size", [RANDOM] + D.COMPANY_SIZES)
role = st.sidebar.selectbox("Target role", [RANDOM] + D.TARGET_ROLES)

st.sidebar.markdown("---")
lock_seed = st.sidebar.checkbox("Lock seed (reproducible)", value=False)
seed_val = st.sidebar.number_input("Seed", value=7, step=1, disabled=not lock_seed)
also_email = st.sidebar.checkbox("Also generate targeting spear email", value=False)

generate = st.sidebar.button("⚡ Generate profile", type="primary", use_container_width=True)


# --- generation -------------------------------------------------------------

def resolve_dims(rng: random.Random) -> dict:
    ind = rng.choices(list(D.INDUSTRY_WEIGHTS), weights=list(D.INDUSTRY_WEIGHTS.values()))[0] \
        if industry == RANDOM else industry
    sz = rng.choices(list(D.COMPANY_SIZE_WEIGHTS), weights=list(D.COMPANY_SIZE_WEIGHTS.values()))[0] \
        if size == RANDOM else size
    rl = _coherent_role(rng, ind) if role == RANDOM else role
    stg = _coherent_stage(rng, rl) if stage == RANDOM else stage
    return {"industry": ind, "company_size": sz, "target_role": rl, "career_stage": stg}


def run_generation():
    rng = random.Random(int(seed_val)) if lock_seed else random.Random()
    is_local = backend_choice == LOCAL_OPT

    with st.status("Generating…", expanded=True) as status:
        status.write("Sampling target dimensions")
        dims = resolve_dims(rng)
        status.write(f"Building synthetic company ({dims['industry']}, {dims['company_size']})")
        org = make_org(rng, dims["industry"], dims["company_size"])
        spec = {**dims, "org_id": org["org_id"]}

        if is_local:
            backend, fewshot, model, label = LocalBackend(rng), [], None, "LocalBackend"
        else:
            from src.prompts import profile_fewshot_messages
            fewshot, model = profile_fewshot_messages(3), BULK_MODEL
            if backend_choice == HAIKU_OPT:
                backend, label = get_haiku_backend(), "claude-haiku-5-5 (live)"
            elif backend_choice == GEMINI_OPT:
                backend, label = get_gemini_backend(), f"{GEMINI_PRIMARY} (live)"
            else:
                backend, label = get_anthropic_backend(), "Sonnet-seed / Haiku-bulk (live)"

        status.write(f"Prompting {label}")
        t0 = time.perf_counter()
        profile = backend.realize_profile(spec, org, model=model, fewshot=fewshot)
        usage = [{"stage": "profile", **(getattr(backend, "last_usage", None) or {})}] \
            if getattr(backend, "last_usage", None) else []

        email = None
        if also_email:
            status.write("Prompting for the targeting spear email")
            efew = []
            if not is_local:
                from src.prompts import email_fewshot_messages
                efew = email_fewshot_messages(3)
            email = backend.realize_email(profile, org, model=model, fewshot=efew)
            if getattr(backend, "last_usage", None):
                usage.append({"stage": "email", **backend.last_usage})

        elapsed = (time.perf_counter() - t0) * 1000
        status.update(label=f"Done in {elapsed:,.0f} ms", state="complete", expanded=False)

    st.session_state["result"] = {
        "org": org, "spec": spec, "profile": profile, "email": email,
        "backend": label, "ms": round(elapsed), "usage": usage,
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
           "(`Profiles.md`). Pick dimensions, click **Generate**.")
st.info("All people, companies, and addresses are **fictional** and use reserved "
        "`.example` domains. Nothing here describes or targets a real person.", icon="🛡️")


def kv(label, value):
    st.markdown(f"**{label}**  \n{value}")


def render(result: dict):
    org, profile, email = result["org"], result["profile"], result["email"]
    core = profile["core"]

    st.success(f"Generated via **{result['backend']}** in {result['ms']:,} ms", icon="✅")
    usage = result.get("usage") or []
    if usage:
        tin = sum((u.get("input_tokens") or 0) for u in usage)
        tout = sum((u.get("output_tokens") or 0) for u in usage)
        model_id = usage[0].get("model", "")
        st.caption(f"🔌 Live call to `{model_id}` — {tin:,} input / {tout:,} output tokens "
                   f"across {len(usage)} prompt(s).")

    # Company
    with st.container(border=True):
        st.subheader(f"🏢 {org['name']}")
        c = st.columns(5)
        c[0].metric("Industry", org["industry"])
        c[1].metric("Size", org["size"])
        c[2].metric("Headcount", f"{org['headcount']:,}")
        c[3].metric("HQ", org["hq_city"])
        c[4].metric("Domain", org["domain"])

    # Identity
    with st.container(border=True):
        st.subheader(f"👤 {core['full_name']} — {core['title']}")
        c = st.columns(4)
        with c[0]:
            kv("Email", f"`{core['email']}`")
        with c[1]:
            kv("Career stage", core["career_stage"])
        with c[2]:
            kv("Target role", core["target_role"])
        with c[3]:
            kv("Location", core["location"])

    # Detail tabs
    tabs = st.tabs(["🌐 Public footprint", "🔒 Private (ground truth)",
                    "🧠 Behavior", "🧾 Raw JSON"])
    pub, pri, beh = profile["public"], profile["private"], profile["behavior"]

    with tabs[0]:
        st.markdown(f"**Footprint level:** {pub.get('footprint_level')}")
        st.markdown("**Résumé bullets**")
        for b in pub.get("resume_bullets", []):
            st.markdown(f"- {b}")
        cols = st.columns(2)
        with cols[0]:
            st.markdown("**Social presence**")
            st.json(pub.get("social_presence", {}))
            if pub.get("personal_website"):
                st.markdown(f"**Website:** {pub['personal_website']}")
        with cols[1]:
            st.markdown("**Posts**")
            for p in pub.get("posts", []):
                st.markdown(f"- *{p.get('date')}* — {p.get('text')}")

    with tabs[1]:
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

    with tabs[2]:
        c = st.columns(2)
        c[0].metric("Security awareness", beh.get("security_awareness"))
        c[1].metric("Busy level", beh.get("busy_level"))
        st.markdown("**Traits:** " + ", ".join(beh.get("traits", [])))
        st.markdown("**Response tendencies**")
        st.json(beh.get("response_tendencies", {}))

    with tabs[3]:
        st.json(profile)

    # Download
    st.download_button(
        "⬇️ Download profile JSON",
        json.dumps({"org": org, **profile}, ensure_ascii=False, indent=2),
        file_name=f"{core['full_name'].replace(' ', '_').lower()}.json",
        mime="application/json",
    )

    # Optional email
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
        st.caption("Personalization used: " + ", ".join(email.get("personalization_fields", [])))


if "result" in st.session_state:
    render(st.session_state["result"])
else:
    st.markdown("> Set your dimensions in the sidebar and press **⚡ Generate profile**. "
                "Leave fields on *— random —* to sample the weighted target distribution.")
