from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import EquipmentInventory, MaterialInventory

router = APIRouter(prefix="/api/v1/inventory", tags=["库存"], dependencies=[Depends(verify_api_key)])


@router.get("/equipment", summary="设备库存列表")
def list_equipment(
    vc_id: Optional[int] = None,
    point_id: Optional[int] = None,
    sku_id: Optional[int] = None,
    operational_status: Optional[str] = None,
    device_status: Optional[str] = None,
    sn: Optional[str] = None,
    deposit_amount_min: Optional[float] = None,
    deposit_amount_max: Optional[float] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    q = session.query(EquipmentInventory)
    if vc_id is not None:
        q = q.filter(EquipmentInventory.virtual_contract_id == vc_id)
    if point_id is not None:
        q = q.filter(EquipmentInventory.point_id == point_id)
    if sku_id is not None:
        q = q.filter(EquipmentInventory.sku_id == sku_id)
    if operational_status:
        q = q.filter(EquipmentInventory.operational_status == operational_status)
    if device_status:
        q = q.filter(EquipmentInventory.device_status == device_status)
    if sn:
        q = q.filter(EquipmentInventory.sn.ilike(f"%{sn}%"))
    if deposit_amount_min is not None:
        q = q.filter(EquipmentInventory.deposit_amount >= deposit_amount_min)
    if deposit_amount_max is not None:
        q = q.filter(EquipmentInventory.deposit_amount <= deposit_amount_max)
    return {"success": True, "data": paginate(session, q, page, size)}


@router.get("/material", summary="物料库存列表")
def list_material(
    sku_id: Optional[int] = None,
    warehouse_point_id: Optional[int] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """物料库存列表查询
    - sku_id + warehouse_point_id: 该SKU在该仓库的库存数量
    - 只有 sku_id: 该SKU所有仓库的库存分布
    - 只有 warehouse_point_id: 该仓库下所有SKU的库存
    """
    q = session.query(MaterialInventory)

    # 基础过滤（warehouse_point_id 在 Python 中过滤）
    if sku_id is not None:
        q = q.filter(MaterialInventory.sku_id == sku_id)

    items = q.all()

    # 场景1: sku_id + warehouse_point_id → 返回该SKU在该仓库的数量
    if sku_id is not None and warehouse_point_id is not None:
        result = []
        for item in items:
            dist = item.stock_distribution or {}
            qty = dist.get(str(warehouse_point_id), 0)
            result.append({
                "id": item.id,
                "sku_id": item.sku_id,
                "warehouse_point_id": warehouse_point_id,
                "quantity": qty,
                "average_price": item.average_price,
                "total_balance": item.total_balance,
            })
        result.sort(key=lambda x: x["id"], reverse=True)
        total = len(result)
        start = (page - 1) * size
        end = start + size
        return {"success": True, "data": {
            "items": result[start:end],
            "total": total,
            "page": page,
            "size": size
        }}

    # 场景3: 只有 warehouse_point_id → 返回该仓库下所有SKU的库存
    if warehouse_point_id is not None:
        result = []
        for item in items:
            dist = item.stock_distribution or {}
            qty = dist.get(str(warehouse_point_id), 0)
            if qty > 0:  # 只返回有库存的
                result.append({
                    "id": item.id,
                    "sku_id": item.sku_id,
                    "warehouse_point_id": warehouse_point_id,
                    "quantity": qty,
                    "average_price": item.average_price,
                })
        result.sort(key=lambda x: x["id"], reverse=True)
        total = len(result)
        start = (page - 1) * size
        end = start + size
        return {"success": True, "data": {
            "items": result[start:end],
            "total": total,
            "page": page,
            "size": size
        }}

    # 场景2: 只有 sku_id → 返回所有仓库分布
    result = []
    for item in items:
        result.append({
            "id": item.id,
            "sku_id": item.sku_id,
            "stock_distribution": item.stock_distribution,
            "average_price": item.average_price,
            "total_balance": item.total_balance,
        })
    result.sort(key=lambda x: x["id"], reverse=True)
    total = len(result)
    start = (page - 1) * size
    end = start + size
    return {"success": True, "data": {
        "items": result[start:end],
        "total": total,
        "page": page,
        "size": size
    }}
