#!/usr/bin/env python3
"""
seed_dummy_data.py — Populate Neon UAT DB with realistic fake transactional data.

Scope  : 2025-08-01 → 2026-10-01 (14 months)
Story  : Hub migration TELEPIN→THUNES→TRANGLO→WU (plan: docs/dummy_data_seed_plan.md)
Mode   : Truncate + full reseed for transactional tables only.
         ml_schema and service_management already contain real data — NOT touched.

Usage:
    python scripts/seed_dummy_data.py
    python scripts/seed_dummy_data.py --ml-db-url "..." --keycloak-db-url "..."

Env (ai-service/.env.local):
    ML_DB_URL, KEYCLOAK_DB_URL
"""

import argparse
import asyncio
import os
import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import asyncpg
from faker import Faker

# ── Seeding ───────────────────────────────────────────────────────────────────
fake = Faker("en_US")
Faker.seed(42)
random.seed(42)

START_DATE = date(2025, 8, 1)
END_DATE   = date(2026, 10, 1)   # exclusive

# ── Hub IDs (source: transaction.hub_id column comment) ───────────────────────
HUB_TELEPIN = 1
HUB_WU      = 2
HUB_THUNES  = 3
HUB_TRANGLO = 5
HUB_NAMES   = {HUB_TELEPIN: "TELEPIN", HUB_WU: "WU",
               HUB_THUNES: "THUNES",   HUB_TRANGLO: "TRANGLO"}

# ── Real country IDs from ml_schema.country ───────────────────────────────────
CID_SG  = 196
CID_PH  = 171
CID_ID  = 103
CID_IN  = 102
CID_BD  = 19
CID_VN  = 238
CID_CN  = 46
CID_TH  = 217
CID_MY  = 131

COUNTRY_INFO = {
    CID_SG: {"name": "SINGAPORE",   "iso": "SGP", "isd": "65",  "currency": "SGD"},
    CID_PH: {"name": "PHILIPPINES", "iso": "PHL", "isd": "63",  "currency": "PHP"},
    CID_ID: {"name": "INDONESIA",   "iso": "IDN", "isd": "62",  "currency": "IDR"},
    CID_IN: {"name": "INDIA",       "iso": "IND", "isd": "91",  "currency": "INR"},
    CID_BD: {"name": "BANGLADESH",  "iso": "BGD", "isd": "880", "currency": "BDT"},
    CID_VN: {"name": "VIETNAM",     "iso": "VNM", "isd": "84",  "currency": "VND"},
    CID_CN: {"name": "CHINA",       "iso": "CHN", "isd": "86",  "currency": "CNY"},
    CID_TH: {"name": "THAILAND",    "iso": "THA", "isd": "66",  "currency": "THB"},
    CID_MY: {"name": "MALAYSIA",    "iso": "MYS", "isd": "60",  "currency": "MYR"},
}

# ── FX rates (SGD → destination, approximate wholesale) ───────────────────────
FX_BASE: dict[str, Decimal] = {
    "PHP": Decimal("41.50"),
    "IDR": Decimal("11500.00"),
    "INR": Decimal("62.50"),
    "BDT": Decimal("82.00"),
    "VND": Decimal("18500.00"),
    "CNY": Decimal("5.20"),
    "THB": Decimal("25.80"),
    "MYR": Decimal("3.40"),
}
RETAIL_MARKUP = Decimal("1.015")

# ── Amount ranges by destination country_id (SGD) ─────────────────────────────
AMOUNT_RANGES = {
    CID_PH: (80,  350),
    CID_ID: (50,  300),
    CID_IN: (100, 500),
    CID_BD: (80,  300),
    CID_VN: (50,  250),
    CID_CN: (150, 500),
    CID_TH: (80,  350),
    CID_MY: (100, 400),
}

# ── Real service definitions ──────────────────────────────────────────────────
# Source: production traffic data (docs/20260818_transaction_traffic_by_service.txt)
#         service info (docs/20260818_service_information.txt)
#
# Columns: (service_id, hub_id, ep_id, foreign_cid, svc_type,
#           active_from, active_to, daily_weight, display_name)
#
# active_from / active_to: based on real min/max transaction dates
# daily_weight: approximate transactions/day from production (count / active days)
# service_type: 1=BANK-ACCOUNT  2=CASH-PICKUP  3=E-WALLET

