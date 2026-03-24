from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from models import EquipmentInventory, MaterialInventory, SKU, Point

def get_equipment_inventory(session: Session) -> List[Dict[str, Any]]:
    items = session.query(EquipmentInventory).all()
    result = []
    for e in items:
        sku = session.query(SKU).get(e.sku_id)
        point = session.query(Point).get(e.point_id) if e.point_id else None
        result.append({
            "id": e.id,
            "sn": e.sn,
            "sku_name": sku.name if sku else "未知",
            "model": sku.model if sku else "",
            "operational_status": e.operational_status,
            "device_status": e.device_status,
            "point_name": point.name if point else "库存中",
            "deposit_amount": e.deposit_amount,
            "deposit_timestamp": e.deposit_timestamp.strftime("%Y-%m-%d") if e.deposit_timestamp else ""
        })
    return result

def get_material_inventory(session: Session) -> List[Dict[str, Any]]:
    items = session.query(MaterialInventory).all()
    result = []
    for m in items:
        sku = session.query(SKU).get(m.sku_id)
        result.append({
            "id": m.id,
            "sku_name": sku.name if sku else "未知",
            "stock_distribution": m.stock_distribution or {},
            "average_price": m.average_price,
            "total_balance": m.total_balance
        })
    return result

def get_inventory_stats(session: Session) -> Dict[str, Any]:
    total_eq = session.query(EquipmentInventory).count()
    mat_skus = session.query(MaterialInventory).count()
    total_mat_qty = sum(m.total_balance or 0 for m in session.query(MaterialInventory).all())
    return {
        "total_equipment": total_eq,
        "material_sku_count": mat_skus,
        "total_material_quantity": total_mat_qty
    }
