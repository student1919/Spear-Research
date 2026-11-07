"""Generation dimensions for synthetic profiles.

These enumerate the sampling space described in Profiles.md. The orchestrator
samples a point in this space per profile (so the resulting histograms are a
property of these weights, independent of which generation backend realizes the
profile text). Weights are plausible spear-phishing target skews, not uniform;
they are declared here so the distribution is auditable and reproducible.
"""

from __future__ import annotations

# --- Profiles.md axes -------------------------------------------------------

INDUSTRIES = ["Finance", "Healthcare", "Tech", "Government", "Education"]

CAREER_STAGES = ["Student", "Entry Level", "Mid Level", "High Level", "Executive"]

COMPANY_SIZES = ["Small", "Medium", "Large"]

# Prime target archetypes (Profiles.md "Prime Targets"), kept as short slugs.
TARGET_ROLES = [
    "Executive / senior leader",
    "Finance / accounting",
    "HR / payroll",
    "IT admin / help desk",
    "Executive assistant",
    "Engineer / researcher (valuable data)",
    "Legal / compliance",
    "Government / defense personnel",
    "Journalist / activist / political",
    "New hire",
]

# --- Sampling weights (auditable, non-uniform) ------------------------------
# Rationale captured inline so the histogram shape is explainable.

INDUSTRY_WEIGHTS = {
    "Finance": 0.26,     # heavily targeted (BEC, wire fraud)
    "Tech": 0.24,        # IP, credentials, broad access
    "Healthcare": 0.20,  # PHI, payroll
    "Government": 0.16,  # espionage-focused
    "Education": 0.14,   # lower but non-trivial
}

CAREER_STAGE_WEIGHTS = {
    "Student": 0.08,
    "Entry Level": 0.22,
    "Mid Level": 0.30,
    "High Level": 0.24,
    "Executive": 0.16,
}

# Smaller orgs lack dedicated security staff (Profiles.md), larger hold more
# money/data; attacker interest spreads across all three.
COMPANY_SIZE_WEIGHTS = {
    "Small": 0.34,
    "Medium": 0.36,
    "Large": 0.30,
}

ROLE_WEIGHTS = {
    "Executive / senior leader": 0.15,
    "Finance / accounting": 0.16,
    "HR / payroll": 0.11,
    "IT admin / help desk": 0.12,
    "Executive assistant": 0.07,
    "Engineer / researcher (valuable data)": 0.13,
    "Legal / compliance": 0.07,
    "Government / defense personnel": 0.07,
    "Journalist / activist / political": 0.04,
    "New hire": 0.08,
}

# Roles that are only coherent within certain industries. When a sampled
# (industry, role) pair is incoherent the sampler resamples the role.
ROLE_INDUSTRY_CONSTRAINTS = {
    "Government / defense personnel": {"Government"},
    "Journalist / activist / political": {"Government", "Education"},
}

# Career stage must be compatible with the role (an "Executive assistant" is not
# an Executive; a "Student" is not a senior leader).
ROLE_STAGE_CONSTRAINTS = {
    "Executive / senior leader": {"High Level", "Executive"},
    "Legal / compliance": {"Mid Level", "High Level", "Executive"},
    "Executive assistant": {"Entry Level", "Mid Level"},
    "New hire": {"Student", "Entry Level", "Mid Level"},
}


def all_axes() -> dict[str, list[str]]:
    """Ordered axis -> categories, used to label histograms consistently."""
    return {
        "industry": INDUSTRIES,
        "career_stage": CAREER_STAGES,
        "company_size": COMPANY_SIZES,
        "target_role": TARGET_ROLES,
    }
