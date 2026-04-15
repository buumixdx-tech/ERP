"""
数据迁移脚本：统一 business.details 数据结构

执行方式: python scripts/migrate_business_details.py

迁移内容：
1. business.details.pricing: product_name key → sku_id key
2. business.details.contract_id → business.details.contracts（is_primary=true）
3. 删除 details.contract_id 字段
4. 删除 business.contract_id FK 列（如存在）
5. 验证新结构
"""
import sys
import json
sys.path.insert(0, '.')

from sqlalchemy import text
from models import get_session, Business, SKU


def drop_business_contract_id_column(session):
    """删除 business.contract_id FK 列（SQLite 不支持 ALTER DROP COLUMN，需重建表）"""
    # 检查列是否仍然存在
    result = session.execute(text("PRAGMA table_info(business)"))
    columns = [row[1] for row in result]
    if "contract_id" not in columns:
        print("  business.contract_id 列已删除，跳过")
        return

    # 检查是否有 FK 约束
    fk_result = session.execute(text("PRAGMA foreign_key_list(business)"))
    has_fk = any(row[3] == "contract_id" for row in fk_result)

    # 禁用 FK 约束
    session.execute(text("PRAGMA foreign_keys=OFF"))
    session.commit()

    try:
        if has_fk:
            # 重建表（删除 FK 约束 + contract_id 列）
            session.execute(text("""
                CREATE TABLE business_new (
                    id INTEGER PRIMARY KEY,
                    customer_id INTEGER,
                    status VARCHAR(50),
                    timestamp DATETIME,
                    details JSON,
                    FOREIGN KEY (customer_id) REFERENCES channel_customers(id)
                )
            """))
            session.execute(text("""
                INSERT INTO business_new(id, customer_id, status, timestamp, details)
                SELECT id, customer_id, status, timestamp, details FROM business
            """))
            session.execute(text("DROP TABLE business"))
            session.execute(text("ALTER TABLE business_new RENAME TO business"))
        else:
            # 无 FK 约束，直接 DROP COLUMN
            session.execute(text("ALTER TABLE business DROP COLUMN contract_id"))
    finally:
        session.execute(text("PRAGMA foreign_keys=ON"))
        session.commit()

    print("  business.contract_id 列已删除（重建表）")


def get_sku_id_by_name(session, sku_name: str):
    """根据 SKU 名称查找 ID"""
    if not sku_name or sku_name in ["未知", "-", ""]:
        return None
    sku = session.query(SKU).filter(SKU.name == sku_name).first()
    return sku.id if sku else None


def migrate_pricing(session):
    """迁移 business.details.pricing: product_name key → sku_id key"""
    businesses = session.query(Business).all()
    migrated = 0
    skipped = 0
    errors = []

    for biz in businesses:
        if not biz.details or "pricing" not in biz.details:
            continue

        pricing = biz.details.get("pricing", {})
        if not pricing:
            continue

        new_pricing = {}
        for sku_name, config in pricing.items():
            if str(sku_name).isdigit():
                new_pricing[str(sku_name)] = config
                continue

            sku_id = get_sku_id_by_name(session, sku_name)
            if sku_id:
                new_pricing[str(sku_id)] = config
                migrated += 1
            else:
                skipped += 1
                errors.append(f"biz_id={biz.id}: SKU名称「{sku_name}」未找到对应ID，跳过")

        if new_pricing != pricing:
            # 构建完整的新 details，保留其他字段
            new_details = dict(biz.details)
            new_details["pricing"] = new_pricing
            session.execute(
                text("UPDATE business SET details = :new_details WHERE id = :id"),
                {"new_details": json.dumps(new_details, ensure_ascii=False), "id": biz.id}
            )

    if migrated:
        session.commit()

    print(f"  pricing: 迁移 {migrated} 条, 跳过 {skipped} 条")
    for e in errors:
        print(f"    {e}")
    return migrated, skipped


def migrate_contracts(session):
    """迁移 business.details.contract_id → business.details.contracts"""
    businesses = session.query(Business).all()
    converted = 0
    already_has_contracts = 0

    for biz in businesses:
        if not biz.details:
            continue

        if "contracts" in biz.details and biz.details["contracts"]:
            already_has_contracts += 1
            continue

        old_cid = biz.details.get("contract_id")
        if old_cid:
            new_details = dict(biz.details)
            new_details["contracts"] = [{"id": old_cid, "is_primary": True}]
            del new_details["contract_id"]
            session.execute(
                text("UPDATE business SET details = :new_details WHERE id = :id"),
                {"new_details": json.dumps(new_details, ensure_ascii=False), "id": biz.id}
            )
            converted += 1
        else:
            new_details = dict(biz.details)
            new_details.setdefault("contracts", [])
            session.execute(
                text("UPDATE business SET details = :new_details WHERE id = :id"),
                {"new_details": json.dumps(new_details, ensure_ascii=False), "id": biz.id}
            )

    if converted:
        session.commit()

    print(f"  contracts: 从 contract_id 转换 {converted} 条, 已有 contracts {already_has_contracts} 条")
    return converted


def verify_structure(session):
    """验证新数据结构"""
    session.expire_all()
    businesses = session.query(Business).all()
    all_ok = True

    for biz in businesses:
        if not biz.details:
            continue

        pricing = biz.details.get("pricing", {})
        bad_keys = [k for k in pricing.keys() if not str(k).isdigit()]
        if bad_keys:
            print(f"  biz_id={biz.id}: pricing 仍有非数字 key: {bad_keys}")
            all_ok = False

        contracts = biz.details.get("contracts", [])
        if contracts:
            primaries = [c for c in contracts if c.get("is_primary")]
            if len(primaries) != 1:
                print(f"  biz_id={biz.id}: contracts is_primary 不唯一: {primaries}")
                all_ok = False

        if "contract_id" in biz.details:
            print(f"  biz_id={biz.id}: contract_id 字段未删除")
            all_ok = False

    if all_ok:
        print("  验证通过: 所有 business.details 结构符合新规范")
    return all_ok


def main():
    session = get_session()
    try:
        print("=" * 50)
        print("Business Details 数据结构迁移")
        print("=" * 50)
        print()

        print("1. 迁移 pricing key: product_name → sku_id")
        migrate_pricing(session)

        print()
        print("2. 迁移 contract_id → contracts")
        migrate_contracts(session)

        print()
        print("3. 删除 business.contract_id FK 列")
        drop_business_contract_id_column(session)

        print()
        print("4. 验证新结构")
        verify_structure(session)

        print()
        print("迁移完成!")

    finally:
        session.close()


if __name__ == "__main__":
    main()