SERVICES = [
    # ── TELEPIN (hub_id=1, ep_id=1) ──────────────────────────────────────────
    # 457: 1,657,123 txs, 2022-11-14 → 2026-04-27  (~1300/day)
    (457, HUB_TELEPIN, 1, CID_PH, 2, date(2025,  8,  1), date(2026,  5,  1), 1300, "TELEPIN SG→PH Cash Pickup"),
    # 428: 553,937 txs, 2022-12-21 → 2026-05-25  (~443/day)
    (428, HUB_TELEPIN, 1, CID_ID, 1, date(2025,  8,  1), date(2026,  6,  1),  443, "TELEPIN SG→ID Bank"),
    # 426: 391,984 txs, ends 2025-09-08 (~381/day)
    (426, HUB_TELEPIN, 1, CID_PH, 1, date(2025,  8,  1), date(2025,  9, 30),  381, "TELEPIN SG→PH Bank"),
    # 524: 450,760 txs, ends 2025-09-08 (~438/day)
    (524, HUB_TELEPIN, 1, CID_MY, 1, date(2025,  8,  1), date(2025,  9, 30),  438, "TELEPIN SG→MY Bank"),
    # 475: 109,099 txs, ends 2026-05-27 (~85/day)
    (475, HUB_TELEPIN, 1, CID_BD, 3, date(2025,  8,  1), date(2026,  6,  1),   85, "TELEPIN SG→BD eWallet"),
    # 629: 18,839 txs, still active as of 2026-09-16 (~14/day)
    (629, HUB_TELEPIN, 1, CID_CN, 1, date(2025,  8,  1), date(2026, 10,  1),   14, "TELEPIN SG→CN Bank"),

    # ── THUNES (hub_id=3, ep_id=3) ───────────────────────────────────────────
    # 720: 1,850,577 txs, still active (~1690/day) — dominant THUNES service
    (720, HUB_THUNES, 3, CID_PH, 3, date(2025,  8,  1), date(2026,  8,  4), 1690, "THUNES SG→PH eWallet"),
    # 703: 967,045 txs, ends 2026-07-27 (~956/day)
    (703, HUB_THUNES, 3, CID_ID, 3, date(2025,  8,  1), date(2026,  7, 28),  956, "THUNES SG→ID eWallet"),
    # 702: 673,429 txs, ends 2026-05-27 (~711/day)
    (702, HUB_THUNES, 3, CID_ID, 1, date(2025,  8,  1), date(2026,  5, 28),  711, "THUNES SG→ID Bank"),
    # 735: 93,451 txs, 2025-10-08 → 2026-06-02 (~394/day)
    (735, HUB_THUNES, 3, CID_PH, 1, date(2025, 10,  8), date(2026,  6,  3),  394, "THUNES SG→PH Bank"),
    # 704: 79,928 txs, ends 2026-07-27 (~79/day)
    (704, HUB_THUNES, 3, CID_ID, 3, date(2025,  8,  1), date(2026,  7, 28),   79, "THUNES SG→ID eWallet B"),
    # 707: 71,000 txs, ends 2026-07-28 (~70/day)
    (707, HUB_THUNES, 3, CID_ID, 3, date(2025,  8,  1), date(2026,  7, 29),   70, "THUNES SG→ID eWallet C"),
    # 705: 64,203 txs, ends 2026-07-27 (~63/day)
    (705, HUB_THUNES, 3, CID_ID, 3, date(2025,  8,  1), date(2026,  7, 28),   63, "THUNES SG→ID eWallet D"),
    # 706: 41,443 txs, ends 2026-07-27 (~41/day)
    (706, HUB_THUNES, 3, CID_ID, 3, date(2025,  8,  1), date(2026,  7, 28),   41, "THUNES SG→ID eWallet E"),
    # 700: 25,547 txs, still active (~23/day)
    (700, HUB_THUNES, 3, CID_CN, 3, date(2025,  8,  1), date(2026, 10,  1),   23, "THUNES SG→CN eWallet"),
    # 701: 9,562 txs, ends 2026-08-24 (~9/day)
    (701, HUB_THUNES, 3, CID_TH, 1, date(2025,  8,  1), date(2026,  8, 25),    9, "THUNES SG→TH Bank"),
    # 699: 12,519 txs, ends 2026-08-24 (~10/day)
    (699, HUB_THUNES, 3, CID_VN, 1, date(2025,  8,  1), date(2026,  8, 25),   10, "THUNES SG→VN Bank"),

    # ── TRANGLO (hub_id=5, ep_id=5) ──────────────────────────────────────────
    # 725: 202,969 txs, 2025-06-10 → still active (~438/day)
    (725, HUB_TRANGLO, 5, CID_MY, 1, date(2025,  8,  1), date(2026, 10,  1),  438, "TRANGLO SG→MY Bank"),
    # 723: 65,583 txs, 2025-04-08 → 2026-08-24 (~130/day)
    (723, HUB_TRANGLO, 5, CID_MY, 3, date(2025,  8,  1), date(2026,  8, 25),  130, "TRANGLO SG→MY eWallet"),
    # 732: 35,016 txs, 2025-08-19 → 2026-05-08 (~133/day)
    (732, HUB_TRANGLO, 5, CID_PH, 1, date(2025,  8, 19), date(2026,  5,  9),  133, "TRANGLO SG→PH Bank"),
    # 729: 5,012 txs, 2025-10-08 → still active (~15/day)
    (729, HUB_TRANGLO, 5, CID_IN, 1, date(2025, 10,  8), date(2026, 10,  1),   15, "TRANGLO SG→IN Bank"),
    # 724: 2,844 txs, still active (~5/day)
    (724, HUB_TRANGLO, 5, CID_MY, 3, date(2025,  8,  1), date(2026, 10,  1),    5, "TRANGLO SG→MY eWallet B"),
    # 733: 785 txs, 2025-08-19 → 2025-09-09 (~37/day short burst)
    (733, HUB_TRANGLO, 5, CID_PH, 2, date(2025,  8, 19), date(2025,  9, 10),   37, "TRANGLO SG→PH Cash Pickup"),

    # ── WU (hub_id=2, ep_id=2) ────────────────────────────────────────────────
    # 736: 124,960 txs, 2026-04-20 → still active (~839/day) — dominant WU service
    (736, HUB_WU, 2, CID_PH, 2, date(2026,  4, 20), date(2026, 10,  1),  839, "WU SG→PH Cash Pickup"),
    # 740: 87,912 txs, 2026-05-20 → still active (~739/day)
    (740, HUB_WU, 2, CID_PH, 3, date(2026,  5, 20), date(2026, 10,  1),  739, "WU SG→PH eWallet"),
    # 743: 73,911 txs, 2026-05-20 → still active (~621/day)
    (743, HUB_WU, 2, CID_ID, 1, date(2026,  5, 20), date(2026, 10,  1),  621, "WU SG→ID Bank"),
    # 747: 56,497 txs, 2026-06-17 → still active (~621/day)
    (747, HUB_WU, 2, CID_ID, 3, date(2026,  6, 17), date(2026, 10,  1),  621, "WU SG→ID eWallet"),
    # 739: 44,160 txs, 2026-05-20 → still active (~371/day)
    (739, HUB_WU, 2, CID_PH, 1, date(2026,  5, 20), date(2026, 10,  1),  371, "WU SG→PH Bank"),
    # 746: 6,963 txs, 2026-07-27 → still active (~137/day)
    (746, HUB_WU, 2, CID_ID, 3, date(2026,  7, 27), date(2026, 10,  1),  137, "WU SG→ID eWallet B"),
    # 750: 4,329 txs, 2026-08-17 → still active (~144/day)
    (750, HUB_WU, 2, CID_MY, 3, date(2026,  8, 17), date(2026, 10,  1),  144, "WU SG→MY eWallet"),
    # 748: 3,169 txs, 2026-07-27 → still active (~62/day)
    (748, HUB_WU, 2, CID_ID, 3, date(2026,  7, 27), date(2026, 10,  1),   62, "WU SG→ID eWallet C"),
    # 752: 6,428 txs, 2026-05-20 → still active (~54/day)
    (752, HUB_WU, 2, CID_BD, 3, date(2026,  5, 20), date(2026, 10,  1),   54, "WU SG→BD eWallet"),
    # 745: 1,449 txs, 2026-06-17 → still active (~16/day)
    (745, HUB_WU, 2, CID_ID, 3, date(2026,  6, 17), date(2026, 10,  1),   16, "WU SG→ID eWallet D"),
    # 744: 1,286 txs, 2026-07-27 → still active (~25/day)
    (744, HUB_WU, 2, CID_ID, 3, date(2026,  7, 27), date(2026, 10,  1),   25, "WU SG→ID eWallet E"),
    # 756: 433 txs, 2026-08-17 → still active (~14/day)
    (756, HUB_WU, 2, CID_VN, 1, date(2026,  8, 17), date(2026, 10,  1),   14, "WU SG→VN Bank"),
    # 751: 543 txs, 2026-05-20 → still active (~5/day)
    (751, HUB_WU, 2, CID_BD, 1, date(2026,  5, 20), date(2026, 10,  1),    5, "WU SG→BD Bank"),
    # 760: 225 txs, 2026-08-17 → still active (~8/day)
    (760, HUB_WU, 2, CID_TH, 1, date(2026,  8, 17), date(2026, 10,  1),    8, "WU SG→TH Bank"),
    # 737: 160 txs, 2026-04-20 → still active (~1/day)
    (737, HUB_WU, 2, CID_BD, 2, date(2026,  4, 20), date(2026, 10,  1),    1, "WU SG→BD Cash Pickup"),
    # 738: 44 txs, 2026-04-20 → still active (~1/day)
    (738, HUB_WU, 2, CID_IN, 2, date(2026,  4, 20), date(2026, 10,  1),    1, "WU SG→IN Cash Pickup"),
]

