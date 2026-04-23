"""Builds the impex-firm sample SQLite databases used by the 'impex' persona.

One file per logical data source: ERP, Finance, Logistics, HR. Called once at
pack install time. Idempotent — if the file already exists it is rebuilt.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


# ── ERP — buyers, invoices, shipments, LCs ───────────────────────────────────

_ERP_SCHEMA = """
DROP TABLE IF EXISTS buyers;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS lcs;

CREATE TABLE buyers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    risk_tier TEXT NOT NULL,
    credit_limit_usd REAL NOT NULL,
    open_exposure_usd REAL NOT NULL,
    tier_updated TEXT NOT NULL
);

CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    buyer_id INTEGER NOT NULL REFERENCES buyers(id),
    invoice_no TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    value_usd REAL NOT NULL,
    paid_usd REAL NOT NULL,
    status TEXT NOT NULL,
    lc_ref TEXT
);

CREATE TABLE shipments (
    id INTEGER PRIMARY KEY,
    buyer_id INTEGER NOT NULL REFERENCES buyers(id),
    shipping_bill_no TEXT NOT NULL,
    sb_date TEXT NOT NULL,
    invoice_id INTEGER REFERENCES invoices(id),
    port_of_loading TEXT NOT NULL,
    port_of_discharge TEXT NOT NULL,
    vessel TEXT,
    bl_no TEXT,
    status TEXT NOT NULL,
    delivered_at TEXT,
    on_time INTEGER NOT NULL
);

