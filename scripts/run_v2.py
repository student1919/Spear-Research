#!/usr/bin/env python3
"""v2 profile generation: calibrated sampler -> LLM narrative -> validation report.

    python scripts/run_v2.py --profiles 12 --backend gemini --out data/v2/test12
    python scripts/run_v2.py --profiles 1000 --backend gemini --out data/v2/run1000
    python scripts/run_v2.py --profiles 5000 --spec-only --out data/v2/spec5000   # sampler + validation, no LLM

`--spec-only` draws and validates the full population without any LLM call; it is the
cheap way to check the statistics before spending API calls on the narratives.
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
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--backend", choices=["gemini", "anthropic", "haiku", "local"], default="gemini")
    ap.add_argument("--spec-only", action="store_true", help="sample + validate only; no LLM calls")
    ap.add_argument("--out", default=str(ROOT / "data" / "v2" / "test"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] sampling {a.profiles} calibrated people (seed {a.seed})")
    pop = Population(seed=a.seed)
    orgs, specs = pop.sample(a.profiles)
    write_jsonl(out / "specs.jsonl", specs)
    write_jsonl(out / FILES["orgs"], orgs)

    print("[2/4] validating the sampled population against the sources")
    res = validate(pop, orgs, specs)
    md = to_markdown(res)
    (out / "validation.md").write_text(md, encoding="utf-8")
    (out / "validation.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    if a.spec_only:
        print(f"spec-only run complete: {out}/validation.md")
        return

    print(f"[3/4] generating narratives with backend={a.backend}")
    from src import llm
    from src.profile_v2 import generate_profiles_v2
    if a.backend == "gemini":
        backend = llm.GeminiBackend()
    elif a.backend == "anthropic":
        backend = llm.AnthropicBackend()
    elif a.backend == "haiku":
        backend = llm.LiveHaikuBackend()
    else:
        backend = llm.LocalBackend(random.Random(a.seed))
    bundles, issues = generate_profiles_v2(backend, orgs, specs, random.Random(a.seed + 1))

    print("[4/4] writing JSONL")
    write_jsonl(out / FILES["core"], [asdict(b.core) for b in bundles])
    write_jsonl(out / FILES["public"], [asdict(b.public) for b in bundles])
    write_jsonl(out / FILES["private"], [asdict(b.private) for b in bundles])
    write_jsonl(out / FILES["behavior"], [asdict(b.behavior) for b in bundles])
    (out / "run_meta.json").write_text(json.dumps({
        "population_version": POPULATION_VERSION, "prompt_version": PROMPT_VERSION, "backend": a.backend,
        "model": getattr(backend, "last_usage", None), "seed": a.seed, "profiles": a.profiles,
        "narrative_issues": issues}, indent=1, default=str), encoding="utf-8")
    print(f"Done: {out}  (narrative issues: {len(issues)})")


if __name__ == "__main__":
    main()
