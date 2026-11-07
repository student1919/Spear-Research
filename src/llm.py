"""Generation backends behind one interface.

AnthropicBackend  -- real Claude calls (Sonnet seed pass, Haiku bulk pass).
                     Ready to run once ANTHROPIC_API_KEY / `ant auth login` is set
                     and `anthropic` is installed; nothing downstream changes.
LocalBackend      -- no API; composes profiles/emails from src/pools.py so the
                     initial run, DB, histograms, and report all work now.

Both return plain dicts; the orchestrator assigns ids and wraps them into the
dataclasses in schema.py.
"""

from __future__ import annotations

import json
import random
import re
from typing import Any

from . import pools

# Model ids per the plan (current-generation Sonnet / Haiku).
SEED_MODEL = "claude-sonnet-5-5"
BULK_MODEL = "claude-haiku-5-5"

# Gemini: primary model, with a fallback used if the primary is unavailable.
GEMINI_PRIMARY = "gemini-3.5-flash-lite"
GEMINI_FALLBACK = "gemini-3.1-flash-lite"

# Security awareness implied by career stage (newer/junior staff less aware).
STAGE_SECURITY = {
    "Student": "low",
    "Entry Level": "low",
    "Mid Level": "medium",
    "High Level": "medium",
    "Executive": "high",
}


# ---------------------------------------------------------------------------
# Anthropic backend (real API; inert until a key is present)
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a model response (tolerant of code fences)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(text[start : end + 1])


class AnthropicBackend:
    def __init__(self, api_key: str | None = None):
        import anthropic  # imported lazily so LocalBackend works without the package

        # Zero-arg client also picks up `ant auth login` profiles; see claude-api.
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def _complete(
        self,
        system: str,
        fewshot: list[dict[str, str]],
        user: str,
        model: str,
        max_tokens: int,
    ) -> str:
        resp = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[*fewshot, {"role": "user", "content": user}],
        )
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    def realize_profile(self, spec, org, model, fewshot) -> dict[str, Any]:
        from .prompts import PROFILE_SYSTEM, build_profile_user_prompt

        out = self._complete(
            PROFILE_SYSTEM, fewshot, build_profile_user_prompt(spec, org), model, 2048
        )
        obj = _extract_json(out)
        # Fold the given dimensions back into core (model is not asked to echo them).
        obj.setdefault("core", {}).update(
            industry=spec["industry"],
            career_stage=spec["career_stage"],
            target_role=spec["target_role"],
        )
        return obj

    def realize_email(self, profile, org, model, fewshot) -> dict[str, Any]:
        from .prompts import EMAIL_SYSTEM, build_email_user_prompt

        out = self._complete(
            EMAIL_SYSTEM, fewshot, build_email_user_prompt(profile, org), model, 1536
        )
        return _extract_json(out)


# ---------------------------------------------------------------------------
# Live Haiku backend (true API) -- one real Claude Haiku call per generation
# ---------------------------------------------------------------------------

