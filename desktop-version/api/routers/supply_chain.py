from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import SupplyChain, SupplyChainItem
from logic.supply_chain import (
    create_supply_chain_action, update_supply_chain_action, delete_supply_chain_action,
    CreateSupplyChainSchema, UpdateSupplyChainSchema, DeleteSupplyChainSchema,
)

router = APIRouter(prefix="/api/v1/supply-chain", tags=["供应链"], dependencies=[Depends(verify_api_key)])


class CreateSupplyChainRequest(BaseModel):
    sc: CreateSupplyChainSchema
    template_rules: Optional[list] = None


@router.post("/create", summary="创建供应链协议")
def create_supply_chain(req: CreateSupplyChainRequest, session: Session = Depends(get_db)):
    """创建供应链协议。自动创建合同、映射SKU定价。可附带模板时间规则。"""
    return create_supply_chain_action(session, req.sc, template_rules=req.template_rules).model_dump()


@router.put("/{sc_id}", summary="更新供应链协议")
def update_supply_chain(sc_id: int, payload: UpdateSupplyChainSchema, session: Session = Depends(get_db)):
    """更新供应链协议。更新定价配置、结算条款等。"""
    if payload.id != sc_id:
        payload.id = sc_id  # 确保路径参数和body中的id一致
    return update_supply_chain_action(session, payload).model_dump()


@router.delete("/{sc_id}", summary="删除供应链协议")
def delete_supply_chain(sc_id: int, session: Session = Depends(get_db)):
    """删除供应链协议及其关联的SKU定价。"""
    return delete_supply_chain_action(session, DeleteSupplyChainSchema(id=sc_id)).model_dump()


# ==================== 查询端点 ====================

@router.get("/list", summary="供应链列表")
def list_supply_chains(
    ids: Optional[str] = None,
    supplier_id: Optional[int] = None,
    supplier_ids: Optional[str] = None,
    status: Optional[str] = None,
    type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """供应链列表查询
    - ids: 多值查询，如 "1,2,3"
    - supplier_ids: 多供应商查询，如 "1,2,3"
    - status: 供应链状态筛选
    - type: 类型（设备/物料）
    - date_from/date_to: 创建时间范围，格式 "YYYY-MM-DD"
    - search: 按供应商名称模糊搜索
    """
    q = session.query(SupplyChain)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(SupplyChain.id.in_(id_list))

    # 精确过滤
    if supplier_id is not None:
        q = q.filter(SupplyChain.supplier_id == supplier_id)
    if supplier_ids:
        s_list = [int(x.strip()) for x in supplier_ids.split(",") if x.strip().isdigit()]
        if s_list:
            q = q.filter(SupplyChain.supplier_id.in_(s_list))
    if status:
        q = q.filter(SupplyChain.status == status)
    if type:
        q = q.filter(SupplyChain.type == type)

    # 时间范围
    if date_from:
        q = q.filter(SupplyChain.created_at >= date_from)
    if date_to:
        q = q.filter(SupplyChain.created_at <= date_to)

    # 模糊搜索（需要关联 Supplier 查询名称）
    if search:
        from models import Supplier
        q = q.join(Supplier, SupplyChain.supplier_id == Supplier.id).filter(
            Supplier.name.ilike(f"%{search}%")
        )

    q = q.order_by(SupplyChain.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/{sc_id}", summary="供应链详情")
def get_supply_chain(sc_id: int, session: Session = Depends(get_db)):
    sc = session.query(SupplyChain).get(sc_id)
    if not sc:
        return {"success": False, "error": "未找到供应链"}
    data = row_to_dict(sc)
    data["items"] = [row_to_dict(i) for i in session.query(SupplyChainItem).filter(SupplyChainItem.supply_chain_id == sc_id).all()]
    return {"success": True, "data": data}
