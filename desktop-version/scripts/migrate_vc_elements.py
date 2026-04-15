"""VC Elements 结构迁移脚本
将旧格式 (skus[], points[].items[]) 迁移为新统一格式 (elements[])
同时为数据库添加 return_direction 列
"""
import sqlite3, json, sys

DB_PATH = "d:/WorkSpace/ShanYin/ERP/desktop-version/data/business_system.db"


# ── 供应商仓库名 → point_id 映射 ──────────────────────────────────────────
WAREHOUSE_NAME_TO_ID = {
    "朝旭食养仓": 3,
    "合肥佳合仓": 4,
    "天津格瑞仓": 5,
    "北冰洋仓": 6,
    "三河星谷仓": 7,
    "广东中贝仓": 8,
    "湖北广绅仓": 9,
    "苏州邦基勒仓": 10,
    "华迈环保仓": 24,
}


def name_to_warehouse_id(warehouse_name: str) -> int:
    """从仓库名推断 point_id"""
    if not warehouse_name:
        return 3  # 默认朝旭食养仓
    clean = warehouse_name.replace(" (供应商仓)", "").replace("(供应商仓)", "").strip()
    return WAREHOUSE_NAME_TO_ID.get(clean, 3)


def make_elem_id(sp_id: int, rp_id: int, sku_id: int) -> str:
    return f"sp{sp_id}_rp{rp_id}_sku{sku_id}"


def sku_to_elements(skus: list, sku_id_to_sp_map: dict) -> list:
    """将 skus[] 转为统一 elements[]

    Args:
        skus: 原始 skus 列表
        sku_id_to_sp_map: {sku_id: shipping_point_id}，从 skus.supplier_id 映射到供应商仓库 point_id
    """
    elements = []
    for sku in skus:
        sku_id = int(sku["sku_id"])
        qty = float(sku["qty"])
        price = float(sku["price"])
        deposit = float(sku.get("deposit") or 0)
        subtotal = qty * price
        sn = sku.get("sn", "-")

        # shipping_point_id: 从 sku_id → supplier → 供应商仓库 point_id
        sp_id = sku_id_to_sp_map.get(sku_id)

        # receiving_point_id: point_id (配送目的地)，None 时用总部仓 id=1
        if sku.get("point_id") is not None:
            rp_id = int(sku["point_id"])
        else:
            rp_id = 1  # 默认总部仓

        elements.append({
            "id": make_elem_id(sp_id, rp_id, sku_id),
            "shipping_point_id": sp_id,
            "receiving_point_id": rp_id,
            "sku_id": sku_id,
            "qty": qty,
            "price": price,
            "deposit": deposit,
            "subtotal": subtotal,
            "sn_list": [sn] if sn and sn != "-" else [],
        })
    return elements


def points_to_elements(points: list) -> list:
    """将 points[].items[] 转为统一 elements[]"""
    elements = []
    for pt in points:
        receiving_point_id = int(pt["pointId"])
        for item in pt.get("items", []):
            sku_id = int(item["sku_id"])
            qty = float(item["qty"])
            price = float(item["price"])
            deposit = float(item.get("deposit") or 0)
            subtotal = qty * price
            sn = item.get("sn", "-")

            source_wh = item.get("source_warehouse", "") or ""
            sp_id = name_to_warehouse_id(source_wh)

            elements.append({
                "id": make_elem_id(sp_id, receiving_point_id, sku_id),
                "shipping_point_id": sp_id,
                "receiving_point_id": receiving_point_id,
                "sku_id": sku_id,
                "qty": qty,
                "price": price,
                "deposit": deposit,
                "subtotal": subtotal,
                "sn_list": [sn] if sn and sn != "-" else [],
            })
    return elements


# SKU ID → 供应商仓库 point_id 映射 (从 points 表分析得出)
SKU_ID_TO_WH_ID = {
    2: 3,   # 原味豆浆-朝旭 → 朝旭食养仓
    3: 3,   # 玉米燕麦-朝旭 → 朝旭食养仓
    17: 8,  # 冰激凌机-广东中贝 → 广东中贝仓
    18: 9,  # 冰激凌机-湖北广绅 → 湖北广绅仓
    19: 10, # 冰沙机-苏州邦基勒 → 苏州邦基勒仓
}


