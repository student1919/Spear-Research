"""Source registry: every calibrated number in config/empirical.py cites one of these ids.

status:
  "primary"    -- the primary document/table was opened and the number read from it
  "secondary"  -- seen only in a news/vendor/aggregator page or a search summary
  "derived"    -- computed by us from primary numbers (arithmetic only)
  "assumption" -- no source found; a modeling choice, listed so it can be replaced

Citation metadata marked (CR) was confirmed against the Crossref API during the
research pass; first-name initials for some co-authors were written from memory and
should be re-checked before publication.
"""

from __future__ import annotations

SOURCES: dict[str, dict[str, str]] = {
    # --- U.S. government statistics -------------------------------------
    "susb22": {
        "status": "primary",
        "cite": "U.S. Census Bureau. (2025). 2022 Statistics of U.S. Businesses (SUSB): U.S., states, and NAICS "
                "industries by detailed enterprise employment size [Data table].",
        "url": "https://www2.census.gov/programs-surveys/susb/tables/2022/us_state_naics_detailedsizes_2022.xlsx",
    },
    "ces_b1": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026). The employment situation, September 2026, Table B-1 "
                "(Current Employment Statistics, preliminary) [News release table].",
        "url": "https://www.bls.gov/news.release/empsit.t17.htm",
    },
    "oews23": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2024). Occupational Employment and Wage Statistics, May 2023: "
                "industry-specific estimates for NAICS 51, 52, 54, 61, 62 and government ownership categories "
                "999100/999200/999300 [Data tables]. (May 2024/2025 industry tables could not be retrieved.)",
        "url": "https://www.bls.gov/oes/2023/may/",
    },
    "oews25_nat": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026). Occupational Employment and Wages, May 2025, "
                "Table 1 [News release table].",
        "url": "https://www.bls.gov/news.release/ocwage.t01.htm",
    },
    "aspep24": {
        "status": "primary",
        "cite": "U.S. Census Bureau. (2025). Annual Survey of Public Employment & Payroll, March 2024.",
        "url": "https://www.census.gov/library/publications/2025/econ/g25-aspep.html",
    },
    "bls_ep53": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2024). Educational attainment for workers 25 years and older by "
                "detailed occupation (Employment Projections Table 5.3, 2023-24) [Data table].",
        "url": "https://www.bls.gov/emp/tables/educational-attainment.htm",
    },
    "cps11": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026). Employed persons by detailed occupation, sex, race, and "
                "Hispanic or Latino ethnicity, 2025 annual averages (Current Population Survey Table 11; 11-month "
                "average excluding October) [Data table].",
        "url": "https://www.bls.gov/cps/cpsaat11.htm",
    },
    "cps11b": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026). Employed persons by detailed occupation and age, 2025 "
                "annual averages (Current Population Survey Table 11b) [Data table].",
        "url": "https://www.bls.gov/cps/cpsaat11b.htm",
    },
    "cps18b": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026). Employed persons by detailed industry and age, 2025 annual "
                "averages (Current Population Survey Table 18b) [Data table].",
        "url": "https://www.bls.gov/cps/cpsaat18b.htm",
    },
    "bls_tenure26": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026, September 24). Employee tenure in 2026 (USDL-26-1532) "
                "[News release].",
        "url": "https://www.bls.gov/news.release/tenure.nr0.htm",
    },
    "atus25": {
        "status": "primary",
        "cite": "U.S. Bureau of Labor Statistics. (2026). American Time Use Survey 2025 results [News release].",
        "url": "https://www.bls.gov/news.release/atus.nr0.htm",
    },
    "ncesdigest": {
        "status": "primary",
        "cite": "National Center for Education Statistics. (2023). Digest of Education Statistics, Tables 303.70, "
                "317.10 and 322.10 [Data tables].",
        "url": "https://nces.ed.gov/programs/digest/",
    },
    "ipeds23": {
        "status": "primary",
        "cite": "National Center for Education Statistics. (2024). Integrated Postsecondary Education Data System "
                "(IPEDS): Institutional Characteristics (HD2023) and Completions by CIP code (C2023_A), 2022-23 "
                "[Data files].",
        "url": "https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx",
    },
    "census_surnames": {
        "status": "primary",
        "cite": "U.S. Census Bureau. (2016). Frequently occurring surnames from the 2010 Census [Data file].",
        "url": "https://www2.census.gov/topics/genealogy/2010surnames/names.zip",
    },
    "ssa_names": {
        "status": "secondary",
        "cite": "Wickham, H. (n.d.). data-baby-names: U.S. Social Security Administration baby names, 1880-2008, "
                "top 1,000 per year and sex [GitHub mirror; the SSA site blocked automated download].",
        "url": "https://github.com/hadley/data-baby-names",
    },
    # --- Online presence ---------------------------------------------------
    "pew26": {
        "status": "primary",
        "cite": "Pew Research Center. (2026). Social media fact sheet (National Public Opinion Reference Survey, "
                "n = 5,511 U.S. adults, fielded Jan 30-Jun 18, 2026).",
        "url": "https://www.pewresearch.org/internet/fact-sheet/social-media/",
    },
    "ms_wti25": {
        "status": "primary",
        "cite": "Microsoft. (2025, June). Breaking down the infinite workday (Work Trend Index special report; "
                "31,000 knowledge workers).",
        "url": "https://www.microsoft.com/en-us/worklab/work-trend-index/breaking-down-infinite-workday",
    },
    "mark16": {
        "status": "primary",
        "cite": "Mark, G., Iqbal, S. T., Czerwinski, M., Johns, P., & Sano, A. (2016). Email duration, batching and "
                "self-interruption: Patterns of email use on productivity and stress. Proceedings of CHI 2016, "
                "1717-1728. (n = 40 information workers, 12 workdays.)",
        "url": "https://doi.org/10.1145/2858036.2858262",
    },
    "so25": {
        "status": "primary",
        "cite": "Stack Overflow. (2025). 2025 Developer Survey (n > 49,000).",
        "url": "https://survey.stackoverflow.co/2025/",
    },
    "octoverse25": {
        "status": "primary",
        "cite": "GitHub. (2025). Octoverse 2025: A new developer joins GitHub every second.",
        "url": "https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/",
    },
    "ceo_social23": {
        "status": "secondary",
        "cite": "Influential Executive. (2023). How many Fortune 500 CEOs are on social media? (consultancy "
                "sample, size not stated).",
        "url": "https://influentialexecutive.com/how-many-fortune-500-ceos-on-social-media-2023/",
    },
    "academic_profiles": {
        "status": "secondary",
        "cite": "Share of researchers with a ResearchGate or Google Scholar profile: 37% (University of Bergen, "
                "BORA 1956/11035), 39% (Spanish sample, Ortega, 2015, via search summary), 78% (University of "
                "Saskatchewan science faculty, n = 129, Issues in Science and Technology Librarianship).",
        "url": "https://bora.uib.no/handle/1956/11035",
    },
    "linkedin_posting": {
        "status": "secondary",
        "cite": "About 1% of LinkedIn users post weekly (1.4% in one source); traced to 2019 session data and "
                "aggregator blogs (AuthoredUp; ContentIn). Weak lineage.",
        "url": "https://authoredup.com/blog/linkedin-content-creator",
    },
    "rapid7_exec": {
        "status": "secondary",
        "cite": "Rapid7. (2025). Executive digital footprint report (about 60% of an individual's digital risk "
                "exposure is retrievable by a simple surface-web search).",
        "url": "https://rapid7.com/blog/",
    },
    # --- Phishing susceptibility / targeting -------------------------------
    "knowbe4_25": {
        "status": "primary",
        "cite": "KnowBe4. (2025). 2025 Phishing by Industry Benchmarking Report (67.7M simulated tests, 62,400 "
                "organizations; baseline phish-prone percentage 33.1%, 4.1% after 12 months).",
        "url": "https://www.knowbe4.com/resources/reports/2025-phishing-by-industry-benchmarking-report",
    },
    "knowbe4_old": {
        "status": "primary",
        "cite": "KnowBe4. (n.d.). Phishing attack landscape and benchmarking (undated edition; about 11K "
                "organizations, > 6M users). Baseline phish-prone percentage by industry and organization size "
                "(1-249 / 250-999 / 1000+ employees).",
        "url": "https://www.knowbe4.com/hubfs/PhishingAttackLandscapeandBenchmarking.pdf",
    },
    "verizon_dbir25": {
        "status": "primary",
        "cite": "Verizon. (2025). 2025 Data Breach Investigations Report.",
        "url": "https://www.verizon.com/business/resources/reports/2025-dbir-data-breach-investigations-report.pdf",
    },
    "ho25": {
        "status": "primary",
        "cite": "Ho, G., Mirian, A., Luo, E., Tong, K., Lee, E., Liu, L., Longhurst, C. A., Dameff, C., Savage, S., & "
                "Voelker, G. M. (2025). Understanding the efficacy of phishing training in practice. 2025 IEEE "
                "Symposium on Security and Privacy (SP), 37-54. (CR)",
        "url": "https://doi.org/10.1109/SP61157.2025.00076",
    },
    "lain22": {
        "status": "primary",
        "cite": "Lain, D., Kostiainen, K., & Capkun, S. (2022). Phishing in organizations: Findings from a "
                "large-scale and long-term study. 2022 IEEE Symposium on Security and Privacy (SP), 842-859. (CR)",
        "url": "https://doi.org/10.1109/SP46214.2022.9833766",
    },
    "sheng10": {
        "status": "primary",
        "cite": "Sheng, S., Holbrook, M., Kumaraguru, P., Cranor, L. F., & Downs, J. (2010). Who falls for phish? "
                "A demographic analysis of phishing susceptibility and effectiveness of interventions. "
                "Proceedings of CHI 2010, 373-382. (CR)",
        "url": "https://doi.org/10.1145/1753326.1753383",
    },
    "oliveira17": {
        "status": "primary",
        "cite": "Oliveira, D., Rocha, H., Yang, H., Ellis, D., Dommaraju, S., Muradoglu, M., Weir, D., Soliman, A., "
                "Lin, T., & Ebner, N. (2017). Dissecting spear phishing emails for older vs young adults. "
                "Proceedings of CHI 2017, 6412-6424. (CR)",
        "url": "https://doi.org/10.1145/3025453.3025831",
    },
    "ebner20": {
        "status": "primary",
        "cite": "Ebner, N. C., Ellis, D. M., Lin, T., Rocha, H. A., Yang, H., Dommaraju, S., Soliman, A., Woodard, "
                "D. L., Turner, G. R., Spreng, R. N., & Oliveira, D. S. (2020). Uncovering susceptibility risk to "
                "online deception in aging. The Journals of Gerontology: Series B, 75(3), 522-533.",
        "url": "https://doi.org/10.1093/geronb/gby036",
    },
    "vishwanath11": {
        "status": "primary",
        "cite": "Vishwanath, A., Herath, T., Chen, R., Wang, J., & Rao, H. R. (2011). Why do people get phished? "
                "Testing individual differences in phishing vulnerability within an integrated, information "
                "processing model. Decision Support Systems, 51, 576-586. (CR)",
        "url": "https://doi.org/10.1016/j.dss.2011.03.002",
    },
    "williams18": {
        "status": "secondary",
        "cite": "Williams, E. J., Hinds, J., & Joinson, A. N. (2018). Exploring susceptibility to phishing in the "
                "workplace. International Journal of Human-Computer Studies, 120, 1-13. (CR; abstract-level only)",
        "url": "https://doi.org/10.1016/j.ijhcs.2018.06.004",
    },
    "hydari26": {
        "status": "primary",
        "cite": "Hydari, M. Z., Adjerid, I., Lu, Y., & Ramasubbu, N. (2026). Research note: Breaking bad email "
                "habits: Bounding the impact of simulated phishing campaigns (arXiv:2603.04324).",
        "url": "https://arxiv.org/abs/2603.04324",
    },
    "keepnet25": {
        "status": "secondary",
        "cite": "Keepnet Labs. (2025). New hires phishing risk report (237 companies; 71% of new hires fell for "
                "phishing within 90 days, 44% more likely than staff past 90 days). Vendor data via Help Net "
                "Security, June 23, 2025.",
        "url": "https://www.helpnetsecurity.com/2025/06/23/new-hire-phishing-risk/",
    },
    "csbs25": {
        "status": "primary",
        "cite": "Department for Science, Innovation and Technology. (2025). Cyber security breaches survey 2025 "
                "(UK; staff cyber training in the last 12 months: micro 15%, small 34%, medium 54%, large 76%).",
        "url": "https://www.gov.uk/government/statistics/cyber-security-breaches-survey-2025/cyber-security-breaches-survey-2025",
    },
    "barracuda21": {
        "status": "secondary",
        "cite": "Barracuda Networks. (2021). Spear phishing: Top threats and trends, Vol. 6 (CEOs average 57 targeted "
                "attacks per year; IT staff 40; sales receives about 1 in 5 BEC emails). Via Malwarebytes summary.",
        "url": "https://blog.barracuda.com/2021/07/28/spear-phishing-report-attackers-evolving-tactics-and-targets",
    },
    "ic3_25": {
        "status": "primary",
        "cite": "Federal Bureau of Investigation, Internet Crime Complaint Center. (2026). 2025 Internet Crime "
                "Report.",
        "url": "https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf",
    },
    "ic3_psa24": {
        "status": "primary",
        "cite": "Federal Bureau of Investigation, Internet Crime Complaint Center. (2024, September 11). Business "
                "email compromise: The $55 billion scam (Alert I-091124-PSA).",
        "url": "https://www.ic3.gov/PSA/2024/PSA240911",
    },
    "steves20": {
        "status": "primary",
        "cite": "Steves, M., Greene, K., & Theofanos, M. (2020). Categorizing human phishing difficulty: A Phish "
                "Scale. Journal of Cybersecurity, 6(1). (CR)",
        "url": "https://doi.org/10.1093/cybsec/tyaa009",
    },
    "citizenlab16": {
        "status": "primary",
        "cite": "Marczak, B., & Scott-Railton, J. (2016, May 29). Keep calm and (don't) enable macros: A new threat "
                "actor targets UAE dissidents. The Citizen Lab.",
        "url": "https://citizenlab.ca/2016/05/stealth-falcon/",
    },
    "mitre_t1566": {
        "status": "primary",
        "cite": "MITRE. (n.d.). Phishing: Spearphishing attachment (T1566.001), ATT&CK v2.2.",
        "url": "https://attack.mitre.org/techniques/T1566/001/",
    },
    "cisa21": {
        "status": "primary",
        "cite": "Cybersecurity and Infrastructure Security Agency. (2021, February 1). Avoiding social engineering "
                "and phishing attacks.",
        "url": "https://www.cisa.gov/news-events/news/avoiding-social-engineering-and-phishing-attacks",
    },
    # --- Not sourced -------------------------------------------------------
    "ASSUMPTION": {
        "status": "assumption",
        "cite": "Modeling choice with no source found in the research pass. Listed in report/CALIBRATION.md so it "
                "can be replaced when data is found.",
        "url": "",
    },
    "DERIVED": {
        "status": "derived",
        "cite": "Arithmetic on the cited primary numbers (shares, weighted means).",
        "url": "",
    },
}
