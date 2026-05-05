from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json
import os
from api.deps import get_db, verify_token, api_success, parse_ids
from api.middleware.error_handler import raise_not_found_error
from logic.api_queries import list_logistics, get_logistics, list_express_orders_global, list_logistics_global
from logic.logistics import (
    create_logistics_plan_action, confirm_inbound_action,
    update_express_order_action, update_express_order_status_action,
    bulk_progress_express_orders_action,
    CreateLogisticsPlanSchema, ConfirmInboundSchema,
    UpdateExpressOrderSchema, ExpressOrderStatusSchema,
    BatchItemSchema,
)
from logic.file_mgmt import save_batch_certificate
from logic.logistics.queries import get_logistics_dashboard_summary

router = APIRouter(prefix="/api/v1/logistics", tags=["物流"], dependencies=[Depends(verify_token)])


@router.post("/create-plan", summary="创建物流发货计划")
def create_logistics_plan(payload: CreateLogisticsPlanSchema, session: Session = Depends(get_db)):
    return create_logistics_plan_action(session, payload).model_dump()


@router.post("/confirm-inbound", summary="确认入库")
def confirm_inbound(payload: ConfirmInboundSchema, session: Session = Depends(get_db)):
    return confirm_inbound_action(session, payload).model_dump()


@router.post("/confirm-inbound-material", summary="物料采购确认入库（含质检报告）")
async def confirm_inbound_material(
    log_id: int = Form(...),
    sn_list: str = Form("[]"),
    batch_items_json: str = Form(..., description="批次明细 JSON 字符串"),
    certificates: List[UploadFile] = File(default=[]),
    session: Session = Depends(get_db)
):
    sn_parsed = json.loads(sn_list)
    batch_items_raw = json.loads(batch_items_json)
    batch_items = [BatchItemSchema(**bi) for bi in batch_items_raw]

    cert_path_map = {}
    for cert_file in certificates:
        if cert_file.filename:
            batch_no_key = os.path.splitext(cert_file.filename)[0]
            saved_path = save_batch_certificate(batch_no_key, cert_file)
            cert_path_map[batch_no_key] = saved_path

    for bi in batch_items:
        if bi.certificate_filename and bi.certificate_filename in cert_path_map:
            bi.certificate_filename = cert_path_map[bi.certificate_filename]

    payload = ConfirmInboundSchema(log_id=log_id, sn_list=sn_parsed, batch_items=batch_items)
    return confirm_inbound_action(session, payload).model_dump()


@router.put("/update-express", summary="更新快递单信息")
def update_express_order(payload: UpdateExpressOrderSchema, session: Session = Depends(get_db)):
    return update_express_order_action(session, payload).model_dump()


@router.post("/update-express-status", summary="更新快递状态")
def update_express_order_status(payload: ExpressOrderStatusSchema, session: Session = Depends(get_db)):
    return update_express_order_status_action(session, payload).model_dump()


class BulkProgressRequest(BaseModel):
    order_ids: List[int]
    target_status: str
    logistics_id: int

@router.post("/bulk-progress", summary="批量推进快递状态")
def bulk_progress_express_orders(req: BulkProgressRequest, session: Session = Depends(get_db)):
    return bulk_progress_express_orders_action(
        session, req.order_ids, req.target_status, req.logistics_id).model_dump()


# ==================== Query Endpoints ====================