class LiveHaikuBackend:
    """True live-API backend: each profile/email is a single real call to Claude
    Haiku (`claude-haiku-5-5`). Unlike AnthropicBackend's two-pass design, there is
    no Sonnet seed pass -- this exists to trigger a live prompt against the user's
    own Haiku. Few-shot exemplars (from seeds/) are passed through when provided.

    The zero-arg Anthropic() client resolves credentials from ANTHROPIC_API_KEY or
    an `ant auth login` profile; construction raises if none are configured.
    """

    model = BULK_MODEL  # claude-haiku-5-5

    def __init__(self, api_key: str | None = None, effort: str = "low"):
        import anthropic  # lazy: only needed for the live path

        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.effort = effort
        self.last_usage: dict | None = None  # token counts from the most recent call

    def _complete(self, system, fewshot, user, max_tokens) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[*(fewshot or []), {"role": "user", "content": user}],
            output_config={"effort": self.effort},
        )
        u = getattr(resp, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
            "model": getattr(resp, "model", self.model),
        }
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")

    def realize_profile(self, spec, org, model=None, fewshot=None) -> dict[str, Any]:
        from .prompts import PROFILE_SYSTEM, build_profile_user_prompt

        text = self._complete(
            PROFILE_SYSTEM, fewshot, build_profile_user_prompt(spec, org), 3072
        )
        obj = _extract_json(text)
        obj.setdefault("core", {}).update(
            industry=spec["industry"],
            career_stage=spec["career_stage"],
            target_role=spec["target_role"],
        )
        return obj

    def realize_email(self, profile, org, model=None, fewshot=None) -> dict[str, Any]:
        from .prompts import EMAIL_SYSTEM, build_email_user_prompt

        text = self._complete(
            EMAIL_SYSTEM, fewshot, build_email_user_prompt(profile, org), 2048
        )
        return _extract_json(text)


# ---------------------------------------------------------------------------
# Gemini backend (true API) -- one real Gemini call per generation, 3.5 -> 3.1
# ---------------------------------------------------------------------------

def _load_cred_env() -> None:
    """Make GEMINI_API_KEY available from cred.env without exposing its contents.

    Uses python-dotenv to load the file into the process environment; the key is
    never read or printed by this code.
    """
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    from pathlib import Path
    for p in (Path(__file__).resolve().parent.parent / "cred.env", Path("cred.env")):
        if p.exists():
            load_dotenv(p, override=False)
            return


class GeminiBackend:
    """True live-API backend over Google Gemini. Each profile/email is one real
    `generate_content` call. Tries `GEMINI_PRIMARY` (gemini-3.5-flash-lite) first and
    falls back to `GEMINI_FALLBACK` (gemini-3.1-flash-lite) if the primary is
    unavailable for any reason; once the primary fails it is skipped for the session.
    """

    primary = GEMINI_PRIMARY
    fallback = GEMINI_FALLBACK

    def __init__(self):
        from google import genai

        _load_cred_env()                 # loads GEMINI_API_KEY from cred.env
        self.client = genai.Client()     # picks up GEMINI_API_KEY from the environment
        self._skip_primary = False
        self.last_usage: dict | None = None

    def _gen(self, system: str, fewshot, user: str) -> str:
        contents = []
        for m in (fewshot or []):
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        contents.append({"role": "user", "parts": [{"text": user}]})
        cfg = {"system_instruction": system, "response_mime_type": "application/json"}

        order = [self.fallback] if self._skip_primary else [self.primary, self.fallback]
        errors = []
        for model in order:
            try:
                resp = self.client.models.generate_content(
                    model=model, config=cfg, contents=contents
                )
            except Exception as e:  # unavailable "for any reason" -> try the fallback
                errors.append(f"{model}: {e}")
                if model == self.primary:
                    self._skip_primary = True
                continue
            if model == self.fallback:
                self._skip_primary = True
            u = getattr(resp, "usage_metadata", None)
            self.last_usage = {
                "model": model,
                "input_tokens": getattr(u, "prompt_token_count", None),
                "output_tokens": getattr(u, "candidates_token_count", None),
            }
            return resp.text
        raise RuntimeError("All Gemini models failed -> " + " | ".join(errors))

    def realize_profile(self, spec, org, model=None, fewshot=None) -> dict[str, Any]:
        from .prompts import PROFILE_SYSTEM, build_profile_user_prompt

        text = self._gen(PROFILE_SYSTEM, fewshot, build_profile_user_prompt(spec, org))
        obj = _extract_json(text)
        obj.setdefault("core", {}).update(
            industry=spec["industry"],
            career_stage=spec["career_stage"],
            target_role=spec["target_role"],
        )
        return obj

    def realize_email(self, profile, org, model=None, fewshot=None) -> dict[str, Any]:
        from .prompts import EMAIL_SYSTEM, build_email_user_prompt

        text = self._gen(EMAIL_SYSTEM, fewshot, build_email_user_prompt(profile, org))
        return _extract_json(text)