# Index by hub
SERVICES_BY_HUB: dict[int, list] = {}
for _s in SERVICES:
    SERVICES_BY_HUB.setdefault(_s[1], []).append(_s)

# ── Hub migration phases ──────────────────────────────────────────────────────
# (phase_start, {hub_id: weight})
PHASES = [
    (date(2025,  8,  1), {HUB_TELEPIN: 1.0}),
    (date(2025, 10,  1), {HUB_TELEPIN: 0.5,  HUB_THUNES: 0.5}),
    (date(2025, 12,  1), {HUB_TELEPIN: 0.3,  HUB_THUNES: 0.6,  HUB_TRANGLO: 0.1}),
    (date(2026,  2,  1), {HUB_TELEPIN: 0.3,  HUB_THUNES: 0.4,  HUB_TRANGLO: 0.1, HUB_WU: 0.2}),
    (date(2026,  4,  1), {HUB_TELEPIN: 0.3,  HUB_THUNES: 0.2,  HUB_TRANGLO: 0.1, HUB_WU: 0.4}),
    (date(2026,  6,  1), {HUB_TELEPIN: 0.1,  HUB_TRANGLO: 0.1, HUB_WU: 0.8}),
    (date(2026,  8,  1), {HUB_WU: 1.0}),
]

# ── Incident days ─────────────────────────────────────────────────────────────
INCIDENTS: dict[date, dict] = {
    date(2025,  8, 14): {"type": "HUB_TIMEOUT",                "hub": HUB_TELEPIN,  "fail_rate": 0.35, "vol": 1.0},
    date(2025,  9, 22): {"type": "MAINTENANCE",                "hub": None,          "fail_rate": 0.0,  "vol": 0.2},
    date(2025, 10,  8): {"type": "SOF_PAY_FAILED",             "hub": HUB_THUNES,   "fail_rate": 0.40, "vol": 1.0},
    date(2025, 11, 19): {"type": "FRAUD_CHECK_TIMEOUT",        "hub": HUB_TELEPIN,  "fail_rate": 0.30, "vol": 1.0},
    date(2025, 12,  3): {"type": "PAYMENT_RESERVATION_FAILED", "hub": None,          "fail_rate": 0.25, "vol": 1.0},
    date(2026,  1, 15): {"type": "HUB_TIMEOUT",                "hub": HUB_TRANGLO,  "fail_rate": 1.00, "vol": 1.0},
    date(2026,  2, 11): {"type": "TRANSACTION_FAILED",         "hub": HUB_WU,       "fail_rate": 0.45, "vol": 1.0},
    date(2026,  3, 27): {"type": "TRANSACTION_DECLINED",       "hub": HUB_THUNES,   "fail_rate": 0.50, "vol": 1.0},
    date(2026,  4,  9): {"type": "VOLUME_SPIKE",               "hub": None,          "fail_rate": 0.12, "vol": 2.5},
    date(2026,  5, 21): {"type": "HUB_TIMEOUT",                "hub": HUB_TELEPIN,  "fail_rate": 0.60, "vol": 0.8},
    date(2026,  6, 16): {"type": "TRANSACTION_FAILED",         "hub": HUB_WU,       "fail_rate": 0.35, "vol": 1.0},
    date(2026,  7,  4): {"type": "HUB_TIMEOUT",                "hub": HUB_TRANGLO,  "fail_rate": 0.70, "vol": 0.5},
    date(2026,  8, 18): {"type": "VOLUME_SPIKE",               "hub": HUB_WU,       "fail_rate": 0.08, "vol": 3.0},
    date(2026,  9,  5): {"type": "SOF_PAY_FAILED",             "hub": HUB_WU,       "fail_rate": 0.40, "vol": 1.0},
}

