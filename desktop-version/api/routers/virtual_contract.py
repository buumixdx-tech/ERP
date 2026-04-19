from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, and_
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import VirtualContract, VirtualContractStatusLog, Logistics, CashFlow
from logic.vc import (
    create_procurement_vc_action, create_material_supply_vc_action,
    create_return_vc_action, create_mat_procurement_vc_action,
    create_stock_procurement_vc_action, create_inventory_allocation_action,
    update_vc_action, delete_vc_action,
    CreateProcurementVCSchema, CreateMaterialSupplyVCSchema, CreateReturnVCSchema,
    CreateMatProcurementVCSchema, CreateStockProcurementVCSchema, AllocateInventorySchema,
    TimeRuleSchema,
)
from logic.constants import VCStatus

router = APIRouter(prefix="/api/v1/vc", tags=["虚拟合同"], dependencies=[Depends(verify_api_key)])


class CreateProcurementVCRequest(BaseModel):
    vc: CreateProcurementVCSchema
    draft_rules: Optional[List[TimeRuleSchema]] = None

class CreateMaterialSupplyVCRequest(BaseModel):
    vc: CreateMaterialSupplyVCSchema
    draft_rules: Optional[List[TimeRuleSchema]] = None

class CreateReturnVCRequest(BaseModel):
    vc: CreateReturnVCSchema
    draft_rules: Optional[List[TimeRuleSchema]] = None

class CreateMatProcurementVCRequest(BaseModel):
    vc: CreateMatProcurementVCSchema
    draft_rules: Optional[List[TimeRuleSchema]] = None

class CreateStockProcurementVCRequest(BaseModel):
    vc: CreateStockProcurementVCSchema
    draft_rules: Optional[List[TimeRuleSchema]] = None

class UpdateVCRequest(BaseModel):
    vc_id: int
    description: str
    elements: dict
    deposit_info: dict

class DeleteVCRequest(BaseModel):
    vc_id: int


@router.post("/create-procurement", summary="创建设备采购执行单")
def create_procurement_vc(req: CreateProcurementVCRequest, session: Session = Depends(get_db)):
    """创建设备采购虚拟合同。需关联业务(ACTIVE状态)和供应链协议。可附带时间规则草稿。"""
    return create_procurement_vc_action(session, req.vc, draft_rules=req.draft_rules).model_dump()


@router.post("/create-material-supply", summary="创建物料供应执行单")
def create_material_supply_vc(req: CreateMaterialSupplyVCRequest, session: Session = Depends(get_db)):
    """创建物料供应虚拟合同。会自动校验库存可用性。"""
    return create_material_supply_vc_action(session, req.vc, draft_rules=req.draft_rules).model_dump()


@router.post("/create-return", summary="创建退货执行单")
def create_return_vc(req: CreateReturnVCRequest, session: Session = Depends(get_db)):
    """创建退货虚拟合同。需指定目标VC和退货方向(客户退我方/我方退供应商)。"""
    return create_return_vc_action(session, req.vc, draft_rules=req.draft_rules).model_dump()


@router.post("/create-mat-procurement", summary="创建物料采购执行单")
def create_mat_procurement_vc(req: CreateMatProcurementVCRequest, session: Session = Depends(get_db)):
    """创建物料采购虚拟合同。不关联客户业务，直接向供应商采购物料。"""
    return create_mat_procurement_vc_action(session, req.vc, draft_rules=req.draft_rules).model_dump()


@router.post("/create-stock-procurement", summary="创建库存采购执行单")
def create_stock_procurement_vc(req: CreateStockProcurementVCRequest, session: Session = Depends(get_db)):
    """创建库存采购虚拟合同。不关联客户业务，向供应商采购设备入自有仓。"""
    return create_stock_procurement_vc_action(session, req.vc, draft_rules=req.draft_rules).model_dump()