# ---------------------------------------------------------------------------
# Local backend (no API) -- composes from pools.py
# ---------------------------------------------------------------------------

def _tidy(s: str) -> str:
    """Collapse article doubling introduced by article-prefixed project names."""
    return re.sub(r"\bthe the\b", "the", s, flags=re.IGNORECASE)


class LocalBackend:
    def __init__(self, rng: random.Random):
        self.rng = rng

    # -- profiles --
    def realize_profile(self, spec, org, model=None, fewshot=None) -> dict[str, Any]:
        r = self.rng
        role = spec["target_role"]
        stage = spec["career_stage"]
        industry = spec["industry"]

        first, last = r.choice(pools.FIRST_NAMES), r.choice(pools.LAST_NAMES)
        name = f"{first} {last}"
        prefix = pools.STAGE_PREFIX[stage]
        title = f"{prefix} {pools.ROLE_BASE_TITLE[role]}".strip()
        domain = org["domain"]
        email = f"{first.lower()}.{last.lower()}@{domain}"
        location = org.get("hq_city") or r.choice(pools.CITIES)

        proj = r.choice(pools.ROLE_PROJECTS[role])
        bullets = [
            _tidy(b.replace("{n}", str(r.choice([3, 6, 12, 40, 120]))).replace("{proj}", proj))
            for b in r.sample(pools.ROLE_RESUME[role], k=min(3, len(pools.ROLE_RESUME[role])))
        ]

        footprint = {"Executive": "high", "High Level": "high"}.get(
            stage, r.choice(["low", "medium"])
        )
        platforms = r.sample(pools.SOCIAL_PLATFORMS, k=r.choice([1, 2]))
        social = {p: f"{first.lower()}{last.lower()[:3]}" for p in platforms}

        role_kw = role.split("/")[0].strip().lower()
        posts = [
            {
                "date": f"2026-{r.randint(1, 9):02d}-{r.randint(1, 28):02d}",
                "text": _tidy(t.format(proj=proj, industry=industry, company=org["name"], role_kw=role_kw)),
            }
            for t in r.sample(pools.POST_TEMPLATES, k=r.choice([2, 3]))
        ]
        website = (
            f"https://{first.lower()}{last.lower()}.example" if r.random() < 0.3 else None
        )

        colleagues = [
            {
                "name": f"{r.choice(pools.FIRST_NAMES)} {r.choice(pools.LAST_NAMES)}",
                "relation": rel,
            }
            for rel in r.sample(
                ["manager", "teammate", "direct report", "cross-team partner"],
                k=r.choice([2, 3]),
            )
        ]
        real_details = [
            f"Actually leads {proj} day to day, though the resume lists it as a contribution.",
            f"Reports into {colleagues[0]['name']}.",
        ]
        access = pools.ROLE_ACCESS[role]

        sec = STAGE_SECURITY.get(stage, "medium")
        traits = r.sample(pools.TRAITS, k=r.choice([3, 4]))
        cues = dict(r.sample(pools.RESPONSE_CUES, k=r.choice([2, 3])))
        busy = {"Executive": "high", "High Level": "high", "Student": "low"}.get(
            stage, r.choice(["medium", "high"])
        )

        return {
            "core": {
                "full_name": name,
                "email": email,
                "industry": industry,
                "career_stage": stage,
                "target_role": role,
                "title": title,
                "location": location,
            },
            "public": {
                "resume_bullets": bullets,
                "social_presence": social,
                "footprint_level": footprint,
                "posts": posts,
                "personal_website": website,
            },
            "private": {
                "projects": r.sample(
                    pools.ROLE_PROJECTS[role], k=min(2, len(pools.ROLE_PROJECTS[role]))
                ),
                "colleagues": colleagues,
                "real_details": real_details,
                "sensitive_access": list(access),
            },
            "behavior": {
                "traits": traits,
                "security_awareness": sec,
                "response_tendencies": cues,
                "busy_level": busy,
            },
        }

    # -- emails --
    def realize_email(self, profile, org, model=None, fewshot=None) -> dict[str, Any]:
        r = self.rng
        core = profile["core"]
        role = core["target_role"]
        first = core["full_name"].split()[0]

        scenarios = pools.ROLE_SCENARIOS.get(
            role,
            [("Credential reset lure", "generic access lure", "IT Help Desk",
              "Action required on your account", "high", "cred")],
        )
        name_s, pretext, imp_role, subject_t, urgency, body_key = r.choice(scenarios)

        proj = (profile.get("private", {}).get("projects") or ["an active project"])[0]
        base, tld = org["domain"].rsplit(".", 1)
        look_alike = f"{base}-{r.choice(['corp', 'inc', 'hr', 'it', 'billing'])}.{tld}"
        sender_display = f"{imp_role}, {org['name']}"
        sender_address = f"{imp_role.split()[0].lower()}@{look_alike}"
        link = f"https://{look_alike}/verify?u={first.lower()}"
        amount = r.choice(["18,400", "42,750", "9,980", "126,500"])

        body = _tidy(pools.BODY_TEMPLATES[body_key].format(
            first=first, sender=sender_display, company=org["name"],
            proj=proj, link=link, amount=amount,
        ))
        subject = _tidy(subject_t.format(proj=proj))
        cta = {
            "wire": "process a wire transfer",
            "invoice": "approve via the link",
            "payroll": "update banking details via the link",
            "cred": "confirm credentials via the link",
            "errand": "reply to receive task details",
            "exfil": "upload documents via the link",
            "doc": "open and acknowledge via the link",
            "source": "open the secure drop via the link",
        }[body_key]

        used = ["target_role", "projects"]
        if "{proj}" in subject_t or "proj" in body_key:
            used.append("project name")
        return {
            "scenario": name_s,
            "pretext": pretext,
            "impersonated_role": imp_role,
            "sender_display": sender_display,
            "sender_address": sender_address,
            "subject": subject,
            "body": body,
            "call_to_action": cta,
            "urgency": urgency,
            "personalization_fields": used,
        }


