n = 100 sampled profiles

### Implementation checks (marginals drawn directly from the sources)

| Quantity | n | TV distance | chi-square p |
|---|---|---|---|
| Industry mix (BLS CES) | 100 | 0.8102 | 0.0 |
| Firm-size class, Tech (Census SUSB, employee-weighted) | 100 | 0.6677 | 0.0 |
| Role mix, Tech (BLS OEWS) | 100 | 0.0899 | 0.562 |

**Sex by role** (observed share of women vs CPS target; z = binomial z-score)

| Role | n | observed | target | z |
|---|---|---|---|---|
| Executive / senior leader | 16 | 0.312 | 0.418 | -0.86 |
| Engineer / researcher | 41 | 0.098 | 0.203 | -1.68 |
| Legal / compliance | 17 | 0.471 | 0.543 | -0.6 |

**Highest education by role** (age 26+; BLS EP 5.3 target)

| Role | n | TV distance | chi-square p |
|---|---|---|---|
| Engineer / researcher | 32 | 0.1167 | 0.755 |

### Held-out checks (not fit directly)

| Quantity | observed | target | note |
|---|---|---|---|
| Median tenure, age 25+ (BLS Jan 2026: 4.9 yrs) | 4.72 | 4.9 | Sampler uses medians by age band only; the overall median is not fit. |
| Median tenure, all (BLS: 4.1 yrs) | 3.88 | 4.1 | Prime-target occupations skew older than all workers; Students cap tenure at 2 yrs. |
| Median tenure, age 25-34 | 2.57 | 3.0 | n=25; tenure capped at time in labor force |
| Median tenure, age 35-44 | 3.49 | 4.7 | n=21; tenure capped at time in labor force |
| Median age, all sampled (CPS all-employed: 42.1) | 40.5 | 42.1 | Roles skew older than all workers |
| LinkedIn use, college graduates (Pew 2026: 51%) | 0.464 | 0.51 | n=69; our sample skews 30-55, Pew averages all adults |
| Mean simulated-phish click probability (KnowBe4: ~27% avg, 2025 baseline 33.1%) | 0.235 | 0.27-0.33 | Inputs: industry x size baseline, training factor, new-hire factor |
| Mean baseline phish-prone % before training factor (KnowBe4 older edition avg ~27%) | 0.289 | 0.27 | Industry x size matrix weighted by this sample's mix |
| Share of new hires (tenure <= 90 days) | 0.04 | derived | Implied by exponential tenure model; no direct benchmark |
| Median email checks per day (Mark 2016: 77) | 80.0 | 77.0 |  |
| Mean emails received per day (Microsoft 2025: 117) | 111.8 | 117.0 | Role factors raise it slightly |
| Share in inbox by 10 pm (Microsoft 2025: 29%) | 0.33 | 0.29 |  |

### Distributions of derived labels (no benchmark)

- **career_stage**: {'Mid Level': 54, 'Entry Level': 14, 'High Level': 17, 'Executive': 11, 'Student': 4}
- **security_awareness**: {'medium': 64, 'high': 23, 'low': 13}
- **busy_level**: {'medium': 62, 'low': 17, 'high': 21}
- **footprint_level**: {'low': 20, 'high': 39, 'medium': 41}
- **company_size**: {'Large': 100}
- **gender**: {'man': 71, 'woman': 29}
- **platforms**: {'Facebook': 68, 'GitHub': 25, 'ResearchGate': 10, 'LinkedIn': 44, 'Instagram': 59, 'X': 17}
- **highest_education**: {'doctoral': 8, 'bachelor': 39, 'associate': 6, 'some_college': 12, 'master': 22, 'high_school': 12, 'less_than_hs': 1}
- **n_orgs**: 1

### Distinctness

- unique_names: 100
- unique_first: 81
- unique_last: 94
- unique_titles: 46
- unique_schools: 106
- duplicate_org_domains: 0