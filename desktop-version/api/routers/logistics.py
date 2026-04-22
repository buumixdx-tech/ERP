from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json
import os
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import Logistics, ExpressOrder
from logic.logistics import (
    create_logistics_plan_action, confirm_inbound_action,
    update_express_order_action, update_express_order_status_action,
    bulk_progress_express_orders_action,
    CreateLogisticsPlanSchema, ConfirmInboundSchema,
    UpdateExpressOrderSchema, ExpressOrderStatusSchema,
    BatchItemSchema,
)
from logic.file_mgmt import save_batch_certificate

router = APIRouter(prefix="/api/v1/logistics", tags=["物流"], dependencies=[Depends(verify_api_key)])


@router.post("/create-plan", summary="创建物流发货计划")
def create_logistics_plan(payload: CreateLogisticsPlanSchema, session: Session = Depends(get_db)):
    """创建物流计划及快递单。orders 中包含 tracking_number、items、address_info。"""
    return create_logistics_plan_action(session, payload).model_dump()


@router.post("/confirm-inbound", summary="确认入库")
def confirm_inbound(payload: ConfirmInboundSchema, session: Session = Depends(get_db)):
    """确认物流入库（JSON 方式）。触发库存模块、状态机、财务模块。设备类需提供 sn_list。"""
    return confirm_inbound_action(session, payload).model_dump()


@router.post("/confirm-inbound-material", summary="物料采购确认入库（含质检报告）")
async def confirm_inbound_material(
    log_id: int = Form(...),
    sn_list: str = Form("[]"),
    batch_items_json: str = Form(..., description="批次明细 JSON 字符串"),
    certificates: List[UploadFile] = File(default=[]),
    session: Session = Depends(get_db)
):
    """
    物料采购入库确认（multipart/form-data 方式，支持质检报告文件上传）。

    - batch_items_json: JSON 字符串，格式为 List[BatchItemSchema]
    - certificates: 质检报告文件列表，每个文件对应一个批次
    - 批次与文件的对应关系：通过 batch_items_json 中的 certificate_filename 字段关联
    """
    # 解析 sn_list
    sn_parsed = json.loads(sn_list)

    # 解析 batch_items
    batch_items_raw = json.loads(batch_items_json)
    batch_items = [BatchItemSchema(**bi) for bi in batch_items_raw]

    # 保存质检报告，建立 batch_no（不含扩展名）-> saved_path 映射
    cert_path_map = {}
    for cert_file in certificates:
        if cert_file.filename:
            # batch_no（不含扩展名）作为 key
            batch_no_key = os.path.splitext(cert_file.filename)[0]
            saved_path = save_batch_certificate(batch_no_key, cert_file)
            cert_path_map[batch_no_key] = saved_path

    # 将 certificate_filename 替换为实际保存路径
    for bi in batch_items:
        if bi.certificate_filename and bi.certificate_filename in cert_path_map:
            bi.certificate_filename = cert_path_map[bi.certificate_filename]

    payload = ConfirmInboundSchema(
        log_id=log_id,
        sn_list=sn_parsed,
        batch_items=batch_items
    )
    return confirm_inbound_action(session, payload).model_dump()


@router.post("/update-express", summary="更新快递单信息")
def update_express_order(payload: UpdateExpressOrderSchema, session: Session = Depends(get_db)):
    """更新快递单号和地址信息。"""
    return update_express_order_action(session, payload).model_dump()


@router.post("/update-express-status", summary="更新快递状态")
def update_express_order_status(payload: ExpressOrderStatusSchema, session: Session = Depends(get_db)):
    """更新快递状态(待发货→在途→签收)。触发物流状态机。"""
    return update_express_order_status_action(session, payload).model_dump()


class BulkProgressRequest(BaseModel):
    order_ids: List[int]
    target_status: str
    logistics_id: int

@router.post("/bulk-progress", summary="批量推进快递状态")
def bulk_progress_express_orders(req: BulkProgressRequest, session: Session = Depends(get_db)):
    """批量更新多个快递单状态。"""
    return bulk_progress_express_orders_action(session, req.order_ids, req.target_status, req.logistics_id).model_dump()


# ==================== 查询端点 ====================

@router.get("/list", summary="物流列表")
def list_logistics(
    ids: Optional[str] = None,
    vc_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tracking_number: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """物流列表查询
    - ids: 多值查询，如 "1,2,3"
    - status: 物流状态筛选
    - date_from/date_to: 创建时间范围，格式 "YYYY-MM-DD"
    - tracking_number: 快递单号模糊搜索
    """
    q = session.query(Logistics)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(Logistics.id.in_(id_list))

    # 精确过滤
    if vc_id is not None:
        q = q.filter(Logistics.virtual_contract_id == vc_id)
    if status:
        q = q.filter(Logistics.status == status)

    # 时间范围
    if date_from:
        q = q.filter(Logistics.created_at >= date_from)
    if date_to:
        q = q.filter(Logistics.created_at <= date_to)

    # 快递单号搜索（通过关联 ExpressOrder）
    if tracking_number:
        q = q.join(ExpressOrder).filter(ExpressOrder.tracking_number.ilike(f"%{tracking_number}%"))

    q = q.order_by(Logistics.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/{log_id}", summary="物流详情")
def get_logistics(log_id: int, session: Session = Depends(get_db)):
    log = session.query(Logistics).get(log_id)
    if not log:
        return {"success": False, "error": "未找到物流记录"}
    data = row_to_dict(log)
    data["express_orders"] = [row_to_dict(e) for e in session.query(ExpressOrder).filter(ExpressOrder.logistics_id == log_id).all()]
    return {"success": True, "data": data}
