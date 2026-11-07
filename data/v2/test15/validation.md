n = 15 sampled profiles

### Implementation checks (marginals drawn directly from the sources)

| Quantity | n | TV distance | chi-square p |
|---|---|---|---|
| Industry mix (BLS CES) | 15 | 0.1825 | 0.676 |

**Sex by role** (observed share of women vs CPS target; z = binomial z-score)

| Role | n | observed | target | z |
|---|---|---|---|---|

**Highest education by role** (age 26+; BLS EP 5.3 target)

| Role | n | TV distance | chi-square p |
|---|---|---|---|

### Held-out checks (not fit directly)

| Quantity | observed | target | note |
|---|---|---|---|
| Median tenure, age 25+ (BLS Jan 2026: 4.9 yrs) | 5.79 | 4.9 | Sampler uses medians by age band only; the overall median is not fit. |
| Median tenure, all (BLS: 4.1 yrs) | 5.79 | 4.1 | Prime-target occupations skew older than all workers; Students cap tenure at 1 yr. |
| Median age, all sampled (CPS all-employed: 42.1) | 46.0 | 42.1 | Roles skew older than all workers |
| LinkedIn use, college graduates (Pew 2026: 51%) | 0.5 | 0.51 | n=10; our sample skews 30-55, Pew averages all adults |
| Mean simulated-phish click probability (KnowBe4: ~27% avg, 2025 baseline 33.1%) | 0.283 | 0.27-0.33 | Inputs: industry x size baseline, training factor, new-hire factor |
| Mean baseline phish-prone % before training factor (KnowBe4 older edition avg ~27%) | 0.279 | 0.27 | Industry x size matrix weighted by this sample's mix |
| Share of new hires (tenure <= 90 days) | 0.0 | derived | Implied by exponential tenure model; no direct benchmark |
| Median email checks per day (Mark 2016: 77) | 59.2 | 77.0 |  |
| Mean emails received per day (Microsoft 2025: 117) | 151.4 | 117.0 | Role factors raise it slightly |
| Share in inbox by 10 pm (Microsoft 2025: 29%) | 0.267 | 0.29 |  |

### Distributions of derived labels (no benchmark)

- **career_stage**: {'Mid Level': 9, 'Entry Level': 1, 'High Level': 3, 'Executive': 2}
- **security_awareness**: {'medium': 8, 'high': 3, 'low': 4}
- **busy_level**: {'high': 8, 'low': 3, 'medium': 4}
- **footprint_level**: {'high': 7, 'medium': 4, 'low': 4}
- **company_size**: {'Small': 6, 'Large': 9}
- **gender**: {'man': 12, 'woman': 3}
- **platforms**: {'Facebook': 11, 'Instagram': 5, 'GitHub': 6, 'LinkedIn': 6, 'ResearchGate': 3, 'X': 1}
- **highest_education**: {'bachelor': 4, 'master': 5, 'associate': 2, 'some_college': 2, 'high_school': 1, 'doctoral': 1}
- **n_orgs**: 10

### Distinctness

- unique_names: 15
- unique_first: 15
- unique_last: 15
- unique_titles: 12
- unique_schools: 19
- duplicate_org_domains: 0