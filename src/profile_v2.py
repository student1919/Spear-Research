"""v2 profile generation: merge the sampled spec with the model's narrative.

Every numeric/categorical field in the output comes from the spec, never from the
model. The model's JSON is checked against the spec (counts, platforms, schools, resume
length and metrics) and re-requested up to `retries` times on a violation.
"""

from __future__ import annotations

import json
import random
import re
from datetime import date, timedelta
from typing import Any

from .prompts_v2 import (CURRENT_JOB_BULLETS, PRIOR_JOB_BULLETS, RESUME_MAX_WORDS, RESUME_MIN_WORDS)
from .schema import (ProfileBehavior, ProfileBundle, ProfileCore, ProfilePrivate, ProfilePublic)

TODAY = date(2026, 11, 1)

_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
_DIGIT = re.compile(r"\d")


def _alnum(t: str) -> str:
    return "".join(ch for ch in t.lower() if ch.isalnum())


def word_count(bullets: list[str]) -> int:
    return sum(len(str(b).split()) for b in bullets)


def has_metric(bullet: str) -> bool:
    """True if the bullet contains a numeral other than a calendar year."""
    return bool(_DIGIT.search(_YEAR.sub("", str(bullet))))


def flatten_resume(resume: dict[str, Any]) -> list[str]:
    """Resume bullets in reading order: current job, prior jobs (in order), education."""
    out = list(resume.get("current_job") or [])
    for job in resume.get("prior_jobs") or []:
        out += list(job.get("bullets", []) if isinstance(job, dict) else job)
    return out + list(resume.get("education") or [])


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


