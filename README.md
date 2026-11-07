# Spear-email generator (synthetic profiles + spear emails)

The `Profiles.md` piece of the spear-phishing **mitigator** project: generate
fictional employee profiles at fictional companies, then generate a spear-phishing
email targeting each one. The corpus is for training and evaluating a **detector**.

**Safety framing.** Every person, company, email address, and web domain is
fictional and lives under a reserved `.example` zone. Nothing generated is sent or
is intended to reach a real inbox. No real individuals' data is used.

## What it does

Two LLM roles (per the plan):

1. one model invents synthetic people + companies, and
2. a second model writes a spear email targeting each synthetic person.

Generation is **two-stage, few-shot**: the first 5 profiles and 5 emails are written
by the higher-capability model (`claude-sonnet-5-5`) with no exemplars and saved to
`seeds/`; the rest are written by `claude-haiku-5-5` conditioned on those seeds.

## Trajectory / current status

- **Step 1 (this MVP) — prompt engineering + pipeline.** Done. Prompts in
  `src/prompts.py`; the full pipeline runs **offline** via a composing backend
  (`LocalBackend`) so the initial 100-profile / 100-email run, SQLite DB,
  histograms, and report all work with no API key.
- **Step 2 — real API calls.** `src/llm.py::AnthropicBackend` already implements the
  Sonnet-seed / Haiku-bulk passes. Install `anthropic`, set credentials, and pass
  `--backend anthropic`. Nothing downstream changes.
- **Step 3 — fine-tune on the 300k-email dataset.** Future; out of scope here.

## Run it

```bash
pip install -r requirements.txt
python scripts/run_initial.py --profiles 100 --emails 100 --seed 7      # offline
python scripts/run_initial.py --profiles 100 --emails 100 --backend anthropic  # real API
```

Outputs: `data/v1/*.jsonl`, `data/v1/spear.sqlite`, `report/figures/*.png`,
`report/REPORT.md` (Markdown, intended to be fed to a slide-generating model).

## Layout

```
config/dimensions.py   industries, stages, sizes, roles + sampling weights (auditable)
src/schema.py          record dataclasses + JSONL I/O (Profiles.md file layout)
src/prompts.py         system prompts + few-shot assembly  (the prompt engineering)
src/pools.py           Claude-authored fragments used by the offline backend
src/llm.py             AnthropicBackend (real) + LocalBackend (offline)
src/sample.py          reproducible company + profile-dimension sampling
src/pipeline.py        two-stage seed->bulk orchestration
src/build_db.py        JSONL -> SQLite (one table per record type, linked by id)
src/analyze.py         histograms + email detectability pass
src/report.py          assembles report/REPORT.md
scripts/run_initial.py end-to-end run
```

## Data files (one SQLite table each, linked by `profile_id` / `org_id`)

`orgs.jsonl`, `profiles_core.jsonl`, `profiles_public.jsonl`,
`profiles_private.jsonl`, `profiles_behavior.jsonl`, `emails_attack.jsonl`.

## Notes

- Target distributions are **non-uniform by design** and declared in
  `config/dimensions.py` so every histogram's shape is explainable.
- In this run the **full** profile is given to the email generator. Selective
  context removal (public-only, etc.) is a later experiment; the schema separates
  public vs. private fields so that ablation is a filter, not a regeneration.
- Runs are reproducible via `--seed`.

## v2: empirically calibrated profiles

`src/population.py` samples each person from distributions in `config/empirical.py` (BLS, Census, NCES, Pew, vendor and
academic phishing studies; every parameter cites an id in `config/sources.py`). The LLM only writes the narrative
(`src/prompts_v2.py`, `src/profile_v2.py`). Reference tables are built by `scripts/build_reference_data.py`.

```bash
python scripts/run_v2.py --profiles 5000 --spec-only --out data/v2/spec5000   # sample + validate, no LLM calls
python scripts/run_v2.py --profiles 15 --backend gemini --out data/v2/test15   # live narratives
python scripts/make_calibration_report.py                                      # report/CALIBRATION.md, AUDIT_V1.md, BIBLIOGRAPHY.md
```

Reports: `report/CALIBRATION.md` (sources, alignment tests, gaps), `report/AUDIT_V1.md` (the original 100),
`report/BIBLIOGRAPHY.md`.