CREATE TABLE lcs (
    id INTEGER PRIMARY KEY,
    lc_ref TEXT UNIQUE NOT NULL,
    buyer_id INTEGER NOT NULL REFERENCES buyers(id),
    opened TEXT NOT NULL,
    expiry TEXT NOT NULL,
    value_usd REAL NOT NULL,
    stage TEXT NOT NULL,
    discrepancies INTEGER NOT NULL,
    issuing_bank TEXT,
    advising_bank TEXT
);
"""

_ERP_ROWS: dict[str, list[tuple]] = {
    "buyers": [
        (1, "Bosch KA", "DE", "A", 1_500_000, 842_000, "2026-03-28"),
        (2, "Daimler Euro", "DE", "A", 2_000_000, 1_124_400, "2026-03-28"),
        (3, "VW Wolfsburg", "DE", "A", 1_800_000, 961_300, "2026-03-28"),
        (4, "Hyundai India", "IN", "B", 900_000, 412_500, "2026-04-05"),
        (5, "Renault", "FR", "B", 1_200_000, 588_200, "2026-04-05"),
        (6, "Stellantis", "IT", "B", 1_100_000, 329_200, "2026-04-05"),
        (7, "TATA AutoComp", "IN", "C", 600_000, 144_800, "2026-04-05"),
        (8, "Mahindra CV", "IN", "C", 500_000, 91_700, "2026-03-22"),
    ],
    "invoices": [
        (1, 1, "EX-26-0041", "2026-02-10", "2026-04-11", 218_400, 218_400, "paid", "LC-2026-041"),
        (2, 2, "EX-26-0042", "2026-02-18", "2026-04-19", 312_900, 312_900, "paid", "LC-2026-042"),
        (3, 4, "EX-26-0043", "2026-02-22", "2026-04-23", 141_000, 0, "open", "LC-2026-043"),
        (4, 3, "EX-26-0044", "2026-03-01", "2026-05-02", 405_600, 0, "overdue", "LC-2026-044"),
        (5, 1, "EX-26-0045", "2026-03-08", "2026-05-09", 198_200, 0, "open", "LC-2026-045"),
        (6, 6, "EX-26-0046", "2026-03-12", "2026-05-13", 267_800, 0, "open", "LC-2026-046"),
        (7, 5, "EX-26-0047", "2026-03-14", "2026-05-15", 189_500, 0, "open", "LC-2026-047"),
        (8, 2, "EX-26-0048", "2026-03-18", "2026-05-19", 358_000, 0, "open", "LC-2026-048"),
        (9, 7, "EX-26-0049", "2026-03-20", "2026-04-19", 72_400, 72_400, "paid", None),
        (10, 8, "EX-26-0050", "2026-03-28", "2026-04-27", 44_300, 0, "overdue", None),
        (11, 4, "EX-26-0051", "2026-04-01", "2026-05-31", 98_900, 0, "open", None),
        (12, 3, "EX-26-0052", "2026-04-05", "2026-06-04", 224_800, 0, "open", None),
        (13, 1, "EX-26-0053", "2026-04-08", "2026-06-07", 311_200, 0, "open", None),
        (14, 5, "EX-26-0054", "2026-04-12", "2026-06-11", 173_300, 0, "open", None),
        (15, 6, "EX-26-0055", "2026-04-15", "2026-06-14", 201_500, 0, "open", None),
    ],
    "shipments": [
        (1, 1, "7420411", "2026-02-10", 1, "Nhava Sheva", "Hamburg", "MSC Loreto", "MSCU 4918201", "delivered", "2026-03-24", 1),
        (2, 2, "7421809", "2026-02-18", 2, "Nhava Sheva", "Bremerhaven", "Hapag Vienna", "HLBU 2210418", "delivered", "2026-03-29", 1),
        (3, 4, "7422814", "2026-02-22", 3, "Chennai", "Mumbai", "Overland", "—", "delivered", "2026-03-10", 1),
        (4, 3, "7424001", "2026-03-01", 4, "Nhava Sheva", "Hamburg", "CMA Palermo", "CMAU 7765500", "delayed", None, 0),
        (5, 1, "7425102", "2026-03-08", 5, "Nhava Sheva", "Hamburg", "MSC Rhea", "MSCU 5019002", "in_transit", None, 1),
        (6, 6, "7426118", "2026-03-12", 6, "Nhava Sheva", "Genoa", "CMA Cirrus", "CMAU 7811110", "in_transit", None, 1),
        (7, 5, "7427017", "2026-03-14", 7, "Nhava Sheva", "Le Havre", "Evergreen Kite", "EGHU 3320119", "in_transit", None, 1),
        (8, 2, "7428210", "2026-03-18", 8, "Nhava Sheva", "Bremerhaven", "Hapag Hamburg", "HLBU 2213308", "in_transit", None, 1),
        (9, 7, "7429311", "2026-03-20", 9, "Chennai", "Mumbai", "Overland", "—", "delivered", "2026-04-02", 1),
        (10, 8, "7430002", "2026-03-28", 10, "Nhava Sheva", "Mumbai", "Overland", "—", "delayed", None, 0),
        (11, 4, "7430999", "2026-04-01", 11, "Chennai", "Chennai", "Overland", "—", "in_transit", None, 1),
        (12, 3, "7431888", "2026-04-05", 12, "Nhava Sheva", "Hamburg", "MSC Sirius", "MSCU 5102880", "booked", None, 1),
        (13, 1, "7432701", "2026-04-08", 13, "Nhava Sheva", "Hamburg", "Maersk Sana", "MAEU 9910218", "booked", None, 1),
        (14, 5, "7433602", "2026-04-12", 14, "Nhava Sheva", "Le Havre", "CMA Topaz", "CMAU 7900045", "booked", None, 1),
        (15, 6, "7434511", "2026-04-15", 15, "Nhava Sheva", "Genoa", "Evergreen Frost", "EGHU 3418876", "booked", None, 1),
    ],
    "lcs": [
        (1, "LC-2026-041", 1, "2026-01-28", "2026-05-15", 218_400, "paid", 0, "Commerzbank", "HDFC"),
        (2, "LC-2026-042", 2, "2026-02-05", "2026-05-28", 312_900, "paid", 0, "Deutsche Bank", "HDFC"),
        (3, "LC-2026-043", 4, "2026-02-15", "2026-06-02", 141_000, "opened", 0, "Kookmin", "ICICI"),
        (4, "LC-2026-044", 3, "2026-02-18", "2026-06-18", 405_600, "discrepant", 2, "Commerzbank", "SBI"),
        (5, "LC-2026-045", 1, "2026-03-01", "2026-06-25", 198_200, "presented", 1, "Commerzbank", "HDFC"),
        (6, "LC-2026-046", 6, "2026-03-04", "2026-06-30", 267_800, "opened", 0, "UniCredit", "ICICI"),
        (7, "LC-2026-047", 5, "2026-03-07", "2026-07-10", 189_500, "opened", 0, "BNP Paribas", "HDFC"),
        (8, "LC-2026-048", 2, "2026-03-10", "2026-07-15", 358_000, "opened", 0, "Deutsche Bank", "HDFC"),
    ],
}


# ── Finance — credit lines, cash flow, cost of capital, CCC, AP ──────────────

_FINANCE_SCHEMA = """
DROP TABLE IF EXISTS credit_lines;
DROP TABLE IF EXISTS cash_flow;
DROP TABLE IF EXISTS cost_of_capital;
DROP TABLE IF EXISTS ccc_inputs;
DROP TABLE IF EXISTS ap_ledger;

