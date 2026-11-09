"""v2 spear-email generation: one email per generated profile, validated and retried.

The model receives the merged profile (core/public/private/behavior, as written to the
JSONL files) and the employer. Its JSON is checked for the required keys, urgency label,
and that the sender and every link sit under a .example domain.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any

from .prompts_v2 import EMAIL_KEYS
from .schema import AttackEmail, ProfileBundle

_URL_HOST = re.compile(r"https?://([^/\s\"'<>)]+)", re.I)


def profile_dict(bundle: ProfileBundle) -> dict[str, Any]:
    return {"core": asdict(bundle.core), "public": asdict(bundle.public),
            "private": asdict(bundle.private), "behavior": asdict(bundle.behavior)}


def check_email(obj: Any) -> list[str]:
    """Return a list of violations (empty = ok)."""
    if not isinstance(obj, dict):
        return ["output must be one JSON object"]
    errs = [f"missing or empty key {k!r}" for k in EMAIL_KEYS if not obj.get(k)]
    if obj.get("urgency") not in ("low", "medium", "high"):
        errs.append("urgency must be low, medium or high")
    if obj.get("personalization_fields") is not None and not isinstance(obj.get("personalization_fields"), list):
        errs.append("personalization_fields must be a list")
    sender = str(obj.get("sender_address", ""))
    if "@" not in sender or not sender.rsplit("@", 1)[1].lower().rstrip(".").endswith(".example"):
        errs.append("sender_address must be an address under a .example domain")
    bad = [h for h in _URL_HOST.findall(str(obj.get("body", ""))) if not h.lower().split(":")[0].endswith(".example")]
    if bad:
        errs.append(f"every link must be under a .example domain (found {bad[0]})")
    return errs


def _generator_label(backend) -> str:
    usage = getattr(backend, "last_usage", None) or {}
    return usage.get("model") or getattr(backend, "model", None) or type(backend).__name__


def generate_emails_v2(backend, bundles: list[ProfileBundle], orgs: list[dict[str, Any]],
                       retries: int = 2, log=print):
    """Returns (emails, issues). An email whose every attempt was unparseable is skipped and logged."""
    orgs_by_id = {o["org_id"]: o for o in orgs}
    emails: list[AttackEmail] = []
    issues: list[dict[str, Any]] = []
    for i, bundle in enumerate(bundles):
        profile, org = profile_dict(bundle), orgs_by_id[bundle.core.org_id]
        obj, errs = None, []
        for _ in range(retries + 1):
            hint = "" if not errs else "\n\nYour previous answer violated: " + "; ".join(errs) + ". Fix these."
            try:
                cand = backend.realize_email(profile, org, extra=hint)
            except (ValueError, json.JSONDecodeError) as e:
                errs = [f"output was not one valid JSON object ({str(e)[:80]})"]
                continue
            obj, errs = cand, check_email(cand)
            if not errs:
                break
        pid = bundle.core.profile_id
        if errs:
            issues.append({"profile_id": pid, "errors": errs, "skipped": obj is None})
            log(f"  email for {pid}: kept after {retries + 1} attempts with issues: {errs}")
        if obj is not None:
            fields = {k: obj.get(k, [] if k == "personalization_fields" else "") for k in EMAIL_KEYS}
            if not isinstance(fields["personalization_fields"], list):
                fields["personalization_fields"] = [str(fields["personalization_fields"])]
            emails.append(AttackEmail(email_id=f"mail_{pid.split('_', 1)[1]}", profile_id=pid,
                                      org_id=org["org_id"], generator=_generator_label(backend), **fields))
        if (i + 1) % 5 == 0 or i + 1 == len(bundles):
            log(f"  emails {i + 1}/{len(bundles)}")
    return emails, issues
