from typing import List, Dict, Optional, Any
from models import get_session, VirtualContract, Business, ChannelCustomer, TimeRule, VirtualContractStatusLog, CashFlow
from logic.constants import VCType, VCStatus, TimeRuleRelatedType

def get_vc_list(
    business_id: Optional[int] = None,
    vc_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """获取虚拟合同列表"""
    session = get_session()
    try:
        query = session.query(VirtualContract)
        if business_id:
            query = query.filter(VirtualContract.business_id == business_id)
        if vc_type:
            query = query.filter(VirtualContract.type == vc_type)
        if status:
            query = query.filter(VirtualContract.status == status)

        contracts = query.order_by(VirtualContract.status_timestamp.desc()).limit(limit).all()

        # 批量预加载 business 和 customer，消除 N+1
        biz_ids = list(set(vc.business_id for vc in contracts if vc.business_id))
        biz_map = {b.id: b for b in session.query(Business).filter(Business.id.in_(biz_ids)).all()} if biz_ids else {}
        cust_ids = list(set(b.customer_id for b in biz_map.values() if b.customer_id))
        cust_map = {c.id: c for c in session.query(ChannelCustomer).filter(ChannelCustomer.id.in_(cust_ids)).all()} if cust_ids else {}

        result = []
        for vc in contracts:
            biz = biz_map.get(vc.business_id)
            customer = cust_map.get(biz.customer_id) if biz else None
            result.append({
                "id": vc.id,
                "type": vc.type,
                "type_label": _get_vc_type_label(vc.type),
                "status": vc.status,
                "status_label": _get_vc_status_label(vc.status),
                "customer_name": customer.name if customer else "未知",
                "total_amount": vc.elements.get("total_amount", 0) if vc.elements else 0,
                "created_at": vc.status_timestamp.strftime("%Y-%m-%d") if vc.status_timestamp else ""
            })
        return result
    finally:
        session.close()

def get_vc_detail(vc_id: int) -> Optional[Dict[str, Any]]:
    """获取虚拟合同详情"""
    session = get_session()
    try:
        vc = session.query(VirtualContract).get(vc_id)
        if not vc: return None
        return {
            "id": vc.id,
            "type": vc.type,
            "status": vc.status,
            "subject_status": vc.subject_status,
            "cash_status": vc.cash_status,
            "elements": vc.elements,
            "deposit_info": vc.deposit_info,
            "description": vc.description,
            "business_id": vc.business_id,
            "supply_chain_id": vc.supply_chain_id,
            "related_vc_id": vc.related_vc_id
        }
    finally:
        session.close()

def get_time_rules_for_vc(vc_id: int) -> List[Dict[str, Any]]:
    """获取虚拟合同关联的时间规则"""
    session = get_session()
    try:
        from logic.constants import TimeRuleStatus
        rules = session.query(TimeRule).filter(
            TimeRule.related_id == vc_id,
            TimeRule.related_type == TimeRuleRelatedType.VIRTUAL_CONTRACT,
            TimeRule.status != TimeRuleStatus.INACTIVE
        ).all()
        return [
            {
                "id": r.id,
                "party": r.party,
                "trigger_event": r.trigger_event,
                "target_event": r.target_event,
                "offset": r.offset,
                "unit": r.unit,
                "direction": r.direction,
                "status": r.status,
                "flag_time": r.flag_time.strftime("%Y-%m-%d %H:%M") if r.flag_time else None
            }
            for r in rules
        ]
    finally:
        session.close()

def _get_vc_type_label(vc_type: str) -> str:
    """获取虚拟合同类型的中文标签"""
    type_map = {
        VCType.EQUIPMENT_PROCUREMENT: "设备采购",
        VCType.STOCK_PROCUREMENT: "设备采购(库存)",
        VCType.INVENTORY_ALLOCATION: "库存拨付",
        VCType.MATERIAL_PROCUREMENT: "物料采购",
        VCType.MATERIAL_SUPPLY: "物料供应",
        VCType.RETURN: "退货",
    }
    return type_map.get(vc_type, vc_type)


def get_vc_status_logs(vc_id: int) -> List[Dict[str, Any]]:
    """获取虚拟合同的状态变更日志"""
    session = get_session()
    try:
        logs = session.query(VirtualContractStatusLog).filter(
            VirtualContractStatusLog.vc_id == vc_id
        ).order_by(VirtualContractStatusLog.timestamp.asc()).all()
        return [
            {
                "category": l.category,
                "status_name": l.status_name,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M")
            }
            for l in logs
        ]
    finally:
        session.close()

def get_vc_cash_flows(vc_id: int) -> List[Dict[str, Any]]:
    """获取虚拟合同关联的资金流水"""
    session = get_session()
    try:
        cfs = session.query(CashFlow).filter(
            CashFlow.virtual_contract_id == vc_id
        ).order_by(CashFlow.transaction_date.desc()).all()
        return [
            {
                "date": cf.transaction_date.strftime("%Y-%m-%d") if cf.transaction_date else "未知",
                "type": cf.type,
                "amount": cf.amount,
                "description": cf.description
            }
            for cf in cfs
        ]
    finally:
        session.close()

def _get_vc_status_label(status: str) -> str:
    """获取虚拟合同状态的中文标签"""
    status_map = {
        VCStatus.EXE: "执行",
        VCStatus.FINISH: "完成",
        VCStatus.TERMINATED: "终止",
        VCStatus.CANCELLED: "取消",
    }
    return status_map.get(status, status)


def get_virtual_contracts_for_return(
    vc_types: List[str],
    statuses: List[str],
    subject_statuses: List[str]
) -> List[Dict[str, Any]]:
    """获取可退货的虚拟合同列表"""
    session = get_session()
    try:
        contracts = session.query(VirtualContract).filter(
            VirtualContract.type.in_(vc_types),
            VirtualContract.status.in_(statuses),
            VirtualContract.subject_status.in_(subject_statuses)
        ).all()

        return [
            {
                "id": c.id,
                "type": c.type,
                "status": c.status,
                "subject_status": c.subject_status,
                "cash_status": c.cash_status,
                "description": c.description,
                "elements": c.elements,
                "business_id": c.business_id,
                "supply_chain_id": c.supply_chain_id,
                "created_at": c.status_timestamp.strftime("%Y-%m-%d %H:%M") if c.status_timestamp else ""
            }
            for c in contracts
        ]
    finally:
        session.close()


def get_vc_detail_with_logs(vc_id: int) -> Optional[Dict[str, Any]]:
    """获取虚拟合同详情（包含日志）"""
    session = get_session()
    try:
        vc = session.query(VirtualContract).get(vc_id)
        if not vc:
            return None

        logs = session.query(VirtualContractStatusLog).filter(
            VirtualContractStatusLog.vc_id == vc_id
        ).order_by(VirtualContractStatusLog.timestamp.asc()).all()

        return {
            "vc": {
                "id": vc.id,
                "type": vc.type,
                "status": vc.status,
                "subject_status": vc.subject_status,
                "cash_status": vc.cash_status,
                "description": vc.description,
                "elements": vc.elements,
                "deposit_info": vc.deposit_info
            },
            "logs": [
                {
                    "id": l.id,
                    "vc_id": l.vc_id,
                    "category": l.category,
                    "status_name": l.status_name,
                    "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M") if l.timestamp else ""
                }
                for l in logs
            ]
        }
    finally:
        session.close()


