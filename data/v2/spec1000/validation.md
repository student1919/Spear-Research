n = 1000 sampled profiles

### Implementation checks (marginals drawn directly from the sources)

| Quantity | n | TV distance | chi-square p |
|---|---|---|---|
| Industry mix (BLS CES) | 1000 | 0.0199 | 0.305 |
| Firm-size class, Finance (Census SUSB, employee-weighted) | 73 | 0.1265 | 0.117 |
| Firm-size class, Healthcare (Census SUSB, employee-weighted) | 342 | 0.028 | 0.806 |
| Firm-size class, Tech (Census SUSB, employee-weighted) | 193 | 0.0437 | 0.688 |
| Firm-size class, Government (Census SUSB, employee-weighted) [assumed targets] | 183 | 0.0543 | 0.154 |
| Firm-size class, Education (Census SUSB, employee-weighted) | 209 | 0.0638 | 0.096 |
| Role mix, Finance (BLS OEWS) | 73 | 0.1195 | 0.552 |
| Role mix, Healthcare (BLS OEWS) | 342 | 0.0479 | 0.766 |
| Role mix, Tech (BLS OEWS) | 193 | 0.0404 | 0.708 |
| Role mix, Government (BLS OEWS) | 183 | 0.0826 | 0.501 |
| Role mix, Education (BLS OEWS) | 209 | 0.096 | 0.212 |

**Sex by role** (observed share of women vs CPS target; z = binomial z-score)

| Role | n | observed | target | z |
|---|---|---|---|---|
| Executive / senior leader | 158 | 0.462 | 0.418 | 1.12 |
| Finance / accounting | 184 | 0.728 | 0.689 | 1.15 |
| HR / payroll | 82 | 0.768 | 0.783 | -0.32 |
| IT admin / help desk | 103 | 0.282 | 0.271 | 0.25 |
| Executive assistant | 42 | 0.929 | 0.935 | -0.17 |
| Engineer / researcher | 296 | 0.247 | 0.203 | 1.87 |
| Legal / compliance | 89 | 0.517 | 0.543 | -0.5 |
| Government / defense personnel | 19 | 0.474 | 0.471 | 0.02 |
| Journalist / communications | 27 | 0.37 | 0.411 | -0.43 |

**Highest education by role** (age 26+; BLS EP 5.3 target)

| Role | n | TV distance | chi-square p |
|---|---|---|---|
| Executive / senior leader | 149 | 0.0567 | 0.765 |
| Finance / accounting | 181 | 0.0535 | 0.708 |
| HR / payroll | 73 | 0.1183 | 0.254 |
| IT admin / help desk | 87 | 0.1392 | 0.049 |
| Executive assistant | 41 | 0.1118 | 0.837 |
| Engineer / researcher | 247 | 0.0627 | 0.461 |
| Legal / compliance | 86 | 0.0813 | 0.444 |

### Held-out checks (not fit directly)

| Quantity | observed | target | note |
|---|---|---|---|
| Median tenure, age 25+ (BLS Jan 2026: 4.9 yrs) | 5.28 | 4.9 | Sampler uses medians by age band only; the overall median is not fit. |
| Median tenure, all (BLS: 4.1 yrs) | 4.66 | 4.1 | Prime-target occupations skew older than all workers; Students cap tenure at 2 yrs. |
| Median tenure, age 20-24 | 1.0 | 1.5 | n=59; tenure capped at time in labor force |
| Median tenure, age 25-34 | 3.0 | 3.0 | n=207; tenure capped at time in labor force |
| Median tenure, age 35-44 | 4.26 | 4.7 | n=259; tenure capped at time in labor force |
| Median tenure, age 45-54 | 7.22 | 7.0 | n=212; tenure capped at time in labor force |
| Median tenure, age 55-64 | 9.44 | 9.6 | n=163; tenure capped at time in labor force |
| Median tenure, age 65-99 | 10.3 | 9.9 | n=84; tenure capped at time in labor force |
| Median age, Executive / senior leader (CPS 11b) | 44.0 | 46.1 | n=158; role medians are cross-industry |
| Median age, Finance / accounting (CPS 11b) | 49.5 | 46.8 | n=184; role medians are cross-industry |
| Median age, HR / payroll (CPS 11b) | 41.0 | 42.0 | n=82; role medians are cross-industry |
| Median age, IT admin / help desk (CPS 11b) | 40.0 | 42.6 | n=103; role medians are cross-industry |
| Median age, Engineer / researcher (CPS 11b) | 39.0 | 38.6 | n=296; role medians are cross-industry |
| Median age, Legal / compliance (CPS 11b) | 44.0 | 45.8 | n=89; role medians are cross-industry |
| Median age, all sampled (CPS all-employed: 42.1) | 43.0 | 42.1 | Roles skew older than all workers |
| LinkedIn use, college graduates (Pew 2026: 51%) | 0.531 | 0.51 | n=650; our sample skews 30-55, Pew averages all adults |
| LinkedIn use, HS or less (Pew 2026: 13%) | 0.169 | 0.13 | n=77; age 25+, excluding the 500+-firm executive override |
| Mean simulated-phish click probability (KnowBe4: ~27% avg, 2025 baseline 33.1%) | 0.241 | 0.27-0.33 | Inputs: industry x size baseline, training factor, new-hire factor |
| Mean baseline phish-prone % before training factor (KnowBe4 older edition avg ~27%) | 0.266 | 0.27 | Industry x size matrix weighted by this sample's mix |
| Share of new hires (tenure <= 90 days) | 0.045 | derived | Implied by exponential tenure model; no direct benchmark |
| Median email checks per day (Mark 2016: 77) | 77.2 | 77.0 |  |
| Mean emails received per day (Microsoft 2025: 117) | 123.5 | 117.0 | Role factors raise it slightly |
| Share in inbox by 10 pm (Microsoft 2025: 29%) | 0.304 | 0.29 |  |

### Distributions of derived labels (no benchmark)

- **career_stage**: {'High Level': 152, 'Mid Level': 615, 'Entry Level': 55, 'Student': 50, 'Executive': 128}
- **security_awareness**: {'medium': 611, 'high': 227, 'low': 162}
- **busy_level**: {'high': 278, 'medium': 528, 'low': 194}
- **footprint_level**: {'high': 422, 'medium': 349, 'low': 229}
- **company_size**: {'Large': 620, 'Small': 233, 'Medium': 147}
- **gender**: {'man': 524, 'woman': 476}
- **platforms**: {'Instagram': 554, 'GitHub': 208, 'LinkedIn': 470, 'Facebook': 725, 'X': 166, 'ResearchGate': 57}
- **highest_education**: {'master': 163, 'bachelor': 416, 'high_school': 130, 'associate': 78, 'some_college': 129, 'doctoral': 71, 'less_than_hs': 13}
- **n_orgs**: 246

### Distinctness

- unique_names: 1000
- unique_first: 516
- unique_last: 786
- unique_titles: 85
- unique_schools: 581
- duplicate_org_domains: 0