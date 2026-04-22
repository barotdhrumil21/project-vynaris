"""Persona starter packs — deep seed content for each of the 5 personas.

A pack is a config dict describing the teams, people, channels, goals, CSVs,
and skills to register. ``install(pack_name)`` dispatches to the right config
and applies it to the admin's org.

Skills are shipped as markdown files under ``.claude/skills/`` (auto-loaded by
the Claude Agent SDK via ``setting_sources=['project']``); we record a
``SkillRecord`` pointing at each one so the admin sees them in /skills as part
of the installed pack.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vynaris.config import get_settings
from vynaris.db.models import Channel, ChannelMember, Person, SkillRecord, Team, TeamMembership
from vynaris.services.goals import create_goal
from vynaris.services.onboarding import PersonDraft, create_person
from vynaris.services.workspace import ensure_workspace, safe_relative

settings = get_settings()


@dataclass
class PackResult:
    people_created: int = 0
    channels_created: int = 0
    teams_created: int = 0
    goals_created: int = 0
    skills_registered: int = 0
    csvs_written: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "people": self.people_created,
            "channels": self.channels_created,
            "teams": self.teams_created,
            "goals": self.goals_created,
            "skills": self.skills_registered,
            "csvs": self.csvs_written,
        }


# ═════════════════════════════════════════════════════════════════════════════
# SANGHAVI — trading house (credit risk, LCs, EDPMS, freight, per-buyer MIS)
# ═════════════════════════════════════════════════════════════════════════════

SANGHAVI_KPI_CSV = """date,default_rate,new_customer_approval_rate,policy_updates_shipped
2026-01-31,3.4,61,0
2026-02-07,3.5,62,0
2026-02-14,3.5,62,1
2026-02-21,3.6,63,1
2026-02-28,3.6,62,1
2026-03-07,3.5,62,1
2026-03-14,3.6,61,1
2026-03-21,3.7,61,1
2026-03-28,3.7,62,1
2026-04-04,3.8,62,1
2026-04-11,3.8,62,1
2026-04-18,3.9,62,1
"""

SANGHAVI_LC_CSV = """lc_ref,buyer,opened,expiry,value_usd,stage,discrepancies
LC-2026-041,Bosch KA,2026-03-10,2026-05-15,218400,presented,1
LC-2026-042,Daimler Euro,2026-03-14,2026-05-28,312900,paid,0
LC-2026-043,Hyundai India,2026-03-22,2026-06-02,141000,opened,0
LC-2026-044,VW Wolfsburg,2026-04-01,2026-06-18,405600,presented,2
LC-2026-045,Bosch KA,2026-04-08,2026-06-25,198200,opened,0
LC-2026-046,Stellantis,2026-04-12,2026-06-30,267800,opened,0
LC-2026-047,Renault,2026-04-14,2026-07-10,189500,opened,0
LC-2026-048,Daimler Euro,2026-04-18,2026-07-15,358000,opened,0
"""

SANGHAVI_EDPMS_CSV = """shipping_bill_no,sb_date,buyer,invoice_value_usd,days_outstanding
7428901,2025-09-02,Bosch KA,118000,233
7439112,2025-11-18,VW Wolfsburg,162400,156
7444201,2025-12-20,Daimler Euro,94100,124
7452903,2026-01-14,Hyundai India,72800,99
7461402,2026-02-11,Bosch KA,83200,70
7464801,2026-02-28,Stellantis,61400,53
"""

SANGHAVI_DSO_CSV = """week_ending,dso_days,ar_outstanding_usd
2026-02-28,74,2840000
2026-03-07,73,2920000
2026-03-14,72,2875000
2026-03-21,71,2810000
2026-03-28,70,2765000
2026-04-04,70,2810000
2026-04-11,69,2740000
2026-04-18,68,2695000
"""

SANGHAVI_BOSCH_CSV = """week_ending,on_time_payment_pct,open_lcs,discrepancies_ytd
2026-03-07,96,3,1
2026-03-14,95,3,1
2026-03-21,94,3,2
2026-03-28,94,3,2
2026-04-04,93,4,3
2026-04-11,93,4,3
2026-04-18,92,4,3
"""

SANGHAVI_FREIGHT_CSV = """week_ending,route,rate_usd_per_teu
2026-03-07,NSA-HAM,3180
2026-03-14,NSA-HAM,3210
2026-03-21,NSA-HAM,3290
2026-03-28,NSA-HAM,3340
2026-04-04,NSA-HAM,3420
2026-04-11,NSA-HAM,3510
2026-04-18,NSA-HAM,3620
"""

SANGHAVI_TF_UTIL_CSV = """date,limit_usd,used_usd,utilization_pct
2026-03-07,12000000,7800000,65
2026-03-14,12000000,8400000,70
2026-03-21,12000000,8800000,73
2026-03-28,12000000,9100000,76
2026-04-04,12000000,9300000,77
2026-04-11,12000000,9600000,80
2026-04-18,12000000,9900000,82
"""

SANGHAVI_AR_AGING_CSV = """as_of,current,days_30,days_60,days_90_plus
2026-03-28,1820000,680000,420000,580000
2026-04-04,1750000,720000,450000,520000
2026-04-11,1690000,740000,490000,495000
2026-04-18,1620000,780000,520000,475000
"""

SANGHAVI_ICEGATE_CSV = """week_ending,avg_tat_hours,files_over_48h
2026-03-14,22,1
2026-03-21,24,2
2026-03-28,21,1
2026-04-04,20,0
2026-04-11,22,1
2026-04-18,26,3
"""


SANGHAVI_PACK: dict[str, Any] = {
    "teams": [
        {"name": "Credit Risk", "slug": "credit-risk", "description": "LC compliance + buyer risk scoring + credit committee.", "lead_email": "rohan@sanghavi.example"},
        {"name": "Shipment Ops", "slug": "shipment-ops", "description": "Freight bookings, container logistics, customs clearance.", "lead_email": "anita@sanghavi.example"},
        {"name": "Compliance", "slug": "compliance", "description": "EDPMS reconciliation, RBI filings, export incentive claims.", "lead_email": "priya@sanghavi.example"},
        {"name": "Trade Finance", "slug": "trade-finance", "description": "LC issuance, trade finance limits, bank liaison.", "lead_email": "kavita@sanghavi.example"},
        {"name": "AR & Collections", "slug": "ar-collections", "description": "Buyer dunning, AR aging, write-offs.", "lead_email": "farhan@sanghavi.example"},
    ],
    "people": [
        {"name": "Vikram Sanghavi", "email": "vikram@sanghavi.example", "title": "Managing Director",
         "level": 1, "level_label": "MD", "role_description": "Runs the firm; owns credit committee veto and the Friday MIS sign-off.",
         "teams": []},
        {"name": "Rohan Desai", "email": "rohan@sanghavi.example", "title": "Head of Credit Risk",
         "level": 2, "level_label": "VP", "role_description": "Signs off on LC discrepancies and buyer limit changes; drives default-rate target.",
         "manager_email": "vikram@sanghavi.example", "teams": ["credit-risk"]},
        {"name": "Anita Mehta", "email": "anita@sanghavi.example", "title": "Head of Shipment Ops",
         "level": 2, "level_label": "VP", "role_description": "Owns freight bookings, sailing schedule, customs clearance across all routes.",
         "manager_email": "vikram@sanghavi.example", "teams": ["shipment-ops"]},
        {"name": "Priya Kulkarni", "email": "priya@sanghavi.example", "title": "Head of Compliance",
         "level": 2, "level_label": "VP", "role_description": "Owns EDPMS reconciliation, AD bank communication, RoDTEP claims, sanctions screening.",
         "manager_email": "vikram@sanghavi.example", "teams": ["compliance"]},
        {"name": "Kavita Menon", "email": "kavita@sanghavi.example", "title": "Head of Trade Finance",
         "level": 2, "level_label": "VP", "role_description": "Owns LC issuance terms, trade-finance limits, bank relationships.",
         "manager_email": "vikram@sanghavi.example", "teams": ["trade-finance"]},
        {"name": "Farhan Siddiqui", "email": "farhan@sanghavi.example", "title": "AR Manager",
         "level": 3, "level_label": "Manager", "role_description": "Collections, AR aging, buyer dunning.",
         "manager_email": "rohan@sanghavi.example", "teams": ["ar-collections", "credit-risk"]},
        {"name": "Aditya Gupta", "email": "aditya@sanghavi.example", "title": "Senior Credit Analyst",
         "level": 4, "level_label": "Sr Analyst", "role_description": "Buyer credit reviews, cohort analysis, MIS building.",
         "manager_email": "rohan@sanghavi.example", "teams": ["credit-risk"]},
        {"name": "Neha Joshi", "email": "neha@sanghavi.example", "title": "Compliance Analyst",
         "level": 5, "level_label": "Analyst", "role_description": "EDPMS daily reconciliation; RoDTEP filing.",
         "manager_email": "priya@sanghavi.example", "teams": ["compliance"]},
        {"name": "Sameer Khan", "email": "sameer@sanghavi.example", "title": "Logistics Coordinator",
         "level": 4, "level_label": "Coordinator", "role_description": "Day-to-day container bookings and forwarder management.",
         "manager_email": "anita@sanghavi.example", "teams": ["shipment-ops"]},
        {"name": "Rhea Iyer", "email": "rhea@sanghavi.example", "title": "EDPMS Specialist",
         "level": 5, "level_label": "Specialist", "role_description": "EDPMS escalations; over-90-day bills.",
         "manager_email": "priya@sanghavi.example", "teams": ["compliance"]},
        {"name": "Arvind Pillai", "email": "arvind@sanghavi.example", "title": "Customs / ICEGATE liaison",
         "level": 4, "level_label": "Specialist", "role_description": "ICEGATE filings, customs disputes, port clearance.",
         "manager_email": "anita@sanghavi.example", "teams": ["shipment-ops"]},
        {"name": "Karan Bhatt", "email": "karan@sanghavi.example", "title": "MIS Analyst",
         "level": 5, "level_label": "Analyst", "role_description": "Weekly MIS build + distribution; dashboards.",
         "manager_email": "rohan@sanghavi.example", "teams": ["credit-risk"]},
    ],
    "channels": [
        {"name": "compliance-edpms", "slug": "compliance-edpms", "kind": "public",
         "description": "EDPMS reconciliation, AD bank threads, RBI filings.",
         "members": ["rohan@sanghavi.example", "priya@sanghavi.example", "neha@sanghavi.example", "rhea@sanghavi.example", "farhan@sanghavi.example"]},
        {"name": "ar-collections", "slug": "ar-collections", "kind": "public",
         "description": "Buyer dunning, aging reviews, write-off decisions.",
         "members": ["rohan@sanghavi.example", "farhan@sanghavi.example", "aditya@sanghavi.example"]},
        {"name": "shipment-ops", "slug": "shipment-ops", "kind": "public",
         "description": "Sailings, freight quotes, customs issues.",
         "members": ["anita@sanghavi.example", "sameer@sanghavi.example", "arvind@sanghavi.example", "farhan@sanghavi.example"]},
        {"name": "friday-mis", "slug": "friday-mis", "kind": "public",
         "description": "Weekly MIS publishing + discussion.",
         "members": ["vikram@sanghavi.example", "rohan@sanghavi.example", "anita@sanghavi.example", "priya@sanghavi.example", "kavita@sanghavi.example", "karan@sanghavi.example"]},
        {"name": "trade-finance", "slug": "trade-finance", "kind": "public",
         "description": "LC drafting, bank correspondence, limit management.",
         "members": ["kavita@sanghavi.example", "rohan@sanghavi.example", "farhan@sanghavi.example"]},
        {"name": "credit-committee", "slug": "credit-committee", "kind": "private",
         "description": "Monthly credit committee — buyer limits, policy changes. Private.",
         "members": ["vikram@sanghavi.example", "rohan@sanghavi.example", "kavita@sanghavi.example", "priya@sanghavi.example"]},
        {"name": "buyer-bosch-ka", "slug": "buyer-bosch-ka", "kind": "public",
         "description": "All Bosch KA account activity — LCs, shipments, compliance.",
         "members": ["rohan@sanghavi.example", "anita@sanghavi.example", "farhan@sanghavi.example", "aditya@sanghavi.example"]},
        {"name": "buyer-daimler-euro", "slug": "buyer-daimler-euro", "kind": "public",
         "description": "All Daimler Euro account activity.",
         "members": ["rohan@sanghavi.example", "anita@sanghavi.example", "kavita@sanghavi.example"]},
        {"name": "lc-ops", "slug": "lc-ops", "kind": "public",
         "description": "Open LCs across all buyers — stages, discrepancies.",
         "members": ["kavita@sanghavi.example", "rohan@sanghavi.example", "aditya@sanghavi.example"]},
    ],
    "csvs": [
        {"owner_email": "rohan@sanghavi.example", "path": "public/kpi.csv", "content": SANGHAVI_KPI_CSV},
        {"owner_email": "rohan@sanghavi.example", "path": "public/lc-tracker.csv", "content": SANGHAVI_LC_CSV},
        {"owner_email": "rohan@sanghavi.example", "path": "public/buyer-bosch-ka-health.csv", "content": SANGHAVI_BOSCH_CSV},
        {"owner_email": "priya@sanghavi.example", "path": "public/edpms-outstanding.csv", "content": SANGHAVI_EDPMS_CSV},
        {"owner_email": "anita@sanghavi.example", "path": "public/freight-rates.csv", "content": SANGHAVI_FREIGHT_CSV},
        {"owner_email": "kavita@sanghavi.example", "path": "public/trade-finance-utilization.csv", "content": SANGHAVI_TF_UTIL_CSV},
        {"owner_email": "farhan@sanghavi.example", "path": "public/dso.csv", "content": SANGHAVI_DSO_CSV},
        {"owner_email": "farhan@sanghavi.example", "path": "public/ar-aging.csv", "content": SANGHAVI_AR_AGING_CSV},
        {"owner_email": "arvind@sanghavi.example", "path": "public/icegate-tat.csv", "content": SANGHAVI_ICEGATE_CSV},
    ],
    "goals": [
        {
            "title": "Reduce default rate on sub-50L SMB book to under 3.2% by end of Q3",
            "description": "Portfolio discipline on the small-ticket SMB book. The Marketplace X cohort is dragging performance.",
            "success_criteria": "Default rate under 3.2% (90-day rolling) with approval rate at or above 65%.",
            "owner_email": "rohan@sanghavi.example", "visibility": "team", "days_out": 75,
            "krs": [
                {"name": "Default rate (sub-50L, 90d rolling)", "unit": "%", "target_value": 3.2,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/kpi.csv", "column": "default_rate", "alias": "default_rate", "cadence_minutes": 1440, "drift_threshold_pct": 10}},
                {"name": "New-customer approval rate", "unit": "%", "target_value": 65,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/kpi.csv", "column": "new_customer_approval_rate", "alias": "approval", "cadence_minutes": 1440}},
                {"name": "Policy updates shipped", "unit": "count", "target_value": 2,
                 "measurement_kind": "manual", "measurement_config": {"alias": "policies"}},
            ],
        },
        {
            "title": "Zero EDPMS bills over 90 days by month-end",
            "description": "RBI exposure reduction — every aged bill has a named owner + date.",
            "success_criteria": "No bill in EDPMS outstanding > 90 days.",
            "owner_email": "priya@sanghavi.example", "visibility": "team", "days_out": 30,
            "krs": [
                {"name": "Bills outstanding > 90 days", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "over90"}},
                {"name": "Total USD outstanding > 90d", "unit": "$", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "over90_usd"}},
            ],
        },
        {
            "title": "Clean LC rate ≥ 85% this quarter",
            "description": "Reduce avoidable discrepancies on LC presentations.",
            "success_criteria": "At least 85% of LCs presented this quarter go through with zero discrepancies on first review.",
            "owner_email": "kavita@sanghavi.example", "visibility": "team", "days_out": 90,
            "krs": [
                {"name": "Clean LC rate (QTD)", "unit": "%", "target_value": 85,
                 "measurement_kind": "manual", "measurement_config": {"alias": "clean_lc"}},
                {"name": "Discrepancies this quarter", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "disc_count"}},
            ],
        },
        {
            "title": "Bring DSO under 68 days by end of quarter",
            "description": "Working-capital pressure — every AR day trimmed frees up trade-finance capacity.",
            "success_criteria": "DSO at or under 68 days on a weekly rolling basis.",
            "owner_email": "farhan@sanghavi.example", "visibility": "team", "days_out": 60,
            "krs": [
                {"name": "DSO (latest week)", "unit": "days", "target_value": 68,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/dso.csv", "column": "dso_days", "alias": "dso", "cadence_minutes": 1440, "drift_threshold_pct": 5}},
                {"name": "AR outstanding", "unit": "$", "target_value": 2600000,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/dso.csv", "column": "ar_outstanding_usd", "alias": "ar", "cadence_minutes": 1440}},
            ],
        },
        {
            "title": "Bosch KA account health ≥ 95% on-time payment",
            "description": "Largest buyer — every week matters. Trend is ticking down; investigate before it breaks.",
            "success_criteria": "On-time payment rate ≥ 95% on 4-week rolling window.",
            "owner_email": "rohan@sanghavi.example", "visibility": "team", "days_out": 45,
            "krs": [
                {"name": "On-time payment rate", "unit": "%", "target_value": 95,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/buyer-bosch-ka-health.csv", "column": "on_time_payment_pct", "alias": "bosch_otp", "cadence_minutes": 1440, "drift_threshold_pct": 3}},
                {"name": "Open LCs (count)", "unit": "count", "target_value": 3,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/buyer-bosch-ka-health.csv", "column": "open_lcs", "alias": "bosch_lcs", "cadence_minutes": 1440}},
                {"name": "Discrepancies YTD", "unit": "count", "target_value": 2,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/buyer-bosch-ka-health.csv", "column": "discrepancies_ytd", "alias": "bosch_disc", "cadence_minutes": 1440}},
            ],
        },
        {
            "title": "Keep NSA→HAM freight rate under $3,200/TEU",
            "description": "Margin erosion — rates are climbing 3%+ weekly. Negotiate forward contracts or switch forwarder.",
            "success_criteria": "Weekly rate below $3,200/TEU on the primary NSA-Hamburg route.",
            "owner_email": "anita@sanghavi.example", "visibility": "team", "days_out": 45,
            "krs": [
                {"name": "NSA-HAM rate (latest week)", "unit": "$/TEU", "target_value": 3200,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/freight-rates.csv", "column": "rate_usd_per_teu", "alias": "nsa_ham", "cadence_minutes": 720, "drift_threshold_pct": 5}},
            ],
        },
        {
            "title": "Trade-finance utilisation ≤ 75% of approved limits",
            "description": "Headroom matters — we can't issue a new LC if we're maxed out.",
            "success_criteria": "Rolling utilisation ≤ 75% of $12M approved.",
            "owner_email": "kavita@sanghavi.example", "visibility": "team", "days_out": 30,
            "krs": [
                {"name": "Utilisation %", "unit": "%", "target_value": 75,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/trade-finance-utilization.csv", "column": "utilization_pct", "alias": "tf_util", "cadence_minutes": 1440, "drift_threshold_pct": 5}},
                {"name": "Used limit ($)", "unit": "$", "target_value": 9000000,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/trade-finance-utilization.csv", "column": "used_usd", "alias": "tf_used", "cadence_minutes": 1440}},
            ],
        },
        {
            "title": "Cut 60–90d AR bucket under $500K by month-end",
            "description": "The aged bucket is stuck. Dunn each name hard, write off what's not coming.",
            "success_criteria": "60–90d bucket under $500K on weekly aging.",
            "owner_email": "farhan@sanghavi.example", "visibility": "team", "days_out": 30,
            "krs": [
                {"name": "60–90d bucket", "unit": "$", "target_value": 500000,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/ar-aging.csv", "column": "days_60", "alias": "ar_60_90", "cadence_minutes": 1440}},
                {"name": "90+ bucket", "unit": "$", "target_value": 400000,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/ar-aging.csv", "column": "days_90_plus", "alias": "ar_90", "cadence_minutes": 1440, "drift_threshold_pct": 10}},
            ],
        },
        {
            "title": "ICEGATE filing TAT < 24 hours",
            "description": "Customs turnaround is slipping — shipments wait at port and freight demurrage accumulates.",
            "success_criteria": "Average TAT under 24h on a weekly rolling window.",
            "owner_email": "arvind@sanghavi.example", "visibility": "team", "days_out": 30,
            "krs": [
                {"name": "Avg TAT (hours)", "unit": "h", "target_value": 24,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/icegate-tat.csv", "column": "avg_tat_hours", "alias": "tat", "cadence_minutes": 1440, "drift_threshold_pct": 15}},
                {"name": "Files over 48h", "unit": "count", "target_value": 0,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/icegate-tat.csv", "column": "files_over_48h", "alias": "over48", "cadence_minutes": 1440}},
            ],
        },
        {
            "title": "RoDTEP export incentive — 100% filed within 90 days",
            "description": "Export incentive claims slip through the cracks. Every late filing is a credit we can't recover.",
            "success_criteria": "All eligible shipments claimed within 90 days of shipping bill.",
            "owner_email": "priya@sanghavi.example", "visibility": "team", "days_out": 90,
            "krs": [
                {"name": "Filing completion rate (QTD)", "unit": "%", "target_value": 100,
                 "measurement_kind": "manual", "measurement_config": {"alias": "rodtep_rate"}},
                {"name": "Eligible but unfiled", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "rodtep_missing"}},
            ],
        },
    ],
    "skills": [
        {"name": "lc-discrepancy-drafter", "description": "Draft LC discrepancy responses.", "path": ".claude/skills/lc-discrepancy-drafter/SKILL.md"},
        {"name": "edpms-reconciliation", "description": "EDPMS reconciliation worksheet + escalation.", "path": ".claude/skills/edpms-reconciliation/SKILL.md"},
        {"name": "freight-spike-detector", "description": "Detect anomalous freight-rate spikes and map to open shipments.", "path": ".claude/skills/freight-spike-detector/SKILL.md"},
        {"name": "buyer-compliance-audit", "description": "Compile a buyer compliance audit.", "path": ".claude/skills/buyer-compliance-audit/SKILL.md"},
        {"name": "friday-mis-builder", "description": "Assemble the weekly MIS from ledger + LC + EDPMS sources.", "path": ".claude/skills/friday-mis-builder/SKILL.md"},
    ],
}


# ═════════════════════════════════════════════════════════════════════════════
# SCHÄFER — German manufacturing (OEE, 8D, shift handovers, SOP gates)
# ═════════════════════════════════════════════════════════════════════════════

SCHAFER_OEE_A_CSV = """date,cell,oee,scrap_ppm,availability
2026-03-30,Cell-A,0.82,18,0.94
2026-04-06,Cell-A,0.81,22,0.93
2026-04-13,Cell-A,0.79,29,0.91
2026-04-20,Cell-A,0.78,31,0.90
"""

SCHAFER_OEE_B_CSV = """date,cell,oee,scrap_ppm,availability
2026-03-30,Cell-B,0.85,12,0.96
2026-04-06,Cell-B,0.84,14,0.95
2026-04-13,Cell-B,0.83,15,0.95
2026-04-20,Cell-B,0.84,13,0.96
"""

SCHAFER_8D_CSV = """customer,complaint_date,part,defect,severity,age_days
Bosch KA,2026-03-28,X04,burr,major,21
Daimler,2026-04-05,P11,color,minor,13
Audi,2026-04-12,Q23,tolerance,major,6
"""


SCHAFER_PACK: dict[str, Any] = {
    "teams": [
        {"name": "Cell A", "slug": "cell-a", "description": "Machining cell A — Bosch KA parts.", "lead_email": "elke@schafer.example"},
        {"name": "Cell B", "slug": "cell-b", "description": "Machining cell B — Daimler + Audi parts.", "lead_email": "manfred@schafer.example"},
        {"name": "Quality", "slug": "quality", "description": "Customer QM, 8D, audits, supplier quality.", "lead_email": "stefan@schafer.example"},
        {"name": "Maintenance", "slug": "maintenance", "description": "Planned + reactive maintenance.", "lead_email": "ute@schafer.example"},
    ],
    "people": [
        {"name": "Friedrich Schäfer", "email": "friedrich@schafer.example", "title": "Geschäftsführer (MD)",
         "level": 1, "level_label": "GF", "role_description": "Family-owned Mittelstand manufacturer. Owns P&L, customer escalations.",
         "teams": []},
        {"name": "Stefan Hoffmann", "email": "stefan@schafer.example", "title": "Head of Quality",
         "level": 2, "level_label": "Director", "role_description": "Customer complaints, 8D, VDA audits, supplier quality. Reports to GF.",
         "manager_email": "friedrich@schafer.example", "teams": ["quality"]},
        {"name": "Thomas Weber", "email": "thomas@schafer.example", "title": "Head of Production",
         "level": 2, "level_label": "Director", "role_description": "Factory floor, OEE across all cells, shift scheduling.",
         "manager_email": "friedrich@schafer.example", "teams": ["cell-a", "cell-b"]},
        {"name": "Elke Braun", "email": "elke@schafer.example", "title": "Cell-A Shift Lead",
         "level": 4, "level_label": "Lead", "role_description": "Runs Cell-A production, OEE, shift handovers. Reports to Thomas.",
         "manager_email": "thomas@schafer.example", "teams": ["cell-a"]},
        {"name": "Manfred Klein", "email": "manfred@schafer.example", "title": "Cell-B Shift Lead",
         "level": 4, "level_label": "Lead", "role_description": "Runs Cell-B production. Coaches Ausbildung rotation.",
         "manager_email": "thomas@schafer.example", "teams": ["cell-b"]},
        {"name": "Ute Becker", "email": "ute@schafer.example", "title": "Maintenance Lead",
         "level": 4, "level_label": "Lead", "role_description": "Planned maintenance scheduling, breakdown response.",
         "manager_email": "thomas@schafer.example", "teams": ["maintenance"]},
        {"name": "Hans Müller", "email": "hans@schafer.example", "title": "QM Engineer (8D lead)",
         "level": 5, "level_label": "Engineer", "role_description": "Owns 8D responses end-to-end.",
         "manager_email": "stefan@schafer.example", "teams": ["quality"]},
    ],
    "channels": [
        {"name": "cell-a", "slug": "cell-a", "kind": "public",
         "description": "Cell-A shift handovers, OEE, maintenance.",
         "members": ["thomas@schafer.example", "elke@schafer.example", "ute@schafer.example", "stefan@schafer.example"]},
        {"name": "cell-b", "slug": "cell-b", "kind": "public",
         "description": "Cell-B shift handovers, OEE.",
         "members": ["thomas@schafer.example", "manfred@schafer.example", "ute@schafer.example", "stefan@schafer.example"]},
        {"name": "qm-8d-open", "slug": "qm-8d-open", "kind": "public",
         "description": "Every open 8D. Customer complaints, root-cause, corrective actions.",
         "members": ["stefan@schafer.example", "hans@schafer.example", "thomas@schafer.example"]},
        {"name": "bosch-ka", "slug": "bosch-ka", "kind": "public",
         "description": "Bosch KA customer account — RFQs, 8Ds, PPM reviews.",
         "members": ["friedrich@schafer.example", "stefan@schafer.example", "thomas@schafer.example"]},
        {"name": "maintenance", "slug": "maintenance", "kind": "public",
         "description": "Planned + reactive maintenance coordination.",
         "members": ["ute@schafer.example", "thomas@schafer.example", "elke@schafer.example", "manfred@schafer.example"]},
    ],
    "csvs": [
        {"owner_email": "elke@schafer.example", "path": "public/oee-cell-a.csv", "content": SCHAFER_OEE_A_CSV},
        {"owner_email": "manfred@schafer.example", "path": "public/oee-cell-b.csv", "content": SCHAFER_OEE_B_CSV},
        {"owner_email": "stefan@schafer.example", "path": "public/open-8d.csv", "content": SCHAFER_8D_CSV},
    ],
    "goals": [
        {
            "title": "Cell-A OEE ≥ 82% next quarter",
            "description": "Recover OEE on Cell-A after the April dip.",
            "success_criteria": "82% or higher on a 4-week rolling average.",
            "owner_email": "elke@schafer.example", "visibility": "team", "days_out": 60,
            "krs": [
                {"name": "Cell-A OEE (latest week)", "unit": "%", "target_value": 82,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/oee-cell-a.csv", "column": "oee", "alias": "oee_a", "cadence_minutes": 1440, "drift_threshold_pct": 5}},
                {"name": "Scrap PPM", "unit": "ppm", "target_value": 20,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/oee-cell-a.csv", "column": "scrap_ppm", "alias": "ppm_a", "cadence_minutes": 1440}},
            ],
        },
        {
            "title": "Cell-B OEE stays ≥ 84% through quarter-end",
            "description": "Protect the reference cell. If it regresses like Cell-A, all-hands.",
            "success_criteria": "Cell-B OEE never dips below 82% any week.",
            "owner_email": "manfred@schafer.example", "visibility": "team", "days_out": 60,
            "krs": [
                {"name": "Cell-B OEE (latest week)", "unit": "%", "target_value": 84,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/oee-cell-b.csv", "column": "oee", "alias": "oee_b", "cadence_minutes": 1440, "drift_threshold_pct": 3}},
            ],
        },
        {
            "title": "Close every open 8D within 15 working days",
            "description": "Customer 8Ds get escalated at 15 days. Anything open at 15 is a red flag.",
            "success_criteria": "No open 8D over 15 working days.",
            "owner_email": "hans@schafer.example", "visibility": "team", "days_out": 21,
            "krs": [
                {"name": "8Ds open > 15 days", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "over15"}},
                {"name": "Total open 8Ds", "unit": "count", "target_value": 3,
                 "measurement_kind": "manual", "measurement_config": {"alias": "open_8d"}},
            ],
        },
        {
            "title": "Bosch KA PPM under 20 this quarter",
            "description": "Customer-specific quality. PPM spike triggers audit visit.",
            "success_criteria": "PPM ≤ 20 on 4-week rolling average for Bosch parts.",
            "owner_email": "stefan@schafer.example", "visibility": "team", "days_out": 60,
            "krs": [
                {"name": "Bosch PPM", "unit": "ppm", "target_value": 20,
                 "measurement_kind": "manual", "measurement_config": {"alias": "bosch_ppm"}},
            ],
        },
    ],
    "skills": [
        {"name": "8d-drafter", "description": "Draft an 8D response for a customer quality complaint.", "path": ".claude/skills/8d-drafter/SKILL.md"},
    ],
}


# ═════════════════════════════════════════════════════════════════════════════
# BARRETT — law firm (M&A practice group, billables, matter management)
# ═════════════════════════════════════════════════════════════════════════════

BARRETT_HOURS_CSV = """week_ending,billable_hours,non_billable_hours,originations_usd
2026-03-07,48,4,0
2026-03-14,46,5,0
2026-03-21,50,3,85000
2026-03-28,52,2,0
2026-04-04,49,3,0
2026-04-11,51,4,120000
2026-04-18,48,3,0
"""

BARRETT_PG_PIPELINE_CSV = """stage,count,value_usd
Prospect,8,2400000
Mandate,4,1600000
Engaged,6,3200000
Closed_YTD,9,4800000
"""


BARRETT_PACK: dict[str, Any] = {
    "teams": [
        {"name": "M&A Practice", "slug": "pg-ma", "description": "Mergers & acquisitions practice group.", "lead_email": "james@barrett.example"},
        {"name": "Acme Matter Team", "slug": "acme-team", "description": "Team staffed on Acme acquisition (2026-0142).", "lead_email": "james@barrett.example"},
    ],
    "people": [
        {"name": "Harold Barrett", "email": "harold@barrett.example", "title": "Managing Partner",
         "level": 1, "level_label": "Mgmt Partner", "role_description": "Firm-wide. Chambers submissions, lateral hires, partnership admissions.",
         "teams": []},
        {"name": "James Holloway", "email": "james@barrett.example", "title": "M&A Partner (Practice Group Head)",
         "level": 2, "level_label": "Partner", "role_description": "Heads M&A practice; owns group P&L + Chambers submission.",
         "manager_email": "harold@barrett.example", "teams": ["pg-ma", "acme-team"]},
        {"name": "Caroline Chen", "email": "caroline@barrett.example", "title": "M&A Partner",
         "level": 2, "level_label": "Partner", "role_description": "Senior partner, cross-border deals.",
         "manager_email": "harold@barrett.example", "teams": ["pg-ma"]},
        {"name": "Michael Ross", "email": "michael@barrett.example", "title": "Senior Associate (Yr 4)",
         "level": 5, "level_label": "Sr Associate", "role_description": "Deal execution on mid-market M&A. On Acme + Stellar.",
         "manager_email": "james@barrett.example", "teams": ["pg-ma", "acme-team"]},
        {"name": "Priya Sharma", "email": "priya.s@barrett.example", "title": "Mid-level Associate (Yr 3)",
         "level": 6, "level_label": "Associate", "role_description": "Diligence lead. 1950 target.",
         "manager_email": "james@barrett.example", "teams": ["pg-ma", "acme-team"]},
        {"name": "Dan O'Connor", "email": "dan@barrett.example", "title": "Junior Associate (Yr 1)",
         "level": 7, "level_label": "Jr Associate", "role_description": "Research, first drafts. 1800 target.",
         "manager_email": "priya.s@barrett.example", "teams": ["pg-ma"]},
    ],
    "channels": [
        {"name": "pg-ma", "slug": "pg-ma", "kind": "private",
         "description": "M&A practice group internal.",
         "members": ["harold@barrett.example", "james@barrett.example", "caroline@barrett.example", "michael@barrett.example", "priya.s@barrett.example", "dan@barrett.example"]},
        {"name": "matter-acme-2026-0142", "slug": "matter-acme-2026-0142", "kind": "private",
         "description": "Acme acquisition — confidential.",
         "members": ["james@barrett.example", "michael@barrett.example", "priya.s@barrett.example", "dan@barrett.example"]},
        {"name": "matter-stellar-2026-0189", "slug": "matter-stellar-2026-0189", "kind": "private",
         "description": "Stellar JV matter — confidential.",
         "members": ["james@barrett.example", "michael@barrett.example"]},
        {"name": "km-ai-pilot", "slug": "km-ai-pilot", "kind": "public",
         "description": "Knowledge Management AI pilot — documentation, precedents.",
         "members": ["james@barrett.example", "caroline@barrett.example", "priya.s@barrett.example"]},
    ],
    "csvs": [
        {"owner_email": "michael@barrett.example", "path": "public/my-hours.csv", "content": BARRETT_HOURS_CSV},
        {"owner_email": "james@barrett.example", "path": "public/pg-pipeline.csv", "content": BARRETT_PG_PIPELINE_CSV},
    ],
    "goals": [
        {
            "title": "1,950 billable hours + zero late entries this year",
            "description": "Personal billable target; late entries kill realization.",
            "success_criteria": "1,950 hours by year-end, zero entries > 48h late.",
            "owner_email": "michael@barrett.example", "visibility": "private", "days_out": 250,
            "krs": [
                {"name": "Billable hours this week", "unit": "h", "target_value": 40,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/my-hours.csv", "column": "billable_hours", "alias": "hrs", "cadence_minutes": 10080}},
                {"name": "Entries > 48h late", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "late"}},
            ],
        },
        {
            "title": "M&A practice group revenue $12M this year",
            "description": "Group P&L target for James's practice.",
            "success_criteria": "$12M revenue by year-end with $4M originations from James personally.",
            "owner_email": "james@barrett.example", "visibility": "team", "days_out": 250,
            "krs": [
                {"name": "Closed YTD ($)", "unit": "$", "target_value": 12000000,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/pg-pipeline.csv", "column": "value_usd", "row": "last", "alias": "pg_revenue", "cadence_minutes": 1440}},
                {"name": "Originations YTD ($)", "unit": "$", "target_value": 4000000,
                 "measurement_kind": "manual", "measurement_config": {"alias": "origin"}},
            ],
        },
        {
            "title": "Acme matter — close by July 31",
            "description": "Strategic deal. Slippage triggers client escalation.",
            "success_criteria": "Signed by July 31; diligence complete by June 1.",
            "owner_email": "michael@barrett.example", "visibility": "team", "days_out": 75,
            "krs": [
                {"name": "Milestone: Diligence complete", "unit": "binary", "target_value": 1,
                 "measurement_kind": "manual", "measurement_config": {"alias": "dd"}},
                {"name": "Milestone: Signed", "unit": "binary", "target_value": 1,
                 "measurement_kind": "manual", "measurement_config": {"alias": "signed"}},
                {"name": "Matter-specific issues open", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "issues"}},
            ],
        },
        {
            "title": "Chambers 2027 submission — win an upgrade in M&A band",
            "description": "Chambers submission window opens in 90 days. Assemble matters, references, quotes now.",
            "success_criteria": "Full package submitted by deadline with ≥ 5 referee names.",
            "owner_email": "james@barrett.example", "visibility": "private", "days_out": 90,
            "krs": [
                {"name": "Referee names collected", "unit": "count", "target_value": 5,
                 "measurement_kind": "manual", "measurement_config": {"alias": "refs"}},
                {"name": "Matter writeups drafted", "unit": "count", "target_value": 12,
                 "measurement_kind": "manual", "measurement_config": {"alias": "writeups"}},
                {"name": "Partner quotes collected", "unit": "count", "target_value": 3,
                 "measurement_kind": "manual", "measurement_config": {"alias": "quotes"}},
            ],
        },
    ],
    "skills": [
        {"name": "time-entry-drafter", "description": "Draft billable time entries from calendar + doc edits + channel activity.", "path": ".claude/skills/time-entry-drafter/SKILL.md"},
    ],
}


# ═════════════════════════════════════════════════════════════════════════════
# NIMBUS — enterprise SaaS (GTM, forecast, pipeline, CS)
# ═════════════════════════════════════════════════════════════════════════════

NIMBUS_OPPS_CSV = """opp_name,account,amount_usd,close_date,stage,last_activity_days
Globex Platform,Globex,180000,2026-05-27,Contracting,3
Meridian Seats,Meridian,80000,2026-05-20,Negotiation,5
Atlas Expansion,Atlas Group,120000,2026-06-15,Discovery,9
Orion Renewal,Orion,240000,2026-07-10,Qualified,2
Helios Platform,Helios,90000,2026-06-05,Negotiation,1
"""

NIMBUS_PIPELINE_CSV = """week_ending,quota_attainment,pipeline_coverage,won_acv
2026-03-07,62,3.2,185000
2026-03-14,65,3.5,208000
2026-03-21,68,3.8,228000
2026-03-28,71,4.1,242000
2026-04-04,73,4.0,258000
2026-04-11,76,4.0,272000
2026-04-18,78,3.9,286000
"""

NIMBUS_CS_CSV = """month,nrr_pct,gross_churn_pct,csqo_count
2026-01-31,113,2.4,4
2026-02-28,114,2.2,5
2026-03-31,115,2.1,6
"""


NIMBUS_PACK: dict[str, Any] = {
    "teams": [
        {"name": "Enterprise GTM", "slug": "enterprise-gtm", "description": "Strategic AE pod.", "lead_email": "sarah@nimbus.example"},
        {"name": "Customer Success", "slug": "cs", "description": "Post-sale customer success org.", "lead_email": "kenji@nimbus.example"},
    ],
    "people": [
        {"name": "Eliza Park", "email": "eliza@nimbus.example", "title": "CRO",
         "level": 1, "level_label": "CRO", "role_description": "Owns revenue org: sales, CS, RevOps.",
         "teams": []},
        {"name": "Sarah Chen", "email": "sarah@nimbus.example", "title": "VP Enterprise Sales",
         "level": 2, "level_label": "VP", "role_description": "Strategic AE pod; quota roll-up.",
         "manager_email": "eliza@nimbus.example", "teams": ["enterprise-gtm"]},
        {"name": "Kenji Tanaka", "email": "kenji@nimbus.example", "title": "VP Customer Success",
         "level": 2, "level_label": "VP", "role_description": "NRR, churn, CSQO motion.",
         "manager_email": "eliza@nimbus.example", "teams": ["cs"]},
        {"name": "Jake Park", "email": "jake@nimbus.example", "title": "Strategic AE",
         "level": 4, "level_label": "AE", "role_description": "Quota $300K ACV quarterly. Globex, Meridian, Atlas book.",
         "manager_email": "sarah@nimbus.example", "teams": ["enterprise-gtm"]},
        {"name": "Maria Fernandez", "email": "maria@nimbus.example", "title": "Strategic AE",
         "level": 4, "level_label": "AE", "role_description": "Quota $300K ACV. Orion + Helios book.",
         "manager_email": "sarah@nimbus.example", "teams": ["enterprise-gtm"]},
        {"name": "Ben Shapiro", "email": "ben@nimbus.example", "title": "CSM",
         "level": 5, "level_label": "CSM", "role_description": "8 enterprise accounts. Drives renewals + expansion signal.",
         "manager_email": "kenji@nimbus.example", "teams": ["cs"]},
    ],
    "channels": [
        {"name": "forecast-call", "slug": "forecast-call", "kind": "private",
         "description": "Weekly forecast + pipeline calls.",
         "members": ["eliza@nimbus.example", "sarah@nimbus.example", "jake@nimbus.example", "maria@nimbus.example"]},
        {"name": "deal-desk", "slug": "deal-desk", "kind": "private",
         "description": "Pricing, legal, MSA threads on live deals.",
         "members": ["sarah@nimbus.example", "jake@nimbus.example", "maria@nimbus.example"]},
        {"name": "cs-health", "slug": "cs-health", "kind": "public",
         "description": "Churn risk, expansion signals, CSQO pipeline.",
         "members": ["kenji@nimbus.example", "ben@nimbus.example", "sarah@nimbus.example"]},
        {"name": "opp-globex", "slug": "opp-globex", "kind": "private",
         "description": "Globex deal — contracting stage. Confidential.",
         "members": ["sarah@nimbus.example", "jake@nimbus.example"]},
    ],
    "csvs": [
        {"owner_email": "jake@nimbus.example", "path": "public/salesforce-opps.csv", "content": NIMBUS_OPPS_CSV},
        {"owner_email": "sarah@nimbus.example", "path": "public/pipeline.csv", "content": NIMBUS_PIPELINE_CSV},
        {"owner_email": "kenji@nimbus.example", "path": "public/cs-metrics.csv", "content": NIMBUS_CS_CSV},
    ],
    "goals": [
        {
            "title": "Q2 quota $300K ACV (Jake)",
            "description": "Personal quota. Globex + Meridian are commit; Atlas is best-case.",
            "success_criteria": "$300K ACV closed-won by end of Q2.",
            "owner_email": "jake@nimbus.example", "visibility": "private", "days_out": 75,
            "krs": [
                {"name": "ACV closed-won (QTD)", "unit": "$", "target_value": 300000,
                 "measurement_kind": "manual", "measurement_config": {"alias": "acv"}},
                {"name": "Pipeline coverage (x quota)", "unit": "x", "target_value": 4,
                 "measurement_kind": "manual", "measurement_config": {"alias": "coverage"}},
            ],
        },
        {
            "title": "Pod pipeline coverage ≥ 4× quota sustained",
            "description": "Pod health leading indicator. If coverage slips, Q3 is already at risk.",
            "success_criteria": "Weekly pipeline coverage ≥ 4× the pod quota.",
            "owner_email": "sarah@nimbus.example", "visibility": "team", "days_out": 90,
            "krs": [
                {"name": "Pipeline coverage (latest)", "unit": "x", "target_value": 4,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/pipeline.csv", "column": "pipeline_coverage", "alias": "cov", "cadence_minutes": 1440, "drift_threshold_pct": 10}},
                {"name": "Quota attainment (pod, YTD %)", "unit": "%", "target_value": 100,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/pipeline.csv", "column": "quota_attainment", "alias": "attain", "cadence_minutes": 1440}},
            ],
        },
        {
            "title": "NRR ≥ 115% through the year",
            "description": "Expansion-motion benchmark. Break it and Series C story weakens.",
            "success_criteria": "Monthly NRR ≥ 115% for Q2 + Q3.",
            "owner_email": "kenji@nimbus.example", "visibility": "team", "days_out": 180,
            "krs": [
                {"name": "NRR (latest month)", "unit": "%", "target_value": 115,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/cs-metrics.csv", "column": "nrr_pct", "alias": "nrr", "cadence_minutes": 10080}},
                {"name": "Gross churn (latest month)", "unit": "%", "target_value": 2,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/cs-metrics.csv", "column": "gross_churn_pct", "alias": "churn", "cadence_minutes": 10080, "drift_threshold_pct": 15}},
            ],
        },
        {
            "title": "Globex closed-won by May 27",
            "description": "Single deal — $180K ACV. Legal review is stalled.",
            "success_criteria": "MSA signed by May 27; PO received.",
            "owner_email": "jake@nimbus.example", "visibility": "private", "days_out": 35,
            "krs": [
                {"name": "MSA signed", "unit": "binary", "target_value": 1,
                 "measurement_kind": "manual", "measurement_config": {"alias": "msa"}},
                {"name": "Days in Contracting", "unit": "days", "target_value": 15,
                 "measurement_kind": "manual", "measurement_config": {"alias": "contracting_days"}},
            ],
        },
    ],
    "skills": [
        {"name": "forecast-call-preparer", "description": "Prepare commit / best / pipeline with risk flags.", "path": ".claude/skills/forecast-call-preparer/SKILL.md"},
    ],
}


# ═════════════════════════════════════════════════════════════════════════════
# LUMA — DTC / e-commerce (perf, lifecycle, subscriptions, launches)
# ═════════════════════════════════════════════════════════════════════════════

LUMA_PERF_CSV = """week_ending,channel,spend_usd,revenue_usd,roas,cac_usd
2026-04-06,Meta,42000,100800,2.40,44
2026-04-13,Meta,45000,103500,2.30,47
2026-04-20,Meta,46000,101200,2.20,49
"""

LUMA_EMAIL_CSV = """week_ending,email_rev_share_pct,welcome_open_rate,subs_count
2026-03-28,25,47,12400
2026-04-04,25,45,12580
2026-04-11,24,42,12640
2026-04-18,24,38,12700
"""

LUMA_SUBS_CSV = """month,subs_count,subs_churn_pct,mrr_usd
2026-02-28,11820,4.8,298000
2026-03-31,12400,4.6,314000
2026-04-30,12700,4.5,322000
"""

LUMA_LAUNCH_CSV = """milestone,target_date,status
Creative approved,2026-05-08,on_track
Landing page live,2026-05-14,at_risk
Email warm-up,2026-05-18,not_started
Launch day,2026-05-22,not_started
"""


LUMA_PACK: dict[str, Any] = {
    "teams": [
        {"name": "Performance Marketing", "slug": "perf", "description": "Paid channels + attribution.", "lead_email": "maya@luma.example"},
        {"name": "Lifecycle", "slug": "lifecycle", "description": "Email + SMS + subscription.", "lead_email": "jordan@luma.example"},
        {"name": "Launch — Serum-Plus", "slug": "launch-serum-plus", "description": "May 22 launch team.", "lead_email": "taylor@luma.example"},
    ],
    "people": [
        {"name": "Priya Mahajan", "email": "priya@luma.example", "title": "CMO",
         "level": 1, "level_label": "CMO", "role_description": "Owns all marketing outcomes. 6 direct reports across paid / lifecycle / brand / CX / e-com / launches.",
         "teams": []},
        {"name": "Maya Tran", "email": "maya@luma.example", "title": "Performance Marketing (Meta)",
         "level": 4, "level_label": "IC", "role_description": "Owns Meta paid.",
         "manager_email": "priya@luma.example", "teams": ["perf"]},
        {"name": "Jordan Ellis", "email": "jordan@luma.example", "title": "Email Lifecycle Manager",
         "level": 3, "level_label": "Manager", "role_description": "Runs Klaviyo flows, welcome-flow perf, subscription churn.",
         "manager_email": "priya@luma.example", "teams": ["lifecycle"]},
        {"name": "Taylor Grant", "email": "taylor@luma.example", "title": "Launch Manager",
         "level": 3, "level_label": "Manager", "role_description": "Owns cross-functional launches. Next up: Serum-Plus on May 22.",
         "manager_email": "priya@luma.example", "teams": ["launch-serum-plus"]},
        {"name": "Riley Cooper", "email": "riley@luma.example", "title": "Senior Copywriter",
         "level": 5, "level_label": "Sr Copy", "role_description": "Ad copy, email, landing pages.",
         "manager_email": "priya@luma.example", "teams": ["perf", "lifecycle", "launch-serum-plus"]},
        {"name": "Sam Patel", "email": "sam@luma.example", "title": "Head of Growth",
         "level": 2, "level_label": "Director", "role_description": "Paid + lifecycle roll-up; owns blended ROAS and CAC targets.",
         "manager_email": "priya@luma.example", "teams": ["perf", "lifecycle"]},
    ],
    "channels": [
        {"name": "perf-weekly-standup", "slug": "perf-weekly-standup", "kind": "public",
         "description": "Monday perf standup + daily ROAS check.",
         "members": ["priya@luma.example", "sam@luma.example", "maya@luma.example"]},
        {"name": "creative-review", "slug": "creative-review", "kind": "public",
         "description": "Creative briefs, approvals, launches.",
         "members": ["priya@luma.example", "maya@luma.example", "jordan@luma.example", "taylor@luma.example", "riley@luma.example"]},
        {"name": "lifecycle-email", "slug": "lifecycle-email", "kind": "public",
         "description": "Email + SMS campaigns, Klaviyo threads.",
         "members": ["jordan@luma.example", "priya@luma.example", "riley@luma.example"]},
        {"name": "launch-serum-plus", "slug": "launch-serum-plus", "kind": "public",
         "description": "Serum-Plus launch — May 22 target.",
         "members": ["priya@luma.example", "taylor@luma.example", "maya@luma.example", "jordan@luma.example", "riley@luma.example"]},
        {"name": "perf-weekly-review", "slug": "perf-weekly-review", "kind": "private",
         "description": "Priya's weekly review with Sam.",
         "members": ["priya@luma.example", "sam@luma.example"]},
    ],
    "csvs": [
        {"owner_email": "maya@luma.example", "path": "public/perf-week.csv", "content": LUMA_PERF_CSV},
        {"owner_email": "jordan@luma.example", "path": "public/email-week.csv", "content": LUMA_EMAIL_CSV},
        {"owner_email": "jordan@luma.example", "path": "public/subs.csv", "content": LUMA_SUBS_CSV},
        {"owner_email": "taylor@luma.example", "path": "public/launch-serum-plus.csv", "content": LUMA_LAUNCH_CSV},
    ],
    "goals": [
        {
            "title": "Meta blended ROAS ≥ 2.4 for April",
            "description": "Reverse April slippage; creative fatigue is the hypothesis.",
            "success_criteria": "Blended Meta ROAS ≥ 2.4 for the full month.",
            "owner_email": "maya@luma.example", "visibility": "team", "days_out": 15,
            "krs": [
                {"name": "Meta ROAS (latest week)", "unit": "x", "target_value": 2.4,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/perf-week.csv", "column": "roas", "alias": "roas", "cadence_minutes": 360, "drift_threshold_pct": 8}},
                {"name": "CAC (new-customer, Meta)", "unit": "$", "target_value": 42,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/perf-week.csv", "column": "cac_usd", "alias": "cac", "cadence_minutes": 360}},
            ],
        },
        {
            "title": "Email = 26% of total revenue this quarter",
            "description": "Lifecycle pulling weight. Welcome-flow open rate is tanking; fix before Q3.",
            "success_criteria": "Email ≥ 26% of revenue on rolling 30-day basis.",
            "owner_email": "jordan@luma.example", "visibility": "team", "days_out": 70,
            "krs": [
                {"name": "Email revenue share", "unit": "%", "target_value": 26,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/email-week.csv", "column": "email_rev_share_pct", "alias": "email_share", "cadence_minutes": 1440}},
                {"name": "Welcome-flow open rate", "unit": "%", "target_value": 45,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/email-week.csv", "column": "welcome_open_rate", "alias": "welcome", "cadence_minutes": 1440, "drift_threshold_pct": 10}},
            ],
        },
        {
            "title": "Subscription churn < 4.0% monthly",
            "description": "Subs are the LTV engine. Churn creep kills payback.",
            "success_criteria": "Monthly churn below 4.0% for Q2.",
            "owner_email": "jordan@luma.example", "visibility": "team", "days_out": 90,
            "krs": [
                {"name": "Subs churn (latest month)", "unit": "%", "target_value": 4.0,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/subs.csv", "column": "subs_churn_pct", "alias": "sub_churn", "cadence_minutes": 10080}},
                {"name": "Active subscribers", "unit": "count", "target_value": 13000,
                 "measurement_kind": "workspace_file",
                 "measurement_config": {"path": "public/subs.csv", "column": "subs_count", "alias": "subs_count", "cadence_minutes": 10080}},
            ],
        },
        {
            "title": "Serum-Plus launch on May 22",
            "description": "Q2 hero launch. Creative review slipping; landing page at risk.",
            "success_criteria": "All launch milestones hit; go-live on May 22.",
            "owner_email": "taylor@luma.example", "visibility": "team", "days_out": 34,
            "krs": [
                {"name": "Milestones completed", "unit": "count", "target_value": 4,
                 "measurement_kind": "manual", "measurement_config": {"alias": "milestones"}},
                {"name": "Milestones at risk", "unit": "count", "target_value": 0,
                 "measurement_kind": "manual", "measurement_config": {"alias": "at_risk"}},
            ],
        },
    ],
    "skills": [
        {"name": "perf-weekly-drafter", "description": "Draft the weekly DTC performance summary.", "path": ".claude/skills/perf-weekly-drafter/SKILL.md"},
    ],
}


# ═════════════════════════════════════════════════════════════════════════════
# registry + install dispatcher
# ═════════════════════════════════════════════════════════════════════════════

PACK_CONFIGS: dict[str, dict[str, Any]] = {
    "sanghavi": SANGHAVI_PACK,
    "schafer": SCHAFER_PACK,
    "barrett": BARRETT_PACK,
    "nimbus": NIMBUS_PACK,
    "luma": LUMA_PACK,
}


async def install(
    db: AsyncSession, *, org_id: uuid.UUID, admin: Person, pack: str,
) -> dict[str, Any]:
    cfg = PACK_CONFIGS.get(pack)
    if cfg is None:
        raise ValueError(f"unknown pack: {pack}")
    result = PackResult()

    people_by_email: dict[str, Person] = {admin.email.lower(): admin}
    teams_by_slug: dict[str, Team] = {}

    # ── teams (pass 1: create; lead_id in pass 2)
    for team_cfg in cfg.get("teams", []):
        slug = team_cfg["slug"]
        existing = (
            await db.execute(select(Team).where(Team.org_id == org_id, Team.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            teams_by_slug[slug] = existing
            continue
        t = Team(
            org_id=org_id, name=team_cfg["name"], slug=slug,
            description=team_cfg.get("description", ""),
        )
        db.add(t)
        await db.flush()
        teams_by_slug[slug] = t
        result.teams_created += 1

    # ── people
    for person_cfg in cfg.get("people", []):
        email = person_cfg["email"].lower()
        existing = (
            await db.execute(select(Person).where(Person.org_id == org_id, Person.email == email))
        ).scalar_one_or_none()
        if existing is not None:
            people_by_email[email] = existing
            continue
        mgr_email = (person_cfg.get("manager_email") or "").lower()
        manager_id = people_by_email[mgr_email].id if mgr_email in people_by_email else None
        draft = PersonDraft(
            name=person_cfg["name"],
            email=email,
            title=person_cfg.get("title", ""),
            level=person_cfg.get("level", 5),
            level_label=person_cfg.get("level_label", ""),
            role_description=person_cfg.get("role_description", ""),
            person_type=person_cfg.get("person_type", "employee"),
            working_mode=person_cfg.get("working_mode", ""),
        )
        p = await create_person(db, org_id=org_id, draft=draft, manager_id=manager_id)
        people_by_email[email] = p
        result.people_created += 1
        for team_slug in person_cfg.get("teams", []):
            t = teams_by_slug.get(team_slug)
            if t is not None:
                db.add(TeamMembership(team_id=t.id, person_id=p.id, role="member"))
    await db.flush()

    # ── team leads
    for team_cfg in cfg.get("teams", []):
        lead_email = (team_cfg.get("lead_email") or "").lower()
        t = teams_by_slug.get(team_cfg["slug"])
        if t is None or not lead_email:
            continue
        lead = people_by_email.get(lead_email)
        if lead is None:
            continue
        t.lead_id = lead.id
        existing = (
            await db.execute(
                select(TeamMembership).where(
                    TeamMembership.team_id == t.id, TeamMembership.person_id == lead.id
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(TeamMembership(team_id=t.id, person_id=lead.id, role="lead"))
        else:
            existing.role = "lead"

    # ── channels
    for ch_cfg in cfg.get("channels", []):
        slug = ch_cfg["slug"]
        existing = (
            await db.execute(select(Channel).where(Channel.org_id == org_id, Channel.slug == slug))
        ).scalar_one_or_none()
        if existing is not None:
            continue
        ch = Channel(
            org_id=org_id, name=ch_cfg["name"], slug=slug,
            description=ch_cfg.get("description", ""),
            kind=ch_cfg.get("kind", "public"),
            created_by_id=admin.id,
        )
        db.add(ch)
        await db.flush()
        added = set()
        db.add(ChannelMember(channel_id=ch.id, person_id=admin.id))
        added.add(admin.id)
        for member_email in ch_cfg.get("members", []):
            p = people_by_email.get(member_email.lower())
            if p is not None and p.id not in added:
                db.add(ChannelMember(channel_id=ch.id, person_id=p.id))
                added.add(p.id)
        result.channels_created += 1

    # ── CSVs into workspaces
    for csv_cfg in cfg.get("csvs", []):
        owner_key = csv_cfg.get("owner_email", "admin").lower()
        owner = admin if owner_key == "admin" else people_by_email.get(owner_key)
        if owner is None:
            continue
        root = ensure_workspace(owner.id)
        target = safe_relative(root, csv_cfg["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(csv_cfg["content"], encoding="utf-8")
        result.csvs_written.append(f"{owner.email}:{csv_cfg['path']}")

    # ── goals
    for goal_cfg in cfg.get("goals", []):
        owner = people_by_email.get(goal_cfg["owner_email"].lower())
        if owner is None:
            continue
        deadline = date.today() + timedelta(days=int(goal_cfg.get("days_out", 60)))
        try:
            await create_goal(
                db,
                org_id=org_id,
                owner_id=owner.id,
                author_id=admin.id,
                title=goal_cfg["title"],
                description=goal_cfg.get("description", ""),
                success_criteria=goal_cfg.get("success_criteria", ""),
                deadline=deadline,
                visibility=goal_cfg.get("visibility", "team"),
                key_results=goal_cfg["krs"],
            )
            result.goals_created += 1
        except ValueError:
            continue

    # ── skills (register SkillRecord rows pointing at shipped markdown)
    for skill_cfg in cfg.get("skills", []):
        name = skill_cfg["name"]
        path = skill_cfg["path"]
        if not Path(path).exists():
            continue
        existing = (
            await db.execute(
                select(SkillRecord).where(
                    SkillRecord.org_id == org_id,
                    SkillRecord.person_id.is_(None),
                    SkillRecord.name == name,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue
        db.add(SkillRecord(
            org_id=org_id, person_id=None,
            name=name, description=skill_cfg.get("description", ""),
            path=path, tier="persona",
        ))
        result.skills_registered += 1

    return result.to_dict()
