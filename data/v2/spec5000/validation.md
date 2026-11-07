n = 5000 sampled profiles

### Implementation checks (marginals drawn directly from the sources)

| Quantity | n | TV distance | chi-square p |
|---|---|---|---|
| Industry mix (BLS CES) | 5000 | 0.01 | 0.543 |
| Firm-size class, Finance (Census SUSB, employee-weighted) | 440 | 0.0692 | 0.057 |
| Firm-size class, Healthcare (Census SUSB, employee-weighted) | 1724 | 0.0075 | 0.929 |
| Firm-size class, Tech (Census SUSB, employee-weighted) | 947 | 0.0238 | 0.52 |
| Firm-size class, Government (Census SUSB, employee-weighted) [assumed targets] | 860 | 0.0365 | 0.157 |
| Firm-size class, Education (Census SUSB, employee-weighted) | 1029 | 0.0477 | 0.007 |
| Role mix, Finance (BLS OEWS) | 440 | 0.0431 | 0.74 |
| Role mix, Healthcare (BLS OEWS) | 1724 | 0.0258 | 0.252 |
| Role mix, Tech (BLS OEWS) | 947 | 0.0221 | 0.786 |
| Role mix, Government (BLS OEWS) | 860 | 0.0406 | 0.363 |
| Role mix, Education (BLS OEWS) | 1029 | 0.0381 | 0.372 |

**Sex by role** (observed share of women vs CPS target; z = binomial z-score)

| Role | n | observed | target | z |
|---|---|---|---|---|
| Executive / senior leader | 839 | 0.398 | 0.418 | -1.17 |
| Finance / accounting | 896 | 0.679 | 0.689 | -0.67 |
| HR / payroll | 436 | 0.823 | 0.783 | 2.05 |
| IT admin / help desk | 563 | 0.297 | 0.271 | 1.38 |
| Executive assistant | 267 | 0.948 | 0.935 | 0.83 |
| Engineer / researcher | 1410 | 0.201 | 0.203 | -0.15 |
| Legal / compliance | 412 | 0.566 | 0.543 | 0.9 |
| Government / defense personnel | 50 | 0.44 | 0.471 | -0.44 |
| Journalist / communications | 127 | 0.37 | 0.411 | -0.94 |

**Highest education by role** (age 26+; BLS EP 5.3 target)

| Role | n | TV distance | chi-square p |
|---|---|---|---|
| Executive / senior leader | 804 | 0.0093 | 0.974 |
| Finance / accounting | 873 | 0.0265 | 0.594 |
| HR / payroll | 393 | 0.0439 | 0.197 |
| IT admin / help desk | 506 | 0.0582 | 0.033 |
| Executive assistant | 262 | 0.0607 | 0.227 |
| Engineer / researcher | 1163 | 0.0208 | 0.776 |
| Legal / compliance | 392 | 0.0353 | 0.901 |
| Government / defense personnel | 50 | 0.099 | 0.62 |
| Journalist / communications | 113 | 0.0803 | 0.083 |

### Held-out checks (not fit directly)

| Quantity | observed | target | note |
|---|---|---|---|
| Median tenure, age 25+ (BLS Jan 2026: 4.9 yrs) | 5.27 | 4.9 | Sampler uses medians by age band only; the overall median is not fit. |
| Median tenure, all (BLS: 4.1 yrs) | 4.66 | 4.1 | Prime-target occupations skew older than all workers; Students cap tenure at 2 yrs. |
| Median tenure, age 18-19 | 1.77 | 1.5 | n=81; tenure capped at time in labor force |
| Median tenure, age 20-24 | 1.0 | 1.5 | n=267; tenure capped at time in labor force |
| Median tenure, age 25-34 | 2.54 | 3.0 | n=1086; tenure capped at time in labor force |
| Median tenure, age 35-44 | 4.54 | 4.7 | n=1158; tenure capped at time in labor force |
| Median tenure, age 45-54 | 7.1 | 7.0 | n=1054; tenure capped at time in labor force |
| Median tenure, age 55-64 | 9.48 | 9.6 | n=902; tenure capped at time in labor force |
| Median tenure, age 65-99 | 10.65 | 9.9 | n=452; tenure capped at time in labor force |
| Median age, Executive / senior leader (CPS 11b) | 47.0 | 46.1 | n=839; role medians are cross-industry |
| Median age, Finance / accounting (CPS 11b) | 47.5 | 46.8 | n=896; role medians are cross-industry |
| Median age, HR / payroll (CPS 11b) | 42.0 | 42.0 | n=436; role medians are cross-industry |
| Median age, IT admin / help desk (CPS 11b) | 43.0 | 42.6 | n=563; role medians are cross-industry |
| Median age, Executive assistant (CPS 11b) | 49.0 | 47.6 | n=267; role medians are cross-industry |
| Median age, Engineer / researcher (CPS 11b) | 38.5 | 38.6 | n=1410; role medians are cross-industry |
| Median age, Legal / compliance (CPS 11b) | 46.0 | 45.8 | n=412; role medians are cross-industry |
| Median age, Journalist / communications (CPS 11b) | 41.0 | 41.4 | n=127; role medians are cross-industry |
| Median age, all sampled (CPS all-employed: 42.1) | 44.0 | 42.1 | Roles skew older than all workers |
| LinkedIn use, college graduates (Pew 2026: 51%) | 0.519 | 0.51 | n=3160; our sample skews 30-55, Pew averages all adults |
| LinkedIn use, HS or less (Pew 2026: 13%) | 0.162 | 0.13 | n=402; age 25+, excluding the 500+-firm executive override |
| Mean simulated-phish click probability (KnowBe4: ~27% avg, 2025 baseline 33.1%) | 0.233 | 0.27-0.33 | Inputs: industry x size baseline, training factor, new-hire factor |
| Mean baseline phish-prone % before training factor (KnowBe4 older edition avg ~27%) | 0.265 | 0.27 | Industry x size matrix weighted by this sample's mix |
| Share of new hires (tenure <= 90 days) | 0.046 | derived | Implied by exponential tenure model; no direct benchmark |
| Median email checks per day (Mark 2016: 77) | 76.7 | 77.0 |  |
| Mean emails received per day (Microsoft 2025: 117) | 125.3 | 117.0 | Role factors raise it slightly |
| Share in inbox by 10 pm (Microsoft 2025: 29%) | 0.281 | 0.29 |  |

### Distributions of derived labels (no benchmark)

- **career_stage**: {'Mid Level': 3023, 'Entry Level': 313, 'High Level': 793, 'Executive': 654, 'Student': 217}
- **security_awareness**: {'low': 769, 'medium': 2975, 'high': 1256}
- **busy_level**: {'medium': 2722, 'low': 927, 'high': 1351}
- **footprint_level**: {'high': 2030, 'medium': 1730, 'low': 1240}
- **company_size**: {'Small': 1147, 'Large': 3146, 'Medium': 707}
- **gender**: {'man': 2693, 'woman': 2307}
- **platforms**: {'LinkedIn': 2243, 'Facebook': 3674, 'GitHub': 953, 'ResearchGate': 263, 'Instagram': 2798, 'X': 792}
- **highest_education**: {'master': 878, 'bachelor': 1958, 'high_school': 636, 'less_than_hs': 74, 'some_college': 724, 'doctoral': 324, 'associate': 406}
- **n_orgs**: 1144

### Distinctness

- unique_names: 5000
- unique_first: 1206
- unique_last: 2885
- unique_titles: 105
- unique_schools: 1334
- duplicate_org_domains: 0