"""
数据迁移脚本：将 JSON 中的名称 key 迁移为 ID key

执行方式: python scripts/migrate_json_keys_to_ids.py

迁移内容：
1. business.details.pricing: SKU name → sku_id
2. supply_chains.pricing_config: SKU name → sku_id
3. material_inventory.stock_distribution: point name → point_id
4. 删除 supply_chains.supplier_name 列
"""
import sys
sys.path.insert(0, '.')

from models import get_session, Business, SupplyChain, MaterialInventory
from sqlalchemy import text


def get_sku_id_by_name(session, sku_name: str):
    """根据 SKU 名称查找 ID"""
    from models import SKU
    if not sku_name or sku_name in ["未知", "-", ""]:
        return None
    sku = session.query(SKU).filter(SKU.name == sku_name).first()
    return sku.id if sku else None


def get_point_id_by_name(session, point_name: str):
    """根据 Point 名称查找 ID"""
    from models import Point
    if not point_name:
        return None
    # 去除括号内容，如 "朝旭食养仓 (供应商仓)" -> "朝旭食养仓"
    clean_name = point_name.split(" (")[0].split(" - ")[0]
    point = session.query(Point).filter(Point.name == clean_name).first()
    return point.id if point else None


def migrate_business_pricing(session):
    """迁移 business.details.pricing: SKU name → sku_id"""
    businesses = session.query(Business).all()
    migrated = 0
    skipped = 0

    for biz in businesses:
        if not biz.details or "pricing" not in biz.details:
            continue

        pricing = biz.details.get("pricing", {})
        if not pricing:
            continue

        new_pricing = {}
        for sku_name, config in pricing.items():
            sku_id = get_sku_id_by_name(session, sku_name)
            if sku_id:
                new_pricing[sku_id] = config
                migrated += 1
            else:
                # 找不到 ID，跳过
                skipped += 1

        biz.details["pricing"] = new_pricing

    session.commit()
    print(f"  business.details.pricing: 迁移 {migrated} 条, 跳过 {skipped} 条")
    return migrated, skipped


def migrate_supply_chain_pricing(session):
    """迁移 supply_chains.pricing_config: SKU name → sku_id"""
    chains = session.query(SupplyChain).all()
    migrated = 0
    skipped = 0

    for chain in chains:
        if not chain.pricing_config:
            continue

        pricing = chain.pricing_config
        if isinstance(pricing, str):
            import json
            pricing = json.loads(pricing)

        new_pricing = {}
        for sku_name, price in pricing.items():
            sku_id = get_sku_id_by_name(session, sku_name)
            if sku_id:
                new_pricing[sku_id] = price
                migrated += 1
            else:
                skipped += 1

        chain.pricing_config = new_pricing

    session.commit()
    print(f"  supply_chains.pricing_config: 迁移 {migrated} 条, 跳过 {skipped} 条")
    return migrated, skipped


def migrate_stock_distribution(session):
    """迁移 material_inventory.stock_distribution: point name → point_id"""
    inventories = session.query(MaterialInventory).all()
    migrated = 0
    skipped = 0

    for inv in inventories:
        if not inv.stock_distribution:
            continue

        dist = inv.stock_distribution
        new_dist = {}
        for wh_name, qty in dist.items():
            point_id = get_point_id_by_name(session, wh_name)
            if point_id:
                new_dist[str(point_id)] = qty
                migrated += 1
            else:
                # 找不到 ID，用 "default" 作为默认点位
                new_dist["default"] = qty
                skipped += 1

        inv.stock_distribution = new_dist

    session.commit()
    print(f"  material_inventory.stock_distribution: 迁移 {migrated} 条, 跳过 {skipped} 条")
    return migrated, skipped


def delete_supplier_name_column(session):
    """删除 supply_chains.supplier_name 列"""
    # 检查列是否存在
    result = session.execute(text("PRAGMA table_info(supply_chains)"))
    columns = [row[1] for row in result]
    if "supplier_name" in columns:
        session.execute(text("ALTER TABLE supply_chains DROP COLUMN supplier_name"))
        session.commit()
        print(f"  supply_chains.supplier_name: 已删除")
    else:
        print(f"  supply_chains.supplier_name: 列不存在，无需删除")


def main():
    session = get_session()
    try:
        print("开始迁移 JSON 字段...")
        print()

        print("1. 迁移 business.details.pricing...")
        migrate_business_pricing(session)

        print()
        print("2. 迁移 supply_chains.pricing_config...")
        migrate_supply_chain_pricing(session)

        print()
        print("3. 迁移 material_inventory.stock_distribution...")
        migrate_stock_distribution(session)

        print()
        print("4. 删除 supply_chains.supplier_name 列...")
        delete_supplier_name_column(session)

        print()
        print("迁移完成!")

    finally:
        session.close()


if __name__ == "__main__":
    main()