def check_resume(resume: Any, spec: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if not isinstance(resume, dict):
        return ["public.resume must be an object with current_job, prior_jobs, education"]
    cur, prior, edu = resume.get("current_job") or [], resume.get("prior_jobs") or [], resume.get("education") or []
    lo, hi = CURRENT_JOB_BULLETS
    if not lo <= len(cur) <= hi:
        errs.append(f"resume.current_job must have {lo}-{hi} bullets")
    n_prior = len(spec["career_skeleton"])
    if len(prior) != n_prior or not all(isinstance(j, list) for j in prior):
        errs.append(f"resume.prior_jobs must be {n_prior} lists of bullets (one per prior job)")
    else:
        lo, hi = PRIOR_JOB_BULLETS
        if any(not lo <= len(j) <= hi for j in prior):
            errs.append(f"each resume.prior_jobs entry must have {lo}-{hi} bullets")
    if len(edu) != len(spec["education"]):
        errs.append(f"resume.education must have {len(spec['education'])} bullets (one per education record)")
    else:
        for e, b in zip(spec["education"], edu):
            if _alnum(e["institution"]["name"])[:10] not in _alnum(str(b)):
                errs.append(f"resume.education bullet must mention {e['institution']['name']}")
                break
    bullets = flatten_resume({"current_job": cur, "prior_jobs": [j for j in prior if isinstance(j, list)],
                              "education": edu})
    n_words = word_count(bullets)
    if not RESUME_MIN_WORDS <= n_words <= RESUME_MAX_WORDS:
        n_b = max(1, len(bullets))
        goal = (RESUME_MIN_WORDS + RESUME_MAX_WORDS) // 2
        errs.append(f"the resume has {n_words} words in total; it must have {RESUME_MIN_WORDS}-{RESUME_MAX_WORDS}. "
                    f"Keep the same bullets but rewrite each one longer: {n_b} bullets now average "
                    f"{n_words / n_b:.0f} words and need to average about {goal / n_b:.0f} "
                    f"({'add' if n_words < goal else 'cut'} about {abs(goal - n_words)} words overall)")
    missing = [b for b in bullets if not has_metric(b)]
    if missing:
        errs.append(f"{len(missing)} resume bullet(s) lack a numeric performance metric (years do not count), "
                    f"e.g. {str(missing[0])[:80]!r}")
    return errs


def check_narrative(obj: dict[str, Any], spec: dict[str, Any], slots: list[dict[str, str]]) -> list[str]:
    """Return a list of violations (empty = ok)."""
    try:
        pub, priv, beh = obj["public"], obj["private"], obj["behavior"]
    except (KeyError, TypeError) as e:
        return [f"missing top-level key {e}"]
    errs = check_resume(pub.get("resume"), spec)
    n_edu = len(spec["education"])
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
    for k in ("projects", "real_details", "sensitive_access"):
        if not priv.get(k):
            errs.append(f"private.{k} is required")
    return errs


def _request(backend, spec, org, slots, retries, log, label):
    """Call the backend until the narrative passes or retries run out. Returns (obj, errors)."""
    obj, errs = None, []
    for _ in range(retries + 1):
        hint = "" if not errs else "\n\nYour previous answer violated: " + "; ".join(errs) + ". Fix these."
        try:
            cand = backend.realize_profile(spec, org, slots, extra=hint)
        except (ValueError, json.JSONDecodeError) as e:   # unparseable / truncated JSON
            errs = [f"output was not one valid JSON object ({str(e)[:80]})"]
            continue
        obj, errs = cand, check_narrative(cand, spec, slots)
        if not errs:
            break
    if errs:
        log(f"  {label}: kept after {retries + 1} attempts with issues: {errs}")
    return obj, errs


def _merge(pid: str, spec: dict[str, Any], obj: dict[str, Any], slots: list[dict[str, str]]) -> ProfileBundle:
    pub, priv, beh = obj.get("public", {}), obj.get("private", {}), obj.get("behavior", {})
    raw = pub.get("resume") if isinstance(pub.get("resume"), dict) else {}
    titles = list(pub.get("career_titles", []))
    history = [{**j, "title": titles[k] if k < len(titles) else ""} for k, j in enumerate(spec["career_skeleton"])]
    prior_raw = [j for j in (raw.get("prior_jobs") or []) if isinstance(j, list)]
    resume = {
        "current_job": {"title": spec["title"], "employer_org_id": spec["org_id"],
                        "bullets": list(raw.get("current_job") or [])},
        "prior_jobs": [{**h, "bullets": prior_raw[k] if k < len(prior_raw) else []} for k, h in enumerate(history)],
        "education": list(raw.get("education") or []),
    }
    bullets = flatten_resume({"current_job": resume["current_job"]["bullets"], "prior_jobs": resume["prior_jobs"],
                              "education": resume["education"]})
    edu = [{**rec, "major": major, "institution": dict(rec["institution"])}
           for rec, major in zip(spec["education"], pub.get("education_majors", []))]
    posts = [{"date": s["date"], "platform": s["platform"], "text": p.get("text", "")}
             for s, p in zip(slots, pub.get("posts", []))]
    presence, rhythm, susc = spec["presence"], spec["rhythm"], spec["susceptibility"]
    return ProfileBundle(
        core=ProfileCore(
            profile_id=pid, org_id=spec["org_id"], full_name=spec["full_name"], email=spec["email"],
            industry=spec["industry"], career_stage=spec["career_stage"], target_role=spec["target_role"],
            title=spec["title"], location=spec["location"], age=spec["age"], gender=spec["gender"],
            birth_year=spec["birth_year"], tenure_years=spec["tenure_years"],
            years_experience=spec["years_experience"], is_new_hire=spec["is_new_hire"],
            highest_education=spec["highest_education"], size_class=spec["size_class"]),
        public=ProfilePublic(
            profile_id=pid, resume_bullets=bullets, resume=resume, resume_word_count=word_count(bullets),
            social_presence=pub.get("social_presence", {}), footprint_level=presence["footprint_level"],
            posts=posts, personal_website=pub.get("personal_website") or None, education=edu,
            career_history=history, platform_activity=presence["platforms"],
            public_posts_per_month=presence["public_posts_per_month"],
            footprint_score=presence["footprint_score"]),
        private=ProfilePrivate(
            profile_id=pid, projects=priv.get("projects", []), colleagues=spec["colleagues"],
            real_details=priv.get("real_details", []), sensitive_access=priv.get("sensitive_access", [])),
        behavior=ProfileBehavior(
            profile_id=pid, traits=beh.get("traits", []), security_awareness=susc["security_awareness"],
            response_tendencies=beh.get("response_tendencies", {}), busy_level=rhythm["busy_level"],
            p_click_simulated_phish=susc["p_click_simulated_phish"],
            received_security_training=susc["received_security_training"],
            email_checks_per_day=rhythm["email_checks_per_day"],
            email_checks_per_computer_hour=rhythm["email_checks_per_computer_hour"],
            emails_received_per_day=rhythm["emails_received_per_day"],
            late_night_inbox=rhythm["late_night_inbox"]),
    )


def generate_profiles_v2(backend, orgs: list[dict[str, Any]], specs: list[dict[str, Any]],
                         rng: random.Random, retries: int = 2, log=print):
    """Returns (bundles, issues). A profile whose every attempt was unparseable is skipped and logged."""
    orgs_by_id = {o["org_id"]: o for o in orgs}
    bundles: list[ProfileBundle] = []
    issues: list[dict[str, Any]] = []
    for i, spec in enumerate(specs):
        org = orgs_by_id[spec["org_id"]]
        slots = make_post_slots(spec, rng)
        obj, errs = _request(backend, spec, org, slots, retries, log, f"profile {i}")
        if errs:
            issues.append({"profile": i, "errors": errs, "skipped": obj is None})
        if obj is not None:
            bundles.append(_merge(f"prof_{i:04d}", spec, obj, slots))
        if (i + 1) % 5 == 0 or i + 1 == len(specs):
            log(f"  generated {i + 1}/{len(specs)}")
    return bundles, issues
