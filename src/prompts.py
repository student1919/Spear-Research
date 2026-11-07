"""Prompt engineering for the generator (step one of the trajectory).

Two generation tasks, each with a system prompt + a few-shot assembler:

  1. Profile generation  -> a ProfileBundle (core/public/private/behavior)
  2. Spear-email generation -> an AttackEmail targeting a given profile

The few-shot exemplars are the five seed profiles/emails (authored by the higher
-capability Sonnet pass, per the plan) loaded from ``seeds/``. The Haiku pass is
conditioned on those exemplars. Prompts are versioned via PROMPT_VERSION so a run
can be tied back to the exact instructions that produced it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROMPT_VERSION = "v1"

# All synthetic identities live under these reserved, non-routable zones so no
# generated address can collide with a real person or company.
SYNTHETIC_EMAIL_ZONE = "example.com"   # RFC 2606 reserved
SYNTHETIC_NOTE = (
    "Everything you produce is FICTIONAL and for a defensive phishing-detection "
    "research corpus. Never use a real person, a real company, a real brand, or a "
    "real email domain. All web/email domains must end in .example or be under "
    "example.com / example.org / example.net."
)


# ---------------------------------------------------------------------------
# Profile generation
# ---------------------------------------------------------------------------

PROFILE_SYSTEM = f"""You generate synthetic employee profiles for a spear-phishing \
DETECTION research project. The profiles are used to train and evaluate a detector; \
they describe invented people at invented companies and are never used to contact \
anyone.

{SYNTHETIC_NOTE}

You are given a target specification (industry, company size, career stage, target \
role, and the employing company). Produce ONE internally consistent profile as a \
single JSON object with exactly these top-level keys: "core", "public", "private", \
"behavior".

- core: full_name, email, title, location. The title must fit the career stage and \
target role; the email must be <first>.<last>@<company-domain>.
- public: resume_bullets (3-5), social_presence (platform -> handle), \
footprint_level (low|medium|high), posts (2-4 items of {{date, text}}), \
personal_website (url under a .example domain, or null).
- private: projects (2-4), colleagues (2-4 items of {{name, relation}}), \
real_details (2-4 ground-truth facts behind the resume lines), sensitive_access \
(what this person can authorize or reach).
- behavior: traits (3-5), security_awareness (low|medium|high), \
response_tendencies (cue -> likely reaction, 2-4 entries), busy_level \
(low|medium|high).

Make profiles varied and realistic. The public footprint and the private details \
must be consistent but NOT identical (private is the ground truth the public \
footprint only hints at). Output JSON only, no prose."""


def build_profile_user_prompt(spec: dict[str, Any], org: dict[str, Any]) -> str:
    return (
        "Target specification:\n"
        + json.dumps(spec, ensure_ascii=False, indent=2)
        + "\n\nEmploying company:\n"
        + json.dumps(
            {k: org[k] for k in ("name", "domain", "industry", "size", "hq_city")},
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nReturn the profile JSON object now."
    )


# ---------------------------------------------------------------------------
# Spear-email generation
# ---------------------------------------------------------------------------

EMAIL_SYSTEM = f"""You generate synthetic spear-phishing emails for a DETECTION \
research corpus. Each email targets ONE invented profile at an invented company. \
The emails are labeled training/evaluation data for a detector and are never sent.

{SYNTHETIC_NOTE}

You are given the full profile (core/public/private/behavior) and the company. \
Craft a plausible spear-phishing email that a real attacker might send to that \
specific person, drawing on their role, access, projects, and colleagues. Choose a \
scenario that fits the target (for example: a business-email-compromise wire \
request to finance staff, a payroll-redirect to HR, a credential-reset lure to a \
new hire, an invoice-approval to an executive, an IP-exfiltration pretext to an \
engineer).

The sender address MUST be a synthetic look-alike under a .example domain (e.g. a \
cousin domain of the company's own example domain). Do NOT impersonate a real brand \
or real person.

Output a single JSON object with exactly these keys: scenario, pretext, \
impersonated_role, sender_display, sender_address, subject, body, call_to_action, \
urgency (low|medium|high), personalization_fields (the profile facts you used). \
Output JSON only, no prose."""


def build_email_user_prompt(profile: dict[str, Any], org: dict[str, Any]) -> str:
    return (
        "Target profile:\n"
        + json.dumps(profile, ensure_ascii=False, indent=2)
        + "\n\nCompany:\n"
        + json.dumps(
            {k: org[k] for k in ("name", "domain", "industry", "size")},
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nReturn the spear-email JSON object now."
    )


# ---------------------------------------------------------------------------
# Few-shot assembly
# ---------------------------------------------------------------------------

def _seed_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "seeds"


def load_seed_profiles() -> list[dict[str, Any]]:
    from .schema import read_jsonl
    return read_jsonl(_seed_dir() / "seed_profiles.jsonl")


def load_seed_emails() -> list[dict[str, Any]]:
    from .schema import read_jsonl
    return read_jsonl(_seed_dir() / "seed_emails.jsonl")


def profile_fewshot_messages(n: int = 5) -> list[dict[str, str]]:
    """User/assistant exemplar turns for profile generation (Haiku pass)."""
    msgs: list[dict[str, str]] = []
    for ex in load_seed_profiles()[:n]:
        spec = {
            "industry": ex["core"]["industry"],
            "career_stage": ex["core"]["career_stage"],
            "target_role": ex["core"]["target_role"],
            "company_size": ex.get("_company_size", "Medium"),
        }
        org = ex.get("_org", {})
        msgs.append({"role": "user", "content": build_profile_user_prompt(spec, org)})
        msgs.append({
            "role": "assistant",
            "content": json.dumps(
                {k: ex[k] for k in ("core", "public", "private", "behavior")},
                ensure_ascii=False,
            ),
        })
    return msgs


def email_fewshot_messages(n: int = 5) -> list[dict[str, str]]:
    """User/assistant exemplar turns for email generation (Haiku pass)."""
    msgs: list[dict[str, str]] = []
    emails = load_seed_emails()[:n]
    for ex in emails:
        profile = ex.get("_profile", {})
        org = ex.get("_org", {})
        msgs.append({"role": "user", "content": build_email_user_prompt(profile, org)})
        payload = {
            k: ex[k]
            for k in (
                "scenario", "pretext", "impersonated_role", "sender_display",
                "sender_address", "subject", "body", "call_to_action",
                "urgency", "personalization_fields",
            )
        }
        msgs.append({"role": "assistant", "content": json.dumps(payload, ensure_ascii=False)})
    return msgs
