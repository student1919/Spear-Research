"""Generation backends behind one interface (v2 pipeline).

Every backend exposes:
    realize_profile(spec, org, post_slots, extra="") -> narrative JSON (src/prompts_v2.py schema)
    realize_email(profile, org, extra="")            -> spear-email JSON (EMAIL_KEYS)

AnthropicBackend  -- real Claude calls (claude-sonnet-5-5 by default).
LiveHaikuBackend  -- real Claude Haiku calls (claude-haiku-5-5, low effort).
GeminiBackend     -- real Gemini calls, 3.5 Flash-Lite with a 3.1 fallback.
LocalBackend      -- no API; composes text from src/pools.py so the full pipeline can be
                     dry-run offline. Its text is not LLM output.

`extra` is appended to the user prompt (used for "fix these violations" retries).
"""

from __future__ import annotations

import json
import random
import re
from typing import Any

from . import pools
from .prompts_v2 import (EMAIL_V2_SYSTEM, PROFILE_V2_SYSTEM, PRIOR_JOB_BULLETS, CURRENT_JOB_BULLETS,
                         RESUME_MIN_WORDS, RESUME_TARGET_WORDS, build_email_v2_user_prompt,
                         build_profile_v2_user_prompt)

SEED_MODEL = "claude-sonnet-5-5"
BULK_MODEL = "claude-haiku-5-5"

# Gemini: primary model, with a fallback used if the primary is unavailable.
GEMINI_PRIMARY = "gemini-3.5-flash-lite"
GEMINI_FALLBACK = "gemini-3.1-flash-lite"

# Output budgets. The profile JSON carries a ~500-word resume (~700 tokens) plus posts and the
# private/behavior sections.
PROFILE_MAX_TOKENS = 8192
EMAIL_MAX_TOKENS = 2048


