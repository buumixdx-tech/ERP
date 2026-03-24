"""
供应链领域 - UI专用查询层

本模块提供供应链相关的UI查询函数，返回格式化字典供UI层直接使用。
遵循CQRS模式，只处理读操作，不涉及写操作。
"""

from typing import List, Dict, Optional, Any
from sqlalchemy import func, cast, String
from models import (
    get_session, SupplyChain, Supplier
)
from logic.constants import (
    SKUType
)


# ============================================================================
# 1. 供应链协议相关查询
# ============================================================================

def get_supply_chain_with_pricing(
    session,
    sc_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    获取带有定价信息的供应链协议列表（专用于UI采购表单）
    
    Args:
        session: 数据库会话
        sc_type: 协议类型过滤（equipment/material）
    
    Returns:
        格式化后的供应链协议列表，包含定价详情
    """
    query = session.query(SupplyChain).join(Supplier)
    
    if sc_type:
        query = query.filter(SupplyChain.type == sc_type)
    
    chains = query.order_by(SupplyChain.id.desc()).all()
    
    result = []
    for chain in chains:
        supplier = session.query(Supplier).get(chain.supplier_id)
        
        # 解析定价配置
        pricing_dict = {}
        if chain.pricing_config:
            import json
            try:
                if isinstance(chain.pricing_config, str):
                    pricing_dict = json.loads(chain.pricing_config)
                else:
                    pricing_dict = chain.pricing_config
            except:
                pricing_dict = {}
        
        result.append({
            "id": chain.id,
            "supplier_id": chain.supplier_id,
            "supplier_name": supplier.name if supplier else "未知供应商",
            "supplier": {"name": supplier.name} if supplier else None,
            "type": chain.type,
            "pricing_dict": pricing_dict,
            "payment_terms": chain.payment_terms or {},
            "contract_id": chain.contract_id
        })
    
    return result


def get_supply_chains_for_ui(
    session_arg=None,
    supplier_id: Optional[int] = None,
    sc_type: Optional[str] = None,
    status: Optional[str] = None,
    search_keyword: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    获取供应链协议列表（专用于UI展示）
    
    Args:
        session_arg: 可选的数据库会话，如果不传则自动创建
        supplier_id: 供应商ID过滤
        sc_type: 协议类型过滤（equipment/material）
        status: 状态过滤
        search_keyword: 搜索关键词（协议ID、供应商名称）
        limit: 返回数量限制
    
    Returns:
        格式化后的供应链协议列表
    """
    own_session = False
    if session_arg is None:
        session = get_session()
        own_session = True
    else:
        session = session_arg
    try:
        query = session.query(SupplyChain).join(Supplier)
        
        if supplier_id:
            query = query.filter(SupplyChain.supplier_id == supplier_id)
        
        if sc_type:
            query = query.filter(SupplyChain.type == sc_type)
        
        
        if search_keyword:
            query = query.filter(
                (SupplyChain.id.cast(String).contains(search_keyword)) |
                (Supplier.name.contains(search_keyword))
            )
        
        chains = query.order_by(SupplyChain.id.desc()).limit(limit).all()
        
        result = []
        for chain in chains:
            supplier = session.query(Supplier).get(chain.supplier_id)
            
            # 解析定价配置
            pricing_dict = chain.get_pricing_dict() if hasattr(chain, 'get_pricing_dict') else (chain.pricing_config or {})
            
            # 解析结算条款
            payment_terms = chain.payment_terms or {}
            
            # 统计SKU数量
            sku_count = len(pricing_dict)
            
            result.append({
                "id": chain.id,
                "supplier_id": chain.supplier_id,
                "supplier_name": supplier.name if supplier else "未知供应商",
                "supplier": {"name": supplier.name} if supplier else None,
                "type": chain.type,
                "type_label": _get_sc_type_label(chain.type),
                "status": "active",
                "status_label": "正常",
                "pricing_count": sku_count,
                "pricing_preview": list(pricing_dict.keys())[:5],  # 只显示前5个
                "payment_terms": {
                    "prepayment_ratio": payment_terms.get("prepayment_ratio", 0),
                    "prepayment_ratio_pct": int(payment_terms.get("prepayment_ratio", 0) * 100),
                    "balance_period": payment_terms.get("balance_period", 0),
                    "day_rule": payment_terms.get("day_rule", "自然日"),
                    "start_trigger": payment_terms.get("start_trigger", "入库")
                },
                "contract_id": chain.contract_id,
                "created_at": "",
                "updated_at": ""
            })
        
        return result
    finally:
        if own_session:
            session.close()


def get_supply_chain_detail_for_ui(sc_id: int) -> Optional[Dict[str, Any]]:
    """
    获取供应链协议详情（专用于UI展示）
    
    Args:
        sc_id: 供应链协议ID
    
    Returns:
        格式化后的供应链协议详情，如果不存在则返回None
    """
    session = get_session()
    try:
        chain = session.query(SupplyChain).get(sc_id)
        if not chain:
            return None
        
        supplier = session.query(Supplier).get(chain.supplier_id)
        
        # 解析定价配置
        pricing_dict = chain.get_pricing_dict() if hasattr(chain, 'get_pricing_dict') else (chain.pricing_config or {})
        
        # 格式化定价明细
        pricing_details = []
        for sku_name, price in pricing_dict.items():
            pricing_details.append({
                "sku_name": sku_name,
                "price": price if isinstance(price, (int, float)) else 0,
                "price_display": f"¥{price:,.2f}" if isinstance(price, (int, float)) else str(price),
                "is_floating": price == "浮动" if isinstance(price, str) else False
            })
        
        # 解析结算条款
        payment_terms = chain.payment_terms or {}
        
        return {
            "id": chain.id,
            "supplier_id": chain.supplier_id,
            "supplier_name": supplier.name if supplier else "未知供应商",
            "supplier": {"name": supplier.name} if supplier else None,
            "supplier_contact": supplier.info if supplier else {},
            "type": chain.type,
            "type_label": _get_sc_type_label(chain.type),
            "status": "active",
            "status_label": "正常",
            "pricing_config": chain.pricing_config or {},
            "pricing_details": pricing_details,
            "pricing_count": len(pricing_details),
            "payment_terms": {
                "prepayment_ratio": payment_terms.get("prepayment_ratio", 0),
                "prepayment_ratio_pct": int(payment_terms.get("prepayment_ratio", 0) * 100),
                "balance_period": payment_terms.get("balance_period", 0),
                "day_rule": payment_terms.get("day_rule", "自然日"),
                "start_trigger": payment_terms.get("start_trigger", "入库")
            },
            "contract_id": chain.contract_id,
            "notes": "",
            "created_at": "",
            "updated_at": ""
        }
    finally:
        session.close()


# ============================================================================
# 3. 私有辅助函数
# ============================================================================

def _get_status_label(status: Optional[str]) -> str:
    """获取状态中文标签"""
    status_map = {
        "active": "正常",
        "inactive": "停用",
        "pending": "待审核",
        "verified": "已认证",
    }
    return status_map.get(status, status or "未知")


def _get_sc_type_label(sc_type: Optional[str]) -> str:
    """获取供应链类型中文标签"""
    type_map = {
        SKUType.EQUIPMENT: "设备",
        SKUType.MATERIAL: "物料",
        "equipment": "设备",
        "material": "物料",
    }
    return type_map.get(sc_type, sc_type or "未知")
