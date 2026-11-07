"""Claude-authored content pools for the local generation backend.

These let the pipeline produce the initial 100+100 run with no API key: the local
backend composes profiles and emails from these fragments. When the Anthropic
backend is switched on, these pools are unused (the model writes the text). They
are deliberately finite, which makes templated repetition measurable in the
detectability analysis.
"""

from __future__ import annotations

FIRST_NAMES = [
    "Amara", "Devin", "Priya", "Marcus", "Sofia", "Ethan", "Leila", "Jamal",
    "Hana", "Oscar", "Nadia", "Theo", "Yuki", "Grace", "Ibrahim", "Clara",
    "Diego", "Wei", "Fatima", "Noah", "Ingrid", "Omar", "Rosa", "Kenji",
    "Lena", "Andre", "Mei", "Samuel", "Zara", "Victor", "Aisha", "Lucas",
    "Tara", "Henrik", "Bianca", "Raj", "Elena", "Cole", "Nina", "Mateo",
]

LAST_NAMES = [
    "Okafor", "Reyes", "Nakamura", "Bauer", "Haddad", "Lindqvist", "Santos",
    "Chen", "Abara", "Delgado", "Novak", "Kowalski", "Mensah", "Ivanova",
    "Tran", "Rossi", "Fernandez", "Larsen", "Khan", "Moreau", "Schmidt",
    "Oyelaran", "Petrov", "Nguyen", "Blackwood", "Castellano", "Adeyemi",
    "Wallace", "Qureshi", "Bergström", "Vargas", "Hoffmann", "Sato", "Dubois",
]

CITIES = [
    "Austin, TX", "Columbus, OH", "Portland, OR", "Raleigh, NC", "Denver, CO",
    "Minneapolis, MN", "Sacramento, CA", "Pittsburgh, PA", "Tampa, FL",
    "Richmond, VA", "Boise, ID", "Hartford, CT", "Albany, NY", "Madison, WI",
    "Spokane, WA", "Tucson, AZ", "Omaha, NE", "Providence, RI",
]

# Company name parts per industry. Domains are derived as a slug under .example.
COMPANY_PARTS = {
    "Finance": (["Meridian", "Cairnwell", "Haskett", "Brightmoor", "Talford"],
                ["Capital", "Financial", "Partners", "Trust", "Advisory"]),
    "Healthcare": (["Alderwood", "Vireo", "Northbay", "Calyx", "Everwell"],
                   ["Health", "Care Systems", "Medical", "Clinics", "Diagnostics"]),
    "Tech": (["Lumat", "Fernstack", "Orbital", "Quillon", "Pinemark"],
             ["Labs", "Systems", "Software", "Technologies", "Dynamics"]),
    "Government": (["Harbor County", "Westridge", "Lakeshore", "Fallon District",
                    "Crestline"],
                   ["Authority", "Agency", "Services", "Bureau", "Council"]),
    "Education": (["Ashgrove", "Brightland", "Kelmore", "Oakbridge", "Sterling"],
                  ["University", "Institute", "College", "Academy", "School District"]),
}

SOCIAL_PLATFORMS = ["LinkedIn", "GitHub", "X", "Mastodon", "ResearchGate", "Medium"]

# --- Titles: base title per role, modified by career stage ------------------

ROLE_BASE_TITLE = {
    "Executive / senior leader": "Operations Officer",
    "Finance / accounting": "Accountant",
    "HR / payroll": "HR Generalist",
    "IT admin / help desk": "Systems Administrator",
    "Executive assistant": "Executive Assistant",
    "Engineer / researcher (valuable data)": "Engineer",
    "Legal / compliance": "Counsel",
    "Government / defense personnel": "Program Analyst",
    "Journalist / activist / political": "Reporter",
    "New hire": "Associate",
}

STAGE_PREFIX = {
    "Student": "Intern,",
    "Entry Level": "Junior",
    "Mid Level": "",
    "High Level": "Senior",
    "Executive": "Chief",
}

