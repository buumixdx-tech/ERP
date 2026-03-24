"""
主数据领域 - UI专用查询层

本模块提供主数据相关的UI查询函数，返回格式化字典供UI层直接使用。
遵循CQRS模式，只处理读操作，不涉及写操作。
"""

from typing import List, Dict, Optional, Any
from sqlalchemy import func, String
from models import (
    get_session, ChannelCustomer, Supplier, Point, SKU, ExternalPartner, BankAccount,
    EquipmentInventory, MaterialInventory, SupplyChain, Contract
)
from logic.constants import (
    AccountOwnerType, SKUType, BankInfoKey, OperationalStatus
)


# ============================================================================
# 1. 客户相关查询
# ============================================================================

def get_customers_for_ui(
    status: Optional[str] = None,
    search_keyword: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取客户列表（专用于UI展示）
    """
    session = get_session()
    try:
        query = session.query(ChannelCustomer)

        if search_keyword:
            query = query.filter(
                ChannelCustomer.name.contains(search_keyword) |
                func.cast(ChannelCustomer.id, String).contains(search_keyword)
            )

        customers = query.order_by(ChannelCustomer.created_at.desc()).limit(limit).all()

        result = []
        for customer in customers:
            info = customer.info or {}
            if isinstance(info, str):
                import json
                try: info = json.loads(info)
                except: info = {}
            result.append({
                "id": customer.id,
                "name": customer.name,
                "contact": info.get("contact", ""),
                "phone": info.get("phone", ""),
                "email": info.get("email", ""),
                "address": info.get("address", ""),
                "status": info.get("status", "active"),
                "status_label": _get_status_label(info.get("status")),
                "info": info,
                "created_at": customer.created_at.strftime("%Y-%m-%d") if customer.created_at else ""
            })

        return result
    finally:
        session.close()


def get_customer_by_id(customer_id: int) -> Optional[Dict[str, Any]]:
    """
    根据ID获取客户详情
    """
    session = get_session()
    try:
        customer = session.query(ChannelCustomer).get(customer_id)
        if not customer:
            return None
        return {
            "id": customer.id,
            "name": customer.name,
            "status": customer.status,
            "info": customer.info or {}
        }
    finally:
        session.close()


# ============================================================================
# 2. 供应商相关查询
# ============================================================================

def get_suppliers_for_ui(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """获取供应商列表（专用于UI展示）"""
    session = get_session()
    try:
        query = session.query(Supplier)

        if category:
            query = query.filter(Supplier.category == category)

        suppliers = query.order_by(Supplier.id.desc()).limit(limit).all()

        result = []
        for supplier in suppliers:
            info = supplier.info or {}
            contact_info = info.get("contact_info", {}) if isinstance(info, dict) else {}

            # 获取该供应商的SKU列表
            sku_list = session.query(SKU).filter(SKU.supplier_id == supplier.id).all()
            sku_names = [sku.name for sku in sku_list]

            supply_types = set()
            for sku in sku_list:
                if sku.type_level1 == SKUType.EQUIPMENT:
                    supply_types.add("equipment")
                elif sku.type_level1 == SKUType.MATERIAL:
                    supply_types.add("material")

            result.append({
                "id": supplier.id,
                "name": supplier.name,
                "contact_person": contact_info.get("contact_person", ""),
                "phone": contact_info.get("phone", ""),
                "email": contact_info.get("email", ""),
                "address": supplier.address or "",
                "status": info.get("status", "active") if isinstance(info, dict) else "active",
                "status_label": _get_status_label(info.get("status") if isinstance(info, dict) else None),
                "supply_types": list(supply_types),
                "sku_count": len(sku_list),
                "sku_list": sku_names[:10],
                "created_at": "",
                "category": supplier.category or ""
            })

        return result
    finally:
        session.close()


def get_supplier_by_id(supplier_id: int) -> Optional[Dict[str, Any]]:
    """
    根据ID获取供应商详情
    """
    session = get_session()
    try:
        supplier = session.query(Supplier).get(supplier_id)
        if not supplier:
            return None
        return {
            "id": supplier.id,
            "name": supplier.name,
            "status": supplier.status,
            "contact_info": supplier.contact_info or {}
        }
    finally:
        session.close()


def get_supplier_by_name(name: str, fuzzy: bool = False) -> Optional[Dict[str, Any]]:
    """
    根据名称获取供应商详情
    """
    session = get_session()
    try:
        query = session.query(Supplier)
        if fuzzy:
            supplier = query.filter(Supplier.name.like(f"%{name}%")).first()
        else:
            supplier = query.filter(Supplier.name == name).first()
        if not supplier: return None
        return {"id": supplier.id, "name": supplier.name, "contact_info": supplier.contact_info or {}}
    finally:
        session.close()


# ============================================================================
# 3. 点位相关查询
# ============================================================================

def get_points_for_ui(
    customer_id: Optional[int] = None,
    supplier_id: Optional[int] = None,
    point_type: Optional[str] = None,
    search_keyword: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """获取点位列表（专用于UI展示）"""
    session = get_session()
    try:
        query = session.query(Point)

        if customer_id is not None:
            query = query.filter(Point.customer_id == customer_id)
        if supplier_id is not None:
            query = query.filter(Point.supplier_id == supplier_id)
        if point_type:
            query = query.filter(Point.type == point_type)
        if search_keyword:
            query = query.filter(Point.name.like(f"%{search_keyword}%"))

        points = query.order_by(Point.name).limit(limit).all()

        # 批量预加载，消除 N+1
        customer_ids = list(set(p.customer_id for p in points if p.customer_id))
        supplier_ids = list(set(p.supplier_id for p in points if p.supplier_id))
        customer_map = {c.id: c.name for c in session.query(ChannelCustomer).filter(ChannelCustomer.id.in_(customer_ids)).all()} if customer_ids else {}
        supplier_map = {s.id: s.name for s in session.query(Supplier).filter(Supplier.id.in_(supplier_ids)).all()} if supplier_ids else {}

        result = []
        for point in points:
            result.append({
                "id": point.id,
                "name": point.name,
                "type": point.type or "",
                "address": point.address or "",
                "receiving_address": point.receiving_address or point.address or "",
                "customer_id": point.customer_id,
                "customer_name": customer_map.get(point.customer_id),
                "supplier_id": point.supplier_id,
                "supplier_name": supplier_map.get(point.supplier_id),
                "contact": "",
                "phone": "",
                "status": "active",
                "status_label": "正常",
                "created_at": "",
                "owner_label": (customer_map.get(point.customer_id) if point.customer_id else (supplier_map.get(point.supplier_id) if point.supplier_id else "我方 (自有)"))
            })

        return result
    finally:
        session.close()


def get_point_by_name(name: str, fuzzy: bool = False) -> Optional[Dict[str, Any]]:
    """
    根据名称获取点位详情
    """
    session = get_session()
    try:
        query = session.query(Point)
        if fuzzy:
            point = query.filter(Point.name.like(f"%{name}%")).first()
        else:
            point = query.filter(Point.name == name).first()
        
        if not point: return None
        
        return {
            "id": point.id,
            "name": point.name,
            "type": point.type,
            "address": point.address,
            "customer_id": point.customer_id,
            "supplier_id": point.supplier_id
        }
    finally:
        session.close()


# ============================================================================
# 4. SKU相关查询
# ============================================================================

def get_skus_for_ui(
    supplier_id: Optional[int] = None,
    sku_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 200
) -> List[Dict[str, Any]]:
    """获取SKU列表（专用于UI展示）"""
    session = get_session()
    try:
        query = session.query(SKU)

        if supplier_id:
            query = query.filter(SKU.supplier_id == supplier_id)
        if sku_type:
            query = query.filter(SKU.type_level1 == sku_type)

        skus = query.order_by(SKU.name).limit(limit).all()

        # 批量预加载供应商名称
        sup_ids = list(set(s.supplier_id for s in skus if s.supplier_id))
        supplier_map = {s.id: s.name for s in session.query(Supplier).filter(Supplier.id.in_(sup_ids)).all()} if sup_ids else {}

        result = []
        for sku in skus:
            params = sku.params or {}
            result.append({
                "id": sku.id,
                "name": sku.name,
                "model": sku.model or "",
                "spec": params.get("spec", ""),
                "type_level1": sku.type_level1 or "",
                "type_level2": sku.type_level2 or "",
                "category": sku.type_level2 or "",
                "unit": params.get("unit", "件"),
                "supplier_id": sku.supplier_id,
                "supplier_name": supplier_map.get(sku.supplier_id),
                "status": "active",
                "status_label": "正常",
                "price_info": params.get("price_info", {}),
                "created_at": ""
            })

        return result
    finally:
        session.close()

def get_equipment_inventory_summary() -> Dict[str, Any]:
    """获取设备库存汇总数据"""
    session = get_session()
    try:
        total_count = session.query(func.count(EquipmentInventory.id)).scalar() or 0
        stock_count = session.query(func.count(EquipmentInventory.id)).filter(EquipmentInventory.operational_status == OperationalStatus.STOCK).scalar() or 0
        operating_count = session.query(func.count(EquipmentInventory.id)).filter(EquipmentInventory.operational_status == OperationalStatus.OPERATING).scalar() or 0
        return {
            "total_count": total_count,
            "stock_count": stock_count,
            "operating_count": operating_count
        }
    finally:
        session.close()

def get_material_inventory_summary() -> Dict[str, Any]:
    """获取物料库存汇总数据"""
    session = get_session()
    try:
        total_skus = session.query(func.count(MaterialInventory.id)).filter(MaterialInventory.total_balance > 0).scalar() or 0
        total_quantity = session.query(func.sum(MaterialInventory.total_balance)).scalar() or 0
        return {
            "total_skus": total_skus,
            "total_quantity": total_quantity
        }
    finally:
        session.close()

def get_equipment_inventory_list(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取详情设备库存列表"""
    session = get_session()
    try:
        query = session.query(EquipmentInventory)
        if status:
            query = query.filter(EquipmentInventory.operational_status == status)
        
        equips = query.all()
        result = []
        for eq in equips:
            result.append({
                "设备ID": eq.id,
                "SN序列号": eq.sn,
                "品类ID": eq.sku_id,
                "品类名称": eq.sku.name if eq.sku else "未知",
                "运营状态": eq.operational_status,
                "所在点位": eq.point.name if eq.point else "自有仓"
            })
        return result
    finally:
        session.close()

def get_material_inventory_list() -> List[Dict[str, Any]]:
    """获取物料详情列表"""
    session = get_session()
    try:
        from sqlalchemy.orm import joinedload
        invs = session.query(MaterialInventory).options(joinedload(MaterialInventory.sku)).all()
        return [
            {
                "物料ID": i.sku_id,
                "物料名称": i.sku.name if i.sku else "未知",
                "总余额": i.total_balance,
                "平均单价": i.average_price or 0.0,
                "库存分布": i.stock_distribution or {}
            }
            for i in invs
        ]
    finally:
        session.close()

def get_warehouse_points() -> List[Dict[str, Any]]:
    """获取所有仓库类型的点位"""
    session = get_session()
    try:
        points = session.query(Point).filter(Point.customer_id == None, Point.supplier_id == None).all()
        return [{"id": p.id, "name": p.name, "type": p.type, "address": p.address} for p in points]
    finally:
        session.close()

def get_sku_map_by_names(names: List[str]) -> Dict[str, Any]:
    """获取 SKU 名称到详情的映射"""
    session = get_session()
    try:
        skus = session.query(SKU).filter(SKU.name.in_(names)).all()
        return {s.name: {"id": s.id, "type": s.type_level1} for s in skus}
    finally:
        session.close()


# ============================================================================
# 5. 合作伙伴相关查询
# ============================================================================

def get_external_partner_by_id(partner_id: int) -> Optional[Dict[str, Any]]:
    """
    根据ID获取外部合作伙伴详情
    
    Args:
        partner_id: 合作伙伴ID
    
    Returns:
        合作伙伴详情字典，如果不存在则返回None
    """
    session = get_session()
    try:
        partner = session.query(ExternalPartner).get(partner_id)
        if not partner:
            return None
        
        return {
            "id": partner.id,
            "name": partner.name or "",
            "type": partner.type or "",
            "address": partner.address or "",
            "contact_info": partner.contact_info or {},
            "content": partner.content or "",
            "status": "active",
            "created_at": partner.created_at.strftime("%Y-%m-%d") if partner.created_at else ""
        }
    finally:
        session.close()


def get_partners_for_ui(
    status: Optional[str] = None,
    partner_type: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """获取外部合作伙伴列表（专用于UI展示）"""
    session = get_session()
    try:
        query = session.query(ExternalPartner)

        if partner_type:
            query = query.filter(ExternalPartner.type == partner_type)

        partners = query.order_by(ExternalPartner.id.desc()).limit(limit).all()

        result = []
        for partner in partners:
            result.append({
                "id": partner.id,
                "name": partner.name or "",
                "partner_type": partner.type or "",
                "contact_person": "",
                "phone": "",
                "email": "",
                "address": partner.address or "",
                "status": "active",
                "status_label": "正常",
                "notes": partner.content or "",
                "created_at": ""
            })

        return result
    finally:
        session.close()


# ============================================================================
# 6. 银行账户相关查询（master领域）
# ============================================================================

def get_bank_accounts_for_ui(
    owner_type: Optional[str] = None,
    owner_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取银行账户列表（专用于UI展示）
    
    Args:
        owner_type: 所有者类型过滤
        owner_id: 所有者ID过滤
        status: 状态过滤
        limit: 返回数量限制
    
    Returns:
        格式化后的银行账户列表
    """
    session = get_session()
    try:
        query = session.query(BankAccount)
        
        if owner_type:
            query = query.filter(BankAccount.owner_type == owner_type)
        
        if owner_id:
            query = query.filter(BankAccount.owner_id == owner_id)
        
        # models.py 中 BankAccount 没有 created_at 和 status 字段，使用 id 排序并移除 status
        accounts = query.order_by(BankAccount.id.desc()).limit(limit).all()
        
        # 批量获取所有者名称，消除 N+1
        customer_ids = list(set(a.owner_id for a in accounts if a.owner_type == AccountOwnerType.CUSTOMER))
        supplier_ids = list(set(a.owner_id for a in accounts if a.owner_type == AccountOwnerType.SUPPLIER))
        partner_ids = list(set(a.owner_id for a in accounts if a.owner_type == AccountOwnerType.OTHER))
        
        customer_names = {c.id: c.name for c in session.query(ChannelCustomer).filter(ChannelCustomer.id.in_(customer_ids)).all()} if customer_ids else {}
        supplier_names = {s.id: s.name for s in session.query(Supplier).filter(Supplier.id.in_(supplier_ids)).all()} if supplier_ids else {}
        partner_names = {p.id: p.name for p in session.query(ExternalPartner).filter(ExternalPartner.id.in_(partner_ids)).all()} if partner_ids else {}
        
        result = []
        for acc in accounts:
            info = acc.account_info or {}
            
            # 确定所有者名称
            if acc.owner_type == AccountOwnerType.CUSTOMER:
                owner_name = f"[客户] {customer_names.get(acc.owner_id, '未知')}"
            elif acc.owner_type == AccountOwnerType.SUPPLIER:
                owner_name = f"[供应商] {supplier_names.get(acc.owner_id, '未知')}"
            elif acc.owner_type == AccountOwnerType.OTHER:
                owner_name = f"[合作方] {partner_names.get(acc.owner_id, '未知')}"
            elif acc.owner_type == AccountOwnerType.OURSELVES:
                owner_name = f"[我方] {info.get(BankInfoKey.BANK_NAME, '未知账户')}"
            else:
                owner_name = "未知所有者"
            
            result.append({
                "id": acc.id,
                "bank_name": info.get(BankInfoKey.BANK_NAME, '未知银行'),
                "account_no": info.get(BankInfoKey.ACCOUNT_NO, ''),
                "account_type": info.get(BankInfoKey.ACCOUNT_TYPE, '对公账户'),
                "holder_name": info.get(BankInfoKey.HOLDER_NAME, ''),
                "owner_type": acc.owner_type,
                "owner_id": acc.owner_id,
                "owner_name": owner_name,
                "owner_label": owner_name,
                "balance": info.get('balance', 0),
                "balance_formatted": f"¥{info.get('balance', 0):,.2f}",
                "is_default": acc.is_default,
                "created_at": ""
            })
        
        return result
    finally:
        session.close()


# ============================================================================
# 7. 库存相关查询 (用于库存拨付等场景)
# ============================================================================

def get_stock_equipment_for_allocation(
    operational_status: Optional[str] = None,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    获取可用于库存拨付的设备列表
    
    Args:
        operational_status: 运营状态过滤，默认为 STOCK（库存中）
        limit: 返回数量限制
    
    Returns:
        格式化的设备列表，包含SKU信息、点位信息
    """
    session = get_session()
    try:
        status_filter = operational_status or OperationalStatus.STOCK
        
        equipments = session.query(EquipmentInventory).filter(
            EquipmentInventory.operational_status == status_filter
        ).limit(limit).all()
        
        result = []
        for eq in equipments:
            sku = session.query(SKU).get(eq.sku_id) if eq.sku_id else None
            point = session.query(Point).get(eq.point_id) if eq.point_id else None
            
            result.append({
                "id": eq.id,
                "sn": eq.sn or "",
                "sku_id": eq.sku_id,
                "sku_name": sku.name if sku else "未知品类",
                "sku_model": sku.model if sku else "",
                "operational_status": eq.operational_status,
                "device_status": eq.device_status,
                "point_id": eq.point_id,
                "point_name": point.name if point else "库存中",
                "warehouse_name": point.name if point else "自有仓",
                "deposit_amount": eq.deposit_amount or 0.0,
            })
        
        return result
    finally:
        session.close()


def get_material_stock_for_supply(
    min_balance: float = 0.01,
    limit: int = 500
) -> List[Dict[str, Any]]:
    """
    获取可用于物料供应的库存物料列表
    
    Args:
        min_balance: 最小库存余额过滤
        limit: 返回数量限制
    
    Returns:
        格式化的物料库存列表，包含可供应数量、仓库分布
    """
    session = get_session()
    try:
        materials = session.query(MaterialInventory).filter(
            MaterialInventory.total_balance >= min_balance
        ).limit(limit).all()
        
        result = []
        for mat in materials:
            sku = session.query(SKU).get(mat.sku_id) if mat.sku_id else None
            
            # 解析库存分布，获取有库存的仓库
            stock_dist = mat.stock_distribution or {}
            available_warehouses = [
                {"warehouse": wh, "qty": qty}
                for wh, qty in stock_dist.items() if qty > 0
            ]
            
            result.append({
                "id": mat.id,
                "sku_id": mat.sku_id,
                "sku_name": sku.name if sku else "未知物料",
                "sku_model": sku.model if sku else "",
                "sku_unit": sku.unit if sku else "件",
                "total_balance": mat.total_balance,
                "average_price": mat.average_price or 0.0,
                "stock_distribution": stock_dist,
                "available_warehouses": available_warehouses,
            })
        
        return result
    finally:
        session.close()




# ============================================================================
# 8. 私有辅助函数
# ============================================================================

def _get_status_label(status: Optional[str]) -> str:
    """获取状态中文标签"""
    status_map = {
        "active": "正常",
        "inactive": "停用",
        "frozen": "冻结",
        "pending": "待审核",
        "verified": "已认证",
    }
    return status_map.get(status, status or "未知")


def _get_bank_account_owner_name(session, account) -> str:
    """获取银行账户所有者名称"""
    owner_type = account.owner_type
    owner_id = account.owner_id
    
    if owner_type == AccountOwnerType.CUSTOMER:
        obj = session.query(ChannelCustomer).get(owner_id)
        return f"[客户] {obj.name}" if obj else "[客户] 未知"
    elif owner_type == AccountOwnerType.SUPPLIER:
        obj = session.query(Supplier).get(owner_id)
        return f"[供应商] {obj.name}" if obj else "[供应商] 未知"
    elif owner_type == AccountOwnerType.OURSELVES:
        return "[我方] 闪饮业务中心"
    else:
        return "[未知]"


def get_points_by_customer(customer_id: int) -> List[Dict[str, Any]]:
    """获取指定客户的所有点位"""
    session = get_session()
    try:
        points = session.query(Point).filter(Point.customer_id == customer_id).all()
        return [{"id": p.id, "name": p.name, "address": p.address} for p in points]
    finally:
        session.close()

def get_skus_by_names(sku_names: List[str], supplier_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """获取指定名称列表的 SKU"""
    session = get_session()
    try:
        query = session.query(SKU).filter(SKU.name.in_(sku_names))
        if supplier_id:
            query = query.filter(SKU.supplier_id == supplier_id)
        skus = query.all()
        return [{"id": s.id, "name": s.name, "supplier_id": s.supplier_id} for s in skus]
    finally:
        session.close()

def get_material_inventory_all() -> List[Dict[str, Any]]:
    """获取所有物料库存信息"""
    session = get_session()
    try:
        from sqlalchemy.orm import joinedload
        invs = session.query(MaterialInventory).options(joinedload(MaterialInventory.sku)).all()
        return [
            {
                "sku_id": i.sku_id,
                "sku_name": i.sku.name if i.sku else "未知",
                "total_balance": i.total_balance,
                "stock_distribution": i.stock_distribution or {}
            }
            for i in invs
        ]
    finally:
        session.close()

def get_supply_chains_by_type(sku_type: str) -> List[Dict[str, Any]]:
    """获取指定类型的供应链协议"""
    session = get_session()
    try:
        chains = session.query(SupplyChain).filter(SupplyChain.type == sku_type).all()
        return [
            {
                "id": c.id,
                "supplier_id": c.supplier_id,
                "supplier_name": c.supplier_name,
                "type": c.type,
                "payment_terms": c.payment_terms
            }
            for c in chains
        ]
    finally:
        session.close()

def get_supply_chain_by_id(sc_id: int) -> Optional[Dict[str, Any]]:
    """获取供应链详情"""
    session = get_session()
    try:
        from sqlalchemy.orm import joinedload
        c = session.query(SupplyChain).options(joinedload(SupplyChain.supplier)).get(sc_id)
        if not c: return None
        return {
            "id": c.id,
            "supplier_id": c.supplier_id,
            "supplier_name": c.supplier_name,
            "type": c.type,
            "payment_terms": c.payment_terms,
            "pricing_dict": c.get_pricing_dict(),
            "supplier": {"name": c.supplier.name} if c.supplier else None
        }
    finally:
        session.close()


def get_point_by_id(point_id: int) -> Optional[Dict[str, Any]]:
    """
    根据ID获取点位详情
    """
    session = get_session()
    try:
        point = session.query(Point).get(point_id)
        if not point:
            return None
        
        return {
            "id": point.id,
            "name": point.name or "",
            "type": point.type or "",
            "address": point.address or "",
            "receiving_address": point.receiving_address or point.address or "",
            "customer_id": point.customer_id,
            "supplier_id": point.supplier_id
        }
    finally:
        session.close()

def get_partner_by_id(partner_id: int) -> Optional[Dict[str, Any]]:
    """获取合作方详情"""
    session = get_session()
    try:
        p = session.query(ExternalPartner).get(partner_id)
        if not p: return None
        return {"id": p.id, "name": p.name, "type": p.type}
    finally:
        session.close()

def get_bank_account_by_id(account_id: int) -> Optional[Dict[str, Any]]:
    """获取银行账户详情"""
    session = get_session()
    try:
        acc = session.query(BankAccount).get(account_id)
        if not acc: return None
        info = acc.account_info or {}
        return {
            "id": acc.id,
            "owner_type": acc.owner_type,
            "owner_id": acc.owner_id,
            "bank_name": info.get(BankInfoKey.BANK_NAME, ""),
            "account_no": info.get(BankInfoKey.ACCOUNT_NO, ""),
            "is_default": acc.is_default
        }
    finally:
        session.close()

def get_contract_detail(contract_id: int) -> Optional[Dict[str, Any]]:
    """
    根据ID获取合同详情
    
    Args:
        contract_id: 合同ID
    
    Returns:
        合同详情字典，如果不存在则返回None
    """
    session = get_session()
    try:
        contract = session.query(Contract).get(contract_id)
        if not contract:
            return None
        
        return {
            "id": contract.id,
            "contract_number": contract.contract_number or "",
            "type": contract.type or "",
            "status": contract.status or "",
            "parties": contract.parties or {},
            "content": contract.content or {},
            "signed_date": contract.signed_date.strftime("%Y-%m-%d") if contract.signed_date else None,
            "effective_date": contract.effective_date.strftime("%Y-%m-%d") if contract.effective_date else None,
            "expiry_date": contract.expiry_date.strftime("%Y-%m-%d") if contract.expiry_date else None,
            "timestamp": contract.timestamp.strftime("%Y-%m-%d") if contract.timestamp else None
        }
    finally:
        session.close()


def get_system_constants() -> Dict[str, Any]:
    """
    获取全局系统常量速查表
    包含所有业务状态、类型定义及枚举地图
    """
    from logic.constants import VCType, VCStatus, SubjectStatus, CashStatus, BusinessStatus, SKUType, CounterpartType
    return {
        "虚拟合同类型 (VCType)": {k: v for k, v in VCType.__dict__.items() if not k.startswith("__")},
        "虚拟合同状态 (VCStatus)": {k: v for k, v in VCStatus.__dict__.items() if not k.startswith("__")},
        "执行阶段状态 (SubjectStatus)": {k: v for k, v in SubjectStatus.__dict__.items() if not k.startswith("__")},
        "资金流阶段状态 (CashStatus)": {k: v for k, v in CashStatus.__dict__.items() if not k.startswith("__")},
        "业务项目状态 (BusinessStatus)": {k: v for k, v in BusinessStatus.__dict__.items() if not k.startswith("__")},
        "货品/一级分类 (SKUType)": {k: v for k, v in SKUType.__dict__.items() if not k.startswith("__")},
        "交易对手类型 (CounterpartType)": {k: v for k, v in CounterpartType.__dict__.items() if not k.startswith("__")}
    }