CREATE TABLE credit_lines (
    id INTEGER PRIMARY KEY,
    bank TEXT NOT NULL,
    facility_type TEXT NOT NULL,
    sanctioned_usd REAL NOT NULL,
    utilized_usd REAL NOT NULL,
    interest_rate REAL NOT NULL,
    maturity TEXT NOT NULL
);

CREATE TABLE cash_flow (
    id INTEGER PRIMARY KEY,
    date TEXT UNIQUE NOT NULL,
    inflow_usd REAL NOT NULL,
    outflow_usd REAL NOT NULL,
    net_usd REAL NOT NULL,
    closing_bank_balance_usd REAL NOT NULL
);

CREATE TABLE cost_of_capital (
    id INTEGER PRIMARY KEY,
    week_ending TEXT UNIQUE NOT NULL,
    weighted_avg_rate_pct REAL NOT NULL,
    total_borrowings_usd REAL NOT NULL
);

CREATE TABLE ccc_inputs (
    id INTEGER PRIMARY KEY,
    week_ending TEXT UNIQUE NOT NULL,
    dso_days REAL NOT NULL,
    dio_days REAL NOT NULL,
    dpo_days REAL NOT NULL,
    ccc_days REAL NOT NULL
);

CREATE TABLE ap_ledger (
    id INTEGER PRIMARY KEY,
    supplier TEXT NOT NULL,
    invoice_no TEXT NOT NULL,
    value_usd REAL NOT NULL,
    due_date TEXT NOT NULL,
    paid INTEGER NOT NULL,
    days_overdue INTEGER NOT NULL
);
"""

_FINANCE_ROWS: dict[str, list[tuple]] = {
    "credit_lines": [
        (1, "HDFC Bank", "PCFC (pre-shipment)", 3_000_000, 2_180_000, 8.9, "2026-12-31"),
        (2, "ICICI Bank", "PCFC (pre-shipment)", 2_500_000, 1_940_000, 9.1, "2026-12-31"),
        (3, "SBI", "Post-shipment credit", 2_000_000, 1_610_000, 9.4, "2026-09-30"),
        (4, "HDFC Bank", "Working capital OD", 1_500_000, 1_100_000, 10.2, "2027-03-31"),
        (5, "Axis Bank", "Term loan", 1_000_000, 800_000, 10.8, "2028-06-30"),
        (6, "Kotak", "BG facility", 800_000, 320_000, 0.0, "2026-12-31"),
    ],
    "cash_flow": [
        (1, "2026-03-28", 412_000, 381_000, 31_000, 1_240_000),
        (2, "2026-04-04", 278_000, 392_000, -114_000, 1_126_000),
        (3, "2026-04-11", 531_400, 308_000, 223_400, 1_349_400),
        (4, "2026-04-18", 189_000, 421_000, -232_000, 1_117_400),
    ],
    "cost_of_capital": [
        (1, "2026-02-28", 9.7, 6_850_000),
        (2, "2026-03-07", 9.8, 6_900_000),
        (3, "2026-03-14", 9.8, 7_010_000),
        (4, "2026-03-21", 9.7, 7_080_000),
        (5, "2026-03-28", 9.6, 7_150_000),
        (6, "2026-04-04", 9.6, 7_230_000),
        (7, "2026-04-11", 9.5, 7_180_000),
        (8, "2026-04-18", 9.5, 7_240_000),
    ],
    "ccc_inputs": [
        (1, "2026-02-28", 74, 36, 22, 88),
        (2, "2026-03-07", 73, 35, 22, 86),
        (3, "2026-03-14", 72, 35, 23, 84),
        (4, "2026-03-21", 71, 34, 24, 81),
        (5, "2026-03-28", 70, 34, 25, 79),
        (6, "2026-04-04", 70, 33, 26, 77),
        (7, "2026-04-11", 69, 33, 27, 75),
        (8, "2026-04-18", 68, 32, 28, 72),
    ],
    "ap_ledger": [
        (1, "Forge Tech Pvt", "FT-8811", 142_000, "2026-04-21", 0, 2),
        (2, "Machined Parts Co", "MP-0044", 88_500, "2026-04-10", 1, 0),
        (3, "Bharat Steel", "BS-2201", 220_000, "2026-04-28", 0, 0),
        (4, "Logistix Forwarders", "LF-INV-1102", 61_200, "2026-04-08", 0, 15),
        (5, "Coating Solutions", "CS-3370", 44_800, "2026-04-15", 1, 0),
        (6, "Nippon Gaskets", "NG-9922", 39_700, "2026-05-02", 0, 0),
    ],
}


# ── Logistics — full shipments, freight rates, EDPMS aging ───────────────────

_LOGISTICS_SCHEMA = """
DROP TABLE IF EXISTS shipments_full;
DROP TABLE IF EXISTS freight_rates;
DROP TABLE IF EXISTS edpms_aging;

