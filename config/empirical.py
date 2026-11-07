"""Empirical parameters that drive the profile sampler (src/population.py).

Every block names its source id(s) from config/sources.py. `PARAM_REGISTRY` at the
bottom lists each parameter with its evidence grade so the calibration report can
state what is data, what is derived, and what is still an assumption.

Evidence grades:  data | derived | proxy | assumption
  data        number read from a primary source for exactly this quantity
  derived     arithmetic on primary numbers
  proxy       a primary number for a nearby quantity (e.g. UK data for a U.S. model)
  assumption  no source found; modeling choice
"""

from __future__ import annotations

INDUSTRIES = ["Finance", "Healthcare", "Tech", "Government", "Education"]

# ---------------------------------------------------------------------------
# 1. Industry mix (share of workers)                      src: ces_b1 (derived)
# BLS CES Table B-1, Sept 2026, thousands. Tech = Information + Professional &
# technical services. Government = federal + (state - state education) +
# (local - local education). Education = private educational services + state and
# local government education.
# ---------------------------------------------------------------------------
INDUSTRY_EMPLOYMENT_K = {
    "Finance": 6644.6,
    "Healthcare": 23958.6,
    "Tech": 2739.0 + 10843.6,
    "Government": 2682.0 + (5472.0 - 2601.8) + (15173.0 - 8204.9),
    "Education": 4046.4 + 2601.8 + 8204.9,
}

# ---------------------------------------------------------------------------
# 2. Firm size: share of an industry's employees by enterprise-size class
#    src: susb22 (data; Census SUSB 2022 employment, March 12 pay period)
# Person-level sampling: a randomly chosen employee works at a firm of class c with
# probability employment_c / employment_total.
# Classes: <20, 20-99, 100-499, 500-4,999, 5,000+. Government is not in SUSB.
# ---------------------------------------------------------------------------
SIZE_CLASSES = ["<20", "20-99", "100-499", "500-4999", "5000+"]
SIZE_CLASS_BOUNDS = {"<20": (3, 19), "20-99": (20, 99), "100-499": (100, 499),
                     "500-4999": (500, 4999), "5000+": (5000, 120000)}  # top bound: assumption
SIZE_LABEL = {"<20": "Small", "20-99": "Small", "100-499": "Medium",
              "500-4999": "Large", "5000+": "Large"}

SUSB_EMPLOYMENT = {
    "Finance":    {"<20": 694735, "20-99": 457348, "100-499": 729538, "500-4999": 1401310, "5000+": 3548966},
    "Healthcare": {"<20": 2724620, "20-99": 3104002, "100-499": 3432316, "500-4999": 4483458, "5000+": 7426836},
    "Tech":       {"<20": 2624264, "20-99": 1993292, "100-499": 1978677, "500-4999": 2609431, "5000+": 4580452},
    "Education":  {"<20": 371766, "20-99": 667337, "100-499": 733380, "500-4999": 1073140, "5000+": 898217},
}
# Government: SUSB excludes government; no source found for employees by employer size.
SUSB_EMPLOYMENT["Government"] = {"<20": 1, "20-99": 4, "100-499": 10, "500-4999": 25, "5000+": 60}  # assumption
# All-industry reference (for the "what share of employees are at small/medium/large firms" claim):
SUSB_ALL_EMPLOYMENT = {"<20": 21950184, "20-99": 21976701, "100-499": 18323671,
                       "500-4999": 24187723, "5000+": 49310128}
SUSB_ALL_FIRMS = {"<20": 5720093, "20-99": 561160, "100-499": 93341, "500-4999": 18779, "5000+": 2262}

# ---------------------------------------------------------------------------
# 3. Occupation mix inside an industry     src: oews23 (data), oews25_nat (data)
# OEWS May 2023 employment counts per column; roles are groups of SOC codes.
# Government rows use OEWS ownership columns (federal executive branch, state and
# local government excluding schools/hospitals). Columns per industry below.
# ---------------------------------------------------------------------------
TARGET_ROLES = [
    "Executive / senior leader",
    "Finance / accounting",
    "HR / payroll",
    "IT admin / help desk",
    "Executive assistant",
    "Engineer / researcher",
    "Legal / compliance",
    "Government / defense personnel",
    "Journalist / communications",
]
# New hires are modeled as a tenure flag (is_new_hire), not as an occupation.