ROLE_RESUME = {
    "Executive / senior leader": [
        "Set and owned the annual operating plan across {n} business units.",
        "Chaired the leadership committee reviewing budget and headcount.",
        "Sponsored a cost-reduction program that reset vendor contracts.",
    ],
    "Finance / accounting": [
        "Owned the accounts-payable cycle and vendor payment approvals.",
        "Reconciled month-end close for a {n}-entity ledger.",
        "Managed wire disbursements and dual-approval controls.",
    ],
    "HR / payroll": [
        "Administered payroll and direct-deposit changes for {n} staff.",
        "Maintained employee tax records and onboarding paperwork.",
        "Ran open enrollment and benefits reconciliation.",
    ],
    "IT admin / help desk": [
        "Administered identity, SSO, and privileged-access tooling.",
        "Resolved tier-2 incidents and managed the password-reset queue.",
        "Maintained endpoint provisioning and VPN configuration.",
    ],
    "Executive assistant": [
        "Managed the calendar, inbox triage, and travel for senior leadership.",
        "Coordinated board materials and expense approvals.",
        "Acted as delegate on leadership scheduling and correspondence.",
    ],
    "Engineer / researcher (valuable data)": [
        "Led the {proj} workstream and owned its design docs.",
        "Maintained the core service handling proprietary datasets.",
        "Authored internal specs later filed as pending IP.",
    ],
    "Legal / compliance": [
        "Reviewed vendor contracts and NDA execution.",
        "Managed the matter tracker for confidential disputes.",
        "Owned regulatory filings and policy attestations.",
    ],
    "Government / defense personnel": [
        "Supported program planning for a multi-year public initiative.",
        "Coordinated inter-agency reporting and data requests.",
        "Maintained controlled project documentation.",
    ],
    "Journalist / activist / political": [
        "Covered the {proj} beat and managed source correspondence.",
        "Published investigative pieces drawing on confidential tips.",
        "Coordinated with editors on embargoed material.",
    ],
    "New hire": [
        "Joined the {proj} team; completing onboarding and tooling setup.",
        "Shadowing senior staff while ramping on internal processes.",
        "Assigned first tasks across the team backlog.",
    ],
}

ROLE_PROJECTS = {
    "Executive / senior leader": ["the FY reorg", "the margin-recovery plan", "the vendor-consolidation effort"],
    "Finance / accounting": ["the AP automation rollout", "the Q3 close", "the vendor master cleanup"],
    "HR / payroll": ["the HRIS migration", "open enrollment", "the payroll-provider switch"],
    "IT admin / help desk": ["the SSO migration", "the MFA rollout", "the laptop refresh"],
    "Executive assistant": ["the board offsite", "the exec travel overhaul", "the calendar consolidation"],
    "Engineer / researcher (valuable data)": ["Project Halcyon", "the inference pipeline", "the sensor-fusion model"],
    "Legal / compliance": ["the acquisition review", "the policy refresh", "the audit response"],
    "Government / defense personnel": ["the grid-resilience study", "the interagency data share", "the modernization program"],
    "Journalist / activist / political": ["the procurement investigation", "the housing series", "the records-request story"],
    "New hire": ["the onboarding cohort", "the starter backlog", "the orientation track"],
}

ROLE_ACCESS = {
    "Executive / senior leader": ["approves budgets and large POs", "broad system access", "signs vendor contracts"],
    "Finance / accounting": ["can initiate wire transfers", "approves invoices", "edits vendor banking details"],
    "HR / payroll": ["edits direct-deposit records", "holds SSNs and tax forms", "approves payroll runs"],
    "IT admin / help desk": ["resets passwords and MFA", "holds privileged credentials", "can grant system access"],
    "Executive assistant": ["acts on the executive's inbox", "schedules and approves on behalf", "sees confidential calendar"],
    "Engineer / researcher (valuable data)": ["accesses proprietary source and data", "holds design documents", "can export datasets"],
    "Legal / compliance": ["handles confidential matters", "accesses sealed documents", "signs attestations"],
    "Government / defense personnel": ["handles controlled documents", "accesses program data", "coordinates classified-adjacent reporting"],
    "Journalist / activist / political": ["holds source identities", "accesses embargoed material", "manages confidential tips"],
    "New hire": ["limited system access", "unfamiliar with internal processes", "still building colleague map"],
}

TRAITS = [
    "responsive to authority", "deadline-driven", "helpful to new colleagues",
    "detail-oriented", "frequently traveling", "overloaded inbox",
    "trusting of internal requests", "cautious with unknown senders",
    "eager to prove themselves", "process-oriented", "skeptical of urgency",
    "quick to click familiar links",
]

RESPONSE_CUES = [
    ("urgent request from a senior leader", "tends to comply quickly"),
    ("email with a login link", "sometimes clicks before checking the domain"),
    ("payment or banking change", "usually follows the dual-approval step"),
    ("message from an unknown sender", "often verifies by a second channel"),
    ("after-hours request", "more likely to act without verifying"),
    ("request citing a real project", "lowers guard and responds"),
]

POST_TEMPLATES = [
    "Excited to share progress on {proj} this quarter.",
    "Great conversations at the {industry} meetup today.",
    "Hiring on my team — reach out if {role_kw} is your thing.",
    "Reflecting on a year at {company}.",
    "New write-up on lessons from {proj}.",
]

