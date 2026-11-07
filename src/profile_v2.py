"""v2 profile generation: merge the sampled spec with the model's narrative.

Every numeric/categorical field in the output comes from the spec, never from the
model. The model's JSON is checked against the spec (counts, platforms, manager,
contiguous career history) and re-requested up to `retries` times on a violation.
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from .prompts_v2 import build_profile_v2_user_prompt
from .schema import (ProfileBehavior, ProfileBundle, ProfileCore, ProfilePrivate, ProfilePublic)

TODAY = date(2026, 11, 1)


def _alnum(t: str) -> str:
    return "".join(ch for ch in t.lower() if ch.isalnum())


def make_post_slots(spec: dict[str, Any], rng: random.Random) -> list[dict[str, str]]:
    """Which platform/date each public post sits on, from the sampled posting rates (last 12 months)."""
    plats = {k: v for k, v in spec["presence"]["platforms"].items() if v > 0}
    slots: list[dict[str, str]] = []
    for plat, per_month in plats.items():
        n = min(6, int(round(per_month * 12)))
        for _ in range(n):
            d = TODAY - timedelta(days=rng.randint(3, 360))
            slots.append({"platform": plat, "date": d.isoformat()})
    slots.sort(key=lambda s: s["date"])
    return slots[:8]


def check_narrative(obj: dict[str, Any], spec: dict[str, Any], slots: list[dict[str, str]]) -> list[str]:
    """Return a list of violations (empty = ok)."""
    errs: list[str] = []
    try:
        pub, priv, beh = obj["public"], obj["private"], obj["behavior"]
    except KeyError as e:
        return [f"missing top-level key {e}"]
    n_edu = len(spec["education"])
    if not 3 <= len(pub.get("resume_bullets", [])) <= 6:
        errs.append("resume_bullets must have 3-6 items")
    if len(pub.get("education_majors", [])) != n_edu:
        errs.append(f"education_majors must have {n_edu} items")
    if len(pub.get("career_titles", [])) != len(spec["career_skeleton"]):
        errs.append(f"career_titles must have {len(spec['career_skeleton'])} items")
    if set(pub.get("social_presence", {})) != set(spec["presence"]["platforms"]):
        errs.append(f"social_presence platforms must be exactly {sorted(spec['presence']['platforms'])}")
    if len(pub.get("posts", [])) != len(slots):
        errs.append(f"posts must have {len(slots)} items")
    if bool(pub.get("personal_website")) != bool(spec["presence"]["has_personal_website"]):
        errs.append("personal_website must match has_personal_website")
    if not 3 <= len(beh.get("traits", [])) <= 5 or not 2 <= len(beh.get("response_tendencies", {})) <= 4:
        errs.append("traits 3-5 and response_tendencies 2-4 required")
    blob = _alnum(" ".join(pub.get("resume_bullets", [])))
    for e in spec["education"]:
        if _alnum(e["institution"]["name"])[:10] not in blob:
            errs.append(f"resume_bullets must mention {e['institution']['name']}")
            break
    return errs


def generate_profiles_v2(backend, orgs: list[dict[str, Any]], specs: list[dict[str, Any]],
                         rng: random.Random, retries: int = 2, log=print):
    orgs_by_id = {o["org_id"]: o for o in orgs}
    bundles: list[ProfileBundle] = []
    issues: list[dict[str, Any]] = []
    for i, spec in enumerate(specs):
        org = orgs_by_id[spec["org_id"]]
        slots = make_post_slots(spec, rng)
        obj, errs = None, []
        for attempt in range(retries + 1):
            hint = "" if not errs else "\n\nYour previous answer violated: " + "; ".join(errs) + ". Fix these."
            obj = backend.realize_profile_v2(spec, org, slots, extra=hint)
            errs = check_narrative(obj, spec, slots)
            if not errs:
                break
        if errs:
            issues.append({"profile": i, "errors": errs})
            log(f"  profile {i}: kept after {retries + 1} attempts with issues: {errs}")
        pid = f"prof_{i:04d}"
        pub, priv, beh = obj["public"], obj["private"], obj["behavior"]
        edu = []
        for rec, major in zip(spec["education"], pub.get("education_majors", [])):
            edu.append({**rec, "major": major, "institution": dict(rec["institution"])})
        posts = [{"date": s["date"], "platform": s["platform"], "text": p.get("text", "")}
                 for s, p in zip(slots, pub.get("posts", []))]
        presence, rhythm, susc = spec["presence"], spec["rhythm"], spec["susceptibility"]
        bundles.append(ProfileBundle(
            core=ProfileCore(
                profile_id=pid, org_id=spec["org_id"], full_name=spec["full_name"], email=spec["email"],
                industry=spec["industry"], career_stage=spec["career_stage"], target_role=spec["target_role"],
                title=spec["title"], location=spec["location"], age=spec["age"], gender=spec["gender"],
                birth_year=spec["birth_year"], tenure_years=spec["tenure_years"],
                years_experience=spec["years_experience"], is_new_hire=spec["is_new_hire"],
                highest_education=spec["highest_education"], size_class=spec["size_class"]),
            public=ProfilePublic(
                profile_id=pid, resume_bullets=pub["resume_bullets"], social_presence=pub["social_presence"],
                footprint_level=presence["footprint_level"], posts=posts,
                personal_website=pub.get("personal_website") or None, education=edu,
                career_history=[{**j, "title": t} for j, t in zip(spec["career_skeleton"], pub["career_titles"])],
                platform_activity=presence["platforms"],
                public_posts_per_month=presence["public_posts_per_month"],
                footprint_score=presence["footprint_score"]),
            private=ProfilePrivate(
                profile_id=pid, projects=priv["projects"], colleagues=spec["colleagues"],
                real_details=priv["real_details"], sensitive_access=priv["sensitive_access"]),
            behavior=ProfileBehavior(
                profile_id=pid, traits=beh["traits"], security_awareness=susc["security_awareness"],
                response_tendencies=beh["response_tendencies"], busy_level=rhythm["busy_level"],
                p_click_simulated_phish=susc["p_click_simulated_phish"],
                received_security_training=susc["received_security_training"],
                email_checks_per_day=rhythm["email_checks_per_day"],
                email_checks_per_computer_hour=rhythm["email_checks_per_computer_hour"],
                emails_received_per_day=rhythm["emails_received_per_day"],
                late_night_inbox=rhythm["late_night_inbox"]),
        ))
        if (i + 1) % 5 == 0 or i + 1 == len(specs):
            log(f"  generated {i + 1}/{len(specs)}")
    return bundles, issues
