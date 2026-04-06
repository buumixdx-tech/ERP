#!/usr/bin/env python3
"""
将 business_system.db 完整导出为 JSON 文件集。
输出目录: desktop-version/scripts/json_export/
每个表一个 .json，含完整列（含 id）。
JSON 字符串字段原样保留，不做任何二次解析。

Android 导入时：
  manifest.json 描述所有表及行数
  每张表按依赖顺序 truncate + re-insert
"""
import sqlite3, json, os
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
DB_PATH = "d:/WorkSpace/ShanYin/ERP/desktop-version/data/business_system.db"
OUT_DIR = "d:/WorkSpace/ShanYin/ERP/desktop-version/scripts/json_export"
MANIFEST_FILE = f"{OUT_DIR}/manifest.json"

# ── Helpers ──────────────────────────────────────────────────────────────────
def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def dt_to_epoch(dt_str):
    """'YYYY-MM-DD HH:MM:SS[.fraction]' → epoch millis or None."""
    if dt_str is None:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(str(dt_str)[:19], fmt).timestamp() * 1000)
        except ValueError:
            pass
    return None

# DATETIME 列名 → 转换为 epoch millis
DATETIME_COLS = {
    "created_at", "timestamp", "signed_date", "effective_date", "expiry_date",
    "transaction_date", "trigger_time", "flag_time", "resultstamp", "endstamp",
    "status_timestamp", "subject_status_timestamp", "cash_status_timestamp",
    "deposit_timestamp", "change_date"
}

# BOOLEAN 列名（SQLite 存储为 0/1）
BOOL_COLS = {"is_default", "finance_triggered", "pushed_to_ai"}

# 导出顺序（外键依赖顺序）
# 插入时：父表先插、子表后插
# Android 导入时会按此顺序 truncate（反向）再 insert（正向）
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

def row_to_dict(row, datetime_cols, bool_cols):
    """将 sqlite3.Row 转为 dict，datetime 转 epoch，bool 转 bool"""
    d = dict(row)
    for col in datetime_cols:
        if col in d:
            d[col] = dt_to_epoch(d[col])
    for col in bool_cols:
        if col in d:
            d[col] = bool(d[col])
    return d

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    conn = connect()
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "db_path": DB_PATH,
        "tables": {}
    }

    total_rows = 0
    for table in TABLE_ORDER:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = [row_to_dict(r, DATETIME_COLS, BOOL_COLS) for r in cursor.fetchall()]

        out = {
            "table": table,
            "rows": rows
        }
        out_path = f"{OUT_DIR}/{table}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)

        count = len(rows)
        manifest["tables"][table] = {"rows": count, "file": f"{table}.json"}
        total_rows += count
        print(f"  {table}: {count} rows")

    conn.close()

    manifest["total_rows"] = total_rows
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nDone. {total_rows} rows, {len(TABLE_ORDER)} tables -> {OUT_DIR}")
    print(f"Manifest: {MANIFEST_FILE}")

if __name__ == "__main__":
    main()
