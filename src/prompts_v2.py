"""v2 prompts: the sampler fixes every number; the model writes the narrative and the spear email.

Profile prompt: the model receives a fully specified person (demographics, title, tenure,
schools, online activity, work rhythm, susceptibility). It must NOT change any given fact.
It writes only the free-text parts: the resume (about 500 words, every bullet carrying a
quantitative performance metric), prior job titles, specific majors, social handles, post
text, projects, ground-truth details, access, traits.

Email prompt: the model receives the merged profile and the employer and writes one spear
email targeting that person.
"""

from __future__ import annotations

import json
import re
from typing import Any

PROMPT_VERSION = "v2.2"

# Resume length limits (words across every resume bullet). Shared by the prompt and the validator.
RESUME_TARGET_WORDS = 500
RESUME_MIN_WORDS = 450
RESUME_MAX_WORDS = 550
CURRENT_JOB_BULLETS = (3, 12)
PRIOR_JOB_BULLETS = (1, 5)

SYNTHETIC_NOTE = (
    "Everything you produce is FICTIONAL and for a defensive phishing-detection research corpus. The "
    "person, their employers and their colleagues are invented. The universities listed in the education "
    "records are real public institutions: use their names exactly as given, but state nothing else about "
    "them (no named professors, programs, clubs or events). Prior employers must be invented companies "
    "(never a real brand). All web/email domains must end in .example."
)

PROFILE_V2_SYSTEM = f"""You write the narrative part of a synthetic employee profile for a spear-phishing \
DETECTION research project. The profiles are used to study and train a detector; they describe invented \
people and are never used to contact anyone.

{SYNTHETIC_NOTE}

You are given a fully specified person ("spec"). Every fact in the spec is FIXED: name, age, title, \
employer, tenure, schools, degrees, graduation years, platforms, number of posts. Do not change, contradict, \
or restate them differently (for example, do not say someone with 2 years of tenure has been at the company \
for 6). Make the narrative internally consistent with the spec:
- Dates: the current date is 2026-11-01. The current job began about `tenure_years` ago.
- resume: the person's public resume, about {RESUME_TARGET_WORDS} words in total. Count the words of every \
  bullet in every section together; the total must be between {RESUME_MIN_WORDS} and {RESUME_MAX_WORDS} \
  words. Sections:
  - current_job: {CURRENT_JOB_BULLETS[0]}-{CURRENT_JOB_BULLETS[1]} bullets of concrete, role-appropriate \
    accomplishments in the CURRENT title at the CURRENT employer, scaled to the tenure.
  - prior_jobs: one list of {PRIOR_JOB_BULLETS[0]}-{PRIOR_JOB_BULLETS[1]} bullets per entry of `prior_jobs` \
    (same order), describing the work done in the title you give that job in career_titles. If `prior_jobs` \
    is empty return [].
  - education: exactly one bullet per education record, in order (institution, degree, major, year). \
    Students list the degree in progress. If there are no education records return [].
  EVERY bullet, including education bullets, states at least one objective, quantitative metric of \
  performance written with numerals: a percentage, dollar amount, count, rate, duration, ranking, GPA or \
  similar (for example "cut month-end close from 9 to 6 days", "graduated with a 3.7 GPA"). Calendar years \
  and dates do not count as metrics. Every metric must be plausible for the role, the seniority and the \
  employer's headcount (no one at a 40-person firm manages 300 people).
- career_titles: exactly one job title per entry of `prior_jobs` (same order), showing a believable \
  progression toward the current title. The employers and years are fixed; do not repeat them. If \
  `prior_jobs` is empty return [].
- education_majors: one specific major name per education record, in order, belonging to its `field` group.
- social_presence: one invented handle for EACH platform in `platforms`, in a varied, natural style \
  (not all the same pattern). No other platforms.
- posts: exactly one post per entry in `post_slots`, written to fit that platform and the person's role, \
  tone and age. If post_slots is empty return [].
- personal_website: a .example URL if `has_personal_website` is true, else null.
- projects (2-4) and real_details (3-4): the private ground truth behind the resume lines, specific and \
  consistent with title and tenure; real_details may add facts the public footprint does not show. Cover \
  the two `detail_themes` with concrete facts (place names, activities) and use the `colleagues` by name \
  where natural. Do not repeat generic habits across people; be specific to THIS person.
- Never write raw numbers for tenure or age (say "about five years", "since early 2025", "in her \
  thirties"). The performance metrics in resume bullets are the only place numerals are required. Never \
  append ".example" to a company name.
- sensitive_access: what this specific person can authorize or reach, appropriate to the role and level.
- traits (3-5) and response_tendencies (2-4, cue -> likely reaction): consistent with `behavior_numbers`. \
  A high click probability means quick, trusting reactions to routine requests; a low one means \
  verification habits. A high email volume means skimming and speed; low means careful reading. Do not \
  quote the numbers.

Output ONE JSON object, no prose, with exactly these keys:
{{"public": {{"resume": {{"current_job": [..], "prior_jobs": [[..]], "education": [..]}}, "career_titles": [..], \
"education_majors": [..], "social_presence": {{"<platform>": "<handle>"}}, \
"posts": [{{"text": ""}}], "personal_website": null}}, \
"private": {{"projects": [..], "real_details": [..], "sensitive_access": [..]}}, \
"behavior": {{"traits": [..], "response_tendencies": {{"<cue>": "<reaction>"}}}}}}"""
PROFILE_V2_SYSTEM = re.sub(r"(?<=\S) {2,}", " ", PROFILE_V2_SYSTEM)   # collapse line-continuation indents


