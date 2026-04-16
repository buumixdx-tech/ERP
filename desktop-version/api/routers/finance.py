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
def list_cashflows(
    ids: Optional[str] = None,
    vc_id: Optional[int] = None,
    vc_ids: Optional[str] = None,
    type: Optional[str] = None,
    payer_id: Optional[int] = None,
    payee_id: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """资金流列表查询
    - ids: 多值查询，如 "1,2,3"
    - vc_ids: 多vc查询，如 "1,2,3"
    - date_from/date_to: 交易时间范围，格式 "YYYY-MM-DD"
    - amount_min/amount_max: 金额范围
    """
    q = session.query(CashFlow)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(CashFlow.id.in_(id_list))

    # 精确过滤
    if vc_id is not None:
        q = q.filter(CashFlow.virtual_contract_id == vc_id)
    if vc_ids:
        vc_list = [int(x.strip()) for x in vc_ids.split(",") if x.strip().isdigit()]
        if vc_list:
            q = q.filter(CashFlow.virtual_contract_id.in_(vc_list))
    if type:
        q = q.filter(CashFlow.type == type)
    if payer_id is not None:
        q = q.filter(CashFlow.payer_account_id == payer_id)
    if payee_id is not None:
        q = q.filter(CashFlow.payee_account_id == payee_id)

    # 时间范围
    if date_from:
        q = q.filter(CashFlow.transaction_date >= date_from)
    if date_to:
        q = q.filter(CashFlow.transaction_date <= date_to)

    # 金额范围
    if amount_min is not None:
        q = q.filter(CashFlow.amount >= amount_min)
    if amount_max is not None:
        q = q.filter(CashFlow.amount <= amount_max)

    q = q.order_by(CashFlow.transaction_date.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/cashflows/{cf_id}", summary="资金流详情")
def get_cashflow(cf_id: int, session: Session = Depends(get_db)):
    obj = session.query(CashFlow).get(cf_id)
    if not obj:
        return {"success": False, "error": "未找到资金流记录"}
    return {"success": True, "data": row_to_dict(obj)}
