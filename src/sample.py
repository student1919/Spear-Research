"""Reproducible dimension sampling for profiles and companies.

Companies are sampled first (industry + size), then profiles are allocated to
companies weighted by headcount so profiles aggregate by company (Profiles.md).
Role and career stage are sampled per profile and resampled until coherent with
the company's industry and with each other (config/dimensions.py constraints).
"""

from __future__ import annotations

import random
from typing import Any

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import dimensions as D  # noqa: E402


def _weighted(rng: random.Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


HEADCOUNT_BANDS = {"Small": (12, 80), "Medium": (120, 900), "Large": (1500, 40000)}


def make_org(rng: random.Random, industry: str, size: str, i: int = 0) -> dict[str, Any]:
    """Build one synthetic company for a given industry + size."""
    from . import pools

    prefixes, suffixes = pools.COMPANY_PARTS[industry]
    name = f"{rng.choice(prefixes)} {rng.choice(suffixes)}"
    slug = name.lower().replace(" ", "").replace(",", "")
    lo, hi = HEADCOUNT_BANDS[size]
    return {
        "org_id": f"org_{i:03d}",
        "name": name,
        "domain": f"{slug}.example",
        "industry": industry,
        "size": size,
        "headcount": rng.randint(lo, hi),
        "hq_city": rng.choice(pools.CITIES),
        "founded": rng.randint(1975, 2021),
        "org_chart": [
            {"title": "Chief Executive", "reports_to": ""},
            {"title": "Director", "reports_to": "Chief Executive"},
            {"title": "Manager", "reports_to": "Director"},
        ],
        "synthetic": True,
    }


def build_orgs(rng: random.Random, n: int) -> list[dict[str, Any]]:
    orgs: list[dict[str, Any]] = []
    for i in range(n):
        industry = _weighted(rng, D.INDUSTRY_WEIGHTS)
        size = _weighted(rng, D.COMPANY_SIZE_WEIGHTS)
        orgs.append(make_org(rng, industry, size, i))
    return orgs


def _coherent_role(rng: random.Random, industry: str) -> str:
    while True:
        role = _weighted(rng, D.ROLE_WEIGHTS)
        allowed = D.ROLE_INDUSTRY_CONSTRAINTS.get(role)
        if allowed is None or industry in allowed:
            return role


def _coherent_stage(rng: random.Random, role: str) -> str:
    allowed = D.ROLE_STAGE_CONSTRAINTS.get(role)
    while True:
        stage = _weighted(rng, D.CAREER_STAGE_WEIGHTS)
        if allowed is None or stage in allowed:
            return stage


# Per-company profile-allocation weight by size tier. Larger companies host more
# profiles, but the range is compressed (not raw headcount) so small companies are
# not starved to zero -- company size stays a meaningful histogram axis.
SIZE_ALLOC_WEIGHT = {"Small": 1.0, "Medium": 2.4, "Large": 4.2}


def sample_specs(
    rng: random.Random, orgs: list[dict[str, Any]], n_profiles: int
) -> list[dict[str, Any]]:
    """One spec per profile, each tied to an org (weighted by size tier)."""
    weights = [SIZE_ALLOC_WEIGHT[o["size"]] for o in orgs]
    specs: list[dict[str, Any]] = []
    for _ in range(n_profiles):
        org = rng.choices(orgs, weights=weights, k=1)[0]
        industry = org["industry"]
        role = _coherent_role(rng, industry)
        stage = _coherent_stage(rng, role)
        specs.append({
            "org_id": org["org_id"],
            "industry": industry,
            "company_size": org["size"],
            "career_stage": stage,
            "target_role": role,
        })
    return specs