WORDS_PER_BULLET = 30   # preferred bullet length when planning the resume layout


def plan_resume_layout(n_prior: int, n_edu: int) -> dict[str, Any]:
    """Exact bullet counts and a per-bullet word budget that land the resume on RESUME_TARGET_WORDS.

    Models write short bullets when left to choose the length, so the layout is prescribed instead:
    education gets one bullet per record, each prior job up to 3 (older jobs fewer), and the current job
    takes the remainder, all inside the allowed ranges. The word budget per bullet is then
    target / total bullets.
    """
    want = round(RESUME_TARGET_WORDS / WORDS_PER_BULLET)
    prior = [min(PRIOR_JOB_BULLETS[1], max(PRIOR_JOB_BULLETS[0], 3 - (k >= 2))) for k in range(n_prior)]
    cur = max(CURRENT_JOB_BULLETS[0], min(CURRENT_JOB_BULLETS[1], want - sum(prior) - n_edu))
    total = cur + sum(prior) + n_edu
    return {"current_job_bullets": cur, "prior_job_bullets": prior, "education_bullets": n_edu,
            "total_bullets": total, "words_per_bullet": round(RESUME_TARGET_WORDS / total),
            "total_words": RESUME_TARGET_WORDS}


def build_profile_v2_user_prompt(spec: dict[str, Any], org: dict[str, Any], post_slots: list[dict[str, str]]) -> str:
    edu = [{"level": e["level"], "status": e["status"], "field": e["field"],
            "institution": f"{e['institution']['name']} ({e['institution']['city']}, {e['institution']['state']})",
            "year": e.get("grad_year") or e.get("expected_grad_year")} for e in spec["education"]]
    p, r, s = spec["presence"], spec["rhythm"], spec["susceptibility"]
    given = {
        "name": spec["full_name"], "age": spec["age"], "gender": spec["gender"], "title": spec["title"],
        "career_stage": spec["career_stage"], "target_role": spec["target_role"],
        "tenure_years": spec["tenure_years"], "is_new_hire": spec["is_new_hire"],
        "years_of_experience": spec["years_experience"], "prior_jobs": [{"employer": j["employer"], "start_year": j["start_year"], "end_year": j["end_year"]}
                       for j in spec["career_skeleton"]],
        "colleagues": spec["colleagues"], "detail_themes": spec["detail_themes"], "education": edu,
        "platforms": list(p["platforms"]), "post_slots": post_slots,
        "has_personal_website": p["has_personal_website"],
        "behavior_numbers": {
            "probability_of_clicking_a_simulated_phish": s["p_click_simulated_phish"],
            "received_security_training": s["received_security_training"],
            "emails_received_per_day": r["emails_received_per_day"],
            "email_checks_per_day": r["email_checks_per_day"],
            "often_in_inbox_late_at_night": r["late_night_inbox"],
        },
    }
    company = {k: org[k] for k in ("name", "domain", "industry", "size", "headcount", "hq_city")}
    layout = plan_resume_layout(len(spec["career_skeleton"]), len(spec["education"]))
    return ("Spec (fixed facts):\n" + json.dumps(given, ensure_ascii=False, indent=1)
            + "\n\nEmployer:\n" + json.dumps(company, ensure_ascii=False, indent=1)
            + "\n\nResume layout (follow exactly): " + json.dumps(layout)
            + f"\nWrite every resume bullet as one full sentence of about {layout['words_per_bullet']} words "
              "(name the scope, the tools or methods, who it was for, and the measured result). The whole "
              f"resume must reach about {RESUME_TARGET_WORDS} words, so terse bullets will fail."
            + "\n\nReturn the narrative JSON object now.")


# ---------------------------------------------------------------------------
# Spear-email generation
# ---------------------------------------------------------------------------

EMAIL_KEYS = ("scenario", "pretext", "impersonated_role", "sender_display", "sender_address", "subject",
              "body", "call_to_action", "urgency", "personalization_fields")

EMAIL_V2_SYSTEM = f"""You generate synthetic spear-phishing emails for a DETECTION research corpus. Each \
email targets ONE invented profile at an invented company. The emails are labeled training/evaluation data \
for a detector and are never sent.

{SYNTHETIC_NOTE}

You are given the full profile (core/public/private/behavior) and the company. Craft a plausible \
spear-phishing email that a real attacker might send to that specific person, drawing on their role, \
access, resume, posts, projects and colleagues. Choose a scenario that fits the target (for example: a \
business-email-compromise wire request to finance staff, a payroll-redirect to HR, a credential-reset lure \
to a new hire, an invoice-approval to an executive, an IP-exfiltration pretext to an engineer).

The sender address MUST be a synthetic look-alike under a .example domain (e.g. a cousin domain of the \
company's own example domain). Every link in the body must also be under a .example domain. Do NOT \
impersonate a real brand or real person.

Output a single JSON object with exactly these keys: {", ".join(EMAIL_KEYS[:-2])}, urgency \
(low|medium|high), personalization_fields (a list of the profile facts you used). Output JSON only, no \
prose."""


def build_email_v2_user_prompt(profile: dict[str, Any], org: dict[str, Any]) -> str:
    company = {k: org[k] for k in ("name", "domain", "industry", "size", "headcount", "hq_city")}
    return ("Target profile:\n" + json.dumps(profile, ensure_ascii=False, indent=1)
            + "\n\nCompany:\n" + json.dumps(company, ensure_ascii=False, indent=1)
            + "\n\nReturn the spear-email JSON object now.")
