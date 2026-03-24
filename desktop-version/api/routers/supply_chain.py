from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import SupplyChain, SupplyChainItem
from logic.supply_chain import create_supply_chain_action, CreateSupplyChainSchema

router = APIRouter(prefix="/api/v1/supply-chain", tags=["供应链"], dependencies=[Depends(verify_api_key)])


class CreateSupplyChainRequest(BaseModel):
    sc: CreateSupplyChainSchema
    template_rules: Optional[list] = None


@router.post("/create", summary="创建供应链协议")
def create_supply_chain(req: CreateSupplyChainRequest, session: Session = Depends(get_db)):
    """创建供应链协议。自动创建合同、映射SKU定价。可附带模板时间规则。"""
    return create_supply_chain_action(session, req.sc, template_rules=req.template_rules).model_dump()


# ==================== 查询端点 ====================

@router.get("/list", summary="供应链列表")
def list_supply_chains(supplier_id: Optional[int] = None, page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    q = session.query(SupplyChain)
    if supplier_id is not None:
        q = q.filter(SupplyChain.supplier_id == supplier_id)
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/{sc_id}", summary="供应链详情")
def get_supply_chain(sc_id: int, session: Session = Depends(get_db)):
    sc = session.query(SupplyChain).get(sc_id)
    if not sc:
        return {"success": False, "error": "未找到供应链"}
    data = row_to_dict(sc)
    data["items"] = [row_to_dict(i) for i in session.query(SupplyChainItem).filter(SupplyChainItem.supply_chain_id == sc_id).all()]
    return {"success": True, "data": data}