def build_sku_sp_map(cur) -> dict:
    """从数据库动态推断 sku_id → shipping_point_id

    优先使用已知的静态映射 SKU_ID_TO_WH_ID，
    对数据库中其他 sku 通过 supplier_id → 仓库名模糊匹配推断。
    """
    # 基础: 已知的正确映射
    sku_sp_map = dict(SKU_ID_TO_WH_ID)

    # 加载所有 skus 的 supplier_id
    cur.execute("SELECT id, supplier_id FROM skus")
    sku_rows = cur.fetchall()

    # 加载所有供应商仓库 point (type='供应商仓')
    cur.execute("SELECT id, name FROM points WHERE type='供应商仓'")
    wh_rows = cur.fetchall()
    wh_id_by_name = {}
    for pt_id, pt_name in wh_rows:
        clean = pt_name.replace(" (供应商仓)", "").replace("(供应商仓)", "").replace("仓", "").strip()
        wh_id_by_name[clean] = pt_id

    # 加载 suppliers
    cur.execute("SELECT id, name FROM suppliers")
    sup_rows = cur.fetchall()
    sup_name = {r[0]: r[1] for r in sup_rows}

    # 对未映射的 sku，尝试推断
    for sku_id, sup_id in sku_rows:
        if sku_id in sku_sp_map:
            continue  # 已知映射，跳过
        sup = sup_name.get(sup_id, "")
        sp_id = None
        for key, pt_id in wh_id_by_name.items():
            if key in sup or sup in key:
                sp_id = pt_id
                break
        if sp_id is None:
            sp_id = 3  # fallback
        sku_sp_map[sku_id] = sp_id

    return sku_sp_map


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── Step 1: 添加 return_direction 列 (如果不存在) ───────────────────────
    cur.execute("PRAGMA table_info(virtual_contracts)")
    columns = [row[1] for row in cur.fetchall()]
    if "return_direction" not in columns:
        print("+ 添加 return_direction 列 ...")
        cur.execute("ALTER TABLE virtual_contracts ADD COLUMN return_direction VARCHAR(50)")
        conn.commit()
        print("  done")
    else:
        print("= return_direction 列已存在，跳过")

    # ── Step 2: 建立 sku → shipping_point 映射 ───────────────────────────────
    sku_sp_map = build_sku_sp_map(cur)
    print(f"= sku → shipping_point 映射: {sku_sp_map}")

    # ── Step 3: 迁移 elements ───────────────────────────────────────────────
    cur.execute("SELECT id, type, elements FROM virtual_contracts ORDER BY id")
    rows = cur.fetchall()

    migrated = []
    skipped = []

    for vc_id, vc_type, elements_json in rows:
        try:
            old_elem = json.loads(elements_json) if elements_json else {}
        except:
            old_elem = {}

        needs_migration = "skus" in old_elem or "points" in old_elem

        if not needs_migration:
            skipped.append(vc_id)
            continue

        new_elem = migrate_vc(vc_id, vc_type, old_elem, sku_sp_map)
        new_json = json.dumps(new_elem, ensure_ascii=False)

        cur.execute(
            "UPDATE virtual_contracts SET elements=? WHERE id=?",
            (new_json, vc_id)
        )

        elem_count = len(new_elem.get("elements", []))
        migrated.append((vc_id, vc_type, elem_count, new_elem))

    conn.commit()

    # ── Step 4: 验证输出 ────────────────────────────────────────────────────
    print(f"\n迁移完成: {len(migrated)} 个 VC")
    for vc_id, vc_type, cnt, elem in migrated:
        total = sum(e["subtotal"] for e in elem.get("elements", []))
        print(f"\nVC {vc_id} ({vc_type}): {cnt} elements, sum={total}")
        for e in elem.get("elements", []):
            print(f"  id={e['id']}, sp={e['shipping_point_id']}, rp={e['receiving_point_id']}, "
                  f"sku={e['sku_id']}, qty={e['qty']}, price={e['price']}, subtotal={e['subtotal']}")

    print(f"\n跳过 (无需迁移): {skipped}")

    conn.close()


if __name__ == "__main__":
    main()