_COLS = ["52", "62", "51", "54", "61", "fed", "state", "local"]
OEWS_ROLE_EMPLOYMENT = {
    # 11-1000 top executives
    "Executive / senior leader":  [242570, 184820, 110740, 471550, 85310, 37550, 40790, 115390],
    # 13-2011 accountants + 43-3031 bookkeeping clerks
    "Finance / accounting":       [206560, 168710, 64590, 698590, 116300, 34620, 56180, 109570],
    # 13-1071 HR specialists + 43-3051 payroll clerks
    "HR / payroll":               [52330, 106750, 33600, 157330, 55410, 38210, 19190, 34280],
    # 15-1231/1232/1244 network, support, sysadmin + 15-1299 other computer
    "IT admin / help desk":       [105820, 64840, 164100, 472450, 145990, 84990, 33430, 50770],
    # 43-6011 executive secretaries
    "Executive assistant":        [61970, 50090, 12320, 65000, 69780, 310, 27360, 35520],
    # 15-1252 software developers + 17-0000 architecture/engineering + 19-0000 science
    "Engineer / researcher":      [155760, 161220, 384410, 2067810, 220290, 278510, 171720, 185880],
    # 23-1011 lawyers + 23-2011 paralegals + 13-1041 compliance officers
    "Legal / compliance":         [92190, 37010, 20010, 783230, 18580, 120610, 98620, 106680],
    # 33-0000 protective service, federal executive branch only (OEWS excludes military)
    "Government / defense personnel": [0, 0, 0, 0, 0, 138860, 0, 0],
    # 27-3023 news analysts/reporters + 27-3031 public relations specialists
    "Journalist / communications": [13500, 21730, 55840, 66690, 33470, 6290, 6650, 14580],
}
# Which OEWS columns make up each of our five industries. The role counts above are
# absolute employment, so summing columns weights them correctly.
INDUSTRY_OEWS_COLUMNS = {
    "Finance":    ["52"],
    "Healthcare": ["62"],
    "Tech":       ["51", "54"],
    "Education":  ["61"],
    "Government": ["fed", "state", "local"],
}
OEWS_COLS = _COLS

# Management share check values (oews25_nat): management 11,132,700 / 155,495,730 = 7.16%;
# top executives 3,720,520 -> 2.39%.

# ---------------------------------------------------------------------------
# 4. Age                                             src: cps18b, cps11b (data)
# Industry age bands (thousands employed). Within a band age is uniform; the 16-19
# band is clipped to 18-19 and 65+ to 65-72. A role shift = role median - 42.1
# (all-employed median) is added, then clipped to [18, 72].
# ---------------------------------------------------------------------------
AGE_BANDS = [(18, 19), (20, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 72)]
INDUSTRY_AGE_COUNTS_K = {
    "Finance":    [40, 409, 1928, 2030, 1740, 1380, 469],
    "Healthcare": [382, 1968, 5512, 5486, 4706, 3871, 1594],
    "Tech":       [53 + 84, 168 + 828, 713 + 3763, 723 + 3746, 571 + 2891, 383 + 2140, 176 + 1102],
    "Government": [44, 361, 1696, 2059, 1833, 1462, 488],      # public administration
    "Education":  [299, 1127, 2841, 3281, 3365, 2536, 986],
}
ALL_EMPLOYED_MEDIAN_AGE = 42.1
ROLE_MEDIAN_AGE = {                                             # CPS 11b 2025
    "Executive / senior leader": 46.1,           # management occupations
    "Finance / accounting": 46.8,                # accountants 44.7 (n1766), bookkeeping 49.8 (n1254), emp-weighted
    "HR / payroll": 42.0,
    "IT admin / help desk": 42.6,                # support 42.4 (677), sysadmin 43.8 (154), emp-weighted
    "Executive assistant": 47.6,
    "Engineer / researcher": 38.6,               # proxy: software developers
    "Legal / compliance": 45.8,                  # lawyers 46.4, paralegals 42.8, compliance 47.3, emp-weighted
    "Government / defense personnel": 44.3,      # proxy: public administration industry median
    "Journalist / communications": 41.4,
}

# ---------------------------------------------------------------------------
# 5. Tenure                                                src: bls_tenure26 (data)
# Median years with current employer by age band (Jan 2026). Individual tenure is
# drawn from an exponential with that median (assumption: exponential shape),
# truncated so it cannot exceed time in the labor force.
# ---------------------------------------------------------------------------
TENURE_MEDIAN_BY_AGE = [(18, 19, 1.5), (20, 24, 1.5), (25, 34, 3.0), (35, 44, 4.7),
                        (45, 54, 7.0), (55, 64, 9.6), (65, 99, 9.9)]
