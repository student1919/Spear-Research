#!/usr/bin/env python3
"""End-to-end initial run: companies -> profiles -> spear emails -> DB -> report.

Offline by default (no API key needed). Use --backend anthropic to run the real
Sonnet-seed / Haiku-bulk passes once `anthropic` is installed and credentials are
configured.

    python scripts/run_initial.py --profiles 100 --emails 100 --seed 7
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import analyze, build_db, report  # noqa: E402
from src.llm import LocalBackend, AnthropicBackend, SEED_MODEL, BULK_MODEL  # noqa: E402
from src.pipeline import generate_profiles, generate_emails  # noqa: E402
from src.prompts import PROMPT_VERSION  # noqa: E402
from src.sample import build_orgs, sample_specs  # noqa: E402
from src.schema import FILES, write_jsonl, read_jsonl  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles", type=int, default=100)
    ap.add_argument("--emails", type=int, default=100)
    ap.add_argument("--orgs", type=int, default=24)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--seed-count", type=int, default=5)
    ap.add_argument("--backend", choices=["local", "anthropic"], default="local")
    ap.add_argument("--data-dir", default=str(ROOT / "data" / "v1"))
    ap.add_argument("--report", default=str(ROOT / "report" / "REPORT.md"))
    ap.add_argument("--fig-dir", default=str(ROOT / "report" / "figures"))
    args = ap.parse_args()

    data_dir = Path(args.data_dir)
    fig_dir = Path(args.fig_dir)
    rng = random.Random(args.seed)

    backend = AnthropicBackend() if args.backend == "anthropic" else LocalBackend(rng)
    backend_name = type(backend).__name__

    print(f"[1/6] building {args.orgs} synthetic companies")
    orgs = build_orgs(rng, args.orgs)

    print(f"[2/6] sampling {args.profiles} target specs")
    specs = sample_specs(rng, orgs, args.profiles)

    print(f"[3/6] generating profiles ({backend_name}: "
          f"{args.seed_count} seed + {args.profiles - args.seed_count} bulk)")
    bundles, _gens = generate_profiles(backend, orgs, specs, rng, args.seed_count)

    n_emails = min(args.emails, len(bundles))
    print(f"[3/6] generating {n_emails} spear emails")
    emails = generate_emails(backend, bundles[:n_emails], orgs, rng, args.seed_count)

    print("[4/6] writing JSONL")
    write_jsonl(data_dir / FILES["orgs"], orgs)
    write_jsonl(data_dir / FILES["core"], [asdict(b.core) for b in bundles])
    write_jsonl(data_dir / FILES["public"], [asdict(b.public) for b in bundles])
    write_jsonl(data_dir / FILES["private"], [asdict(b.private) for b in bundles])
    write_jsonl(data_dir / FILES["behavior"], [asdict(b.behavior) for b in bundles])
    write_jsonl(data_dir / FILES["emails_attack"], [asdict(e) for e in emails])

    print("[5/6] building SQLite database")
    counts = build_db.build(data_dir, data_dir / "spear.sqlite")

    print("[6/6] analyzing + writing report")
    core_rows = read_jsonl(data_dir / FILES["core"])
    email_rows = read_jsonl(data_dir / FILES["emails_attack"])
    profile_stats = analyze.profile_histograms(core_rows, orgs, fig_dir)
    email_stats = analyze.email_detectability(email_rows, orgs, fig_dir)

    run_meta = {
        "backend": backend_name,
        "seed_model": SEED_MODEL,
        "bulk_model": BULK_MODEL,
        "prompt_version": PROMPT_VERSION,
        "seed": args.seed,
        "seed_count": args.seed_count,
        "counts": counts,
    }
    out = report.build_report(data_dir, args.report, profile_stats, email_stats, run_meta)
    print(f"\nDone. DB tables: {counts}")
    print(f"Report: {out}")
    print(f"Figures: {fig_dir}")


if __name__ == "__main__":
    main()
