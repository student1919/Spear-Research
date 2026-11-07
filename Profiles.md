# Synthetic Employee Profile Generation

5 Industries: Finance, Healthcare, Tech, Government, Education

Career Stages: Student, Entry Level, Mid Level, High Level, Executive

Company size: Small - lacks dedicated security staff, Medium, Large - more money/data

Prime Targets: 
Executives and senior leaders: Often called whaling when aimed at C-suite members, since they have broad access and authority.
Finance and accounting staff: These employees can authorize payments, so they’re the usual targets of business email compromise (BEC) schemes, like fake invoices or urgent wire transfer requests.
HR and payroll staff: They hold sensitive employee data (tax forms, SSNs) and can redirect direct deposits.
IT administrators and help desk staff: They have privileged credentials and system access, so compromising one can open the whole network.
Executive assistants: They have access to an executive’s inbox, calendar, and accounts, and are often trusted to act on the executive’s behalf.
Employees with access to valuable data: This includes engineers or researchers with intellectual property, and legal staff handling confidential matters.
Government, military, and defense personnel: Frequent targets of espionage-focused campaigns, often by state-sponsored groups.
Journalists, activists, and political figures: Targeted for surveillance or to leak information.
New hires: They’re less familiar with internal processes and colleagues, so impersonating a manager or IT is more likely to work.

# Profiles Organization + Creation:

  profiles_core.jsonl      # identity, sector, stage, employer
  profiles_public.jsonl    # resume bullets, social presence, footprint level, posts over time, personal website?
  profiles_private.jsonl   # projects, colleagues, real details behind resume lines -> provides a baseline for under-knowledge comparison
  profiles_behavior.jsonl  # traits and response tendencies
  orgs.jsonl # companies, domains, org charts
  emails_benign.jsonl      # synthetic internal traffic
  emails_attack.jsonl      # generated spear emails
  sim_results.jsonl        # ignore/reply/click/verify/report/comply outcomes

The database is SQLite, with one table per record type from the schema, all linked by a profile_id.

The profiles will be created in batches by different llms to prevent them from being too similar.

Email traffic will be generated using an llm trained on the email dataset.

Profiles will be created in aggregate by company (artificial with real website) with the companies having varying sizes and belonging to the respective fields.
Potential late-stage step: test the spear attack generator and detector on one of the group members after training it on the synthetic profiles.

