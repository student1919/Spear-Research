"""Histograms and an email-detectability pass over the generated corpus.

Figures are single-series categorical bar charts (one accent hue, recessive grid,
direct value labels) so they read cleanly when the report is turned into slides.
Company size is ordinal, so the industry x size view uses a light->dark sequential
ramp rather than arbitrary categorical colors.

The detectability pass scores each email on features commonly used by phishing
detectors and measures corpus-level template repetition. Numbers are reported as
observations, not judgements.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import dimensions as D  # noqa: E402

# One accent hue + ordinal ramp (dark text on light surface).
ACCENT = "#2f6fb0"
SIZE_RAMP = {"Small": "#bcd3ea", "Medium": "#6fa3d2", "Large": "#2f6fb0"}
INK = "#1b2733"
GRID = "#e4e9ef"


def _style(ax):
    ax.set_facecolor("white")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=INK, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _bar(path, labels, values, title, accent=ACCENT, rotate=0):
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=130)
    colors = accent if isinstance(accent, str) else accent
    bars = ax.bar(range(len(labels)), values, color=colors, width=0.66, zorder=3)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=rotate, ha="right" if rotate else "center", color=INK)
    ax.set_title(title, color=INK, fontsize=12, fontweight="bold", loc="left", pad=12)
    for b, v in zip(bars, values):
        ax.text(b.get_x() + b.get_width() / 2, v, str(v), ha="center", va="bottom",
                color=INK, fontsize=9)
    _style(ax)
    ax.set_ylim(0, max(values) * 1.18 if values else 1)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def _ordered_counts(values, order):
    c = Counter(values)
    return order, [c.get(k, 0) for k in order]


def profile_histograms(core_rows, orgs, outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, Any] = {}

    labels, vals = _ordered_counts([r["industry"] for r in core_rows], D.INDUSTRIES)
    _bar(outdir / "profiles_by_industry.png", labels, vals, "Profiles by industry")
    stats["industry"] = dict(zip(labels, vals))

    labels, vals = _ordered_counts([r["career_stage"] for r in core_rows], D.CAREER_STAGES)
    _bar(outdir / "profiles_by_career_stage.png", labels, vals, "Profiles by career stage")
    stats["career_stage"] = dict(zip(labels, vals))

    o_by_id = {o["org_id"]: o for o in orgs}
    sizes = [o_by_id[r["org_id"]]["size"] for r in core_rows]
    labels, vals = _ordered_counts(sizes, D.COMPANY_SIZES)
    _bar(outdir / "profiles_by_company_size.png", labels, vals,
         "Profiles by company size", accent=[SIZE_RAMP[s] for s in labels])
    stats["company_size"] = dict(zip(labels, vals))

    labels, vals = _ordered_counts([r["target_role"] for r in core_rows], D.TARGET_ROLES)
    _bar(outdir / "profiles_by_target_role.png", labels, vals,
         "Profiles by target role", rotate=35)
    stats["target_role"] = dict(zip(labels, vals))

    labels, vals = _ordered_counts([o["size"] for o in orgs], D.COMPANY_SIZES)
    _bar(outdir / "orgs_by_size.png", labels, vals, "Companies by size",
         accent=[SIZE_RAMP[s] for s in labels])
    stats["org_size"] = dict(zip(labels, vals))

    labels, vals = _ordered_counts([o["industry"] for o in orgs], D.INDUSTRIES)
    _bar(outdir / "orgs_by_industry.png", labels, vals, "Companies by industry")
    stats["org_industry"] = dict(zip(labels, vals))

    return stats


# --- Detectability ----------------------------------------------------------

SECRECY = re.compile(r"\b(between us|discreet|confidential|don't loop|keep this)\b", re.I)
TIME_PRESSURE = re.compile(r"\b(today|24 hours|before close|immediately|urgent|asap)\b", re.I)
LINK = re.compile(r"https?://")


def _domain(addr: str) -> str:
    return addr.split("@")[-1].strip().lower()


def email_detectability(email_rows, orgs, outdir: Path) -> dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)
    o_by_id = {o["org_id"]: o for o in orgs}

    feats = {"has_link": 0, "high_urgency": 0, "secrecy_language": 0,
             "time_pressure": 0, "sender_domain_mismatch": 0, "financial_action": 0}
    scores: list[float] = []
    body_sigs: list[str] = []

    for e in email_rows:
        body = e["body"]
        org = o_by_id[e["org_id"]]
        has_link = bool(LINK.search(body))
        high_urg = e["urgency"] == "high"
        secrecy = bool(SECRECY.search(body))
        tpress = bool(TIME_PRESSURE.search(body + " " + e["subject"]))
        mismatch = _domain(e["sender_address"]) != org["domain"].lower()
        financial = e["scenario"] in ("BEC wire transfer", "Invoice approval", "Payroll redirect")

        feats["has_link"] += has_link
        feats["high_urgency"] += high_urg
        feats["secrecy_language"] += secrecy
        feats["time_pressure"] += tpress
        feats["sender_domain_mismatch"] += mismatch
        feats["financial_action"] += financial

        w = {"has_link": .18, "high_urgency": .16, "secrecy_language": .18,
             "time_pressure": .14, "sender_domain_mismatch": .20, "financial_action": .14}
        s = (w["has_link"] * has_link + w["high_urgency"] * high_urg
             + w["secrecy_language"] * secrecy + w["time_pressure"] * tpress
             + w["sender_domain_mismatch"] * mismatch + w["financial_action"] * financial)
        scores.append(round(s, 3))

        # Template signature: normalized first 12 tokens of the body.
        toks = re.findall(r"[a-z']+", body.lower())
        body_sigs.append(" ".join(toks[3:15]))

    n = len(email_rows)
    # Prevalence bars.
    flabels = list(feats)
    fvals = [round(100 * feats[k] / n) for k in flabels]
    _bar(outdir / "email_feature_prevalence.png",
         [k.replace("_", " ") for k in flabels], fvals,
         "Detector-relevant features (% of emails)", rotate=35)

    # Scenario distribution.
    sc = Counter(e["scenario"] for e in email_rows)
    _bar(outdir / "email_scenarios.png", list(sc), list(sc.values()),
         "Spear-email scenarios", rotate=35)

    # Urgency.
    ul, uv = _ordered_counts([e["urgency"] for e in email_rows], ["low", "medium", "high"])
    _bar(outdir / "email_urgency.png", ul, uv, "Email urgency")

    # Detectability score histogram.
    fig, ax = plt.subplots(figsize=(7.2, 4.2), dpi=130)
    ax.hist(scores, bins=[0, .15, .3, .45, .6, .75, .9, 1.0], color=ACCENT, zorder=3,
            edgecolor="white")
    ax.set_title("Heuristic detectability score per email", color=INK, fontsize=12,
                 fontweight="bold", loc="left", pad=12)
    ax.set_xlabel("score (0 = few signals, 1 = many)", color=INK, fontsize=9)
    _style(ax)
    fig.tight_layout()
    fig.savefig(outdir / "email_detectability_score.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

    distinct_sigs = len(set(body_sigs))
    all_tokens = [t for e in email_rows for t in re.findall(r"[a-z']+", e["body"].lower())]
    ttr = round(len(set(all_tokens)) / max(1, len(all_tokens)), 4)

    return {
        "n": n,
        "feature_prevalence_pct": dict(zip(flabels, fvals)),
        "scenario_counts": dict(sc),
        "mean_detectability": round(sum(scores) / max(1, n), 3),
        "distinct_body_signatures": distinct_sigs,
        "corpus_type_token_ratio": ttr,
        "scores": scores,
    }