# ---------------------------------------------------------------------------
# v2 profile realization (narrative only; the spec is fixed by src/population.py)
# ---------------------------------------------------------------------------

def _gemini_v2(self, spec, org, slots, extra=""):
    from .prompts_v2 import PROFILE_V2_SYSTEM, build_profile_v2_user_prompt
    return _extract_json(self._gen(PROFILE_V2_SYSTEM, [], build_profile_v2_user_prompt(spec, org, slots) + extra))


def _haiku_v2(self, spec, org, slots, extra=""):
    from .prompts_v2 import PROFILE_V2_SYSTEM, build_profile_v2_user_prompt
    return _extract_json(self._complete(PROFILE_V2_SYSTEM, [], build_profile_v2_user_prompt(spec, org, slots) + extra, 3072))


def _anthropic_v2(self, spec, org, slots, extra=""):
    from .prompts_v2 import PROFILE_V2_SYSTEM, build_profile_v2_user_prompt
    return _extract_json(self._complete(PROFILE_V2_SYSTEM, [], build_profile_v2_user_prompt(spec, org, slots) + extra,
                                        SEED_MODEL, 3072))


GeminiBackend.realize_profile_v2 = _gemini_v2
LiveHaikuBackend.realize_profile_v2 = _haiku_v2
AnthropicBackend.realize_profile_v2 = _anthropic_v2

_OLD_ROLE = {"Engineer / researcher": "Engineer / researcher (valuable data)",
             "Journalist / communications": "Journalist / activist / political"}
