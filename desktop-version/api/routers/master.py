from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from api.deps import get_db, verify_api_key, row_to_dict, paginate
from models import ChannelCustomer, Point, Supplier, SKU, ExternalPartner, BankAccount
from logic.master import (
    create_customer_action, update_customers_action, delete_customers_action,
    create_point_action, update_points_action, delete_points_action,
    create_supplier_action, update_suppliers_action, delete_suppliers_action,
    create_sku_action, update_skus_action, delete_skus_action,
    create_partner_action, update_partners_action, delete_partners_action,
    CustomerSchema, PointSchema, SupplierSchema, SKUSchema, PartnerSchema,
    DeleteMasterDataSchema,
)
from logic.finance import (
    create_bank_account_action, update_bank_accounts_action,
    CreateBankAccountSchema, UpdateBankAccountSchema,
)

router = APIRouter(prefix="/api/v1/master", tags=["主数据"], dependencies=[Depends(verify_api_key)])

# --- Customer ---
@router.post("/create-customer", summary="创建渠道客户")
def create_customer(payload: CustomerSchema, session: Session = Depends(get_db)):
    """创建新的渠道客户。name 必填且唯一。"""
    return create_customer_action(session, payload).model_dump()

@router.post("/update-customers", summary="批量更新客户")
def update_customers(payloads: List[CustomerSchema], session: Session = Depends(get_db)):
    return update_customers_action(session, payloads).model_dump()

@router.post("/delete-customers", summary="批量删除客户")
def delete_customers(payloads: List[DeleteMasterDataSchema], session: Session = Depends(get_db)):
    """删除客户。如果客户已关联业务记录则无法删除。"""
    return delete_customers_action(session, payloads).model_dump()

# --- Point ---
@router.post("/create-point", summary="创建点位/仓库")
def create_point(payload: PointSchema, session: Session = Depends(get_db)):
    """创建运营点位、客户仓、自有仓或供应商仓。"""
    return create_point_action(session, payload).model_dump()

@router.post("/update-points", summary="批量更新点位")
def update_points(payloads: List[PointSchema], session: Session = Depends(get_db)):
    return update_points_action(session, payloads).model_dump()

@router.post("/delete-points", summary="批量删除点位")
def delete_points(payloads: List[DeleteMasterDataSchema], session: Session = Depends(get_db)):
    return delete_points_action(session, payloads).model_dump()

# --- Supplier ---
@router.post("/create-supplier", summary="创建供应商")
def create_supplier(payload: SupplierSchema, session: Session = Depends(get_db)):
    """创建供应商。category 可选：设备、物料、兼备。"""
    return create_supplier_action(session, payload).model_dump()

@router.post("/update-suppliers", summary="批量更新供应商")
def update_suppliers(payloads: List[SupplierSchema], session: Session = Depends(get_db)):
    return update_suppliers_action(session, payloads).model_dump()

@router.post("/delete-suppliers", summary="批量删除供应商")
def delete_suppliers(payloads: List[DeleteMasterDataSchema], session: Session = Depends(get_db)):
    return delete_suppliers_action(session, payloads).model_dump()

# --- SKU ---
@router.post("/create-sku", summary="创建SKU")
def create_sku(payload: SKUSchema, session: Session = Depends(get_db)):
    """创建设备或物料SKU。type_level1: 设备/物料。"""
    return create_sku_action(session, payload).model_dump()

@router.post("/update-skus", summary="批量更新SKU")
def update_skus(payloads: List[SKUSchema], session: Session = Depends(get_db)):
    return update_skus_action(session, payloads).model_dump()

@router.post("/delete-skus", summary="批量删除SKU")
def delete_skus(payloads: List[DeleteMasterDataSchema], session: Session = Depends(get_db)):
    return delete_skus_action(session, payloads).model_dump()

# --- Partner ---
@router.post("/create-partner", summary="创建外部合作方")
def create_partner(payload: PartnerSchema, session: Session = Depends(get_db)):
    return create_partner_action(session, payload).model_dump()

@router.post("/update-partners", summary="批量更新合作方")
def update_partners(payloads: List[PartnerSchema], session: Session = Depends(get_db)):
    return update_partners_action(session, payloads).model_dump()

@router.post("/delete-partners", summary="批量删除合作方")
def delete_partners(payloads: List[DeleteMasterDataSchema], session: Session = Depends(get_db)):
    return delete_partners_action(session, payloads).model_dump()

# --- Bank Account ---
@router.post("/create-bank-account", summary="创建银行账户")
def create_bank_account(payload: CreateBankAccountSchema, session: Session = Depends(get_db)):
    """创建银行账户。owner_type: 客户/供应商/我方/合作伙伴。"""
    return create_bank_account_action(session, payload).model_dump()

@router.post("/update-bank-accounts", summary="批量更新银行账户")
def update_bank_accounts(payloads: List[UpdateBankAccountSchema], session: Session = Depends(get_db)):
    return update_bank_accounts_action(session, payloads).model_dump()


# ==================== 查询端点 ====================

@router.get("/customers", summary="客户列表")
def list_customers(page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    return {"success": True, "data": paginate(session, session.query(ChannelCustomer), page, size)}

@router.get("/customers/{cid}", summary="客户详情")
def get_customer(cid: int, session: Session = Depends(get_db)):
    obj = session.query(ChannelCustomer).get(cid)
    if not obj:
        return {"success": False, "error": "未找到客户"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/points", summary="点位列表")
def list_points(customer_id: Optional[int] = None, page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    q = session.query(Point)
    if customer_id is not None:
        q = q.filter(Point.customer_id == customer_id)
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/points/{pid}", summary="点位详情")
def get_point(pid: int, session: Session = Depends(get_db)):
    obj = session.query(Point).get(pid)
    if not obj:
        return {"success": False, "error": "未找到点位"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/suppliers", summary="供应商列表")
def list_suppliers(page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    return {"success": True, "data": paginate(session, session.query(Supplier), page, size)}

@router.get("/suppliers/{sid}", summary="供应商详情")
def get_supplier(sid: int, session: Session = Depends(get_db)):
    obj = session.query(Supplier).get(sid)
    if not obj:
        return {"success": False, "error": "未找到供应商"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/skus", summary="SKU列表")
def list_skus(supplier_id: Optional[int] = None, type_level1: Optional[str] = None, page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    q = session.query(SKU)
    if supplier_id is not None:
        q = q.filter(SKU.supplier_id == supplier_id)
    if type_level1:
        q = q.filter(SKU.type_level1 == type_level1)
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/skus/{sku_id}", summary="SKU详情")
def get_sku(sku_id: int, session: Session = Depends(get_db)):
    obj = session.query(SKU).get(sku_id)
    if not obj:
        return {"success": False, "error": "未找到SKU"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/partners", summary="合作方列表")
def list_partners(page: int = 1, size: int = 50, session: Session = Depends(get_db)):
    return {"success": True, "data": paginate(session, session.query(ExternalPartner), page, size)}

@router.get("/bank-accounts", summary="银行账户列表")
def list_bank_accounts(owner_type: Optional[str] = None, owner_id: Optional[int] = None, session: Session = Depends(get_db)):
    q = session.query(BankAccount)
    if owner_type:
        q = q.filter(BankAccount.owner_type == owner_type)
    if owner_id is not None:
        q = q.filter(BankAccount.owner_id == owner_id)
    return {"success": True, "data": {"items": [row_to_dict(a) for a in q.all()]}}
