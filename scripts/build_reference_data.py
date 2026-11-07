#!/usr/bin/env python3
"""Build the compact reference tables in data/reference/ from public raw files.

Raw inputs (download first; URLs are listed in config/sources.py):
  --ipeds-dir   folder holding HD2023.csv and C2023_a.csv (NCES IPEDS, 2022-23 completions)
  --surnames    Names_2010Census.csv (Census Bureau 2010 surnames)
  --ssa         baby-names.csv (SSA given names by year/sex, top 1000/yr, through 2008)

Outputs:
  institutions.csv        unitid,name,city,state,control
  completions.csv         unitid,level,field,count   (degrees awarded 2022-23)
  surnames.csv            name,count,pctwhite,pctblack,pctapi,pctaian,pct2prace,pcthispanic (top N)
  given_names.csv         decade,sex,name,weight
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

CIP2_FIELD = {
    52: "business", 11: "computing", 14: "engineering", 15: "engineering", 51: "health",
    13: "education", 22: "law", 45: "social_science", 42: "psychology", 26: "biological",
    9: "communication", 44: "public_admin", 27: "math_stat", 40: "physical_science",
    23: "humanities", 24: "humanities", 16: "humanities", 54: "humanities", 38: "humanities",
    43: "security_justice", 30: "interdisciplinary",
}
LEVELS = {3: "associate", 5: "bachelor", 7: "master", 17: "doctoral", 18: "doctoral", 19: "doctoral"}
CONTROL = {1: "public", 2: "private nonprofit", 3: "private for-profit"}


def _rd(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path, encoding="latin1")
    d.columns = [c.replace("ï»¿", "").strip() for c in d.columns]
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ipeds-dir", required=True)
    ap.add_argument("--surnames", required=True)
    ap.add_argument("--ssa", required=True)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "data" / "reference"))
    ap.add_argument("--top-surnames", type=int, default=20000)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    ip = Path(a.ipeds_dir)
    hd = _rd(ip / "HD2023.csv")[["UNITID", "INSTNM", "CITY", "STABBR", "CONTROL"]]
    hd = hd[hd.CONTROL.isin(CONTROL)].copy()
    hd["control"] = hd.CONTROL.map(CONTROL)
    c = _rd(ip / "C2023_a.csv")
    c = c[(c.MAJORNUM == 1) & (c.AWLEVEL.isin(LEVELS)) & (c.CIPCODE != 99)].copy()
    c["field"] = c.CIPCODE.astype(int).map(CIP2_FIELD).fillna("other")
    c["level"] = c.AWLEVEL.map(LEVELS)
    # IPEDS lists only 6-digit CIP rows (plus the 99 grand total): group by leading 2 digits
    long = (c.groupby(["UNITID", "level", "field"], as_index=False).CTOTALT.sum()
              .rename(columns={"UNITID": "unitid", "CTOTALT": "count"}))
    long = long[long["count"] > 0]
    long = long[long.unitid.isin(hd.UNITID)]
    long.to_csv(out / "completions.csv", index=False)
    hd[hd.UNITID.isin(long.unitid)].rename(
        columns={"UNITID": "unitid", "INSTNM": "name", "CITY": "city", "STABBR": "state"}
    )[["unitid", "name", "city", "state", "control"]].to_csv(out / "institutions.csv", index=False)

    s = pd.read_csv(a.surnames)
    s = s[s["name"] != "ALL OTHER NAMES"].sort_values("count", ascending=False).head(a.top_surnames)
    for col in ["pctwhite", "pctblack", "pctapi", "pctaian", "pct2prace", "pcthispanic"]:
        s[col] = pd.to_numeric(s[col], errors="coerce")   # '(S)' suppressed cells -> NaN
    s[["name", "count", "pctwhite", "pctblack", "pctapi", "pctaian", "pct2prace", "pcthispanic"]].to_csv(
        out / "surnames.csv", index=False)

    g = pd.read_csv(a.ssa)
    g["decade"] = (g.year // 10) * 10
    g["sex"] = g.sex.map({"boy": "M", "girl": "F"})
    g = g.groupby(["decade", "sex", "name"], as_index=False).percent.sum().rename(columns={"percent": "weight"})
    g.to_csv(out / "given_names.csv", index=False)
    print({p.name: len(pd.read_csv(p)) for p in out.glob("*.csv")})


if __name__ == "__main__":
    main()