def _extract_json(text: str) -> dict[str, Any]:
    """Pull a JSON object out of a model response (tolerant of code fences)."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"no JSON object in model output: {text[:200]!r}")
    return json.loads(text[start : end + 1])


class _PromptedBackend:
    """Shared prompt plumbing; subclasses implement `_complete(system, user, max_tokens) -> str`."""

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        raise NotImplementedError

    def realize_profile(self, spec, org, post_slots, extra: str = "") -> dict[str, Any]:
        user = build_profile_v2_user_prompt(spec, org, post_slots) + extra
        return _extract_json(self._complete(PROFILE_V2_SYSTEM, user, PROFILE_MAX_TOKENS))

    def realize_email(self, profile, org, extra: str = "") -> dict[str, Any]:
        user = build_email_v2_user_prompt(profile, org) + extra
        return _extract_json(self._complete(EMAIL_V2_SYSTEM, user, EMAIL_MAX_TOKENS))


# ---------------------------------------------------------------------------
# Anthropic backends
# ---------------------------------------------------------------------------

class AnthropicBackend(_PromptedBackend):
    """One real Claude call per generation. The zero-arg Anthropic() client resolves
    credentials from ANTHROPIC_API_KEY or an `ant auth login` profile."""

    model = SEED_MODEL
    effort: str | None = None

    def __init__(self, api_key: str | None = None, model: str | None = None, effort: str | None = None):
        import anthropic  # lazy: only needed for the live path

        self.client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
        self.model = model or self.model
        self.effort = effort or self.effort
        self.last_usage: dict | None = None  # token counts from the most recent call

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        kwargs: dict[str, Any] = {}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        resp = self.client.messages.create(
            model=self.model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}], **kwargs,
        )
        u = getattr(resp, "usage", None)
        self.last_usage = {
            "input_tokens": getattr(u, "input_tokens", None),
            "output_tokens": getattr(u, "output_tokens", None),
            "model": getattr(resp, "model", self.model),
        }
        return "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")


class ClaudeCLIBackend(_PromptedBackend):
    """Claude through the logged-in `claude` CLI (`claude -p`), so no ANTHROPIC_API_KEY is needed.

    Each generation is one headless prompt with the system prompt replaced, all tools disabled, no
    session persisted, and a scratch working directory so no project instructions leak in.
    """

    model = SEED_MODEL

    def __init__(self, model: str | None = None, effort: str | None = None, timeout: int = 600):
        import shutil
        import tempfile

        if not shutil.which("claude"):
            raise RuntimeError("the `claude` CLI is not on PATH")
        self.model = model or self.model
        self.effort = effort
        self.timeout = timeout
        self.cwd = tempfile.mkdtemp(prefix="claude_cli_")
        self.last_usage: dict | None = None

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        import subprocess

        cmd = ["claude", "-p", "--model", self.model, "--system-prompt", system, "--tools", "",
               "--disable-slash-commands", "--no-session-persistence", "--setting-sources", "",
               "--output-format", "json"]
        if self.effort:
            cmd += ["--effort", self.effort]
        r = subprocess.run(cmd, input=user, capture_output=True, text=True, cwd=self.cwd, timeout=self.timeout)
        if r.returncode != 0:
            raise RuntimeError(f"claude CLI failed ({r.returncode}): {(r.stderr or r.stdout)[:300]}")
        out = json.loads(r.stdout)
        if out.get("is_error"):
            raise RuntimeError(f"claude CLI error: {str(out.get('result'))[:300]}")
        u = out.get("usage") or {}
        self.last_usage = {"input_tokens": u.get("input_tokens"), "output_tokens": u.get("output_tokens"),
                           "model": self.model}
        return out.get("result") or ""


class LiveHaikuBackend(AnthropicBackend):
    """Claude Haiku (`claude-haiku-5-5`) at low effort."""

    model = BULK_MODEL
    effort = "low"


# ---------------------------------------------------------------------------
# Gemini backend
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


class GeminiBackend(_PromptedBackend):
    """One real `generate_content` call per generation. Tries `GEMINI_PRIMARY` first and
    falls back to `GEMINI_FALLBACK` if the primary is unavailable for any reason; once the
    primary fails it is skipped for the session.
    """

    primary = GEMINI_PRIMARY
    fallback = GEMINI_FALLBACK

    def __init__(self):
        from google import genai

        _load_cred_env()                 # loads GEMINI_API_KEY from cred.env
        self.client = genai.Client()     # picks up GEMINI_API_KEY from the environment
        self._skip_primary = False
        self.last_usage: dict | None = None

    def _complete(self, system: str, user: str, max_tokens: int) -> str:
        # max_tokens is not forwarded: Gemini's default output limit applies (as before).
        cfg = {"system_instruction": system, "response_mime_type": "application/json"}
        contents = [{"role": "user", "parts": [{"text": user}]}]
        order = [self.fallback] if self._skip_primary else [self.primary, self.fallback]
        errors = []
        for model in order:
            try:
                resp = self.client.models.generate_content(model=model, config=cfg, contents=contents)
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


# ---------------------------------------------------------------------------
# Local backend (no API) -- composes from pools.py
# ---------------------------------------------------------------------------

def _tidy(s: str) -> str:
    """Collapse article doubling introduced by article-prefixed project names."""
    return re.sub(r"\bthe the\b", "the", s, flags=re.IGNORECASE)


# Population role names -> the role keys used in pools.py.
_POOL_ROLE = {"Engineer / researcher": "Engineer / researcher (valuable data)",
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
_METRICS = [
    "cutting turnaround time by {p}% over {q} quarters",
    "saving an estimated ${k},000 per year",
    "raising on-time completion from {a}% to {b}%",
    "covering {n} teams and roughly {m} internal stakeholders",
    "reducing open backlog items by {p}% within {q} months",
    "handling {m} requests per month with a satisfaction score of {b}%",
]
_CONTEXT = [
    "while coordinating weekly with finance, legal and operations partners so that reporting stayed consistent "
    "across every affected group and leadership saw one set of figures",
    "and documented the process in a shared playbook that new staff used during onboarding, which kept handoffs "
    "predictable when priorities or owners changed mid-cycle",
    "working through competing deadlines by agreeing priorities with the manager up front and sending a short "
    "written status update to stakeholders at the end of each week",
    "and presented the results at the quarterly review, answering follow-up questions from department heads "
    "and turning their feedback into the next round of planned improvements",
]
_DEGREE = {"juris doctor": "J.D.", "doctoral": "Ph.D.", "master": "Master's degree", "bachelor": "B.S./B.A.",
           "associate": "Associate degree", "some college": "Coursework"}


class LocalBackend:
    """Offline composition for dry runs. Not LLM text: used only to exercise the pipeline."""

    model = "local"

    def __init__(self, rng: random.Random):
        self.rng = rng

    def _bullet(self, fragment: str) -> str:
        r = self.rng
        metric = r.choice(_METRICS).format(p=r.randint(8, 45), q=r.randint(2, 6), k=r.randint(15, 240),
                                           a=r.randint(55, 80), b=r.randint(85, 98), n=r.randint(2, 9),
                                           m=r.randint(20, 400))
        return _tidy(f"{fragment.rstrip('.')}, {metric}, {r.choice(_CONTEXT)}.")

    def _resume(self, spec, role, proj, majors) -> dict[str, Any]:
        r = self.rng
        frags = [b.replace("{n}", str(r.choice([3, 6, 12, 40]))).replace("{proj}", proj)
                 for b in pools.ROLE_RESUME[role]]
        edu = []
        for e, m in zip(spec["education"], majors):
            yr = e.get("grad_year") or e.get("expected_grad_year")
            edu.append(f"{_DEGREE.get(e['level'], e['level'])} in {m}, {e['institution']['name']} ({yr}); "
                       f"{r.choice(['3.4', '3.6', '3.7', '3.8'])} GPA, top {r.randint(5, 30)}% of the cohort, "
                       f"{r.randint(2, 4)}-course capstone sequence.")
        cur = [self._bullet(r.choice(frags)) for _ in range(CURRENT_JOB_BULLETS[0])]
        prior = [[self._bullet(r.choice(frags))] for _ in spec["career_skeleton"]]

        def words():
            return sum(len(b.split()) for b in cur + edu + [x for j in prior for x in j])

        goal = (RESUME_MIN_WORDS + RESUME_TARGET_WORDS) // 2
        while words() < goal and len(cur) < CURRENT_JOB_BULLETS[1]:
            cur.append(self._bullet(r.choice(frags)))
        k = 0
        while words() < goal and prior and any(len(j) < PRIOR_JOB_BULLETS[1] for j in prior):
            if len(prior[k % len(prior)]) < PRIOR_JOB_BULLETS[1]:
                prior[k % len(prior)].append(self._bullet(r.choice(frags)))
            k += 1
        return {"current_job": cur, "prior_jobs": prior, "education": edu}

    def realize_profile(self, spec, org, post_slots, extra: str = "") -> dict[str, Any]:
        r = self.rng
        role = _POOL_ROLE.get(spec["target_role"], spec["target_role"])
        first, last = spec["full_name"].split(" ", 1)
        majors = [r.choice(_MAJORS.get(e["field"], [e["field"].replace("_", " ").title()])) for e in spec["education"]]
        proj = r.choice(pools.ROLE_PROJECTS[role])
        hist = [r.choice(["Associate", "Specialist", "Analyst", "Coordinator", "Senior Analyst"])
                for _ in spec["career_skeleton"]]
        styles = [f"{first.lower()}{last.lower()[:4]}", f"{first[0].lower()}.{last.lower()}",
                  f"{first.lower()}_{last.lower()}{r.randint(1, 99)}", f"{last.lower()}{first[0].lower()}"]
        social = {p: r.choice(styles) for p in spec["presence"]["platforms"]}
        posts = [{"text": _tidy(r.choice(pools.POST_TEMPLATES).format(
            proj=proj, industry=spec["industry"], company=org["name"], role_kw=role.split("/")[0].strip().lower()))}
            for _ in post_slots]
        boss = spec["colleagues"][0]["name"] if spec["colleagues"] else "the department head"
        p = spec["susceptibility"]["p_click_simulated_phish"]
        traits = r.sample(pools.TRAITS, k=3)
        if p > 0.35 and "quick to click familiar links" not in traits:
            traits.append("quick to click familiar links")
        return {
            "public": {"resume": self._resume(spec, role, proj, majors), "career_titles": hist,
                       "education_majors": majors, "social_presence": social, "posts": posts,
                       "personal_website": f"https://{first.lower()}{last.lower()}.example"
                       if spec["presence"]["has_personal_website"] else None},
            "private": {"projects": r.sample(pools.ROLE_PROJECTS[role], k=min(2, len(pools.ROLE_PROJECTS[role]))),
                        "real_details": [f"Reports to {boss}.", f"Day-to-day owner of {proj}."],
                        "sensitive_access": list(pools.ROLE_ACCESS[role])},
            "behavior": {"traits": traits, "response_tendencies": dict(r.sample(pools.RESPONSE_CUES, k=2))},
        }

    def realize_email(self, profile, org, extra: str = "") -> dict[str, Any]:
        r = self.rng
        core = profile["core"]
        role = _POOL_ROLE.get(core["target_role"], core["target_role"])
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
        link = f"https://{look_alike}/verify?u={first.lower()}"
        amount = r.choice(["18,400", "42,750", "9,980", "126,500"])
        body = _tidy(pools.BODY_TEMPLATES[body_key].format(
            first=first, sender=sender_display, company=org["name"], proj=proj, link=link, amount=amount))
        cta = {
            "wire": "process a wire transfer", "invoice": "approve via the link",
            "payroll": "update banking details via the link", "cred": "confirm credentials via the link",
            "errand": "reply to receive task details", "exfil": "upload documents via the link",
            "doc": "open and acknowledge via the link", "source": "open the secure drop via the link",
        }[body_key]
        used = ["target_role", "projects"] + (["project name"] if "{proj}" in subject_t else [])
        return {
            "scenario": name_s, "pretext": pretext, "impersonated_role": imp_role,
            "sender_display": sender_display,
            "sender_address": f"{imp_role.split()[0].lower()}@{look_alike}",
            "subject": _tidy(subject_t.format(proj=proj)), "body": body, "call_to_action": cta,
            "urgency": urgency, "personalization_fields": used,
        }


def make_backend(name: str, rng: random.Random | None = None):
    """Backend by CLI name: gemini | anthropic | claude-cli | haiku | local."""
    if name == "gemini":
        return GeminiBackend()
    if name == "anthropic":
        return AnthropicBackend()
    if name == "haiku":
        return LiveHaikuBackend()
    if name == "claude-cli":
        return ClaudeCLIBackend()
    if name == "local":
        return LocalBackend(rng or random.Random())
    raise ValueError(f"unknown backend {name!r}")