@router.post("/allocate-inventory", summary="库存拨付")
def allocate_inventory(payload: AllocateInventorySchema, session: Session = Depends(get_db)):
    """将自有仓库存设备分配到客户业务点位。支持多点位分配。"""
    return create_inventory_allocation_action(session, payload).model_dump()


@router.post("/update", summary="更新虚拟合同")
def update_vc(req: UpdateVCRequest, session: Session = Depends(get_db)):
    """更新虚拟合同的描述、明细和押金信息。用于数据修正。"""
    from logic.vc.schemas import UpdateVCSchema
    payload = UpdateVCSchema(id=req.vc_id, description=req.description, elements=req.elements, deposit_info=req.deposit_info)
    return update_vc_action(session, payload).model_dump()


@router.post("/delete", summary="删除虚拟合同")
def delete_vc(req: DeleteVCRequest, session: Session = Depends(get_db)):
    """删除虚拟合同及其关联物流记录。"""
    from logic.vc.schemas import DeleteVCSchema
    return delete_vc_action(session, DeleteVCSchema(id=req.vc_id)).model_dump()


# ==================== 查询端点 ====================

@router.get("/list", summary="虚拟合同列表")
def list_vcs(
    ids: Optional[str] = None,
    business_id: Optional[int] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    cash_status: Optional[str] = None,
    subject_status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """虚拟合同列表查询
    - ids: 多值查询，如 "1,2,3"
    - date_from/date_to: 创建时间范围，格式 "YYYY-MM-DD"
    - search: 按描述模糊搜索
    """
    q = session.query(VirtualContract)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(VirtualContract.id.in_(id_list))

    # 精确过滤
    if business_id is not None:
        q = q.filter(VirtualContract.business_id == business_id)
    if type:
        q = q.filter(VirtualContract.type == type)
    if status:
        q = q.filter(VirtualContract.status == status)
    if cash_status:
        q = q.filter(VirtualContract.cash_status == cash_status)
    if subject_status:
        q = q.filter(VirtualContract.subject_status == subject_status)

    # 时间范围：通过 vc_status_logs 中 category="status" 且 status_name="执行" 的条目确定 VC 创建时间
    if date_from or date_to:
        # 子查询：找到每个 VC 的创建时间（category="status" 且 status_name=执行 的第一条日志）
        created_log = session.query(
            VirtualContractStatusLog.vc_id,
            func.min(VirtualContractStatusLog.timestamp).label('created_time')
        ).filter(
            VirtualContractStatusLog.category == 'status',
            VirtualContractStatusLog.status_name == VCStatus.EXE
        ).group_by(VirtualContractStatusLog.vc_id).subquery()

        q = q.join(created_log, VirtualContract.id == created_log.c.vc_id)

        if date_from:
            q = q.filter(func.date(created_log.c.created_time) >= date_from)
        if date_to:
            q = q.filter(func.date(created_log.c.created_time) <= date_to)

    # 模糊搜索
    if search:
        q = q.filter(VirtualContract.description.ilike(f"%{search}%"))

    q = q.order_by(VirtualContract.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/{vc_id}", summary="虚拟合同详情")
def get_vc(vc_id: int, session: Session = Depends(get_db)):
    """获取虚拟合同详情（已优化：使用 selectinload 避免 N+1 查询）"""
    # 使用 selectinload 预加载关联数据，避免 N+1 查询
    # selectinload 会使用单独的 SELECT 语句批量加载关联数据
    vc = session.query(VirtualContract).options(
        selectinload(VirtualContract.status_logs),
        selectinload(VirtualContract.logistics),
        selectinload(VirtualContract.cash_flows),
    ).get(vc_id)
    
    if not vc:
        return {"success": False, "error": "未找到虚拟合同"}
    
    data = row_to_dict(vc)
    # 关联数据已预加载，无需额外查询
    data["status_logs"] = [row_to_dict(l) for l in vc.status_logs]
    data["logistics"] = [row_to_dict(l) for l in vc.logistics]
    data["cash_flows"] = [row_to_dict(c) for c in vc.cash_flows]
    return {"success": True, "data": data}
