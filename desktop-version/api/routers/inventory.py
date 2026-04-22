from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import EquipmentInventory, MaterialInventory, SKU, Point

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
    """
    物料库存列表查询（新批次结构）

    - sku_id + warehouse_point_id: 该SKU在该仓库的批次库存
    - 只有 sku_id: 该SKU所有批次的库存
    - 只有 warehouse_point_id: 该仓库下所有SKU的批次库存
    - 都没有: 返回所有批次库存
    """
    # 构建基础查询
    q = session.query(MaterialInventory)

    # 按sku_id过滤
    if sku_id is not None:
        q = q.filter(MaterialInventory.sku_id == sku_id)

    # 按point_id过滤
    if warehouse_point_id is not None:
        q = q.filter(MaterialInventory.point_id == warehouse_point_id)

    # 获取批次行
    batches = q.filter(MaterialInventory.qty > 0).all()

    # 收集所有需要的sku_id和point_id
    sku_ids = set(b.sku_id for b in batches if b.sku_id)
    point_ids = set(b.point_id for b in batches if b.point_id)

    # 批量查询SKU和Point
    sku_map = {}
    if sku_ids:
        skus = session.query(SKU).filter(SKU.id.in_(sku_ids)).all()
        sku_map = {s.id: s for s in skus}

    point_map = {}
    if point_ids:
        points = session.query(Point).filter(Point.id.in_(point_ids)).all()
        point_map = {p.id: p for p in points}

    # 按SKU分组统计
    result = []
    if sku_id is not None and warehouse_point_id is not None:
        # 场景1: sku_id + warehouse_point_id → 返回该SKU在该仓库的数量
        for b in batches:
            sku = sku_map.get(b.sku_id)
            result.append({
                "id": b.id,
                "sku_id": b.sku_id,
                "sku_name": sku.name if sku else "未知",
                "batch_no": b.batch_no,
                "warehouse_point_id": warehouse_point_id,
                "warehouse_point_name": point_map.get(warehouse_point_id).name if point_map.get(warehouse_point_id) else "未知",
                "quantity": b.qty,
                "average_price": float(sku.params.get("average_price", 0.0)) if sku and sku.params else 0.0,
                "vc_id": b.latest_purchase_vc_id
            })
    elif sku_id is not None:
        # 场景2: 只有 sku_id → 返回所有批次
        for b in batches:
            sku = sku_map.get(b.sku_id)
            point = point_map.get(b.point_id)
            result.append({
                "id": b.id,
                "sku_id": b.sku_id,
                "sku_name": sku.name if sku else "未知",
                "batch_no": b.batch_no,
                "warehouse_point_id": b.point_id,
                "warehouse_point_name": point.name if point else f"点位{b.point_id}",
                "quantity": b.qty,
                "average_price": float(sku.params.get("average_price", 0.0)) if sku and sku.params else 0.0,
                "vc_id": b.latest_purchase_vc_id
            })
    elif warehouse_point_id is not None:
        # 场景3: 只有 warehouse_point_id → 返回该仓库下所有SKU
        for b in batches:
            sku = sku_map.get(b.sku_id)
            result.append({
                "id": b.id,
                "sku_id": b.sku_id,
                "sku_name": sku.name if sku else "未知",
                "batch_no": b.batch_no,
                "warehouse_point_id": warehouse_point_id,
                "warehouse_point_name": point_map.get(warehouse_point_id).name if point_map.get(warehouse_point_id) else "未知",
                "quantity": b.qty,
                "average_price": float(sku.params.get("average_price", 0.0)) if sku and sku.params else 0.0,
                "vc_id": b.latest_purchase_vc_id
            })
    else:
        # 场景4: 都没有 → 返回所有批次
        for b in batches:
            sku = sku_map.get(b.sku_id)
            point = point_map.get(b.point_id)
            result.append({
                "id": b.id,
                "sku_id": b.sku_id,
                "sku_name": sku.name if sku else "未知",
                "batch_no": b.batch_no,
                "warehouse_point_id": b.point_id,
                "warehouse_point_name": point.name if point else f"点位{b.point_id}",
                "quantity": b.qty,
                "average_price": float(sku.params.get("average_price", 0.0)) if sku and sku.params else 0.0,
                "vc_id": b.latest_purchase_vc_id
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