# 18-19 uses the 20-24 value (not published separately): assumption.
NEW_HIRE_DAYS = 90        # "new hire" = tenure <= 90 days, the window used in the new-hire phishing study (keepnet25)

# ---------------------------------------------------------------------------
# 6. Sex and race/ethnicity by role (CPS Table 11, 2025)        src: cps11 (data)
# Components are (share women, % Black, % Asian, % Hispanic, employed K) rows for
# the occupations that make up each role; they are employment-weighted below.
# ---------------------------------------------------------------------------
CPS11_ROWS = {
    "management":        (41.8, 8.8, 7.4, 13.5, 20876),
    "accountants":       (59.1, 10.3, 12.7, 11.5, 1766),
    "bookkeeping":       (82.7, 8.4, 6.5, 16.2, 1254),
    "hr":                (78.3, 13.4, 5.6, 16.2, 897),
    "it_support":        (29.1, 13.1, 14.0, 9.2, 677),
    "sysadmin":          (18.2, 17.3, 8.5, 15.3, 154),
    "exec_secretary":    (93.5, 12.1, 4.8, 16.3, 249),
    "software_dev":      (20.3, 5.4, 39.8, 6.1, 2254),
    "lawyers":           (42.9, 5.9, 6.0, 9.2, 1146),
    "paralegals":        (82.4, 11.4, 5.7, 20.4, 486),
    "compliance":        (52.7, 11.9, 12.3, 13.9, 312),
    "reporters":         (41.1, 11.7, 7.0, 6.1, 86),
    "all_employed":      (47.1, 12.7, 7.5, 20.0, 163493),
}
ROLE_CPS_COMPONENTS = {
    "Executive / senior leader": ["management"],
    "Finance / accounting": ["accountants", "bookkeeping"],
    "HR / payroll": ["hr"],
    "IT admin / help desk": ["it_support", "sysadmin"],
    "Executive assistant": ["exec_secretary"],
    "Engineer / researcher": ["software_dev"],                    # proxy
    "Legal / compliance": ["lawyers", "paralegals", "compliance"],
    "Government / defense personnel": ["all_employed"],           # NOT FOUND for protective service: fallback
    "Journalist / communications": ["reporters"],
}

