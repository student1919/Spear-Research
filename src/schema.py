"""Record schemas for the synthetic dataset (Profiles.md layout).

One dataclass per JSONL file. Everything is linked by ``profile_id`` (orgs by
``org_id``). ``asdict``/JSONL helpers keep the on-disk format stable regardless
of which backend produced the content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Iterable


# --- Companies --------------------------------------------------------------

@dataclass
class Org:
    org_id: str
    name: str
    domain: str              # synthetic; always under an *.example zone
    industry: str
    size: str                # Small | Medium | Large
    headcount: int
    hq_city: str
    founded: int
    org_chart: list[dict[str, str]]  # [{title, reports_to}] skeleton
    synthetic: bool = True
    size_class: str = ""     # v2: SUSB enterprise-size class (<20, 20-99, 100-499, 500-4999, 5000+)


# --- Profile pieces (one file each) -----------------------------------------

@dataclass
class ProfileCore:
    profile_id: str
    org_id: str
    full_name: str
    email: str
    industry: str
    career_stage: str
    target_role: str
    title: str
    location: str
    # v2 (empirically sampled; zero/empty in v1 data)
    age: int = 0
    gender: str = ""
    birth_year: int = 0
    tenure_years: float = 0.0
    years_experience: float = 0.0
    is_new_hire: bool = False
    highest_education: str = ""
    size_class: str = ""


@dataclass
class ProfilePublic:
    profile_id: str
    resume_bullets: list[str]
    social_presence: dict[str, str]     # platform -> handle/url
    footprint_level: str                # low | medium | high
    posts: list[dict[str, str]]         # [{date, text}]
    personal_website: str | None
    # v2
    education: list[dict] = field(default_factory=list)        # sampled: level, field, institution, grad_year
    career_history: list[dict] = field(default_factory=list)   # prior roles (fictional employers)
    platform_activity: dict[str, float] = field(default_factory=dict)   # platform -> public posts per month
    public_posts_per_month: float = 0.0
    footprint_score: float = 0.0


@dataclass
class ProfilePrivate:
    profile_id: str
    projects: list[str]
    colleagues: list[dict[str, str]]    # [{name, relation}]
    real_details: list[str]             # ground truth behind resume lines
    sensitive_access: list[str]         # what this person can authorize/reach


@dataclass
class ProfileBehavior:
    profile_id: str
    traits: list[str]
    security_awareness: str             # low | medium | high
    response_tendencies: dict[str, str] # cue -> likely reaction
    busy_level: str                     # low | medium | high
    # v2 (numeric, sampled from calibrated distributions; categories above are derived from these)
    p_click_simulated_phish: float = 0.0
    received_security_training: bool = False
    email_checks_per_day: float = 0.0
    email_checks_per_computer_hour: float = 0.0
    emails_received_per_day: float = 0.0
    late_night_inbox: bool = False


@dataclass
class ProfileBundle:
    """Everything one generation call yields for a single person."""
    core: ProfileCore
    public: ProfilePublic
    private: ProfilePrivate
    behavior: ProfileBehavior


# --- Attack emails ----------------------------------------------------------

@dataclass
class AttackEmail:
    email_id: str
    profile_id: str
    org_id: str
    scenario: str                 # e.g. BEC wire transfer, credential reset
    pretext: str                  # one-line social-engineering premise
    impersonated_role: str        # who the sender claims to be
    sender_display: str
    sender_address: str           # synthetic look-alike under *.example
    subject: str
    body: str
    call_to_action: str
    urgency: str                  # low | medium | high
    personalization_fields: list[str]   # profile facts used in the email
    generator: str                # model id / backend that produced it
    synthetic: bool = True


# --- JSONL I/O --------------------------------------------------------------

def write_jsonl(path: str | Path, rows: Iterable[Any]) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            obj = row if isinstance(row, dict) else asdict(row)
            fh.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


# File names (Profiles.md "Profiles Organization + Creation").
FILES = {
    "orgs": "orgs.jsonl",
    "core": "profiles_core.jsonl",
    "public": "profiles_public.jsonl",
    "private": "profiles_private.jsonl",
    "behavior": "profiles_behavior.jsonl",
    "emails_attack": "emails_attack.jsonl",
}
