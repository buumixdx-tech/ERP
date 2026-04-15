from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key
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

router = APIRouter(prefix="/api/v1/addon-business", tags=["附加业务"], dependencies=[Depends(verify_api_key)])


@router.post("/create", summary="创建附加业务政策")
def create_addon(payload: CreateAddonSchema, session: Session = Depends(get_db)):
    """在指定业务下创建附加政策（价格折扣/新增SKU/付款条款）。同类+同SKU有效期不可重叠。"""
    return create_addon_business_action(session, payload).model_dump()


@router.post("/update", summary="更新附加业务政策")
def update_addon(payload: UpdateAddonSchema, session: Session = Depends(get_db)):
    """更新附加政策的日期、覆盖值、备注、状态。不允许修改 addon_type 和 sku_id。"""
    return update_addon_business_action(session, payload).model_dump()


@router.post("/deactivate", summary="失效附加业务")
def deactivate_addon(addon_id: int, session: Session = Depends(get_db)):
    """将附加业务标记为失效（软删除）"""
    return deactivate_addon_business_action(session, addon_id).model_dump()


@router.get("/list/{business_id}", summary="查询业务的附加政策列表")
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


@router.get("/active/{business_id}", summary="查询业务当前生效的附加政策")
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


@router.get("/detail/{addon_id}", summary="附加政策详情")
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