# ---------------------------------------------------------------------------
# 7. Highest education by role (BLS EP Table 5.3, workers 25+)    src: bls_ep53 (data)
# Order: <HS, HS, some college, associate, bachelor, master, doctoral/professional.
# ---------------------------------------------------------------------------
EDU_LEVELS = ["less_than_hs", "high_school", "some_college", "associate", "bachelor", "master", "doctoral"]
EP53_ROWS = {
    "chief_exec":      [1.5, 7.7, 12.5, 5.0, 40.9, 25.3, 7.0],
    "gen_ops_mgr":     [3.3, 17.0, 23.2, 9.6, 33.6, 11.4, 2.0],
    "accountants":     [0.0, 2.2, 3.2, 5.7, 58.9, 26.6, 3.4],
    "bookkeeping":     [4.0, 24.4, 33.5, 16.0, 17.7, 3.7, 0.6],
    "hr_specialists":  [1.2, 9.3, 15.1, 7.9, 45.6, 19.0, 2.0],
    "it_support":      [1.2, 10.7, 23.4, 14.8, 36.4, 11.9, 1.5],
    "sysadmin":        [1.1, 8.2, 22.7, 15.2, 40.1, 11.3, 1.4],
    "exec_secretary":  [1.3, 13.6, 26.5, 12.6, 36.0, 8.9, 1.2],
    "software_dev":    [0.6, 2.2, 7.3, 3.9, 51.7, 30.2, 4.0],
    "lawyers":         [0.4, 0.7, 0.8, 0.4, 6.6, 4.6, 86.5],
    "paralegals":      [1.3, 11.1, 20.3, 17.4, 38.7, 7.6, 3.5],
    "compliance":      [1.1, 10.5, 14.9, 8.8, 39.9, 18.8, 6.0],
    "reporters":       [0.8, 3.0, 5.1, 2.8, 62.1, 23.2, 3.0],
}
# Weights between component rows (employment: CPS K, or OEWS May 2025 for execs).
ROLE_EDU_COMPONENTS = {
    "Executive / senior leader": {"gen_ops_mgr": 3503020, "chief_exec": 204350},
    "Finance / accounting": {"accountants": 1766, "bookkeeping": 1254},
    "HR / payroll": {"hr_specialists": 1},
    "IT admin / help desk": {"it_support": 677, "sysadmin": 154},
    "Executive assistant": {"exec_secretary": 1},
    "Engineer / researcher": {"software_dev": 1},                 # proxy
    "Legal / compliance": {"lawyers": 1146, "paralegals": 486, "compliance": 312},
    "Government / defense personnel": {"compliance": 1},          # NOT FOUND for protective service: proxy
    "Journalist / communications": {"reporters": 1},
}
# Sub-occupation inside a role (same components/weights as above). Education AND title are drawn from the same
# sub-occupation so a paralegal does not get a J.D. while a lawyer's title is chosen independently.
# Minimum age to hold the sub-occupation (assumption).
SUB_MIN_AGE = {"lawyers": 26, "chief_exec": 28}
# ---------------------------------------------------------------------------
# Career stage: share of a role's workers who are managers (the "High Level" stage).   src: oews23, oews25_nat
# manager count (OEWS May 2025) / (manager count + worker count, OEWS May 2023 national):
#   finance:  841,710 / (841,710 + 1,435,770 accountants + 1,501,910 bookkeeping clerks)        = 0.223
#   HR:       220,660 / (220,660 + 895,970 HR specialists + 157,230 payroll clerks)              = 0.173
#   IT:       670,570 / (670,570 + 158,720 + 689,700 + 323,020 network/support/sysadmin)          = 0.364
# Other roles: no ratio retrieved -> assumption (0.15; executive assistants 0.03).
# ---------------------------------------------------------------------------
MANAGER_SHARE = {
    "Finance / accounting": 0.223, "HR / payroll": 0.173, "IT admin / help desk": 0.364,
    "Executive assistant": 0.03, "Engineer / researcher": 0.15, "Legal / compliance": 0.15,
    "Government / defense personnel": 0.15, "Journalist / communications": 0.15,
    "Executive / senior leader": 1.0,
}
MANAGER_MIN_EXPERIENCE = 8      # assumption
# Minimum plausible age by completed level (assumption).
EDU_MIN_AGE = {"less_than_hs": 0, "high_school": 0, "some_college": 0, "associate": 20,
               "bachelor": 21, "master": 23, "doctoral": 26}
EDU_TYPICAL_AGE = {"associate": 20, "bachelor": 22, "master": 24, "doctoral": 28}   # assumption
LABOR_ENTRY_AGE = {"less_than_hs": 17, "high_school": 18, "some_college": 19, "associate": 20,
                   "bachelor": 22, "master": 24, "doctoral": 27}                  # assumption

# Field of study by role: IPEDS field groups. ASSUMPTION (BLS gives level, not field;
# ACS field-of-degree by occupation not obtained).
FIELD_BY_ROLE = {
    "Executive / senior leader": {"business": 0.50, "engineering": 0.12, "social_science": 0.08, "health": 0.06,
                                  "computing": 0.05, "humanities": 0.05, "public_admin": 0.04,
                                  "education": 0.04, "law": 0.03, "other": 0.03},
    "Finance / accounting": {"business": 0.88, "math_stat": 0.04, "social_science": 0.04, "other": 0.04},
    "HR / payroll": {"business": 0.50, "psychology": 0.15, "social_science": 0.10, "communication": 0.08,
                     "humanities": 0.07, "public_admin": 0.05, "other": 0.05},
    "IT admin / help desk": {"computing": 0.55, "engineering": 0.12, "business": 0.10, "math_stat": 0.04,
                             "other": 0.19},
    "Executive assistant": {"business": 0.40, "communication": 0.12, "humanities": 0.12, "other": 0.36},
    "Engineer / researcher": {"computing": 0.35, "engineering": 0.35, "physical_science": 0.08,
                              "biological": 0.10, "math_stat": 0.07, "other": 0.05},
    "Legal / compliance": {"business": 0.25, "social_science": 0.20, "humanities": 0.20, "security_justice": 0.15,
                           "public_admin": 0.10, "other": 0.10},
    "Government / defense personnel": {"security_justice": 0.30, "public_admin": 0.15, "social_science": 0.20,
                                       "business": 0.15, "humanities": 0.10, "other": 0.10},
    "Journalist / communications": {"communication": 0.55, "humanities": 0.25, "social_science": 0.10,
                                    "other": 0.10},
}
# Level-specific overrides of the field distribution (assumption).
FIELD_OVERRIDE = {
    ("Legal / compliance", "doctoral"): {"law": 1.0},
    ("Executive / senior leader", "master"): {"business": 0.65, "engineering": 0.10, "public_admin": 0.08,
                                              "health": 0.07, "education": 0.05, "other": 0.05},
    ("Finance / accounting", "master"): {"business": 0.90, "math_stat": 0.05, "other": 0.05},
    ("Engineer / researcher", "doctoral"): {"engineering": 0.30, "computing": 0.20, "physical_science": 0.18,
                                            "biological": 0.20, "math_stat": 0.12},
}
# Share of workers who attended college but hold no degree get a school sampled from
# bachelor's-awarding institutions (some_college). Associate -> associate-level schools.

