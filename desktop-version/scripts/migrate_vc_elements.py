"""
VC Elements 结构迁移脚本
将所有旧结构 VC 的 elements 统一转换为新的 elements 结构。

旧结构类型:
  1. 设备采购/库存采购/物料采购: {"skus": [...], "total_amount": ..., "payment_terms": ...}
  2. 物料供应: {"points": [...], "total_amount": ..., "payment_terms": ...}
  3. 退货: {"return_items": [...], ...}
  4. 库存拨付: {"allocation_items": [...], ...}

新统一结构:
  {
    "elements": [
      {
        "id": "sp{shipping_point_id}_rp{receiving_point_id}_sku{sku_id}",
        "shipping_point_id": int,
        "receiving_point_id": int,
        "sku_id": int,
        "qty": float,
        "price": float,
        "deposit": float,
        "subtotal": float,
        "sn_list": []
      }
    ],
    "total_amount": float,
    "payment_terms": {...}
  }
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import init_db, get_session, VirtualContract, Point, SKU
from sqlalchemy.orm.attributes import flag_modified
from logic.constants import VCType
import json


# 默认发货点位（总仓库）
DEFAULT_SHIPPING_POINT_ID = 1


def get_point_id_by_name(session, name: str) -> int | None:
    """根据点位名称查找点位ID"""
    if not name or name == "未知" or name == "-":
        return None
    point = session.query(Point).filter(Point.name == name).first()
    return point.id if point else None


def get_sku_id_by_name(session, name: str) -> int | None:
    """根据SKU名称查找SKU ID"""
    if not name or name == "未知" or name == "-":
        return None
    sku = session.query(SKU).filter(SKU.name == name).first()
    return sku.id if sku else None


def migrate_procurement_vc(session, vc: VirtualContract) -> bool:
    """
    迁移采购类 VC (设备采购/库存采购/物料采购)
    旧: {"skus": [...], "total_amount": ..., "payment_terms": ...}
    """
    old = vc.elements
    skus = old.get("skus", [])
    if not skus:
        return False

    new_elements = []
    for item in skus:
        sku_id = item.get("sku_id")
        # 如果 sku_id 为空，尝试用名称查找
        if not sku_id:
            sku_id = get_sku_id_by_name(session, item.get("sku_name", ""))
        if not sku_id:
            print(f"  [WARN] VC {vc.id}: 无法找到SKU '{item.get('sku_name')}'，跳过")
            continue

        point_id = item.get("point_id")
        # receiving_point_id: 旧数据中的 point_id（客户运营点位）
        # 如果 point_id 为空，尝试用名称查找
        if not point_id:
            pt_name = item.get("point_name", "")
            if pt_name and pt_name != "未知" and pt_name != "-":
                point_id = get_point_id_by_name(session, pt_name)

        # shipping_point_id: 默认总仓库
        shipping_pt = DEFAULT_SHIPPING_POINT_ID
        # receiving_point_id: point_id（运营点位），如果也没有则用1
        receiving_pt = point_id if point_id else 1

        qty = float(item.get("qty", 0))
        price = float(item.get("price", 0))
        deposit = float(item.get("deposit", 0))
        subtotal = qty * price
        sn = item.get("sn", "-")
        sn_list = [] if sn in ["-", "", None] else [sn]

        elem = {
            "id": f"sp{shipping_pt}_rp{receiving_pt}_sku{sku_id}",
            "shipping_point_id": shipping_pt,
            "receiving_point_id": receiving_pt,
            "sku_id": sku_id,
            "qty": qty,
            "price": price,
            "deposit": deposit,
            "subtotal": subtotal,
            "sn_list": sn_list,
        }
        new_elements.append(elem)

    if not new_elements:
        return False

    # 确定 vc_type
    vc_type_map = {
        "设备采购": VCType.EQUIPMENT_PROCUREMENT,
        "设备采购(库存)": VCType.STOCK_PROCUREMENT,
        "物料采购": VCType.MATERIAL_PROCUREMENT,
    }
    vc_type = vc_type_map.get(vc.type, VCType.EQUIPMENT_PROCUREMENT)

    new_elements_data = {
        "elements": new_elements,
        "total_amount": old.get("total_amount"),
        "payment_terms": old.get("payment_terms"),
    }

    vc.elements = new_elements_data
    flag_modified(vc, "elements")
    return True


def migrate_material_supply_vc(session, vc: VirtualContract) -> bool:
    """
    迁移物料供应 VC
    旧: {"order_id": ..., "points": [...], "total_amount": ..., "payment_terms": ...}
    """
    old = vc.elements
    points = old.get("points", [])
    if not points:
        return False

    new_elements = []
    for pt in points:
        receiving_pt = pt.get("pointId")
        if not receiving_pt:
            pt_name = pt.get("pointName", "")
            if pt_name:
                receiving_pt = get_point_id_by_name(session, pt_name)

        items = pt.get("items", [])
        for item in items:
            sku_id = item.get("sku_id")
            if not sku_id:
                sku_id = get_sku_id_by_name(session, item.get("sku_name", ""))
            if not sku_id:
                print(f"  [WARN] VC {vc.id}: 无法找到SKU '{item.get('sku_name')}'，跳过")
                continue

            # shipping_point: 尝试从 source_warehouse 名称查找，默认为总仓库
            source_wh = item.get("source_warehouse", "")
            shipping_pt = 1
            if source_wh and source_wh != "未知":
                pid = get_point_id_by_name(session, source_wh)
                if pid:
                    shipping_pt = pid

            qty = float(item.get("qty", 0))
            price = float(item.get("price", 0))
            deposit = float(item.get("deposit", 0))
            subtotal = qty * price
            sn = item.get("sn", "-")
            sn_list = [] if sn in ["-", "", None] else [sn]

            receiving_final = receiving_pt if receiving_pt else 1

            elem = {
                "id": f"sp{shipping_pt}_rp{receiving_final}_sku{sku_id}",
                "shipping_point_id": shipping_pt,
                "receiving_point_id": receiving_final,
                "sku_id": sku_id,
                "qty": qty,
                "price": price,
                "deposit": deposit,
                "subtotal": subtotal,
                "sn_list": sn_list,
            }
            new_elements.append(elem)

    if not new_elements:
        return False

    new_elements_data = {
        "elements": new_elements,
        "total_amount": old.get("total_amount"),
        "payment_terms": old.get("payment_terms"),
    }

    vc.elements = new_elements_data
    flag_modified(vc, "elements")
    return True


def migrate_return_vc(session, vc: VirtualContract) -> bool:
    """
    迁移退货 VC
    旧: {"return_items": [...], "return_direction": ..., "total_refund": ...}
    """
    old = vc.elements
    return_items = old.get("return_items", [])
    if not return_items:
        return False

    new_elements = []
    for item in return_items:
        sku_id = item.get("sku_id")
        if not sku_id:
            sku_id = get_sku_id_by_name(session, item.get("sku_name", ""))
        if not sku_id:
            print(f"  [WARN] VC {vc.id}: 无法找到SKU '{item.get('sku_name')}'，跳过")
            continue

        point_id = item.get("point_id")
        if not point_id:
            pt_name = item.get("point_name", "")
            if pt_name:
                point_id = get_point_id_by_name(session, pt_name)

        shipping_pt = DEFAULT_SHIPPING_POINT_ID
        receiving_pt = point_id if point_id else 1

        qty = float(item.get("qty", 0))
        price = float(item.get("price", 0))
        deposit = float(item.get("deposit", 0))
        subtotal = qty * price
        sn = item.get("sn", "-")
        sn_list = [] if sn in ["-", "", None] else [sn]

        elem = {
            "id": f"sp{shipping_pt}_rp{receiving_pt}_sku{sku_id}",
            "shipping_point_id": shipping_pt,
            "receiving_point_id": receiving_pt,
            "sku_id": sku_id,
            "qty": qty,
            "price": price,
            "deposit": deposit,
            "subtotal": subtotal,
            "sn_list": sn_list,
        }
        new_elements.append(elem)

    if not new_elements:
        return False

    # 退货 VC 顶层字段保留
    new_elements_data = {
        "elements": new_elements,
        "return_direction": old.get("return_direction"),
        "goods_amount": old.get("goods_amount"),
        "deposit_amount": old.get("deposit_amount"),
        "logistics_cost": old.get("logistics_cost"),
        "logistics_bearer": old.get("logistics_bearer"),
        "total_refund": old.get("total_refund"),
        "reason": old.get("reason"),
    }

    vc.elements = new_elements_data
    flag_modified(vc, "elements")
    return True


def migrate_inventory_allocation_vc(session, vc: VirtualContract) -> bool:
    """
    迁移库存拨付 VC
    旧: {"allocation_items": [...]}
    """
    old = vc.elements
    allocation_items = old.get("allocation_items", [])
    if not allocation_items:
        return False

    new_elements = []
    for item in allocation_items:
        sku_id = item.get("sku_id")
        if not sku_id:
            sku_id = get_sku_id_by_name(session, item.get("sku_name", ""))
        if not sku_id:
            print(f"  [WARN] VC {vc.id}: 无法找到SKU '{item.get('sku_name')}'，跳过")
            continue

        shipping_pt = item.get("shipping_point_id", DEFAULT_SHIPPING_POINT_ID)
        receiving_pt = item.get("receiving_point_id", 1)

        qty = float(item.get("qty", 0))
        price = float(item.get("price", 0))
        deposit = float(item.get("deposit", 0))
        subtotal = qty * price
        sn_list = item.get("sn_list", [])

        elem = {
            "id": f"sp{shipping_pt}_rp{receiving_pt}_sku{sku_id}",
            "shipping_point_id": shipping_pt,
            "receiving_point_id": receiving_pt,
            "sku_id": sku_id,
            "qty": qty,
            "price": price,
            "deposit": deposit,
            "subtotal": subtotal,
            "sn_list": sn_list,
        }
        new_elements.append(elem)

    if not new_elements:
        return False

    new_elements_data = {
        "elements": new_elements,
    }

    vc.elements = new_elements_data
    flag_modified(vc, "elements")
    return True


def is_already_migrated(elements: dict) -> bool:
    """检查是否已经是新结构（新结构只有 elements 键，不再有 vc_type）
    返回 True 表示不需要迁移，返回 False 表示需要迁移
    """
    if not elements:
        return False
    # 有 elements 但不含 vc_type：已是正确新结构，不需要迁移
    if "elements" in elements and "vc_type" not in elements:
        return True
    # 有 elements 且含 vc_type：旧迁移遗留，需要重新迁移（清理 vc_type）
    if "elements" in elements and "vc_type" in elements:
        return False
    # 其他情况（旧结构）：需要迁移
    return False


def main():
    print("=" * 60)
    print("VC Elements 结构迁移脚本")
    print("=" * 60)

    init_db()
    session = get_session()

    try:
        all_vcs = session.query(VirtualContract).all()
        total = len(all_vcs)
        print(f"\n共找到 {total} 个 VC\n")

        migrated = 0
        skipped = 0
        errors = 0

        for vc in all_vcs:
            if is_already_migrated(vc.elements):
                print(f"[SKIP] VC id={vc.id} type={vc.type} - 已是正确结构")
                skipped += 1
                continue

            old_str = str(vc.elements)[:80]
            print(f"[MIGRATE] VC id={vc.id} type={vc.type}")
            print(f"         old keys: {list(vc.elements.keys()) if vc.elements else None}")

            try:
                old_type = vc.type
                success = False

                # 如果 elements 有 vc_type（旧迁移遗留），直接清理该字段
                if vc.elements and "elements" in vc.elements and "vc_type" in vc.elements:
                    print(f"  [CLEAN] VC {vc.id} 清理冗余 vc_type 字段")
                    del vc.elements["vc_type"]
                    flag_modified(vc, "elements")
                    session.flush()
                    migrated += 1
                    continue

                if old_type in ["设备采购", "设备采购(库存)", "物料采购"]:
                    success = migrate_procurement_vc(session, vc)
                elif old_type == "物料供应":
                    success = migrate_material_supply_vc(session, vc)
                elif old_type == "退货":
                    success = migrate_return_vc(session, vc)
                elif old_type == "库存拨付":
                    success = migrate_inventory_allocation_vc(session, vc)
                else:
                    print(f"  [WARN] 未知 VC 类型 '{old_type}'，跳过")
                    skipped += 1
                    continue

                if success:
                    # 每条迁移后立即 flush，确保写入当前事务
                    session.flush()
                    new_elems = vc.elements
                    print(f"         new elements count: {len(new_elems.get('elements', []))}")
                    migrated += 1
                else:
                    print(f"  [ERROR] VC {vc.id} 迁移失败（无有效数据）")
                    errors += 1

            except Exception as e:
                print(f"  [ERROR] VC {vc.id} 迁移异常: {e}")
                import traceback
                traceback.print_exc()
                errors += 1

        print(f"\n{'=' * 60}")
        print(f"迁移完成: 成功={migrated}, 跳过(已是新结构)={skipped}, 错误={errors}")
        print(f"{'=' * 60}")

        # 提交事务
        if migrated > 0:
            session.commit()
            print(f"\n数据库已提交 {migrated} 条迁移记录")

        # 打印验证信息（提交之后，强制 checkpoint 确保 WAL 数据落盘）
        print("\n验证迁移结果:")
        print("-" * 60)
        from sqlalchemy import text
        with session.get_bind().connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            conn.commit()

        # 重新查询，强制读取数据库实际值
        session.expire_all()
        all_vcs_after = session.query(VirtualContract).all()
        for vc in all_vcs_after:
            elems = vc.elements
            has_elements = "elements" in elems if elems else False
            count = len(elems.get("elements", [])) if has_elements else 0
            status = "[OK]" if has_elements else "[FAIL]"
            print(f"  {status} VC id={vc.id} type={vc.type} elements_count={count}")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
    finally:
        session.close()


if __name__ == "__main__":
    main()