CREATE TABLE shipments_full (
    id INTEGER PRIMARY KEY,
    bl_no TEXT NOT NULL,
    vessel TEXT NOT NULL,
    route TEXT NOT NULL,
    etd TEXT NOT NULL,
    eta TEXT NOT NULL,
    actual_arrival TEXT,
    status TEXT NOT NULL,
    on_time_flag INTEGER NOT NULL
);

CREATE TABLE freight_rates (
    id INTEGER PRIMARY KEY,
    route TEXT NOT NULL,
    week_ending TEXT NOT NULL,
    rate_usd_per_teu REAL NOT NULL,
    carrier TEXT NOT NULL
);

CREATE TABLE edpms_aging (
    id INTEGER PRIMARY KEY,
    shipping_bill_no TEXT UNIQUE NOT NULL,
    sb_date TEXT NOT NULL,
    buyer TEXT NOT NULL,
    invoice_value_usd REAL NOT NULL,
    days_outstanding INTEGER NOT NULL,
    ab_status TEXT NOT NULL
);
"""

_LOGISTICS_ROWS: dict[str, list[tuple]] = {
    "shipments_full": [
        (1, "MSCU 4918201", "MSC Loreto", "Nhava Sheva–Hamburg", "2026-02-10", "2026-03-18", "2026-03-24", "delivered", 0),
        (2, "HLBU 2210418", "Hapag Vienna", "Nhava Sheva–Bremerhaven", "2026-02-18", "2026-03-28", "2026-03-29", "delivered", 0),
        (3, "CMAU 7765500", "CMA Palermo", "Nhava Sheva–Hamburg", "2026-03-01", "2026-04-08", None, "delayed", 0),
        (4, "MSCU 5019002", "MSC Rhea", "Nhava Sheva–Hamburg", "2026-03-08", "2026-04-14", None, "in_transit", 1),
        (5, "CMAU 7811110", "CMA Cirrus", "Nhava Sheva–Genoa", "2026-03-12", "2026-04-19", None, "in_transit", 1),
        (6, "EGHU 3320119", "Evergreen Kite", "Nhava Sheva–Le Havre", "2026-03-14", "2026-04-22", None, "in_transit", 1),
        (7, "HLBU 2213308", "Hapag Hamburg", "Nhava Sheva–Bremerhaven", "2026-03-18", "2026-04-25", None, "in_transit", 1),
        (8, "MSCU 5102880", "MSC Sirius", "Nhava Sheva–Hamburg", "2026-04-05", "2026-05-12", None, "booked", 1),
        (9, "MAEU 9910218", "Maersk Sana", "Nhava Sheva–Hamburg", "2026-04-08", "2026-05-15", None, "booked", 1),
        (10, "CMAU 7900045", "CMA Topaz", "Nhava Sheva–Le Havre", "2026-04-12", "2026-05-20", None, "booked", 1),
        (11, "EGHU 3418876", "Evergreen Frost", "Nhava Sheva–Genoa", "2026-04-15", "2026-05-21", None, "booked", 1),
    ],
    "freight_rates": [
        (1, "Nhava Sheva–Hamburg", "2026-02-28", 1_820, "MSC"),
        (2, "Nhava Sheva–Hamburg", "2026-03-07", 1_880, "MSC"),
        (3, "Nhava Sheva–Hamburg", "2026-03-14", 1_940, "MSC"),
        (4, "Nhava Sheva–Hamburg", "2026-03-21", 2_010, "MSC"),
        (5, "Nhava Sheva–Hamburg", "2026-03-28", 2_060, "MSC"),
        (6, "Nhava Sheva–Hamburg", "2026-04-04", 2_110, "MSC"),
        (7, "Nhava Sheva–Hamburg", "2026-04-11", 2_240, "MSC"),
        (8, "Nhava Sheva–Hamburg", "2026-04-18", 2_390, "MSC"),
        (9, "Nhava Sheva–Genoa", "2026-03-28", 1_970, "CMA"),
        (10, "Nhava Sheva–Genoa", "2026-04-04", 2_020, "CMA"),
        (11, "Nhava Sheva–Genoa", "2026-04-11", 2_110, "CMA"),
        (12, "Nhava Sheva–Genoa", "2026-04-18", 2_180, "CMA"),
        (13, "Nhava Sheva–Le Havre", "2026-03-28", 2_020, "Evergreen"),
        (14, "Nhava Sheva–Le Havre", "2026-04-04", 2_080, "Evergreen"),
        (15, "Nhava Sheva–Le Havre", "2026-04-11", 2_150, "Evergreen"),
        (16, "Nhava Sheva–Le Havre", "2026-04-18", 2_230, "Evergreen"),
    ],
    "edpms_aging": [
        (1, "7428901", "2025-09-02", "Bosch KA", 118_000, 233, "overdue"),
        (2, "7439112", "2025-11-18", "VW Wolfsburg", 162_400, 156, "overdue"),
        (3, "7444201", "2025-12-20", "Daimler Euro", 94_100, 124, "watch"),
        (4, "7452903", "2026-01-14", "Hyundai India", 72_800, 99, "watch"),
        (5, "7461402", "2026-02-11", "Bosch KA", 83_200, 70, "ok"),
        (6, "7464801", "2026-02-28", "Stellantis", 61_400, 53, "ok"),
    ],
}


# ── HR — employees (PII), payroll (PII), attrition, open reqs ────────────────

_HR_SCHEMA = """
DROP TABLE IF EXISTS employees_pii;
DROP TABLE IF EXISTS payroll;
DROP TABLE IF EXISTS attrition;
DROP TABLE IF EXISTS open_reqs;