# ---------------------------------------------------------------------------
# 8. Online presence                                  src: pew26 (data), others as tagged
# ---------------------------------------------------------------------------
PEW_AGE_BANDS = [(18, 29), (30, 49), (50, 64), (65, 120)]
PEW_LINKEDIN_AGE = [0.41, 0.37, 0.32, 0.13]
PEW_LINKEDIN_EDU = {"hs_or_less": 0.13, "some_college": 0.29, "college": 0.51}
PEW_X_AGE = [0.31, 0.20, 0.17, 0.07]
PEW_X_EDU = {"hs_or_less": 0.14, "some_college": 0.20, "college": 0.22}
PEW_FACEBOOK_AGE = [0.69, 0.78, 0.71, 0.59]
PEW_INSTAGRAM_AGE = [0.79, 0.64, 0.41, 0.21]
PEW_LINKEDIN_OVERALL = 0.33     # Pew overall cells flagged by the fetch tool as column-order inferences
PEW_X_OVERALL = 0.25
# Fortune 500 CEOs (2023): 73% on any social platform, 98% of those on LinkedIn (ceo_social23, secondary).
# Applied to the Executive stage at firms of 500+ employees only.
EXEC_LARGE_FIRM_LINKEDIN = 0.73 * 0.98
# GitHub / ResearchGate: no representative rate found. ASSUMPTION by role (see report).
GITHUB_BY_ROLE = {"Engineer / researcher": 0.55, "IT admin / help desk": 0.22}
GITHUB_DEFAULT = 0.02
RESEARCHGATE_ACADEMIC = 0.39     # academics with a RG/Scholar profile: 37% / 39% / 78% (academic_profiles, secondary)
RESEARCHGATE_OTHER_RESEARCHER = 0.12   # assumption
# Posting: ~1.4% of LinkedIn users post weekly (linkedin_posting, weak). The occasional-poster share
# and the role multipliers are assumptions.
WEEKLY_POSTER_SHARE = 0.014
OCCASIONAL_POSTER_SHARE = 0.18          # assumption: posts a few times a year
POSTER_ROLE_MULTIPLIER = {"Journalist / communications": 6.0, "Executive / senior leader": 2.5}   # assumption
PERSONAL_WEBSITE_SHARE = 0.08           # assumption (raised for academics/engineers in code)

# ---------------------------------------------------------------------------
# 9. Work rhythm                                     src: mark16, ms_wti25 (data)
# ---------------------------------------------------------------------------
EMAIL_CHECKS_PER_DAY_MEDIAN = 77.0      # Mark et al. 2016 (n=40)
EMAIL_CHECKS_SIGMA = 0.45               # assumption (spread)
COMPUTER_HOURS_PER_DAY = 4.5            # Mark et al. 2016 -> ~17 checks per computer-hour (derived)
EMAILS_RECEIVED_MEAN = 117.0            # Microsoft WTI 2025 (knowledge workers)
EMAILS_RECEIVED_SIGMA = 0.6             # assumption
EMAIL_VOLUME_ROLE_FACTOR = {"Executive / senior leader": 1.25, "Executive assistant": 1.25}   # assumption
LATE_NIGHT_INBOX_SHARE = 0.29           # Microsoft WTI 2025: back in inbox by 10 pm
BUSY_THRESHOLDS = (60.0, 150.0)         # emails/day: low < 60 <= medium < 150 <= high (labels anchored on 117 mean)

