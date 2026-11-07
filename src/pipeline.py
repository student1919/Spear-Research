"""Two-stage generation orchestrator.

Stage A (seed pass): the first ``seed_count`` profiles/emails are produced by the
higher-capability model (Sonnet, `SEED_MODEL`) with no exemplars. Those outputs
are written to ``seeds/`` and become the few-shot exemplars for Stage B.

Stage B (bulk pass): the remainder are produced by Haiku (`BULK_MODEL`) conditioned
on the seed exemplars.

With LocalBackend the same structure runs offline (the seed items are composed
rather than Sonnet-written); swapping to AnthropicBackend makes the passes real
without changing this file.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from .llm import SEED_MODEL, BULK_MODEL, AnthropicBackend
from .prompts import build_profile_user_prompt, build_email_user_prompt
from .schema import (
    ProfileCore, ProfilePublic, ProfilePrivate, ProfileBehavior, ProfileBundle,
    AttackEmail,
)

SEED_DIR = Path(__file__).resolve().parent.parent / "seeds"


def _is_api(backend) -> bool:
    return isinstance(backend, AnthropicBackend)


def _profile_fewshot(seed_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    for it in seed_items:
        spec = {
            "industry": it["core"]["industry"],
            "career_stage": it["core"]["career_stage"],
            "target_role": it["core"]["target_role"],
            "company_size": it["_company_size"],
        }
        msgs.append({"role": "user", "content": build_profile_user_prompt(spec, it["_org"])})
        msgs.append({"role": "assistant", "content": json.dumps(
            {k: it[k] for k in ("core", "public", "private", "behavior")}, ensure_ascii=False)})
    return msgs


def _email_fewshot(seed_items: list[dict[str, Any]]) -> list[dict[str, str]]:
    msgs: list[dict[str, str]] = []
    keys = ("scenario", "pretext", "impersonated_role", "sender_display",
            "sender_address", "subject", "body", "call_to_action", "urgency",
            "personalization_fields")
    for it in seed_items:
        msgs.append({"role": "user", "content": build_email_user_prompt(it["_profile"], it["_org"])})
        msgs.append({"role": "assistant", "content": json.dumps(
            {k: it[k] for k in keys}, ensure_ascii=False)})
    return msgs


# ---------------------------------------------------------------------------

def generate_profiles(backend, orgs, specs, rng: random.Random, seed_count: int = 5):
    orgs_by_id = {o["org_id"]: o for o in orgs}
    bundles: list[ProfileBundle] = []
    gens: list[str] = []
    seed_raw: list[dict[str, Any]] = []

    for i, spec in enumerate(specs):
        org = orgs_by_id[spec["org_id"]]
        seed_phase = i < seed_count
        model = SEED_MODEL if seed_phase else BULK_MODEL
        fewshot = [] if seed_phase else _profile_fewshot(seed_raw)

        obj = backend.realize_profile(spec, org, model=model, fewshot=fewshot)
        pid = f"prof_{i:03d}"
        c = obj["core"]
        bundle = ProfileBundle(
            core=ProfileCore(profile_id=pid, org_id=org["org_id"], full_name=c["full_name"],
                             email=c["email"], industry=spec["industry"],
                             career_stage=spec["career_stage"], target_role=spec["target_role"],
                             title=c["title"], location=c["location"]),
            public=ProfilePublic(profile_id=pid, **obj["public"]),
            private=ProfilePrivate(profile_id=pid, **obj["private"]),
            behavior=ProfileBehavior(profile_id=pid, **obj["behavior"]),
        )
        bundles.append(bundle)
        gens.append(model if _is_api(backend) else f"local:{'seed' if seed_phase else 'bulk'}")

        if seed_phase:
            seed_raw.append({**obj, "_org": org, "_company_size": spec["company_size"]})

    _write_seed_profiles(seed_raw)
    return bundles, gens


def generate_emails(backend, bundles, orgs, rng: random.Random, seed_count: int = 5):
    orgs_by_id = {o["org_id"]: o for o in orgs}
    emails: list[AttackEmail] = []
    seed_raw: list[dict[str, Any]] = []

    for i, bundle in enumerate(bundles):
        from dataclasses import asdict
        profile = {
            "core": asdict(bundle.core), "public": asdict(bundle.public),
            "private": asdict(bundle.private), "behavior": asdict(bundle.behavior),
        }
        org = orgs_by_id[bundle.core.org_id]
        seed_phase = i < seed_count
        model = SEED_MODEL if seed_phase else BULK_MODEL
        fewshot = [] if seed_phase else _email_fewshot(seed_raw)

        obj = backend.realize_email(profile, org, model=model, fewshot=fewshot)
        gen = model if _is_api(backend) else f"local:{'seed' if seed_phase else 'bulk'}"
        emails.append(AttackEmail(
            email_id=f"mail_{i:03d}", profile_id=bundle.core.profile_id,
            org_id=org["org_id"], generator=gen, **obj,
        ))
        if seed_phase:
            seed_raw.append({**obj, "_profile": profile, "_org": org})

    _write_seed_emails(seed_raw)
    return emails


def _write_seed_profiles(seed_raw: list[dict[str, Any]]) -> None:
    SEED_DIR.mkdir(exist_ok=True)
    with (SEED_DIR / "seed_profiles.jsonl").open("w", encoding="utf-8") as fh:
        for it in seed_raw:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")


def _write_seed_emails(seed_raw: list[dict[str, Any]]) -> None:
    SEED_DIR.mkdir(exist_ok=True)
    with (SEED_DIR / "seed_emails.jsonl").open("w", encoding="utf-8") as fh:
        for it in seed_raw:
            fh.write(json.dumps(it, ensure_ascii=False) + "\n")
