"""Assemble the Markdown run report (<run dir>/REPORT.md) for a v2 run.

The report is designed to be fed to another model that turns it into slides, so it
leans on figures (in <run dir>/figures/) and compact tables. It states methodology,
the generated distributions, resume statistics, examples, and the detectability pass
as observations. Per project convention it contains no recommendations.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from .schema import FILES, read_jsonl


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |",
           "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def _counts_table(d: dict[str, int], label: str) -> str:
    total = sum(d.values()) or 1
    rows = [[k, v, f"{100*v/total:.0f}%"] for k, v in d.items()]
    return _table([label, "count", "share"], rows)


def _join_profiles(data_dir: Path) -> dict[str, dict]:
    def by_id(name, key):
        return {r[key]: r for r in read_jsonl(data_dir / FILES[name])}
    core = by_id("core", "profile_id")
    public = by_id("public", "profile_id")
    private = by_id("private", "profile_id")
    behavior = by_id("behavior", "profile_id")
    return {pid: {"core": c, "public": public.get(pid, {}), "private": private.get(pid, {}),
                  "behavior": behavior.get(pid, {})} for pid, c in core.items()}


def _example_profile_md(p: dict) -> str:
    c, pub, pri, beh = p["core"], p["public"], p["private"], p["behavior"]
    res = pub.get("resume") or {}
    lines = [
        f"**{c['full_name']}** — {c['title']}  ",
        f"`{c['email']}` · {c['industry']} · {c['career_stage']} · target role: _{c['target_role']}_ · "
        f"{c['location']} · age {c.get('age')} · tenure {c.get('tenure_years')} y",
        "",
        f"Resume ({pub.get('resume_word_count', 0)} words):",
        "",
        f"- *{c['title']} (current)*",
    ]
    lines += [f"  - {b}" for b in (res.get("current_job") or {}).get("bullets", [])]
    for job in res.get("prior_jobs", []):
        lines.append(f"- *{job.get('title')}, {job.get('employer')} ({job.get('start_year')}–{job.get('end_year')})*")
        lines += [f"  - {b}" for b in job.get("bullets", [])]
    if res.get("education"):
        lines.append("- *Education*")
        lines += [f"  - {b}" for b in res["education"]]
    lines += [
        "",
        "- Public footprint: " + str(pub.get("footprint_level")),
        "- Private projects: " + ", ".join(pri.get("projects", [])),
        "- Sensitive access: " + ", ".join(pri.get("sensitive_access", [])),
        "- Behavior: security awareness " + str(beh.get("security_awareness"))
        + f", p(click) {beh.get('p_click_simulated_phish')}; traits: " + ", ".join(beh.get("traits", [])),
    ]
    return "\n".join(lines)


def _example_email_md(e: dict) -> str:
    return (
        f"**Scenario:** {e['scenario']} · **urgency:** {e['urgency']} · "
        f"impersonating _{e['impersonated_role']}_\n\n"
        f"- From: `{e['sender_display']} <{e['sender_address']}>`\n"
        f"- Subject: **{e['subject']}**\n"
        f"- Personalization used: {', '.join(map(str, e['personalization_fields']))}\n\n"
        "```\n" + e["body"].strip() + "\n```"
    )


def build_report(data_dir, out_path, profile_stats, resume_st, email_stats, run_meta,
                 fig_rel="figures") -> Path:
    data_dir, out_path = Path(data_dir), Path(out_path)
    profiles = _join_profiles(data_dir)
    emails = read_jsonl(data_dir / FILES["emails_attack"])

    ex_profiles, seen = [], set()
    for p in profiles.values():
        if p["core"]["target_role"] not in seen:
            seen.add(p["core"]["target_role"])
            ex_profiles.append(p)
        if len(ex_profiles) >= 3:
            break
    ex_emails, seen_s = [], set()
    for e in emails:
        if e["scenario"] not in seen_s:
            seen_s.add(e["scenario"])
            ex_emails.append(e)
        if len(ex_emails) >= 4:
            break

    def fig(name, caption):
        return f"![{caption}]({fig_rel}/{name})\n\n*{caption}*\n"

    counts = run_meta["counts"]
    lo, hi = resume_st["range"]
    md: list[str] = []
    md.append("# Synthetic Spear-Phishing Corpus — v2 Run\n")
    md.append(
        f"_Generated {date.today().isoformat()} · backend: **{run_meta['backend']}** · "
        f"model: `{run_meta.get('model') or '-'}` · population {run_meta['population_version']} · "
        f"prompt {run_meta['prompt_version']} · random seed {run_meta['seed']}_\n"
    )
    md.append(
        "> All profiles, companies, and emails are **fictional**. Every email address "
        "and web domain is under a reserved `.example` zone. The corpus exists to train "
        "and evaluate a spear-phishing **detector**; nothing here is or can be sent.\n"
    )

    md.append("## 1. Scope and method\n")
    md.append(
        "1. **Sampler** (`src/population.py`): every person's industry, employer size, occupation, age, sex, "
        "education, school, tenure, career stage, prior employers, online presence, email workload and phishing "
        "susceptibility are drawn from the sourced distributions in `config/empirical.py`. The sampled population "
        "is checked against the sources in `validation.md`.\n"
        "2. **Narrative** (`src/prompts_v2.py`, `src/profile_v2.py`): the model receives the fixed spec and writes "
        f"only text: a resume of {lo}–{hi} words with current-job, prior-job and education sections in which "
        "every bullet carries a numeric performance metric, prior job titles, majors, social handles, posts, "
        "projects, private details, access, traits and response tendencies. Output that violates the spec or the "
        "resume rules is re-requested with the violations listed.\n"
        "3. **Spear email** (`src/emails_v2.py`): the model receives the full merged profile and the employer and "
        "writes one spear email; the sender and every link must be under `.example`.\n"
    )
    md.append("**Record files** (one SQLite table each in `spear.sqlite`, linked by `profile_id` / `org_id`):\n")
    md.append(_table(["file", "records"], [[FILES[k], counts.get(k, "-")] for k in FILES]) + "\n")
    md.append(_table(["validation", "count"], [
        ["profiles kept with narrative issues", len(run_meta.get("narrative_issues", []))],
        ["emails kept with issues", len(run_meta.get("email_issues", []))],
    ]) + "\n")

    md.append("## 2. Who was generated\n")
    md.append(f"{counts.get('core')} profiles across {counts.get('orgs')} synthetic companies.\n")
    md.append(fig("profiles_by_industry.png", "Profiles by industry"))
    md.append(_counts_table(profile_stats["industry"], "industry") + "\n")
    md.append(fig("profiles_by_career_stage.png", "Profiles by career stage"))
    md.append(_counts_table(profile_stats["career_stage"], "career stage") + "\n")
    md.append(fig("profiles_by_company_size.png", "Profiles by employer size"))
    md.append(_counts_table(profile_stats["company_size"], "employees") + "\n")
    md.append(fig("profiles_by_target_role.png", "Profiles by target role"))
    md.append(_counts_table(profile_stats["target_role"], "target role") + "\n")
    md.append("### Companies\n")
    md.append(fig("orgs_by_industry.png", "Companies by industry"))
    md.append(fig("orgs_by_size.png", "Companies by size"))

    md.append("## 3. Resumes\n")
    if resume_st["n"]:
        md.append(fig("resume_word_count.png", "Resume length per profile"))
    md.append(_table(["metric", "value"], [
        ["profiles", resume_st["n"]],
        ["words per resume (min / median / max)",
         f"{resume_st['min_words']} / {resume_st['median_words']} / {resume_st['max_words']}"],
        [f"resumes within {lo}–{hi} words", f"{resume_st['in_range']} / {resume_st['n']}"],
        ["bullets with a numeric metric", f"{resume_st['bullets_with_metric']} / {resume_st['bullets']}"],
        ["distinct bullets", f"{resume_st['distinct_bullets']} / {resume_st['bullets']}"],
    ]) + "\n")

    md.append("## 4. Example profiles\n")
    for p in ex_profiles:
        md.append(_example_profile_md(p) + "\n")

    md.append("## 5. Example spear emails\n")
    if not ex_emails:
        md.append("No emails were generated in this run.\n")
    for e in ex_emails:
        md.append(_example_email_md(e) + "\n")

    if email_stats["n"]:
        md.append("## 6. Email detectability pass\n")
        md.append(
            "Each email is scored on features phishing detectors commonly key on, and the "
            "corpus is measured for template repetition. The numbers are observations.\n"
        )
        md.append(fig("email_scenarios.png", "Spear-email scenarios"))
        md.append(fig("email_urgency.png", "Email urgency"))
        md.append(fig("email_feature_prevalence.png", "Detector-relevant feature prevalence"))
        md.append(fig("email_detectability_score.png", "Heuristic detectability score per email"))
        md.append(_table(["metric", "value"], [
            ["emails", email_stats["n"]],
            ["mean heuristic detectability (0–1)", email_stats["mean_detectability"]],
            ["distinct email-body signatures", f"{email_stats['distinct_body_signatures']} / {email_stats['n']}"],
            ["corpus type–token ratio", email_stats["corpus_type_token_ratio"]],
        ] + [[f"{k.replace('_', ' ')} (% of emails)", v]
             for k, v in email_stats["feature_prevalence_pct"].items()]) + "\n")

    if run_meta["backend"] == "local":
        md.append("> This run used the offline `local` backend: the resume, post and email text is composed from "
                  "the fixed fragments in `src/pools.py`, not written by a model.\n")

    md.append("## Appendix — reproducing\n")
    md.append(
        "```bash\n"
        f"python scripts/run_v2.py --profiles {run_meta['profiles']} --emails {run_meta['emails_requested']} "
        f"--backend {run_meta['backend']} --seed {run_meta['seed']} --out {data_dir}\n"
        "```\n"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md), encoding="utf-8")
    return out_path