# ---------------------------------------------------------------------------
# 10. Phishing susceptibility                         src: knowbe4_old, csbs25, keepnet25
# Baseline phish-prone percentage by industry and org size (1-249 / 250-999 / 1000+).
# ---------------------------------------------------------------------------
PPP_BASELINE = {
    "Finance":    [27.41, 28.47, 23.00],      # "Financial Svcs"
    "Healthcare": [29.80, 27.85, 25.60],      # "Healthcare & Pharma"
    "Tech":       [30.68, 30.67, 28.92],      # "Technology"
    "Government": [29.32, 25.12, 20.84],
    "Education":  [29.20, 26.23, 26.05],
}
PPP_SIZE_BREAKS = (250, 1000)
TRAINING_SHARE_BY_HEADCOUNT = [(10, 0.15), (50, 0.34), (250, 0.54), (10**9, 0.76)]   # UK CSBS 2025 (proxy)
TRAINING_FACTOR = 0.80          # assumption: between Ho et al. 2025 (~2% effect) and vendor claims (large effect)
NEW_HIRE_FACTOR = 1.44          # "44% more likely" than staff past 90 days (keepnet25, vendor)
# Beta concentration for person-level spread, solved so that a person-level Beta with mean 5.67% (per-email
# click rate) gives 32.1% of people clicking at least once in 8 emails (lain22: 4,729/14,733). It then predicts
# 30.4% of clickers clicking 2+ times vs 30.6% observed in the same study (held-out confirmation).
PPP_HETEROGENEITY_KAPPA = 16.1
AWARENESS_THRESHOLDS = (0.15, 0.35)   # p_click: high awareness < 0.15 <= medium < 0.35 <= low (labels only)

# ---------------------------------------------------------------------------
# 11. Titles (assumption): realistic title lists per role and career stage.
# ---------------------------------------------------------------------------
TITLES = {
    "Executive / senior leader": {
        "Executive": ["Chief Executive Officer", "Chief Operating Officer", "President", "Chief Financial Officer",
                      "Chief Administrative Officer", "Executive Vice President"],
        "High Level": ["Vice President of Operations", "Senior Director of Operations", "General Manager",
                       "Vice President, Business Services"],
        "Mid Level": ["Director of Operations", "Operations Manager", "Regional Manager"],
        "Entry Level": ["Assistant Operations Manager", "Operations Coordinator"],
        "Student": ["Operations Intern"],
    },
    "Finance / accounting": {
        "Executive": ["Chief Financial Officer", "Controller"],
        "High Level": ["Senior Accounting Manager", "Director of Finance", "Assistant Controller"],
        "Mid Level": ["Senior Accountant", "Accounts Payable Supervisor", "Financial Analyst"],
        "Entry Level": ["Staff Accountant", "Accounts Payable Clerk", "Accounting Associate"],
        "Student": ["Accounting Intern"],
    },
    "HR / payroll": {
        "Executive": ["Chief People Officer"],
        "High Level": ["Director of Human Resources", "Senior HR Business Partner", "Payroll Manager"],
        "Mid Level": ["HR Generalist", "Payroll Specialist", "Benefits Administrator"],
        "Entry Level": ["HR Coordinator", "Payroll Clerk", "Recruiting Coordinator"],
        "Student": ["HR Intern"],
    },
    "IT admin / help desk": {
        "Executive": ["Chief Information Officer"],
        "High Level": ["IT Director", "Senior Systems Administrator", "IT Operations Manager"],
        "Mid Level": ["Systems Administrator", "Network Administrator", "IT Support Lead"],
        "Entry Level": ["Help Desk Technician", "IT Support Specialist"],
        "Student": ["IT Help Desk Intern"],
    },
    "Executive assistant": {
        "Executive": ["Chief of Staff"],
        "High Level": ["Senior Executive Assistant", "Executive Assistant to the CEO"],
        "Mid Level": ["Executive Assistant", "Administrative Business Partner"],
        "Entry Level": ["Administrative Assistant", "Office Coordinator"],
        "Student": ["Administrative Intern"],
    },
    "Engineer / researcher": {
        "Executive": ["Chief Technology Officer", "Chief Scientist"],
        "High Level": ["Principal Engineer", "Senior Research Scientist", "Engineering Director"],
        "Mid Level": ["Senior Software Engineer", "Research Scientist", "Systems Engineer"],
        "Entry Level": ["Software Engineer", "Research Associate", "Junior Engineer"],
        "Student": ["Engineering Intern", "Research Assistant"],
    },
    "Legal / compliance": {
        "Executive": ["General Counsel", "Chief Compliance Officer"],
        "High Level": ["Senior Counsel", "Director of Compliance", "Associate General Counsel"],
        "Mid Level": ["Counsel", "Compliance Manager", "Senior Paralegal"],
        "Entry Level": ["Paralegal", "Compliance Analyst", "Contracts Coordinator"],
        "Student": ["Legal Intern"],
    },
    "Government / defense personnel": {
        "Executive": ["Deputy Director", "Agency Director"],
        "High Level": ["Senior Program Manager", "Branch Chief", "Supervisory Analyst"],
        "Mid Level": ["Program Analyst", "Security Specialist", "Contracting Officer"],
        "Entry Level": ["Staff Analyst", "Administrative Specialist"],
        "Student": ["Pathways Intern"],
    },
    "Journalist / communications": {
        "Executive": ["Editor-in-Chief", "Chief Communications Officer"],
        "High Level": ["Managing Editor", "Director of Communications"],
        "Mid Level": ["Senior Reporter", "Communications Manager"],
        "Entry Level": ["Reporter", "Communications Coordinator"],
        "Student": ["Editorial Intern", "Communications Intern"],
    },
}