def get_vc_list_for_overview(
    status_list: Optional[List[str]] = None,
    subject_status_list: Optional[List[str]] = None,
    cash_status_list: Optional[List[str]] = None,
    type_list: Optional[List[str]] = None,
    exclude_subject_status: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """获取虚拟合同列表（用于合同概览）"""
    session = get_session()
    try:
        query = session.query(VirtualContract)

        if status_list:
            query = query.filter(VirtualContract.status.in_(status_list))
        if subject_status_list:
            query = query.filter(VirtualContract.subject_status.in_(subject_status_list))
        if cash_status_list:
            query = query.filter(VirtualContract.cash_status.in_(cash_status_list))
        if type_list:
            query = query.filter(VirtualContract.type.in_(type_list))
        if exclude_subject_status:
            query = query.filter(VirtualContract.subject_status.notin_(exclude_subject_status))

        contracts = query.order_by(VirtualContract.id.desc()).all()
        return [
            {
                "id": c.id,
                "type": c.type,
                "status": c.status,
                "subject_status": c.subject_status,
                "cash_status": c.cash_status,
                "description": c.description,
                "elements": c.elements,
                "business_id": c.business_id,
                "created_at": c.status_timestamp.strftime("%Y-%m-%d %H:%M") if c.status_timestamp else ""
            }
            for c in contracts
        ]
    finally:
        session.close()


def get_returnable_vcs(
    vc_types: List[str],
    statuses: List[str],
    subject_statuses: List[str]
) -> List[Dict[str, Any]]:
    """获取可退货的虚拟合同列表"""
    return get_virtual_contracts_for_return(vc_types, statuses, subject_statuses)


def get_vc_full_detail(vc_id: int) -> Optional[Dict[str, Any]]:
    """获取虚拟合同完整详情（包含业务、供应链信息）"""
    from models import Business, SupplyChain
    session = get_session()
    try:
        vc = session.query(VirtualContract).get(vc_id)
        if not vc:
            return None

        biz_info = None
        if vc.business_id:
            biz = session.query(Business).get(vc.business_id)
            if biz:
                customer = session.query(ChannelCustomer).get(biz.customer_id) if biz.customer_id else None
                biz_info = {
                    "id": biz.id,
                    "customer_name": customer.name if customer else "未知",
                    "status": biz.status
                }

        sc_info = None
        if vc.supply_chain_id:
            sc = session.query(SupplyChain).get(vc.supply_chain_id)
            if sc:
                from models import Supplier
                supplier = session.query(Supplier).get(sc.supplier_id) if sc.supplier_id else None
                sc_info = {
                    "id": sc.id,
                    "supplier_name": supplier.name if supplier else "未知",
                    "type": sc.type
                }

        return {
            "id": vc.id,
            "type": vc.type,
            "status": vc.status,
            "subject_status": vc.subject_status,
            "cash_status": vc.cash_status,
            "description": vc.description,
            "elements": vc.elements,
            "deposit_info": vc.deposit_info,
            "business": biz_info,
            "supply_chain": sc_info,
            "related_vc_id": vc.related_vc_id,
            "created_at": vc.status_timestamp.strftime("%Y-%m-%d %H:%M") if vc.status_timestamp else ""
        }
    finally:
        session.close()


def get_vc_by_id(vc_id: int) -> Optional[Dict[str, Any]]:
    """
    根据ID获取虚拟合同详情
    """
    session = get_session()
    try:
        vc = session.query(VirtualContract).get(vc_id)
        if not vc:
            return None
        return {
            "id": vc.id,
            "type": vc.type,
            "status": vc.status,
            "subject_status": vc.subject_status,
            "cash_status": vc.cash_status,
            "description": vc.description,
            "elements": vc.elements,
            "business_id": vc.business_id,
            "supply_chain_id": vc.supply_chain_id,
            "created_at": vc.status_timestamp.strftime("%Y-%m-%d %H:%M") if vc.status_timestamp else ""
        }
    finally:
        session.close()


def get_vc_count_by_business(business_id: int) -> int:
    """
    获取指定业务下的虚拟合同数量
    """
    session = get_session()
    try:
        return session.query(VirtualContract).filter(VirtualContract.business_id == business_id).count()
    finally:
        session.close()
