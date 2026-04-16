from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import Business, VirtualContract
from logic.business import (
    create_business_action, update_business_status_action,
    delete_business_action, advance_business_stage_action,
    CreateBusinessSchema, UpdateBusinessStatusSchema, AdvanceBusinessStageSchema,
)

router = APIRouter(prefix="/api/v1/business", tags=["业务"], dependencies=[Depends(verify_api_key)])


@router.post("/create", summary="创建业务")
def create_business(payload: CreateBusinessSchema, session: Session = Depends(get_db)):
    """创建新业务项，初始状态为"前期接洽"。需提供 customer_id。"""
    return create_business_action(session, payload).model_dump()


@router.post("/update-status", summary="更新业务状态")
def update_business_status(payload: UpdateBusinessStatusSchema, session: Session = Depends(get_db)):
    """直接更新业务状态和详情（暂缓/终止等），并写入 history 记录。会触发时间规则传播。"""
    return update_business_status_action(session, payload).model_dump()


class DeleteBusinessRequest(BaseModel):
    business_id: int

@router.post("/delete", summary="删除业务")
def delete_business(payload: DeleteBusinessRequest, session: Session = Depends(get_db)):
    """删除业务。如果存在关联虚拟合同则无法删除。"""
    return delete_business_action(session, payload.business_id).model_dump()


@router.post("/advance-stage", summary="推进业务阶段")
def advance_business_stage(payload: AdvanceBusinessStageSchema, session: Session = Depends(get_db)):
    """推进业务阶段。合法路径：前期接洽→业务评估→客户反馈→合作落地→业务开展。落地阶段需提供 payment_terms。"""
    return advance_business_stage_action(session, payload).model_dump()


# ==================== 查询端点 ====================

@router.get("/list", summary="业务列表")
def list_businesses(
    ids: Optional[str] = None,
    customer_id: Optional[int] = None,
    customer_ids: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """业务列表查询
    - ids: 多值查询，如 "1,2,3"
    - customer_ids: 多客户查询，如 "1,2,3"
    - date_from/date_to: 创建时间范围，格式 "YYYY-MM-DD"
    - search: 按业务描述模糊搜索
    """
    q = session.query(Business)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(Business.id.in_(id_list))

    # 精确过滤
    if customer_id is not None:
        q = q.filter(Business.customer_id == customer_id)
    if customer_ids:
        c_list = [int(x.strip()) for x in customer_ids.split(",") if x.strip().isdigit()]
        if c_list:
            q = q.filter(Business.customer_id.in_(c_list))
    if status:
        q = q.filter(Business.status == status)

    # 时间范围
    if date_from:
        q = q.filter(Business.timestamp >= date_from)
    if date_to:
        q = q.filter(Business.timestamp <= date_to)

    # 模糊搜索（需要关联 ChannelCustomer 查询名称）
    if search:
        from models import ChannelCustomer
        q = q.join(ChannelCustomer, Business.customer_id == ChannelCustomer.id).filter(
            ChannelCustomer.name.ilike(f"%{search}%")
        )

    q = q.order_by(Business.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/{bid}", summary="业务详情")
def get_business(bid: int, session: Session = Depends(get_db)):
    biz = session.query(Business).get(bid)
    if not biz:
        return {"success": False, "error": "未找到业务"}
    data = row_to_dict(biz)
    vcs = session.query(VirtualContract).filter(VirtualContract.business_id == bid).all()
    data["virtual_contracts"] = [row_to_dict(vc) for vc in vcs]
    return {"success": True, "data": data}