# Titles by sub-occupation (assumption), used where they differ from the role-level lists above.
TITLES_SUB = {
    ("Executive / senior leader", "gen_ops_mgr"): {
        "Executive": ["Chief Operating Officer", "Executive Vice President", "Chief Administrative Officer"],
        "High Level": ["General Manager", "Vice President of Operations", "Operations Director"],
    },
    ("Executive / senior leader", "chief_exec"): {
        "Executive": ["Chief Executive Officer", "President", "Founder and Chief Executive Officer"],
        "High Level": ["Managing Director", "Vice President"],
    },
    ("Finance / accounting", "bookkeeping"): {
        "High Level": ["Accounting Supervisor", "Office and Accounts Manager"],
        "Mid Level": ["Senior Accounting Clerk", "Bookkeeper", "Payroll and Accounts Clerk"],
        "Entry Level": ["Accounts Payable Clerk", "Bookkeeper", "Accounting Clerk"],
    },
    ("IT admin / help desk", "it_support"): {
        "High Level": ["IT Support Manager", "Service Desk Manager"],
        "Mid Level": ["Senior Support Specialist", "IT Support Lead"],
        "Entry Level": ["Help Desk Technician", "IT Support Specialist"],
    },
    ("IT admin / help desk", "sysadmin"): {
        "High Level": ["Senior Systems Administrator", "IT Operations Manager", "IT Director"],
        "Mid Level": ["Systems Administrator", "Network Administrator"],
        "Entry Level": ["Junior Systems Administrator", "Network Technician"],
    },
    ("Legal / compliance", "lawyers"): {
        "High Level": ["Senior Counsel", "Associate General Counsel"],
        "Mid Level": ["Counsel", "Senior Associate Attorney"],
        "Entry Level": ["Associate Attorney", "Staff Attorney"],
    },
    ("Legal / compliance", "paralegals"): {
        "High Level": ["Paralegal Manager", "Litigation Support Manager"],
        "Mid Level": ["Senior Paralegal", "Contracts Specialist"],
        "Entry Level": ["Paralegal", "Legal Assistant"],
    },
    ("Legal / compliance", "compliance"): {
        "High Level": ["Director of Compliance", "Senior Compliance Manager"],
        "Mid Level": ["Compliance Specialist", "Compliance Manager"],
        "Entry Level": ["Compliance Analyst"],
    },
}


def titles_for(role: str, sub: str, stage: str) -> list[str]:
    return TITLES_SUB.get((role, sub), {}).get(stage) or TITLES[role][stage]


