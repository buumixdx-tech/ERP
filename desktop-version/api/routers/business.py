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
from logic.addon_business import (
    create_addon_business_action,
    update_addon_business_action,
    deactivate_addon_business_action,
)
from logic.addon_business.queries import (
    get_addon_detail,
    get_business_addons,
    get_active_addons,
)
from logic.addon_business.schemas import CreateAddonSchema, UpdateAddonSchema

router = APIRouter(prefix="/api/v1/business", tags=["业务"], dependencies=[Depends(verify_api_key)])


# ==================== 业务 CRUD ====================

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


# ==================== 附加业务 ====================

@router.post("/addons/create", summary="创建附加业务政策")
def create_addon(payload: CreateAddonSchema, session: Session = Depends(get_db)):
    """在指定业务下创建附加政策（价格折扣/新增SKU/付款条款）。同类+同SKU有效期不可重叠。"""
    return create_addon_business_action(session, payload).model_dump()


@router.post("/addons/update", summary="更新附加业务政策")
def update_addon(payload: UpdateAddonSchema, session: Session = Depends(get_db)):
    """更新附加政策的日期、覆盖值、备注、状态。不允许修改 addon_type 和 sku_id。"""
    return update_addon_business_action(session, payload).model_dump()


@router.post("/addons/deactivate", summary="失效附加业务")
def deactivate_addon(addon_id: int, session: Session = Depends(get_db)):
    """将附加业务标记为失效（软删除）"""
    return deactivate_addon_business_action(session, addon_id).model_dump()


@router.get("/addons/list/{business_id}", summary="查询业务的附加政策列表")
def list_addons(business_id: int, include_expired: bool = False, session: Session = Depends(get_db)):
    """获取业务下所有附加政策（可包含已过期的）"""
    addons = get_business_addons(session, business_id, include_expired=include_expired)
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "business_id": a.business_id,
                "addon_type": a.addon_type,
                "status": a.status,
                "sku_id": a.sku_id,
                "override_price": a.override_price,
                "override_deposit": a.override_deposit,
                "start_date": a.start_date.isoformat() if a.start_date else None,
                "end_date": a.end_date.isoformat() if a.end_date else None,
                "remark": a.remark,
            }
            for a in addons
        ]
    }


@router.get("/addons/active/{business_id}", summary="查询业务当前生效的附加政策")
def list_active_addons(business_id: int, session: Session = Depends(get_db)):
    """获取业务下当前时间生效的所有附加政策"""
    addons = get_active_addons(session, business_id)
    return {
        "success": True,
        "data": [
            {
                "id": a.id,
                "business_id": a.business_id,
                "addon_type": a.addon_type,
                "status": a.status,
                "sku_id": a.sku_id,
                "override_price": a.override_price,
                "override_deposit": a.override_deposit,
                "start_date": a.start_date.isoformat() if a.start_date else None,
                "end_date": a.end_date.isoformat() if a.end_date else None,
                "remark": a.remark,
            }
            for a in addons
        ]
    }


@router.get("/addons/detail/{addon_id}", summary="附加政策详情")
def get_addon(addon_id: int, session: Session = Depends(get_db)):
    """获取单个附加政策详情"""
    addon = get_addon_detail(session, addon_id)
    if not addon:
        return {"success": False, "error": "附加政策不存在"}
    return {
        "success": True,
        "data": {
            "id": addon.id,
            "business_id": addon.business_id,
            "addon_type": addon.addon_type,
            "status": addon.status,
            "sku_id": addon.sku_id,
            "override_price": addon.override_price,
            "override_deposit": addon.override_deposit,
            "start_date": addon.start_date.isoformat() if addon.start_date else None,
            "end_date": addon.end_date.isoformat() if addon.end_date else None,
            "remark": addon.remark,
        }
    }


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
