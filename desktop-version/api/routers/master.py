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
    create_bank_account_action, update_bank_accounts_action, delete_bank_accounts_action,
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

@router.post("/delete-bank-accounts", summary="批量删除银行账户")
def delete_bank_accounts(payloads: List[DeleteMasterDataSchema], session: Session = Depends(get_db)):
    return delete_bank_accounts_action(session, payloads).model_dump()


# ==================== 查询端点 ====================

@router.get("/customers", summary="客户列表")
def list_customers(
    ids: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """客户列表查询 - ids: 多值查询，search: 名称模糊搜索"""
    q = session.query(ChannelCustomer)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(ChannelCustomer.id.in_(id_list))
    if search:
        q = q.filter(ChannelCustomer.name.ilike(f"%{search}%"))
    q = q.order_by(ChannelCustomer.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/customers/suggest", summary="客户名称自动补全")
def suggest_customers(
    q: str,
    limit: int = 10,
    session: Session = Depends(get_db)
):
    """客户名称自动补全
    - q: 搜索关键字（至少1个字符）
    - limit: 返回数量，默认10
    """
    if not q or len(q) < 1:
        return {"success": True, "data": {"suggestions": []}}

    customers = session.query(ChannelCustomer).filter(
        ChannelCustomer.name.ilike(f"%{q}%")
    ).order_by(ChannelCustomer.id.desc()).limit(limit).all()

    return {
        "success": True,
        "data": {
            "suggestions": [{"id": c.id, "name": c.name} for c in customers]
        }
    }

@router.get("/customers/{cid}", summary="客户详情")
def get_customer(cid: int, session: Session = Depends(get_db)):
    obj = session.query(ChannelCustomer).get(cid)
    if not obj:
        return {"success": False, "error": "未找到客户"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/points", summary="点位列表")
def list_points(
    ids: Optional[str] = None,
    customer_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """点位列表查询 - ids: 多值查询，supplier_id: 供应商ID筛选，search: 名称模糊搜索"""
    q = session.query(Point)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(Point.id.in_(id_list))
    if customer_id is not None:
        q = q.filter(Point.customer_id == customer_id)
    if supplier_id is not None:
        q = q.filter(Point.supplier_id == supplier_id)
    if type:
        q = q.filter(Point.type == type)
    if search:
        q = q.filter(
            (Point.name.ilike(f"%{search}%")) | (Point.address.ilike(f"%{search}%"))
        )
    q = q.order_by(Point.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/points/suggest", summary="点位名称自动补全")
def suggest_points(
    q: str,
    limit: int = 10,
    session: Session = Depends(get_db)
):
    """点位名称自动补全
    - q: 搜索关键字（至少1个字符）
    - limit: 返回数量，默认10
    """
    if not q or len(q) < 1:
        return {"success": True, "data": {"suggestions": []}}

    points = session.query(Point).filter(
        Point.name.ilike(f"%{q}%")
    ).order_by(Point.id.desc()).limit(limit).all()

    return {
        "success": True,
        "data": {
            "suggestions": [{"id": p.id, "name": p.name, "type": p.type} for p in points]
        }
    }

@router.get("/points/{pid}", summary="点位详情")
def get_point(pid: int, session: Session = Depends(get_db)):
    obj = session.query(Point).get(pid)
    if not obj:
        return {"success": False, "error": "未找到点位"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/suppliers", summary="供应商列表")
def list_suppliers(
    ids: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """供应商列表查询 - ids: 多值查询，category: 类型筛选，search: 名称模糊搜索"""
    q = session.query(Supplier)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(Supplier.id.in_(id_list))
    if category:
        q = q.filter(Supplier.category == category)
    if search:
        q = q.filter(
            (Supplier.name.ilike(f"%{search}%")) | (Supplier.address.ilike(f"%{search}%"))
        )
    q = q.order_by(Supplier.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/suppliers/suggest", summary="供应商名称自动补全")
def suggest_suppliers(
    q: str,
    category: Optional[str] = None,
    limit: int = 10,
    session: Session = Depends(get_db)
):
    """供应商名称自动补全
    - q: 搜索关键字（至少1个字符）
    - category: 可选，按类型过滤（设备/物料/兼备）
    - limit: 返回数量，默认10
    """
    if not q or len(q) < 1:
        return {"success": True, "data": {"suggestions": []}}

    suppliers = session.query(Supplier).filter(
        (Supplier.name.ilike(f"%{q}%")) | (Supplier.address.ilike(f"%{q}%"))
    )
    if category:
        suppliers = suppliers.filter(Supplier.category == category)

    suppliers = suppliers.order_by(Supplier.id.desc()).limit(limit).all()

    return {
        "success": True,
        "data": {
            "suggestions": [{"id": s.id, "name": s.name, "category": s.category} for s in suppliers]
        }
    }

@router.get("/suppliers/{sid}", summary="供应商详情")
def get_supplier(sid: int, session: Session = Depends(get_db)):
    obj = session.query(Supplier).get(sid)
    if not obj:
        return {"success": False, "error": "未找到供应商"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/skus", summary="SKU列表")
def list_skus(
    ids: Optional[str] = None,
    supplier_id: Optional[int] = None,
    type_level1: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """SKU列表查询 - ids: 多值查询，search: 名称模糊搜索"""
    q = session.query(SKU)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(SKU.id.in_(id_list))
    if supplier_id is not None:
        q = q.filter(SKU.supplier_id == supplier_id)
    if type_level1:
        q = q.filter(SKU.type_level1 == type_level1)
    if search:
        q = q.filter(SKU.name.ilike(f"%{search}%"))
    q = q.order_by(SKU.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/skus/suggest", summary="SKU名称自动补全")
def suggest_skus(
    q: str,
    type_level1: Optional[str] = None,
    limit: int = 10,
    session: Session = Depends(get_db)
):
    """SKU名称自动补全
    - q: 搜索关键字（至少1个字符）
    - type_level1: 可选，按类型过滤（设备/物料）
    - limit: 返回数量，默认10
    """
    if not q or len(q) < 1:
        return {"success": True, "data": {"suggestions": []}}

    skus = session.query(SKU).filter(
        SKU.name.ilike(f"%{q}%")
    )
    if type_level1:
        skus = skus.filter(SKU.type_level1 == type_level1)

    skus = skus.order_by(SKU.id.desc()).limit(limit).all()

    return {
        "success": True,
        "data": {
            "suggestions": [{"id": s.id, "name": s.name, "type_level1": s.type_level1} for s in skus]
        }
    }

@router.get("/skus/{sku_id}", summary="SKU详情")
def get_sku(sku_id: int, session: Session = Depends(get_db)):
    obj = session.query(SKU).get(sku_id)
    if not obj:
        return {"success": False, "error": "未找到SKU"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/partners", summary="合作方列表")
def list_partners(
    ids: Optional[str] = None,
    type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """合作方列表查询 - ids: 多值查询，type: 类型筛选，search: 名称模糊搜索"""
    q = session.query(ExternalPartner)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(ExternalPartner.id.in_(id_list))
    if type:
        q = q.filter(ExternalPartner.type == type)
    if search:
        q = q.filter(
            (ExternalPartner.name.ilike(f"%{search}%")) | (ExternalPartner.address.ilike(f"%{search}%"))
        )
    q = q.order_by(ExternalPartner.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/partners/suggest", summary="合作方名称自动补全")
def suggest_partners(
    q: str,
    type: Optional[str] = None,
    limit: int = 10,
    session: Session = Depends(get_db)
):
    """合作方名称自动补全
    - q: 搜索关键字（至少1个字符）
    - type: 可选，按类型过滤
    - limit: 返回数量，默认10
    """
    if not q or len(q) < 1:
        return {"success": True, "data": {"suggestions": []}}

    partners = session.query(ExternalPartner).filter(
        (ExternalPartner.name.ilike(f"%{q}%")) | (ExternalPartner.address.ilike(f"%{q}%"))
    )
    if type:
        partners = partners.filter(ExternalPartner.type == type)

    partners = partners.order_by(ExternalPartner.id.desc()).limit(limit).all()

    return {
        "success": True,
        "data": {
            "suggestions": [{"id": p.id, "name": p.name, "type": p.type} for p in partners]
        }
    }

@router.get("/partners/{pid}", summary="合作方详情")
def get_partner(pid: int, session: Session = Depends(get_db)):
    obj = session.query(ExternalPartner).get(pid)
    if not obj:
        return {"success": False, "error": "未找到合作方"}
    return {"success": True, "data": row_to_dict(obj)}

@router.get("/bank-accounts", summary="银行账户列表")
def list_bank_accounts(
    ids: Optional[str] = None,
    owner_type: Optional[str] = None,
    owner_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """银行账户列表查询 - ids: 多值查询，search: 模糊搜索"""
    q = session.query(BankAccount)
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(BankAccount.id.in_(id_list))
    if owner_type:
        q = q.filter(BankAccount.owner_type == owner_type)
        if owner_type != 'ourselves' and owner_id is not None:
            q = q.filter(BankAccount.owner_id == owner_id)
    elif owner_id is not None:
        q = q.filter(BankAccount.owner_id == owner_id)
    if search:
        q = q.filter(BankAccount.account_info.ilike(f"%{search}%"))
    q = q.order_by(BankAccount.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/bank-accounts/suggest", summary="银行账户自动补全")
def suggest_bank_accounts(
    q: str,
    owner_type: Optional[str] = None,
    owner_id: Optional[int] = None,
    limit: int = 10,
    session: Session = Depends(get_db)
):
    """银行账户自动补全
    - q: 搜索关键字（至少1个字符）
    - owner_type: 可选，按账户所有者类型过滤
    - owner_id: 可选，按账户所有者ID过滤
    - limit: 返回数量，默认10
    """
    if not q or len(q) < 1:
        return {"success": True, "data": {"suggestions": []}}

    accounts = session.query(BankAccount).filter(
        BankAccount.account_info.ilike(f"%{q}%")
    )
    if owner_type:
        accounts = accounts.filter(BankAccount.owner_type == owner_type)
    if owner_id is not None:
        accounts = accounts.filter(BankAccount.owner_id == owner_id)

    accounts = accounts.order_by(BankAccount.id.desc()).limit(limit).all()

    return {
        "success": True,
        "data": {
            "suggestions": [
                {"id": a.id, "account_info": a.account_info, "owner_type": a.owner_type, "owner_id": a.owner_id}
                for a in accounts
            ]
        }
    }

@router.get("/bank-accounts/{account_id}", summary="银行账户详情")
def get_bank_account(account_id: int, session: Session = Depends(get_db)):
    obj = session.query(BankAccount).get(account_id)
    if not obj:
        return {"success": False, "error": "未找到银行账户"}
    return {"success": True, "data": row_to_dict(obj)}