CREATE TABLE employees_pii (
    id INTEGER PRIMARY KEY,
    employee_no TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    title TEXT NOT NULL,
    pan TEXT NOT NULL,
    aadhaar TEXT NOT NULL,
    bank_account TEXT NOT NULL,
    dob TEXT NOT NULL,
    phone TEXT NOT NULL
);

CREATE TABLE payroll (
    id INTEGER PRIMARY KEY,
    employee_no TEXT NOT NULL,
    month TEXT NOT NULL,
    gross_salary_inr REAL NOT NULL,
    tax_deducted_inr REAL NOT NULL,
    net_salary_inr REAL NOT NULL,
    bonus_inr REAL NOT NULL
);

CREATE TABLE attrition (
    id INTEGER PRIMARY KEY,
    month TEXT NOT NULL,
    dept TEXT NOT NULL,
    hires INTEGER NOT NULL,
    exits INTEGER NOT NULL,
    attrition_pct REAL NOT NULL
);

CREATE TABLE open_reqs (
    id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,
    department TEXT NOT NULL,
    posted_on TEXT NOT NULL,
    days_open INTEGER NOT NULL,
    hiring_manager TEXT NOT NULL
);
"""

_HR_ROWS: dict[str, list[tuple]] = {
    "employees_pii": [
        (1, "EVP-0001", "Rakesh Shah", "Leadership", "CEO", "ABCPS1122K", "4812-3344-9901", "HDFC-50100998811", "1978-06-02", "+91 98210 00001"),
        (2, "EVP-0002", "Priya Menon", "Finance", "CFO", "BCXPM2031R", "5728-4911-2210", "HDFC-50100998812", "1982-11-17", "+91 98210 00002"),
        (3, "EVP-0003", "Arjun Desai", "Finance", "Credit Risk Analyst", "AKTPD3348N", "9911-2231-4455", "ICICI-400291008819", "1990-04-08", "+91 98210 00003"),
        (4, "EVP-0004", "Neha Iyer", "Logistics", "Logistics Manager", "DMLPI4421V", "8842-1119-3345", "ICICI-400291008820", "1986-02-21", "+91 98210 00004"),
        (5, "EVP-0005", "Kavya Reddy", "HR", "HR Head", "KVRPR5609M", "6611-2248-1198", "HDFC-50100998813", "1984-09-29", "+91 98210 00005"),
        (6, "EVP-0006", "Vikram Singh", "Sales", "Senior Sales Exec", "SNGPV6712P", "3391-8842-2210", "SBI-31099008811", "1988-12-14", "+91 98210 00006"),
        (7, "EVP-0007", "Aditi Sharma", "Finance", "Junior Analyst", "ADSPS7899L", "4429-1022-3341", "ICICI-400291008821", "1996-07-03", "+91 98210 00007"),
    ],
    "payroll": [
        (1, "EVP-0001", "2026-03", 1_250_000, 312_500, 937_500, 0),
        (2, "EVP-0002", "2026-03", 950_000, 237_500, 712_500, 0),
        (3, "EVP-0003", "2026-03", 340_000, 68_000, 272_000, 0),
        (4, "EVP-0004", "2026-03", 420_000, 84_000, 336_000, 25_000),
        (5, "EVP-0005", "2026-03", 500_000, 100_000, 400_000, 0),
        (6, "EVP-0006", "2026-03", 380_000, 76_000, 304_000, 80_000),
        (7, "EVP-0007", "2026-03", 140_000, 14_000, 126_000, 0),
    ],
    "attrition": [
        (1, "2026-01", "Finance", 0, 0, 0.0),
        (2, "2026-01", "Logistics", 1, 0, 0.0),
        (3, "2026-01", "Sales", 0, 1, 12.5),
        (4, "2026-02", "Finance", 1, 0, 0.0),
        (5, "2026-02", "Logistics", 0, 0, 0.0),
        (6, "2026-02", "Sales", 0, 0, 0.0),
        (7, "2026-03", "Finance", 0, 0, 0.0),
        (8, "2026-03", "Logistics", 0, 1, 9.1),
        (9, "2026-03", "Sales", 1, 0, 0.0),
    ],
    "open_reqs": [
        (1, "Senior Credit Analyst", "Finance", "2026-02-08", 75, "Priya Menon"),
        (2, "Logistics Ops Lead", "Logistics", "2026-03-01", 54, "Neha Iyer"),
        (3, "Sales Exec – EU", "Sales", "2026-03-15", 40, "Vikram Singh"),
        (4, "HR Business Partner", "HR", "2026-04-05", 19, "Kavya Reddy"),
    ],
}


# ── Driver ───────────────────────────────────────────────────────────────────


_BUILD = [
    ("everport_erp.sqlite3", _ERP_SCHEMA, _ERP_ROWS),
    ("everport_finance.sqlite3", _FINANCE_SCHEMA, _FINANCE_ROWS),
    ("everport_logistics.sqlite3", _LOGISTICS_SCHEMA, _LOGISTICS_ROWS),
    ("everport_hr.sqlite3", _HR_SCHEMA, _HR_ROWS),
]


def build_impex_samples(base_dir: Path) -> dict[str, Path]:
    """(Re)create the four impex SQLite files under ``base_dir``.

    Returns a mapping of filename → absolute path for use by the pack installer.
    """
    base_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    for filename, schema, rows in _BUILD:
        target = base_dir / filename
        if target.exists():
            target.unlink()
        conn = sqlite3.connect(target)
        try:
            conn.executescript(schema)
            for table, values in rows.items():
                if not values:
                    continue
                placeholders = ",".join("?" for _ in values[0])
                conn.executemany(
                    f"INSERT INTO {table} VALUES ({placeholders})", values,
                )
            conn.commit()
        finally:
            conn.close()
        out[filename] = target.resolve()
    return out