# ── Status distribution (normal day) ─────────────────────────────────────────
STATUS_WEIGHTS = [
    ("TRANSACTION_COMPLETED",     75),
    ("TRANSACTION_IN_PROGRESS",    8),
    ("REFUNDED",                   4),
    ("TRANSACTION_CANCELLED",      3),
    ("TRANSACTION_FAILED",         5),
    ("SOF_PAY_FAILED",             2),
    ("HUB_TIMEOUT",                2),
    ("PAYMENT_RESERVATION_FAILED", 1),
]
STATUS_CHOICES = [s for s, _ in STATUS_WEIGHTS]
STATUS_WVALS   = [w for _, w in STATUS_WEIGHTS]

FINAL_STATUS = {
    "TRANSACTION_COMPLETED":     "TRANSACTION_COMPLETED",
    "TRANSACTION_IN_PROGRESS":   "TRANSACTION_IN_PROGRESS",
    "REFUNDED":                  "REFUNDED",
    "TRANSACTION_CANCELLED":     "TRANSACTION_CANCELLED",
    "TRANSACTION_FAILED":        "TRANSACTION_FAILED",
    "SOF_PAY_FAILED":            "SOF_PAY_FAILED",
    "HUB_TIMEOUT":               "TRANSACTION_FAILED",
    "PAYMENT_RESERVATION_FAILED":"PAYMENT_RESERVATION_FAILED",
}

AUDIT_PATHS: dict[str, list[str]] = {
    "TRANSACTION_COMPLETED":     ["INITIATED", "PAYMENT_RESERVED", "SOF_PAY_COMPLETED", "TRANSACTION_COMPLETED"],
    "TRANSACTION_IN_PROGRESS":   ["INITIATED", "PAYMENT_RESERVED", "SOF_PAY_COMPLETED", "TRANSACTION_IN_PROGRESS"],
    "REFUNDED":                  ["INITIATED", "PAYMENT_RESERVED", "TRANSACTION_COMPLETED", "REFUNDED"],
    "TRANSACTION_CANCELLED":     ["INITIATED", "TRANSACTION_CANCELLED"],
    "TRANSACTION_FAILED":        ["INITIATED", "PAYMENT_RESERVED", "SOF_PAY_COMPLETED", "TRANSACTION_FAILED"],
    "SOF_PAY_FAILED":            ["INITIATED", "PAYMENT_RESERVED", "SOF_PAY_FAILED"],
    "HUB_TIMEOUT":               ["INITIATED", "PAYMENT_RESERVED", "SOF_PAY_COMPLETED", "TRANSACTION_FAILED"],
    "PAYMENT_RESERVATION_FAILED":["INITIATED", "PAYMENT_RESERVATION_FAILED"],
}

INCIDENT_ERRORS = {
    # error_code max 10 chars, hub_error_code max 10 chars
    "HUB_TIMEOUT":                ("HUB_TMOUT",  "Hub connection timed out after 30s",         "TIMEOUT",   "Gateway timeout"),
    "SOF_PAY_FAILED":             ("SOF_FAIL",   "PayNow payment failed: insufficient funds",  None,        None),
    "FRAUD_CHECK_TIMEOUT":        ("FRD_TMOUT",  "Fraud check service timed out",              None,        None),
    "PAYMENT_RESERVATION_FAILED": ("PAY_RSV_F",  "Payment reservation failed: limit exceeded", None,        None),
    "TRANSACTION_FAILED":         ("INV_ACCT",   "Beneficiary account not found",              "ERR_ACCT",  "Account does not exist"),
    "TRANSACTION_DECLINED":       ("TX_DECLIN",  "Transaction declined by hub",                "DECLINED",  "Daily limit exceeded"),
    "MAINTENANCE":                ("MAINT",      "Scheduled maintenance window",               None,        None),
}