_MAJORS = {
    "business": ["Accounting", "Finance", "Business Administration", "Management", "Marketing"],
    "computing": ["Computer Science", "Information Systems", "Cybersecurity"],
    "engineering": ["Mechanical Engineering", "Electrical Engineering", "Industrial Engineering"],
    "health": ["Nursing", "Health Administration", "Public Health"],
    "education": ["Educational Leadership", "Curriculum and Instruction"],
    "law": ["Law"], "social_science": ["Economics", "Political Science", "Sociology"],
    "psychology": ["Psychology"], "biological": ["Biology", "Biochemistry"],
    "communication": ["Journalism", "Communications"], "public_admin": ["Public Administration"],
    "math_stat": ["Statistics", "Applied Mathematics"], "physical_science": ["Physics", "Chemistry"],
    "humanities": ["English", "History", "Liberal Arts"], "security_justice": ["Criminal Justice"],
}


def _local_v2(self, spec, org, slots, extra=""):
    """Offline composition for dry runs. Not LLM text: used only to exercise the pipeline."""
    r = self.rng
    role = _OLD_ROLE.get(spec["target_role"], spec["target_role"])
    first, last = spec["full_name"].split(" ", 1)
    majors = [r.choice(_MAJORS.get(e["field"], [e["field"].replace("_", " ").title()])) for e in spec["education"]]
    edu_bullets = []
    for e, m in zip(spec["education"], majors):
        yr = e.get("grad_year") or e.get("expected_grad_year")
        deg = {"juris doctor": "J.D.", "doctoral": "Ph.D.", "master": "Master's degree", "bachelor": "B.S./B.A.",
               "associate": "Associate degree", "some college": "Coursework"}.get(e["level"], e["level"])
        edu_bullets.append(f"{deg} in {m}, {e['institution']['name']} ({yr}).")
    proj = r.choice(pools.ROLE_PROJECTS[role])
    bullets = [_tidy(b.replace("{n}", str(r.choice([3, 6, 12, 40]))).replace("{proj}", proj))
               for b in r.sample(pools.ROLE_RESUME[role], k=min(2, len(pools.ROLE_RESUME[role])))] + edu_bullets
    hist = [r.choice(["Associate", "Specialist", "Analyst", "Coordinator", "Senior Analyst"])
            for _ in spec["career_skeleton"]]
    styles = [f"{first.lower()}{last.lower()[:4]}", f"{first[0].lower()}.{last.lower()}",
              f"{first.lower()}_{last.lower()}{r.randint(1, 99)}", f"{last.lower()}{first[0].lower()}"]
    social = {p: r.choice(styles) for p in spec["presence"]["platforms"]}
    posts = [{"text": _tidy(r.choice(pools.POST_TEMPLATES).format(
        proj=proj, industry=spec["industry"], company=org["name"], role_kw=role.split("/")[0].strip().lower()))}
        for _ in slots]
    boss = spec["colleagues"][0]["name"]
    p = spec["susceptibility"]["p_click_simulated_phish"]
    cues = dict(r.sample(pools.RESPONSE_CUES, k=2))
    return {
        "public": {"resume_bullets": bullets, "career_titles": hist, "education_majors": majors,
                   "social_presence": social, "posts": posts,
                   "personal_website": f"https://{first.lower()}{last.lower()}.example"
                   if spec["presence"]["has_personal_website"] else None},
        "private": {"projects": r.sample(pools.ROLE_PROJECTS[role], k=min(2, len(pools.ROLE_PROJECTS[role]))),
                    "real_details": [f"Reports to {boss}.", f"Day-to-day owner of {proj}."],
                    "sensitive_access": list(pools.ROLE_ACCESS[role])},
        "behavior": {"traits": r.sample(pools.TRAITS, k=3) + (["quick to click familiar links"] if p > 0.35 else []),
                     "response_tendencies": cues},
    }


LocalBackend.realize_profile_v2 = _local_v2
