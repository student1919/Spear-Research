# Spear-email generator (synthetic profiles + spear emails)

The `Profiles.md` piece of the spear-phishing **mitigator** project: generate
fictional employee profiles at fictional companies, then generate a spear-phishing
email targeting each one. The corpus is for training and evaluating a **detector**.

**Safety framing.** Every person, company, email address, and web domain is
fictional and lives under a reserved `.example` zone. Nothing generated is sent or
is intended to reach a real inbox. No real individuals' data is used.

## Pipeline (v2)

1. **Sampler** — `src/population.py` draws each person (industry, employer size,
   occupation, age, sex, education and school, tenure, career stage, prior employers,
   online presence, email workload, phishing susceptibility) from the distributions in
   `config/empirical.py`. Every parameter cites an id in `config/sources.py`.
   `src/validate.py` checks the sampled population against those sources.
2. **Narrative** — the model receives the fixed spec and writes only text
   (`src/prompts_v2.py`, `src/profile_v2.py`). The resume is **450–550 words**
   (target 500) with current-job, prior-job and education sections, and **every
   bullet carries a numeric performance metric** (years do not count). Output that
   violates the spec or these rules is re-requested with the violations listed.
3. **Spear email** — the model receives the merged profile and the employer and
   writes one email per profile (`src/emails_v2.py`); the sender and every link must
   be under `.example`.
4. **Outputs** — JSONL files, a SQLite DB, figures and a Markdown report per run.

The resume limits live in `src/prompts_v2.py` (`RESUME_TARGET_WORDS`,
`RESUME_MIN_WORDS`, `RESUME_MAX_WORDS`, `CURRENT_JOB_BULLETS`, `PRIOR_JOB_BULLETS`)
and are used by both the prompt and the validator.

## Run it

```bash
pip install -r requirements.txt
python scripts/run_v2.py --profiles 5000 --spec-only --out data/v2/spec5000   # sample + validate, no LLM calls
python scripts/run_v2.py --profiles 100 --backend local --out data/v2/dry100   # offline dry run (pool text, not LLM)
python scripts/run_v2.py --profiles 15 --backend gemini --out data/v2/test15   # live narratives + emails
python scripts/make_calibration_report.py                                      # report/CALIBRATION.md, AUDIT_V1.md, BIBLIOGRAPHY.md
streamlit run streamlit_app.py                                                 # one-at-a-time live demo
```

Backends: `gemini` (Gemini 3.5 Flash-Lite, falling back to 3.1), `anthropic`
(`claude-sonnet-5-5`), `haiku` (`claude-haiku-5-5`), `local` (offline). `--emails N`
limits emails to the first N profiles (`0` skips them); `--retries` sets re-requests
after a validation failure.

Each run directory holds `specs.jsonl`, `orgs.jsonl`, `profiles_*.jsonl`,
`emails_attack.jsonl`, `validation.{md,json}`, `run_meta.json`, `spear.sqlite`,
`REPORT.md` and `figures/`.

## Layout

```
config/empirical.py      calibrated distributions (each parameter cites a source)
config/sources.py        source registry
src/population.py        calibrated person + company sampler
src/validate.py          population-vs-source alignment checks
src/prompts_v2.py        profile-narrative and spear-email prompts; resume limits
src/profile_v2.py        narrative validation/retry + merge with the spec
src/emails_v2.py         spear-email validation/retry
src/llm.py               Anthropic / Haiku / Gemini / Local backends
src/pools.py             text fragments for the offline Local backend
src/schema.py            record dataclasses + JSONL I/O (Profiles.md file layout)
src/build_db.py          JSONL -> SQLite (one table per record type, linked by id)
src/analyze.py           histograms, resume statistics, email detectability pass
src/report.py            per-run REPORT.md
scripts/run_v2.py        end-to-end run
scripts/build_reference_data.py   reference tables in data/reference/
scripts/make_calibration_report.py
streamlit_app.py         live demo
```

## Data files (one SQLite table each, linked by `profile_id` / `org_id`)

`orgs.jsonl`, `profiles_core.jsonl`, `profiles_public.jsonl`,
`profiles_private.jsonl`, `profiles_behavior.jsonl`, `emails_attack.jsonl`.
`profiles_public.jsonl` stores the structured `resume` (current job, prior jobs,
education), the flattened `resume_bullets`, and `resume_word_count`.

## Archive

`data/v1/` and `report/AUDIT_V1.md` are the outputs of the retired v1 pipeline
(hand-weighted dimensions, template-composed text). They are kept for the v1-vs-v2
comparison in `report/CALIBRATION.md`; the v1 code is in git history.
`data/v2/test15/` was generated with prompt v2, before the 500-word resume.