# ---------------------------------------------------------------------------
# 12. Headquarters location                               src: BLS metro labor force (proxy)
# Top-25 metro areas by civilian labor force, Sept 2026 preliminary
# (https://www.bls.gov/news.release/metro.t01.htm). Metro job counts were not obtained.
# ---------------------------------------------------------------------------
METRO_LABOR_FORCE = {
    "New York, NY": 10339740, "Los Angeles, CA": 6646903, "Chicago, IL": 4922539, "Dallas, TX": 4611425,
    "Houston, TX": 3926342, "Washington, DC": 3435021, "Atlanta, GA": 3387001, "Philadelphia, PA": 3338921,
    "Miami, FL": 3302668, "Boston, MA": 2812598, "Phoenix, AZ": 2662258, "San Francisco, CA": 2473516,
    "Seattle, WA": 2340379, "Riverside, CA": 2222701, "Detroit, MI": 2174276, "Minneapolis, MN": 2086164,
    "Denver, CO": 1747030, "Tampa, FL": 1706261, "San Diego, CA": 1656661, "Austin, TX": 1572032,
    "Orlando, FL": 1536874, "Baltimore, MD": 1512195, "Charlotte, NC": 1494983, "St. Louis, MO": 1491799,
    "Portland, OR": 1385215,
}

# ---------------------------------------------------------------------------
# Parameter registry for the report: (parameter, source ids, evidence grade, note)
# ---------------------------------------------------------------------------
PARAM_REGISTRY = [
    ("Industry mix", "ces_b1", "derived", "Employment shares among the five groups; Government = non-education public sector."),
    ("Firm-size class (person-level)", "susb22", "data", "Employee-weighted. Government not in SUSB: assumption."),
    ("Organization headcount within class", "ASSUMPTION", "assumption", "Log-uniform inside the class; top class capped at 120k."),
    ("Role mix within industry", "oews23", "data", "SOC groups mapped to target roles; May 2023 (newer industry tables unavailable)."),
    ("Government / defense personnel", "oews23", "proxy", "OEWS excludes military; federal protective service used as stand-in."),
    ("Age by industry", "cps18b", "data", "Band counts; uniform within band."),
    ("Age shift by role", "cps11b", "proxy", "Role median age minus all-employed median (42.1); additive shift."),
    ("Tenure by age", "bls_tenure26", "data", "Median by age band; exponential shape is an assumption."),
    ("New-hire share", "bls_tenure26", "derived", "P(tenure <= 90 days) implied by the exponential tenure model."),
    ("Sex by role", "cps11", "data", "Employment-weighted CPS rows; protective service not found -> all-employed."),
    ("Race/ethnicity group -> surname", "cps11,census_surnames", "proxy", "Used only to draw a surname; not stored on the profile."),
    ("Given names", "ssa_names", "data", "SSA top-1000 by birth decade and sex (secondary mirror, through 2008)."),
    ("Highest education by role", "bls_ep53", "data", "Workers 25+; younger workers re-weighted to feasible degrees."),
    ("Field of study by role", "ASSUMPTION", "assumption", "BLS gives level, not field; ACS field-of-degree by occupation not obtained."),
    ("School attended", "ipeds23", "data", "Institution sampled by degrees awarded 2022-23 at that level and field."),
    ("Career stage", "oews25_nat", "proxy", "Entry <5 yrs experience; High Level = manager share (OEWS manager/worker ratios for finance, HR, IT; others assumed 0.15) among those with 8+ yrs; Executive = OEWS top-executive role."),
    ("LinkedIn / X presence", "pew26", "data", "Age x education logit model; overall cells flagged inferred; Executive at 500+ firms uses CEO study."),
    ("Facebook / Instagram presence", "pew26", "data", "By age band."),
    ("GitHub / ResearchGate presence", "academic_profiles", "assumption", "No representative rate found; academics use 37-78% range midpoint-ish 39%."),
    ("Posting activity", "linkedin_posting", "assumption", "1.4% weekly posters (weak); occasional-poster share and role multipliers assumed."),
    ("Email checks per day", "mark16", "data", "Median 77, n = 40; spread assumed."),
    ("Emails received per day", "ms_wti25", "data", "Mean 117 (knowledge workers); spread and role factors assumed."),
    ("Late-night inbox", "ms_wti25", "data", "29% back in inbox by 10 pm."),
    ("Baseline phish-prone %", "knowbe4_old", "data", "Industry x org size; undated vendor edition (avg ~27% vs 33.1% in 2025 edition)."),
    ("Security training share", "csbs25", "proxy", "UK survey by org size; effect factor assumed."),
    ("New-hire susceptibility", "keepnet25", "data", "x1.44 (vendor study, n = 237 companies)."),
    ("Person-level spread of susceptibility", "lain22", "derived", "Beta concentration 16.1 solved from Lain et al. ever-clicked rate; reproduces their 2+-click share."),
]