# --- Email scenarios per role ----------------------------------------------
# Each scenario: (name, pretext, impersonated_role, subject, urgency, body_key)

ROLE_SCENARIOS = {
    "Finance / accounting": [
        ("BEC wire transfer", "finance staff can authorize payments", "Chief Operations Officer",
         "Urgent: vendor payment before close", "high", "wire"),
        ("Invoice approval", "pending invoice tied to a known project", "AP Supervisor",
         "Re: outstanding invoice for {proj}", "medium", "invoice"),
    ],
    "Executive / senior leader": [
        ("Invoice approval", "executive approvals on large POs", "Finance Director",
         "Approval needed: {proj} vendor PO", "high", "invoice"),
        ("BEC wire transfer", "confidential acquisition payment", "External Counsel",
         "Confidential — wire authorization", "high", "wire"),
    ],
    "HR / payroll": [
        ("Payroll redirect", "HR edits direct-deposit records", "Employee (self-service)",
         "Direct deposit update request", "medium", "payroll"),
    ],
    "IT admin / help desk": [
        ("Credential reset lure", "IT handles privileged access", "Security Operations",
         "Action required: privileged account review", "high", "cred"),
    ],
    "Executive assistant": [
        ("Gift-card / task errand", "assistant acts for the executive", "Chief Executive",
         "Quick favor — need this handled discreetly", "high", "errand"),
    ],
    "Engineer / researcher (valuable data)": [
        ("IP exfiltration pretext", "engineer holds proprietary data", "Partner Integrations",
         "Shared workspace for {proj} deliverables", "medium", "exfil"),
    ],
    "Legal / compliance": [
        ("Document access lure", "legal handles confidential matters", "Opposing Counsel",
         "Sealed filing — review access", "medium", "doc"),
    ],
    "Government / defense personnel": [
        ("Document access lure", "handles controlled documents", "Program Office",
         "Updated guidance — acknowledgement required", "medium", "doc"),
    ],
    "Journalist / activist / political": [
        ("Source lure", "manages confidential tips", "Prospective Source",
         "Documents for your {proj} reporting", "medium", "source"),
    ],
    "New hire": [
        ("Credential reset lure", "new hires are unfamiliar with processes", "IT Help Desk",
         "Welcome — finish your account setup", "high", "cred"),
    ],
}

# Body templates keyed by body_key. Slots filled from the profile/company.
BODY_TEMPLATES = {
    "wire": (
        "Hi {first},\n\n{sender} here. We have a time-sensitive vendor payment that "
        "needs to go out before close today. I'm tied up in meetings and can't reach "
        "the bank line. Can you process a wire to the account below and confirm once "
        "done? Please keep this between us until the {proj} announcement.\n\n"
        "Amount: ${amount}\nReference: {proj}\n\nThanks for the quick turnaround.\n{sender}\n{company}"
    ),
    "invoice": (
        "Hi {first},\n\nFollowing up on the outstanding invoice tied to {proj}. The "
        "vendor is asking for approval today. Review and approve at the link so we don't "
        "slip the deadline:\n\n{link}\n\nAppreciate it,\n{sender}\n{company}"
    ),
    "payroll": (
        "Hello {first},\n\nI'd like to update my direct deposit to a new account "
        "effective this pay cycle. Please find the updated banking details in the secure "
        "form here:\n\n{link}\n\nLet me know if you need anything else from me.\nThanks"
    ),
    "cred": (
        "Hi {first},\n\nOur records show your account on the {company} portal needs "
        "re-verification after a policy change. To avoid a lockout, confirm your "
        "credentials within 24 hours:\n\n{link}\n\nRegards,\n{sender}"
    ),
    "errand": (
        "Hi {first},\n\nAre you at your desk? I need a quick, discreet favor handled "
        "before my next meeting — don't loop anyone else in yet. Reply and I'll send "
        "details.\n\n{sender}"
    ),
    "exfil": (
        "Hi {first},\n\nWe're setting up the shared workspace for the {proj} "
        "deliverables. Please upload the latest design docs and dataset exports here so "
        "we can sync before the review:\n\n{link}\n\nThanks,\n{sender}"
    ),
    "doc": (
        "Hi {first},\n\nThere's an updated document related to {proj} that requires your "
        "acknowledgement. Access and confirm receipt at the link:\n\n{link}\n\n"
        "Regards,\n{sender}"
    ),
    "source": (
        "Hello {first},\n\nI have documents relevant to your {proj} reporting that I can "
        "only share through a secure drop. Open the link and verify to view:\n\n{link}\n\n"
        "Please keep this confidential."
    ),
}
