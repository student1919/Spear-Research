"""v2 profile prompt: the sampler fixes every number; the model writes the narrative.

The model receives a fully specified person (demographics, title, tenure, schools,
online activity, work rhythm, susceptibility). It must NOT change any given fact. It
writes only the free-text parts: resume bullets, prior career, specific majors,
social handles, post text, projects, colleagues, ground-truth details, access, traits.
"""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION = "v2"

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
- Resume bullets (3-5): concrete, role-appropriate accomplishments at the CURRENT employer scaled to \
  the tenure, plus exactly one bullet for each education record (institution, degree, major, year). \
  Students list the degree in progress.
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
  thirties"). Never append ".example" to a company name.
- sensitive_access: what this specific person can authorize or reach, appropriate to the role and level.
- traits (3-5) and response_tendencies (2-4, cue -> likely reaction): consistent with `behavior_numbers`. \
  A high click probability means quick, trusting reactions to routine requests; a low one means \
  verification habits. A high email volume means skimming and speed; low means careful reading. Do not \
  quote the numbers.

Output ONE JSON object, no prose, with exactly these keys:
{{"public": {{"resume_bullets": [..], "career_titles": [..], "education_majors": [..], "social_presence": {{"<platform>": "<handle>"}}, \
"posts": [{{"text": ""}}], "personal_website": null}}, \
"private": {{"projects": [..], "real_details": [..], "sensitive_access": [..]}}, \
"behavior": {{"traits": [..], "response_tendencies": {{"<cue>": "<reaction>"}}}}}}"""


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
    return ("Spec (fixed facts):\n" + json.dumps(given, ensure_ascii=False, indent=1)
            + "\n\nEmployer:\n" + json.dumps(company, ensure_ascii=False, indent=1)
            + "\n\nReturn the narrative JSON object now.")
