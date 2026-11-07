"""Assemble the Markdown report (report/REPORT.md).

The report is designed to be fed to another model that turns it into slides, so it
leans on figures (in report/figures/) and compact tables. It states methodology,
the generated distributions, examples, and the detectability pass as observations.
Per project convention it contains no recommendations.
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
    out = {}
    for pid, c in core.items():
        out[pid] = {"core": c, "public": public.get(pid, {}),
                    "private": private.get(pid, {}), "behavior": behavior.get(pid, {})}
    return out


def _example_profile_md(p: dict) -> str:
    c, pub, pri, beh = p["core"], p["public"], p["private"], p["behavior"]
    lines = [
        f"**{c['full_name']}** — {c['title']}  ",
        f"`{c['email']}` · {c['industry']} · {c['career_stage']} · "
        f"target role: _{c['target_role']}_ · {c['location']}",
        "",
        "- Resume: " + "; ".join(pub.get("resume_bullets", [])),
        "- Public footprint: " + str(pub.get("footprint_level")),
        "- Private projects: " + ", ".join(pri.get("projects", [])),
        "- Sensitive access: " + ", ".join(pri.get("sensitive_access", [])),
        "- Behavior: security awareness " + str(beh.get("security_awareness"))
        + "; traits: " + ", ".join(beh.get("traits", [])),
    ]
    return "\n".join(lines)


def _example_email_md(e: dict) -> str:
    return (
        f"**Scenario:** {e['scenario']} · **urgency:** {e['urgency']} · "
        f"impersonating _{e['impersonated_role']}_\n\n"
        f"- From: `{e['sender_display']} <{e['sender_address']}>`\n"
        f"- Subject: **{e['subject']}**\n"
        f"- Personalization used: {', '.join(e['personalization_fields'])}\n\n"
        "```\n" + e["body"].strip() + "\n```"
    )


def build_report(data_dir, out_path, profile_stats, email_stats, run_meta,
                 fig_rel="figures") -> Path:
    data_dir, out_path = Path(data_dir), Path(out_path)
    profiles = _join_profiles(data_dir)
    emails = read_jsonl(data_dir / FILES["emails_attack"])
    orgs = read_jsonl(data_dir / FILES["orgs"])

    # Pick diverse examples.
    ex_profiles, seen = [], set()
    for p in profiles.values():
        key = p["core"]["target_role"]
        if key not in seen:
            seen.add(key)
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

    md: list[str] = []
    md.append("# Synthetic Spear-Phishing Corpus — Initial Run\n")
    md.append(
        f"_Generated {date.today().isoformat()} · backend: **{run_meta['backend']}** · "
        f"seed model: `{run_meta['seed_model']}` · bulk model: `{run_meta['bulk_model']}` · "
        f"prompt {run_meta['prompt_version']} · random seed {run_meta['seed']}_\n"
    )
    md.append(
        "> All profiles, companies, and emails are **fictional**. Every email address "
        "and web domain is under a reserved `.example` zone. The corpus exists to train "
        "and evaluate a spear-phishing **detector**; nothing here is or can be sent.\n"
    )

    md.append("## 1. Scope and method\n")
    md.append(
        "This covers the profile-and-email **generator** only (the `Profiles.md` piece). "
        "Two LLM roles are used: one LLM invents synthetic people and companies, a second "
        "writes a spear email targeting each synthetic person.\n\n"
        "**Two-stage, few-shot generation.** The first "
        f"{run_meta['seed_count']} profiles and {run_meta['seed_count']} emails are written "
        f"by the higher-capability model (`{run_meta['seed_model']}`) with no exemplars and "
        f"saved to `seeds/`. The remaining items are written by `{run_meta['bulk_model']}` "
        "conditioned on those seeds as few-shot exemplars.\n\n"
        "**MVP note.** This run was produced with the offline composing backend "
        f"(`{run_meta['backend']}`): no API key was used (per the stated trajectory, the API "
        "call is the next step). The prompts, two-stage structure, schema, database, and "
        "analysis are the same ones the API path uses; switching the backend to "
        "`AnthropicBackend` makes the two passes real without other changes. In this run the "
        "full profile is given to the email generator (no context ablation yet).\n"
    )
    md.append("**Record files** (one SQLite table each, linked by `profile_id` / `org_id`):\n")
    md.append(_table(["file", "records"],
              [[FILES[k], run_meta["counts"].get(k, "-")] for k in FILES]) + "\n")

    md.append("## 2. Who was generated\n")
    md.append(f"{run_meta['counts'].get('core')} profiles across "
              f"{run_meta['counts'].get('orgs')} synthetic companies.\n")
    md.append(fig("profiles_by_industry.png", "Profiles by industry"))
    md.append(_counts_table(profile_stats["industry"], "industry") + "\n")
    md.append(fig("profiles_by_career_stage.png", "Profiles by career stage"))
    md.append(_counts_table(profile_stats["career_stage"], "career stage") + "\n")
    md.append(fig("profiles_by_company_size.png", "Profiles by company size"))
    md.append(_counts_table(profile_stats["company_size"], "company size") + "\n")
    md.append(fig("profiles_by_target_role.png", "Profiles by target role"))
    md.append(_counts_table(profile_stats["target_role"], "target role") + "\n")
    md.append("### Companies\n")
    md.append(fig("orgs_by_industry.png", "Companies by industry"))
    md.append(fig("orgs_by_size.png", "Companies by size"))

    md.append("## 3. Example profiles\n")
    for p in ex_profiles:
        md.append(_example_profile_md(p) + "\n")

    md.append("## 4. Example spear emails\n")
    for e in ex_emails:
        md.append(_example_email_md(e) + "\n")

    md.append("## 5. Email detectability pass\n")
    md.append(
        "Each email is scored on features phishing detectors commonly key on, and the "
        "corpus is measured for template repetition. Figures and figures only; numbers are "
        "observations.\n"
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
    ]) + "\n")

    md.append("## 6. Observations\n")
    mis = email_stats["feature_prevalence_pct"].get("sender_domain_mismatch", 0)
    md.append(
        f"- The sampled target distribution is non-uniform by design (see §2): finance, "
        f"tech, and executive/finance roles are over-represented relative to a flat prior, "
        f"matching the weighting declared in `config/dimensions.py`.\n"
        f"- Sender-domain mismatch appears in {mis}% of emails — in this run it is universal "
        f"because every sender address is a synthetic look-alike cousin of the company "
        f"`.example` domain, so it is a trivially separable signal as generated.\n"
        f"- Body-template repetition is high: {email_stats['distinct_body_signatures']} "
        f"distinct body signatures across {email_stats['n']} emails and a corpus type–token "
        f"ratio of {email_stats['corpus_type_token_ratio']}. The MVP composing backend draws "
        f"from a finite template pool, so the emails cluster into few lexical shapes — i.e. "
        f"they are quickly identifiable by n-gram repetition, consistent with the stated "
        f"hypothesis for this stub.\n"
        f"- These repetition and mismatch signals are properties of the offline backend. The "
        f"next step in the stated trajectory (real `{run_meta['bulk_model']}` generation, then "
        f"selective context removal) is what tests whether LLM-written emails remain this "
        f"separable; the same analysis code applies unchanged.\n"
    )

    md.append("## Appendix — reproducing / switching to the API\n")
    md.append(
        "```bash\n"
        "# offline run (no key), as used here:\n"
        "python scripts/run_initial.py --profiles 100 --emails 100 --seed 7\n\n"
        "# real API run (Sonnet seeds + Haiku bulk): install the SDK and set credentials,\n"
        "# then pass --backend anthropic\n"
        "pip install anthropic\n"
        "python scripts/run_initial.py --profiles 100 --emails 100 --backend anthropic\n"
        "```\n"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md), encoding="utf-8")
    return out_path
