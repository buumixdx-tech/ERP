#!/usr/bin/env python3
"""
将 business_system.db 完整导出为单个 UTF-8 JSON 文件。
输出: desktop-version/scripts/json_export/database.json

结构:
{
  "generated_at": "...",
  "db_path": "...",
  "tables": {
    "channel_customers": [ {row}, {row}, ... ],
    "suppliers": [ ... ],
    ...
  }
}
"""
import sqlite3, json, os
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH = "d:/WorkSpace/ShanYin/ERP/desktop-version/data/business_system.db"
OUT_FILE = "d:/WorkSpace/ShanYin/ERP/desktop-version/scripts/json_export/database.json"

# ── Helpers ──────────────────────────────────────────────────────────────────
def dt_to_epoch(dt_str):
    if dt_str is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(str(dt_str)[:19], fmt).timestamp() * 1000)
        except ValueError:
            pass
    return None

DATETIME_COLS = {
    "created_at", "timestamp", "signed_date", "effective_date", "expiry_date",
    "transaction_date", "trigger_time", "flag_time", "resultstamp", "endstamp",
    "status_timestamp", "subject_status_timestamp", "cash_status_timestamp",
    "deposit_timestamp", "change_date"
}

BOOL_COLS = {"is_default", "finance_triggered", "pushed_to_ai"}

TABLE_ORDER = [
    "channel_customers",
    "suppliers",
    "contracts",
    "finance_accounts",
    "external_partners",
    "bank_accounts",
    "time_rules",
    "system_events",
    "points",
    "skus",
    "business",
    "supply_chains",
    "material_inventory",
    "supply_chain_items",
    "virtual_contracts",
    "equipment_inventory",
    "vc_status_logs",
    "financial_journal",
    "logistics",
    "cash_flows",
    "vc_history",
    "express_orders",
    "cash_flow_ledger",
]

def row_to_dict(row):
    d = dict(row)
    for col in DATETIME_COLS:
        if col in d:
            d[col] = dt_to_epoch(d[col])
    for col in BOOL_COLS:
        if col in d:
            d[col] = bool(d[col])
    return d

def main():
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    tables = {}
    total_rows = 0
    for table in TABLE_ORDER:
        cursor.execute(f"SELECT * FROM {table}")
        rows = [row_to_dict(r) for r in cursor.fetchall()]
        tables[table] = rows
        total_rows += len(rows)
        print(f"  {table}: {len(rows)} rows")

    conn.close()

    output = {
        "generated_at": datetime.now().isoformat(),
        "db_path": DB_PATH,
        "tables": tables
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {total_rows} rows -> {OUT_FILE}")

if __name__ == "__main__":
    main()
