from fastapi import APIRouter, Depends
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import CashFlow
from logic.finance import (
    create_cash_flow_action, internal_transfer_action, external_fund_action,
    CreateCashFlowSchema, InternalTransferSchema, ExternalFundSchema
)

router = APIRouter(prefix="/api/v1/finance", tags=["财务"], dependencies=[Depends(verify_api_key)])


@router.post("/create-cashflow", summary="录入资金流水")
def create_cashflow(payload: CreateCashFlowSchema, session: Session = Depends(get_db)):
    """录入资金流水。type: 预付/履约/押金/退还押金/退款。自动触发状态机和复式记账。"""
    return create_cash_flow_action(session, payload).model_dump()


@router.post("/internal-transfer", summary="内部转账")
def internal_transfer(payload: InternalTransferSchema, session: Session = Depends(get_db)):
    """银行账户间内部转账。自动生成财务凭证。"""
    return internal_transfer_action(session, payload).model_dump()


@router.post("/external-fund", summary="外部资金出入")
def external_fund(payload: ExternalFundSchema, session: Session = Depends(get_db)):
    """外部资金流入/流出。is_inbound=true 为流入，false 为流出。"""
    return external_fund_action(session, payload).model_dump()


# ==================== 查询端点 ====================

@router.get("/cashflows", summary="资金流列表")
def list_cashflows(vc_id: Optional[int] = None, type: Optional[str] = None, page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    q = session.query(CashFlow)
    if vc_id is not None:
        q = q.filter(CashFlow.virtual_contract_id == vc_id)
    if type:
        q = q.filter(CashFlow.type == type)
    return {"success": True, "data": paginate(session, q, page, size)}