NORMAL_FAIL_ERRORS = [
    ("INV_ACCT",  "Recipient account not found",      "ERR001", "Account not found"),
    ("INSUF_FND", "Sender insufficient funds",        None,     None),
    ("LMT_EXCEE", "Daily transaction limit exceeded", "ERR003", "Limit exceeded"),
    ("HUB_TMOUT", "Hub connection timed out",         "TIMEOUT","Gateway timeout"),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_env_local() -> None:
    env_path = Path(__file__).parent.parent / ".env.local"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def to_asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://")


def hub_weights(d: date) -> dict[int, float]:
    result: dict[int, float] = {}
    for phase_start, w in reversed(PHASES):
        if d >= phase_start:
            result = w
            break
    return result


def active_services_for_hub(hub_id: int, d: date) -> list[tuple]:
    """Return services active on date d for the given hub, with their weights."""
    return [s for s in SERVICES_BY_HUB.get(hub_id, [])
            if s[5] <= d < s[6]]  # active_from <= d < active_to


def pick_service(hub_id: int, d: date):
    pool = active_services_for_hub(hub_id, d)
    if not pool:
        return None
    weights = [s[7] for s in pool]   # daily_weight
    return random.choices(pool, weights=weights, k=1)[0]


def daily_volume(d: date) -> int:
    days    = (d - START_DATE).days
    growth  = 1.0 + 0.007 * (days / 7)
    base    = 5 if d.weekday() < 5 else 2
    vol     = max(1, round(base * growth))
    inc     = INCIDENTS.get(d)
    if inc:
        vol = max(1, round(vol * inc["vol"]))
    return vol


def pick_hub(d: date) -> int:
    w     = hub_weights(d)
    hubs  = list(w.keys())
    probs = list(w.values())
    return random.choices(hubs, weights=probs, k=1)[0]


def pick_status_type(hub_id: int, d: date) -> str:
    inc = INCIDENTS.get(d)
    if inc and inc["type"] != "VOLUME_SPIKE":
        inc_hub = inc.get("hub")
        if (inc_hub is None or inc_hub == hub_id) and random.random() < inc["fail_rate"]:
            return inc["type"]
    return random.choices(STATUS_CHOICES, weights=STATUS_WVALS, k=1)[0]


def rand_time(d: date) -> datetime:
    # 24 weights for hours 0-23; peak evening 18-21 (SGT remittance pattern)
    hour_w = [0,0,0,0,0,0,1,1, 3,4,5,6, 8,7,6, 8,10,12, 20,18,15,12, 8,4]
    hour   = random.choices(range(24), weights=hour_w, k=1)[0]
    return datetime(d.year, d.month, d.day, hour, random.randint(0, 59), random.randint(0, 59))


def rand_sg_msisdn() -> str:
    return f"+65{random.choice(['8','9'])}{random.randint(1000000, 9999999)}"


def rand_dest_msisdn(isd: str) -> str:
    return f"+{isd}{random.randint(1000000000, 9999999999)}"


def rand_amount(cid: int) -> Decimal:
    lo, hi = AMOUNT_RANGES.get(cid, (50, 300))
    return Decimal(str(round(random.uniform(lo, hi), 2)))


def calc_recipient_amount(sgd: Decimal, currency: str) -> Decimal:
    rate = FX_BASE.get(currency, Decimal("1.0"))
    return (sgd * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def retail_rate(currency: str) -> Decimal:
    base = FX_BASE.get(currency, Decimal("1.0"))
    return (base / RETAIL_MARKUP).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)


def rand_fee(amount: Decimal) -> Decimal:
    pct  = Decimal(str(round(random.uniform(0.005, 0.025), 4)))
    flat = Decimal(str(round(random.uniform(1.0, 5.0), 2)))
    return (amount * pct + flat).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ─────────────────────────────────────────────────────────────────────────────
# ml_schema.ml_fx_rates  (only table we seed in ml_schema)
# ─────────────────────────────────────────────────────────────────────────────

async def seed_fx_rates(conn: asyncpg.Connection) -> None:
    print("  → Truncating ml_schema.ml_fx_rates …")
    await conn.execute("TRUNCATE ml_schema.ml_fx_rates RESTART IDENTITY")

    rows = []
    for i, s in enumerate(SERVICES, start=1):
        sid, _, _, foreign_cid, _, _, _, _, _ = s
        currency = COUNTRY_INFO[foreign_cid]["currency"]
        rate = FX_BASE.get(currency, Decimal("1.0"))
        jitter = Decimal(str(round(random.uniform(-0.003, 0.003), 6)))
        rows.append((i, "ML", "SGD", currency, rate + rate * jitter, sid, str(foreign_cid)))

    await conn.executemany(
        "INSERT INTO ml_schema.ml_fx_rates "
        "(id, brand_id, from_currency, to_currency, fx_rate, service_id, receiving_country_id) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7)",
        rows,
    )
    print(f"  ✓ Inserted {len(rows)} fx rate rows")


# ─────────────────────────────────────────────────────────────────────────────
# customer.beneficiary
# ─────────────────────────────────────────────────────────────────────────────

def build_beneficiary_pool(n: int = 50) -> list[dict]:
    dest_cids = [CID_PH, CID_ID, CID_IN, CID_BD, CID_VN, CID_CN, CID_TH, CID_MY]
    benes = []
    for i in range(1, n + 1):
        cid  = dest_cids[(i - 1) % len(dest_cids)]
        c    = COUNTRY_INFO[cid]
        benes.append({
            "id":                i,
            "bene_id":           i,                          # bigint
            "sender_account_id": random.randint(10000, 99999),  # bigint
            "bene_first_name":   fake.first_name(),
            "bene_last_name":    fake.last_name(),
            "benemsisdn":        rand_dest_msisdn(c["isd"]),
            "bene_bank_acct_no": f"{''.join(str(random.randint(0,9)) for _ in range(12))}",
            "receiving_country": cid,
            "nationality":       cid,                         # integer (country_id)
            "remit_purpose":     None,                        # integer ref unknown — keep NULL
            "status":            "ACTIVE",
        })
        benes[-1]["bene_full_name"] = f"{benes[-1]['bene_first_name']} {benes[-1]['bene_last_name']}"
    return benes


async def seed_beneficiaries(conn: asyncpg.Connection, benes: list[dict]) -> None:
    await conn.execute("TRUNCATE customer.beneficiary RESTART IDENTITY CASCADE")
    rows = [(
        b["id"], b["bene_id"], b["sender_account_id"],
        b["bene_first_name"], b["bene_last_name"], b["bene_full_name"],
        None, None,
        b["benemsisdn"], b["bene_bank_acct_no"], None,
        b["receiving_country"], None, None,    # mobile_operator, issuer_id
        None, False,
        b["remit_purpose"], None, None,
        b["nationality"], None, None, None,
        None, None, None, None,
        b["status"], None, None, None, None,
    ) for b in benes]
    await conn.executemany(
        "INSERT INTO customer.beneficiary "
        "(id, bene_id, sender_account_id,"
        " bene_first_name, bene_last_name, bene_full_name,"
        " sender_first_name, sender_last_name,"
        " benemsisdn, bene_bank_acct_no, wallet_account_number,"
        " receiving_country, mobile_operator, issuer_id,"
        " branch_code, bank_acc_type_flag,"
        " remit_purpose, remit_purpose_note, cust_relationship,"
        " nationality, dob, birth_place, gender,"
        " bene_address, province_id, city_id, postal_code,"
        " status, status_remark, warning_message, sys_flag, old_bene_id"
        ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,"
        "          $17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32)",
        rows,
    )
    print(f"  ✓ Inserted {len(benes)} beneficiaries")


# ─────────────────────────────────────────────────────────────────────────────
# Transaction generation
# ─────────────────────────────────────────────────────────────────────────────

def build_transactions(benes: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    benes_by_cid: dict[int, list[dict]] = {}
    for b in benes:
        benes_by_cid.setdefault(b["receiving_country"], []).append(b)

    transactions: list[dict] = []
    audit_rows:   list[dict] = []
    sof_payments: list[dict] = []

    tx_id  = 10_001
    aud_id = 1
    current = START_DATE

    while current < END_DATE:
        volume = daily_volume(current)

        for _ in range(volume):
            hub_id = pick_hub(current)
            svc    = pick_service(hub_id, current)
            if svc is None:
                # No active service for this hub today — fall back to any available hub
                for fallback_hub in [HUB_TELEPIN, HUB_THUNES, HUB_TRANGLO, HUB_WU]:
                    svc = pick_service(fallback_hub, current)
                    if svc:
                        hub_id = fallback_hub
                        break
            if svc is None:
                continue

            (sid, s_hub, s_ep, foreign_cid, svc_type,
             _aFrom, _aTo, _weight, svc_name) = svc

            c_info   = COUNTRY_INFO[foreign_cid]
            currency = c_info["currency"]

            dest_benes = benes_by_cid.get(foreign_cid, [])
            bene       = random.choice(dest_benes) if dest_benes else None

            status_type = pick_status_type(hub_id, current)
            final_st    = FINAL_STATUS[status_type]

            sgd_amount  = rand_amount(foreign_cid)
            dest_amount = calc_recipient_amount(sgd_amount, currency)
            hub_rate    = FX_BASE.get(currency, Decimal("1.0"))
            ret_rate    = retail_rate(currency)
            fee         = rand_fee(sgd_amount)

            created = rand_time(current)
            proc_m  = random.randint(3, 15) if final_st == "TRANSACTION_COMPLETED" else random.randint(1, 8)
            updated = created + timedelta(minutes=proc_m)

            partner_id  = random.choice(["DASH", "HIAPP"])
            hub_tx_id   = f"HUB{tx_id:010d}"
            pay_ref     = f"PAY{tx_id:010d}" if hub_id == HUB_TELEPIN else None
            ext_svc_id  = (1001 if partner_id == "DASH" else 1002) if hub_id == HUB_TELEPIN else None

            sender_acc    = f"SG{random.randint(10000000, 99999999)}"
            sender_msisdn = rand_sg_msisdn()
            sender_name   = fake.name()
            sender_dob    = fake.date_of_birth(minimum_age=21, maximum_age=65).strftime("%Y-%m-%d")

            rec_msisdn = bene["benemsisdn"]    if bene else rand_dest_msisdn(c_info["isd"])
            rec_name   = bene["bene_full_name"] if bene else fake.name()
            rec_id     = str(bene["bene_id"])   if bene else None

            error_code = error_msg = hub_err_code = hub_err_msg = None
            terminal_fail = final_st not in ("TRANSACTION_COMPLETED",
                                              "TRANSACTION_IN_PROGRESS",
                                              "REFUNDED",
                                              "TRANSACTION_CANCELLED")
            if terminal_fail and status_type in INCIDENT_ERRORS:
                ec, em, hec, hem = INCIDENT_ERRORS[status_type]
                error_code, error_msg, hub_err_code, hub_err_msg = ec, em, hec, hem
            elif terminal_fail:
                ec, em, hec, hem = random.choice(NORMAL_FAIL_ERRORS)
                error_code, error_msg, hub_err_code, hub_err_msg = ec, em, hec, hem

            transactions.append({
                "internal_transaction_id":  tx_id,
                "hub_id":                   hub_id,
                "hub_name":                 HUB_NAMES[hub_id],
                "payment_reference_id":     pay_ref,
                "hub_transaction_id":       hub_tx_id,
                "hub_transaction_id_check": f"CHK{tx_id:010d}",
                "hub_transaction_id_submit":f"SUB{tx_id:010d}",
                "service_id":               sid,
                "service_name":             svc_name,
                "service_type":             svc_type,
                "partner_id":               partner_id,
                "status":                   final_st,
                "sender_account_id":        sender_acc,
                "sender_msisdn":            sender_msisdn,
                "sender_fullname":          sender_name,
                "sender_dob":               sender_dob,
                "sender_currency":          "SGD",
                "sender_country":           "SINGAPORE",
                "sender_country_of_residence": "SINGAPORE",
                "sender_nationality":       "SGP",
                "recipient_id":             rec_id,
                "recipient_msisdn":         rec_msisdn,
                "recipient_fullname":       rec_name,
                "recipient_currency":       currency,
                "recipient_country":        c_info["name"],
                "remittance_amount":        sgd_amount,
                "recipient_amount":         dest_amount,
                "customer_key_in_amount":   sgd_amount,
                "currency_flag":            0,
                "retail_fee":               fee,
                "hub_exchange_rate":        hub_rate,
                "retail_exchange_rate":     ret_rate,
                "markup_rate":              Decimal("0.0150"),
                "error_code":               error_code,
                "error_message":            error_msg,
                "hub_error_code":           hub_err_code,
                "hub_error_message":        hub_err_msg,
                "payment_mode":             random.choice(["PAYNOW", "NETS_CLICK"]),
                "external_service_id":      ext_svc_id,
                "remit_purpose_id":         random.choice(["FAMILY_SUPPORT","SAVINGS","EDUCATION","BUSINESS"]),
                "is_notify_sms_sender":     False,
                "created_date":             created,
                "updated_date":             updated,
                "version":                  1,
            })

            # Audit trail
            path      = AUDIT_PATHS.get(status_type, ["INITIATED", final_st])
            step_time = created
            for step_status in path:
                audit_rows.append({
                    "id":                      aud_id,
                    "internal_transaction_id": tx_id,
                    "audit_date":              step_time,
                    "status":                  step_status,
                    "hub_error_code":          hub_err_code if step_status == final_st else None,
                    "hub_error_message":       hub_err_msg  if step_status == final_st else None,
                    "error_code":              error_code   if step_status == final_st else None,
                    "error_message":           error_msg    if step_status == final_st else None,
                    "created_date":            step_time,
                    "version":                 1,
                })
                aud_id    += 1
                step_time += timedelta(seconds=random.randint(30, 180))

            if final_st in ("TRANSACTION_COMPLETED", "REFUNDED"):
                sof_payments.append({
                    "payment_id":              tx_id,
                    "internal_transaction_id": tx_id,
                    "card_id":                 f"SOF{tx_id:010d}",
                    "payment_amount":          sgd_amount + fee,
                    "request_datetime":        created,
                    "status":                  "COMPLETED" if final_st == "TRANSACTION_COMPLETED" else "REFUNDED",
                    "created_date":            created,
                    "updated_date":            updated,
                    "version":                 1,
                })

            tx_id += 1

        current += timedelta(days=1)

    return transactions, audit_rows, sof_payments


# ─────────────────────────────────────────────────────────────────────────────
# Keycloak DB inserts
# ─────────────────────────────────────────────────────────────────────────────

async def seed_keycloak_db(
    conn: asyncpg.Connection,
    benes: list[dict],
    transactions: list[dict],
    audit_rows: list[dict],
    sof_payments: list[dict],
) -> None:
    print("  → Truncating transactional tables …")
    await conn.execute("""
        TRUNCATE payment.ml_m_sof_payment,
                 remittance.transaction_aud,
                 remittance.transaction
        RESTART IDENTITY CASCADE
    """)

    await seed_beneficiaries(conn, benes)

    print(f"  → Inserting {len(transactions)} transactions …")
    tx_rows = [(
        t["internal_transaction_id"], t["hub_id"],    t["hub_name"],
        t["payment_reference_id"],    t["hub_transaction_id"],
        t["hub_transaction_id_check"],t["hub_transaction_id_submit"],
        t["service_id"],   t["service_name"],  t["service_type"],
        t["partner_id"],   t["status"],
        t["sender_account_id"],   t["sender_msisdn"],     t["sender_fullname"],
        t["sender_dob"],          t["sender_currency"],   t["sender_country"],
        t["sender_country_of_residence"],                 t["sender_nationality"],
        t["recipient_id"],        t["recipient_msisdn"],  t["recipient_fullname"],
        t["recipient_currency"],  t["recipient_country"],
        t["remittance_amount"],   t["recipient_amount"],
        t["customer_key_in_amount"], t["currency_flag"],
        t["retail_fee"],          t["hub_exchange_rate"], t["retail_exchange_rate"],
        t["markup_rate"],
        t["error_code"],          t["error_message"],
        t["hub_error_code"],      t["hub_error_message"],
        t["payment_mode"],        t["external_service_id"], t["remit_purpose_id"],
        t["is_notify_sms_sender"],
        t["created_date"],        t["updated_date"],      t["version"],
    ) for t in transactions]

    await conn.executemany(
        "INSERT INTO remittance.transaction ("
        " internal_transaction_id, hub_id, hub_name,"
        " payment_reference_id, hub_transaction_id,"
        " hub_transaction_id_check, hub_transaction_id_submit,"
        " service_id, service_name, service_type,"
        " partner_id, status,"
        " sender_account_id, sender_msisdn, sender_fullname,"
        " sender_dob, sender_currency, sender_country,"
        " sender_country_of_residence, sender_nationality,"
        " recipient_id, recipient_msisdn, recipient_fullname,"
        " recipient_currency, recipient_country,"
        " remittance_amount, recipient_amount,"
        " customer_key_in_amount, currency_flag,"
        " retail_fee, hub_exchange_rate, retail_exchange_rate,"
        " markup_rate,"
        " error_code, error_message,"
        " hub_error_code, hub_error_message,"
        " payment_mode, external_service_id, remit_purpose_id,"
        " is_notify_sms_sender,"
        " created_date, updated_date, version"
        ") VALUES ("
        "$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,"
        "$19,$20,$21,$22,$23,$24,$25,$26,$27,$28,$29,$30,$31,$32,$33,$34,"
        "$35,$36,$37,$38,$39,$40,$41,$42,$43,$44)",
        tx_rows,
    )

    print(f"  → Inserting {len(audit_rows)} audit rows …")
    await conn.executemany(
        "INSERT INTO remittance.transaction_aud ("
        " id, internal_transaction_id, audit_date,"
        " status, hub_error_code, hub_error_message,"
        " error_code, error_message, created_date, version"
        ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)",
        [(a["id"], a["internal_transaction_id"], a["audit_date"],
          a["status"], a["hub_error_code"], a["hub_error_message"],
          a["error_code"], a["error_message"], a["created_date"], a["version"])
         for a in audit_rows],
    )

    print(f"  → Inserting {len(sof_payments)} SOF payments …")
    await conn.executemany(
        "INSERT INTO payment.ml_m_sof_payment "
        "(payment_id, internal_transaction_id, card_id, payment_amount, request_datetime, status, version, created_date, updated_date) "
        "VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
        [(s["payment_id"], s["internal_transaction_id"], s["card_id"],
          s["payment_amount"], s["request_datetime"], s["status"],
          s["version"], s["created_date"], s["updated_date"]) for s in sof_payments],
    )

    print(f"  ✓ keycloak: {len(transactions)} tx | {len(audit_rows)} aud | {len(sof_payments)} sof")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

async def main(ml_db_url: str, keycloak_db_url: str) -> None:
    print("Connecting …")
    ml_conn = await asyncpg.connect(to_asyncpg_dsn(ml_db_url))
    kc_conn = await asyncpg.connect(to_asyncpg_dsn(keycloak_db_url))

    try:
        print("\n[1/3] Seeding ml_schema.ml_fx_rates …")
        await seed_fx_rates(ml_conn)

        print("\n[2/3] Building transaction dataset …")
        benes = build_beneficiary_pool(50)
        transactions, audit_rows, sof_payments = build_transactions(benes)
        print(f"  Generated: {len(transactions)} tx | {len(audit_rows)} aud | {len(sof_payments)} sof")

        print("\n[3/3] Seeding keycloak …")
        await seed_keycloak_db(kc_conn, benes, transactions, audit_rows, sof_payments)

        print("\n✅ Seed complete.")
    finally:
        await ml_conn.close()
        await kc_conn.close()


if __name__ == "__main__":
    load_env_local()

    parser = argparse.ArgumentParser(description="Seed Neon UAT DB with dummy data")
    parser.add_argument("--ml-db-url",       default=os.getenv("ML_DB_URL"))
    parser.add_argument("--keycloak-db-url", default=os.getenv("KEYCLOAK_DB_URL"))
    args = parser.parse_args()

    if not args.ml_db_url:
        raise SystemExit("ERROR: ML_DB_URL not set")
    if not args.keycloak_db_url:
        raise SystemExit("ERROR: KEYCLOAK_DB_URL not set")

    asyncio.run(main(args.ml_db_url, args.keycloak_db_url))
