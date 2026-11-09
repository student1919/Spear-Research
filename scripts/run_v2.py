#!/usr/bin/env python3
"""v2 pipeline: calibrated sampler -> LLM narrative -> spear emails -> SQLite -> report.

    python scripts/run_v2.py --profiles 12 --backend gemini --out data/v2/test12
    python scripts/run_v2.py --profiles 1000 --backend gemini --out data/v2/run1000
    python scripts/run_v2.py --profiles 100 --backend local --out data/v2/dry100      # offline dry run
    python scripts/run_v2.py --profiles 5000 --spec-only --out data/v2/spec5000       # sampler + validation, no LLM

`--spec-only` draws and validates the full population without any LLM call; it is the
cheap way to check the statistics before spending API calls on the narratives.
`--emails N` limits spear emails to the first N profiles (default: one per profile; 0 skips).

Outputs in --out: specs.jsonl, orgs.jsonl, profiles_*.jsonl, emails_attack.jsonl,
validation.{md,json}, run_meta.json, spear.sqlite, REPORT.md, figures/*.png.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.population import Population, POPULATION_VERSION  # noqa: E402
from src.prompts_v2 import PROMPT_VERSION  # noqa: E402
from src.schema import FILES, write_jsonl  # noqa: E402
from src.validate import validate, to_markdown  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", type=int, default=12)
    ap.add_argument("--emails", type=int, default=None, help="spear emails for the first N profiles (default: all)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--backend", choices=["gemini", "anthropic", "claude-cli", "haiku", "local"], default="gemini")
    ap.add_argument("--retries", type=int, default=2, help="re-requests per item after a validation failure")
    ap.add_argument("--spec-only", action="store_true", help="sample + validate only; no LLM calls")
    ap.add_argument("--single-org", action="store_true",
                    help="put every profile at one company (see --industry/--size-class/--headcount)")
    ap.add_argument("--industry", default="Tech", choices=["Finance", "Healthcare", "Tech", "Government", "Education"])
    ap.add_argument("--size-class", default="5000+", choices=["<20", "20-99", "100-499", "500-4999", "5000+"])
    ap.add_argument("--headcount", type=int, default=None, help="pin the single company's headcount")
    ap.add_argument("--out", default=str(ROOT / "data" / "v2" / "test"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] sampling {a.profiles} calibrated people (seed {a.seed})")
    pop = Population(seed=a.seed, headcount=a.headcount,
                     single_org=(a.industry, a.size_class) if a.single_org else None)
    orgs, specs = pop.sample(a.profiles)
    write_jsonl(out / "specs.jsonl", specs)
    write_jsonl(out / FILES["orgs"], orgs)

    print("[2/6] validating the sampled population against the sources")
    res = validate(pop, orgs, specs)
    (out / "validation.md").write_text(to_markdown(res), encoding="utf-8")
    (out / "validation.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    if a.spec_only:
        print(f"spec-only run complete: {out}/validation.md")
        return

    from src import analyze, build_db, report
    from src.emails_v2 import generate_emails_v2
    from src.llm import make_backend
    from src.profile_v2 import generate_profiles_v2

    backend = make_backend(a.backend, random.Random(a.seed))

    print(f"[3/6] generating narratives with backend={a.backend}")
    bundles, issues = generate_profiles_v2(backend, orgs, specs, random.Random(a.seed + 1), retries=a.retries)
    profile_model = (getattr(backend, "last_usage", None) or {}).get("model") or getattr(backend, "model", None)

    n_emails = len(bundles) if a.emails is None else max(0, min(a.emails, len(bundles)))
    print(f"[4/6] generating {n_emails} spear emails")
    emails, email_issues = generate_emails_v2(backend, bundles[:n_emails], orgs, retries=a.retries)

    print("[5/6] writing JSONL + SQLite")
    write_jsonl(out / FILES["core"], [asdict(b.core) for b in bundles])
    write_jsonl(out / FILES["public"], [asdict(b.public) for b in bundles])
    write_jsonl(out / FILES["private"], [asdict(b.private) for b in bundles])
    write_jsonl(out / FILES["behavior"], [asdict(b.behavior) for b in bundles])
    write_jsonl(out / FILES["emails_attack"], [asdict(e) for e in emails])
    counts = build_db.build(out, out / "spear.sqlite")

    run_meta = {
        "population_version": POPULATION_VERSION, "prompt_version": PROMPT_VERSION, "backend": a.backend,
        "model": profile_model, "last_usage": getattr(backend, "last_usage", None), "seed": a.seed,
        "profiles": a.profiles, "emails_requested": n_emails, "counts": counts,
        "narrative_issues": issues, "email_issues": email_issues,
    }
    (out / "run_meta.json").write_text(json.dumps(run_meta, indent=1, default=str), encoding="utf-8")

    print("[6/6] analyzing + writing report")
    fig_dir = out / "figures"
    profile_stats = analyze.profile_histograms([asdict(b.core) for b in bundles], orgs, fig_dir)
    resume_st = analyze.resume_stats([asdict(b.public) for b in bundles], fig_dir)
    email_stats = analyze.email_detectability([asdict(e) for e in emails], orgs, fig_dir)
    rep = report.build_report(out, out / "REPORT.md", profile_stats, resume_st, email_stats, run_meta)
    print(f"Done: {out}  (DB tables: {counts}; narrative issues: {len(issues)}; email issues: {len(email_issues)})")
    print(f"Report: {rep}")


if __name__ == "__main__":
    main()