@router.get("/list", summary="物流列表")
def get_logistics_list(
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
    id_list = parse_ids(ids)
    result = list_logistics(session, ids=id_list, vc_id=vc_id, status=status,
                             date_from=date_from, date_to=date_to,
                             tracking_number=tracking_number, page=page, size=size)
    return api_success(result)


@router.get("/express-orders/global", summary="快递单全局概览")
def get_express_orders_global(
    ids: Optional[int] = None,
    tracking_number: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sku_id: Optional[int] = None,
    sku_name_kw: Optional[str] = None,
    shipping_point_id: Optional[int] = None,
    shipping_point_name_kw: Optional[str] = None,
    receiving_point_id: Optional[int] = None,
    receiving_point_name_kw: Optional[str] = None,
    vc_id: Optional[int] = None,
    vc_type: Optional[str] = None,
    vc_status_type: Optional[str] = None,
    vc_status_value: Optional[str] = None,
    subject_status: Optional[str] = None,
    business_id: Optional[int] = None,
    business_customer_name_kw: Optional[str] = None,
    supply_chain_id: Optional[int] = None,
    supply_chain_supplier_name_kw: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    session: Session = Depends(get_db)
):
    id_list = [ids] if ids else None
    result = list_express_orders_global(
        session, ids=id_list, tracking_number=tracking_number, status=status,
        date_from=date_from, date_to=date_to,
        sku_id=sku_id, sku_name_kw=sku_name_kw,
        shipping_point_id=shipping_point_id, shipping_point_name_kw=shipping_point_name_kw,
        receiving_point_id=receiving_point_id, receiving_point_name_kw=receiving_point_name_kw,
        vc_id=vc_id, vc_type=vc_type, vc_status_type=vc_status_type, vc_status_value=vc_status_value,
        subject_status=subject_status,
        business_id=business_id, business_customer_name_kw=business_customer_name_kw,
        supply_chain_id=supply_chain_id, supply_chain_supplier_name_kw=supply_chain_supplier_name_kw,
        page=page, size=size
    )
    return api_success(result)


@router.get("/global", summary="物流全局概览")
def get_logistics_global(
    ids: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    tracking_number: Optional[str] = None,
    express_order_id: Optional[int] = None,
    sku_id: Optional[int] = None,
    sku_name_kw: Optional[str] = None,
    shipping_point_id: Optional[int] = None,
    shipping_point_name_kw: Optional[str] = None,
    receiving_point_id: Optional[int] = None,
    receiving_point_name_kw: Optional[str] = None,
    vc_id: Optional[int] = None,
    vc_type: Optional[str] = None,
    vc_status_type: Optional[str] = None,
    vc_status_value: Optional[str] = None,
    subject_status: Optional[str] = None,
    business_id: Optional[int] = None,
    business_customer_name_kw: Optional[str] = None,
    supply_chain_id: Optional[int] = None,
    supply_chain_supplier_name_kw: Optional[str] = None,
    page: int = 1,
    size: int = 20,
    session: Session = Depends(get_db)
):
    id_list = [ids] if ids else None
    result = list_logistics_global(
        session, ids=id_list, status=status,
        date_from=date_from, date_to=date_to,
        tracking_number=tracking_number, express_order_id=express_order_id,
        sku_id=sku_id, sku_name_kw=sku_name_kw,
        shipping_point_id=shipping_point_id, shipping_point_name_kw=shipping_point_name_kw,
        receiving_point_id=receiving_point_id, receiving_point_name_kw=receiving_point_name_kw,
        vc_id=vc_id, vc_type=vc_type, vc_status_type=vc_status_type, vc_status_value=vc_status_value,
        subject_status=subject_status,
        business_id=business_id, business_customer_name_kw=business_customer_name_kw,
        supply_chain_id=supply_chain_id, supply_chain_supplier_name_kw=supply_chain_supplier_name_kw,
        page=page, size=size
    )
    return api_success(result)


@router.get("/dashboard/summary", summary="物流看板统计")
def get_logistics_dash(session: Session = Depends(get_db)):
    """物流看板：各状态数量统计、今日新增。"""
    return api_success(get_logistics_dashboard_summary())


@router.get("/{log_id}", summary="物流详情")
def get_logistics_detail(log_id: int, session: Session = Depends(get_db)):
    data = get_logistics(session, log_id)
    if data is None:
        raise_not_found_error("物流", str(log_id))
    return api_success(data)
