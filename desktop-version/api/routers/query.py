from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key
from logic.services import (
    get_returnable_items, get_sku_agreement_price, validate_inventory_availability,
    calculate_cashflow_progress, get_counterpart_info, get_suggested_cashflow_parties,
)
from models import VirtualContract

router = APIRouter(prefix="/api/v1/query", tags=["业务查询"], dependencies=[Depends(verify_api_key)])


@router.get("/returnable-items", summary="可退货项目")
def returnable_items(vc_id: int, direction: str, session: Session = Depends(get_db)):
    """查询指定VC可退货的SKU/SN列表。direction: 客户退我方/我方退供应商。"""
    result = get_returnable_items(session, vc_id, direction)
    return {"success": True, "data": result}


@router.get("/sku-agreement-price", summary="SKU协议价格")
def sku_agreement_price(sc_id: int, business_id: int, sku_name: str, session: Session = Depends(get_db)):
    """查询供应链协议中某SKU的单价、押金和类型。"""
    price, deposit, sku_type = get_sku_agreement_price(session, sc_id, business_id, sku_name)
    return {"success": True, "data": {"unit_price": price, "deposit": deposit, "sku_type": sku_type}}


class InventoryCheckItem(BaseModel):
    sku_name: str
    qty: float
    warehouse: str

@router.post("/inventory-availability", summary="库存可用性校验")
def inventory_availability(items: List[InventoryCheckItem], session: Session = Depends(get_db)):
    """校验物料库存是否满足需求。"""
    request_items = [i.model_dump() for i in items]
    is_valid, errors = validate_inventory_availability(session, request_items)
    return {"success": True, "data": {"is_valid": is_valid, "errors": errors}}


@router.get("/cashflow-progress", summary="资金流进度")
def cashflow_progress(vc_id: int, session: Session = Depends(get_db)):
    """查询VC的货款/押金收付进度。"""
    vc = session.query(VirtualContract).get(vc_id)
    if not vc:
        return {"success": False, "error": "未找到虚拟合同"}
    from models import CashFlow
    cfs = session.query(CashFlow).filter(CashFlow.virtual_contract_id == vc_id).all()
    progress = calculate_cashflow_progress(session, vc, cfs)
    return {"success": True, "data": progress}


@router.get("/counterpart-info", summary="交易对手信息")
def counterpart_info(vc_id: int, session: Session = Depends(get_db)):
    """查询VC的交易对手（穿透退货VC到原始对手）。"""
    vc = session.query(VirtualContract).get(vc_id)
    if not vc:
        return {"success": False, "error": "未找到虚拟合同"}
    cp_type, cp_id = get_counterpart_info(session, vc)
    return {"success": True, "data": {"counterpart_type": cp_type, "counterpart_id": cp_id}}


@router.get("/suggested-cashflow-parties", summary="建议的收付款方")
def suggested_cashflow_parties(vc_id: int, cf_type: str, session: Session = Depends(get_db)):
    """根据VC类型和资金流类型，推荐付款方和收款方。"""
    vc = session.query(VirtualContract).get(vc_id)
    if not vc:
        return {"success": False, "error": "未找到虚拟合同"}
    payer_type, payer_id, payee_type, payee_id = get_suggested_cashflow_parties(session, vc, cf_type)
    return {"success": True, "data": {"payer_type": payer_type, "payer_id": payer_id, "payee_type": payee_type, "payee_id": payee_id}}
