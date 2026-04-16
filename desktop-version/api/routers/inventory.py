from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import EquipmentInventory, MaterialInventory

router = APIRouter(prefix="/api/v1/inventory", tags=["库存"], dependencies=[Depends(verify_api_key)])


@router.get("/equipment", summary="设备库存列表")
def list_equipment(vc_id: Optional[int] = None, point_id: Optional[int] = None, operational_status: Optional[str] = None, page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    q = session.query(EquipmentInventory)
    if vc_id is not None:
        q = q.filter(EquipmentInventory.virtual_contract_id == vc_id)
    if point_id is not None:
        q = q.filter(EquipmentInventory.point_id == point_id)
    if operational_status:
        q = q.filter(EquipmentInventory.operational_status == operational_status)
    return {"success": True, "data": paginate(session, q, page, size)}


@router.get("/material", summary="物料库存列表")
def list_material(
    ids: Optional[str] = None,
    sku_id: Optional[int] = None,
    warehouse_point_id: Optional[int] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """物料库存列表查询
    - ids: 多值查询，如 "1,2,3"
    - sku_id: 按SKU过滤
    - warehouse_point_id: 按仓库点位过滤
    """
    q = session.query(MaterialInventory)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(MaterialInventory.id.in_(id_list))

    # 精确过滤
    if sku_id is not None:
        q = q.filter(MaterialInventory.sku_id == sku_id)
    if warehouse_point_id is not None:
        q = q.filter(MaterialInventory.warehouse_point_id == warehouse_point_id)

    q = q.order_by(MaterialInventory.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}
