from sqlalchemy.orm import Session
from models import VirtualContract, TimeRule, Business, SupplyChain, EquipmentInventory, Point
from logic.constants import (
    VCType, VCStatus, SubjectStatus, CashStatus, TimeRuleRelatedType, 
    TimeRuleStatus, BusinessStatus, SKUType, SystemEventType, SystemAggregateType,
    OperationalStatus
)
from logic.time_rules import RuleManager
from logic.offset_manager import apply_offset_to_vc
from logic.events.dispatcher import emit_event
from .schemas import (
    CreateProcurementVCSchema, CreateStockProcurementVCSchema, CreateMatProcurementVCSchema,
    CreateMaterialSupplyVCSchema, CreateReturnVCSchema, AllocateInventorySchema,
    UpdateVCSchema, DeleteVCSchema
)
from logic.base import ActionResult
from datetime import datetime

def create_procurement_vc_action(session: Session, payload: CreateProcurementVCSchema, draft_rules: list = None) -> ActionResult:
    """设备采购执行单创建 Action"""
    try:
        biz = session.query(Business).get(payload.business_id)
        if not biz: return ActionResult(success=False, error="未找到关联业务项目")
        if biz.status not in [BusinessStatus.ACTIVE, BusinessStatus.LANDING]:
            return ActionResult(success=False, error=f"项目当前状态为 {biz.status}，不允许下达采购单")
        
        if payload.sc_id:
            sc = session.query(SupplyChain).get(payload.sc_id)
            if not sc: return ActionResult(success=False, error="未找到供应链协议")
            if sc.type != SKUType.EQUIPMENT:
                return ActionResult(success=False, error="该协议类型不属于设备供应，无法用于设备采购")

        clean_items = [item.dict() for item in payload.items]
        new_vc = VirtualContract(
            business_id=payload.business_id,
            supply_chain_id=payload.sc_id,
            type=VCType.EQUIPMENT_PROCUREMENT,
            elements={
                "skus": clean_items,
                "total_amount": payload.total_amt,
                "payment_terms": payload.payment
            },
            deposit_info={
                "should_receive": payload.total_deposit,
                "total_deposit": 0.0
            },
            status=VCStatus.EXE,
            subject_status=SubjectStatus.EXE,
            cash_status=CashStatus.EXE,
            description=payload.description
        )
        session.add(new_vc)
        session.flush()
        RuleManager(session).sync_from_parent(TimeRuleRelatedType.VIRTUAL_CONTRACT, new_vc.id)
        if draft_rules:
            for r in draft_rules:
                session.add(TimeRule(
                    related_id=new_vc.id, related_type=TimeRuleRelatedType.VIRTUAL_CONTRACT,
                    party=r.get("party"), trigger_event=r.get("trigger_event"),
                    target_event=r.get("target_event"), offset=r.get("offset"),
                    unit=r.get("unit"), direction=r.get("direction"),
                    inherit=r.get("inherit", 0), status=r.get("status", TimeRuleStatus.ACTIVE),
                    timestamp=datetime.now()
                ))
        apply_offset_to_vc(session, new_vc)
        emit_event(session, SystemEventType.VC_CREATED, SystemAggregateType.VIRTUAL_CONTRACT, new_vc.id, {
            "type": new_vc.type, "business_id": new_vc.business_id, "total_amount": payload.total_amt
        })
        session.commit()
        return ActionResult(success=True, data={"vc_id": new_vc.id}, message=f"设备采购单 VC-{new_vc.id} 创建成功")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def create_material_supply_vc_action(session: Session, payload: CreateMaterialSupplyVCSchema, draft_rules: list = None) -> ActionResult:
    """物料供应执行单创建 Action"""
    try:
        biz = session.query(Business).get(payload.business_id)
        if not biz: return ActionResult(success=False, error="未找到关联业务项目")
        if biz.status not in [BusinessStatus.ACTIVE, BusinessStatus.LANDING]:
            return ActionResult(success=False, error=f"项目尚未正式开展 (当前状态: {biz.status})，无法进行物料供应")
        
        from logic.services import validate_inventory_availability
        check_items = []
        for p in payload.order.get('points', []):
            for item in p.get('items', []):
                wh_n = item.get('source_warehouse') or p.get('source_warehouse') or "默认仓"
                check_items.append((item.get('sku_name'), wh_n, float(item.get('qty', 0))))
        
        is_ok, over_stock = validate_inventory_availability(session, check_items)
        if not is_ok:
            return ActionResult(success=False, error=f"库存严重不足: {' | '.join(over_stock)}")

        new_vc = VirtualContract(
            business_id=payload.business_id,
            type=VCType.MATERIAL_SUPPLY,
            elements=payload.order,
            status=VCStatus.EXE,
            subject_status=SubjectStatus.EXE,
            cash_status=CashStatus.EXE,
            description=payload.description
        )
        session.add(new_vc)
        session.flush()
        RuleManager(session).sync_from_parent(TimeRuleRelatedType.VIRTUAL_CONTRACT, new_vc.id)
        if draft_rules:
            for r in draft_rules:
                session.add(TimeRule(
                    related_id=new_vc.id, related_type=TimeRuleRelatedType.VIRTUAL_CONTRACT,
                    party=r.get("party"), trigger_event=r.get("trigger_event"),
                    target_event=r.get("target_event"), offset=r.get("offset"),
                    unit=r.get("unit"), direction=r.get("direction"),
                    inherit=r.get("inherit", 0), status=r.get("status", TimeRuleStatus.ACTIVE),
                    timestamp=datetime.now()
                ))
        apply_offset_to_vc(session, new_vc)
        emit_event(session, SystemEventType.VC_CREATED, SystemAggregateType.VIRTUAL_CONTRACT, new_vc.id, {
            "type": new_vc.type, "business_id": new_vc.business_id, "total_amount": payload.order.get('total_amount', 0)
        })
        session.commit()
        return ActionResult(success=True, data={"vc_id": new_vc.id}, message=f"物料供应单 VC-{new_vc.id} 创建成功")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def create_return_vc_action(session: Session, payload: CreateReturnVCSchema, draft_rules: list = None) -> ActionResult:
    """退货执行单创建 Action"""
    try:
        target_vc = session.query(VirtualContract).get(payload.target_vc_id)
        if not target_vc: return ActionResult(success=False, error="未找到目标虚拟合同")
        
        if target_vc.subject_status not in [SubjectStatus.EXE, SubjectStatus.FINISH]:
            return ActionResult(success=False, error=f"原单标的状态为 {target_vc.subject_status}，此时无法发起退货")

        from logic.services import get_returnable_items
        allowed_items = get_returnable_items(session, target_vc.id, payload.return_direction)
        allowed_map = {}
        for ai in allowed_items:
            key = (ai['sku_id'], ai.get('point_name'), ai.get('sn', '-'))
            allowed_map[key] = allowed_map.get(key, 0) + ai['qty']
        
        for ri in payload.return_items:
            key = (ri.sku_id, ri.point_name, ri.sn)
            avail = allowed_map.get(key, 0)
            if ri.qty > avail:
                return ActionResult(success=False, error=f"退货越界: {ri.sku_name} (点位:{ri.point_name}) 申请退货 {ri.qty}，而最大可退仅 {avail}")

        clean_ret_items = [item.dict() for item in payload.return_items]
        new_vc = VirtualContract(
            related_vc_id=payload.target_vc_id, business_id=target_vc.business_id,
            supply_chain_id=target_vc.supply_chain_id, type=VCType.RETURN,
            status=VCStatus.EXE, subject_status=SubjectStatus.EXE,
            cash_status=CashStatus.EXE if payload.total_refund > 0 else CashStatus.FINISH, 
            description=payload.description,
            elements={
                "return_direction": payload.return_direction, "return_items": clean_ret_items,
                "goods_amount": payload.goods_amount, "deposit_amount": payload.deposit_amount,
                "total_refund": payload.total_refund, "total_amount": payload.total_refund, "reason": payload.reason
            }
        )
        session.add(new_vc)
        session.flush()
        RuleManager(session).sync_from_parent(TimeRuleRelatedType.VIRTUAL_CONTRACT, new_vc.id)
        if draft_rules:
            for r in draft_rules:
                session.add(TimeRule(
                    related_id=new_vc.id, related_type=TimeRuleRelatedType.VIRTUAL_CONTRACT,
                    party=r.get("party"), trigger_event=r.get("trigger_event"),
                    target_event=r.get("target_event"), offset=r.get("offset"),
                    unit=r.get("unit"), direction=r.get("direction"),
                    inherit=r.get("inherit", 0), status=r.get("status", TimeRuleStatus.ACTIVE),
                    timestamp=datetime.now()
                ))
        apply_offset_to_vc(session, new_vc)
        emit_event(session, SystemEventType.VC_CREATED, SystemAggregateType.VIRTUAL_CONTRACT, new_vc.id, {
            "type": new_vc.type, "business_id": new_vc.business_id, 
            "related_vc_id": new_vc.related_vc_id, "total_refund": payload.total_refund
        })
        session.commit()
        return ActionResult(success=True, data={"vc_id": new_vc.id}, message=f"退货单 VC-{new_vc.id} 创建成功")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def update_vc_action(session: Session, payload: UpdateVCSchema) -> ActionResult:
    """底层 VC 数据修正 Action"""
    try:
        vc = session.query(VirtualContract).get(payload.id)
        if not vc: return ActionResult(success=False, error="未找到 VC")
        
        if payload.description is not None:
            vc.description = payload.description
        if payload.elements is not None:
            vc.elements = payload.elements
        if payload.deposit_info is not None:
            vc.deposit_info = payload.deposit_info
        
        emit_event(session, SystemEventType.VC_UPDATED, SystemAggregateType.VIRTUAL_CONTRACT, vc.id, {"desc": vc.description})
        session.commit()
        return ActionResult(success=True, message="底层数据已更新")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def delete_vc_action(session: Session, payload: DeleteVCSchema) -> ActionResult:
    """物理删除 VC Action (含级联清理)"""
    try:
        vc_id = payload.id
        vc = session.query(VirtualContract).get(vc_id)
        if not vc: return ActionResult(success=False, error="未找到 VC")
        
        from models import Logistics
        session.query(Logistics).filter(Logistics.virtual_contract_id == vc_id).delete()
        session.delete(vc)
        
        emit_event(session, SystemEventType.VC_DELETED, SystemAggregateType.VIRTUAL_CONTRACT, vc_id)
        session.commit()
        return ActionResult(success=True, message="该虚拟合同已从系统中完全移除")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def create_mat_procurement_vc_action(session: Session, payload: CreateMatProcurementVCSchema, draft_rules: list = None) -> ActionResult:
    """物料采购执行单创建 Action"""
    try:
        sc = session.query(SupplyChain).get(payload.sc_id)
        if not sc or sc.type != SKUType.MATERIAL:
            return ActionResult(success=False, error="无效的物料供应链协议")

        clean_items = [item.dict() for item in payload.items]
        new_vc = VirtualContract(
            supply_chain_id=payload.sc_id,
            type=VCType.MATERIAL_PROCUREMENT,
            elements={
                "skus": clean_items,
                "total_amount": payload.total_amt,
                "payment_terms": payload.payment
            },
            status=VCStatus.EXE,
            subject_status=SubjectStatus.EXE,
            cash_status=CashStatus.EXE,
            description=payload.description or f"物料采购: {len(clean_items)}项物料"
        )
        session.add(new_vc)
        session.flush()
        RuleManager(session).sync_from_parent(TimeRuleRelatedType.VIRTUAL_CONTRACT, new_vc.id)
        apply_offset_to_vc(session, new_vc)
        emit_event(session, SystemEventType.VC_CREATED, SystemAggregateType.VIRTUAL_CONTRACT, new_vc.id, {"type": new_vc.type, "total_amount": payload.total_amt})
        session.commit()
        return ActionResult(success=True, data={"vc_id": new_vc.id}, message=f"物料采购单 VC-{new_vc.id} 创建成功")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def create_stock_procurement_vc_action(session: Session, payload: CreateStockProcurementVCSchema, draft_rules: list = None) -> ActionResult:
    """库存采购执行单创建 Action"""
    try:
        sc = session.query(SupplyChain).get(payload.sc_id)
        if not sc or sc.type != SKUType.EQUIPMENT:
            return ActionResult(success=False, error="无效的设备供应链协议")

        clean_items = [item.dict() for item in payload.items]
        new_vc = VirtualContract(
            business_id=None,
            supply_chain_id=payload.sc_id,
            type=VCType.STOCK_PROCUREMENT,
            elements={
                "skus": clean_items,
                "total_amount": payload.total_amt,
                "payment_terms": payload.payment
            },
            deposit_info={"should_receive": 0.0, "total_deposit": 0.0},
            status=VCStatus.EXE,
            subject_status=SubjectStatus.EXE,
            cash_status=CashStatus.EXE,
            description=payload.description or f"库存采购: {len(clean_items)}项设备"
        )
        session.add(new_vc)
        session.flush()
        RuleManager(session).sync_from_parent(TimeRuleRelatedType.VIRTUAL_CONTRACT, new_vc.id)
        apply_offset_to_vc(session, new_vc)
        emit_event(session, SystemEventType.VC_CREATED, SystemAggregateType.VIRTUAL_CONTRACT, new_vc.id, {"type": new_vc.type, "total_amount": payload.total_amt})
        session.commit()
        return ActionResult(success=True, data={"vc_id": new_vc.id}, message=f"库存采购单 VC-{new_vc.id} 创建成功")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def allocate_inventory_action(session: Session, payload: AllocateInventorySchema) -> ActionResult:
    """库存拨付 Action"""
    try:
        biz = session.query(Business).get(payload.business_id)
        if not biz: return ActionResult(success=False, error="未找到关联业务项目")
        
        equipment_ids = list(payload.allocation_map.keys())
        equipments = []
        for eq_id in equipment_ids:
            eq = session.query(EquipmentInventory).get(eq_id)
            if not eq or eq.operational_status != OperationalStatus.STOCK:
                return ActionResult(success=False, error=f"设备 ID={eq_id} 不在库或不存在")
            equipments.append(eq)

        target_point_ids = set(payload.allocation_map.values())
        point_map = {}
        for p_id in target_point_ids:
            p = session.query(Point).get(p_id)
            if not p: return ActionResult(success=False, error=f"未找到目标点位 ID={p_id}")
            point_map[p_id] = p

        biz_pricing = biz.details.get("pricing", {}) if biz.details else {}
        total_deposit = 0.0
        alloc_items = []
        for eq in equipments:
            t_point_id = payload.allocation_map[eq.id]
            t_point = point_map[t_point_id]
            sku_name = eq.sku.name if eq.sku else "未知"
            deposit = biz_pricing.get(sku_name, {}).get("deposit", 0.0) if isinstance(biz_pricing.get(sku_name), dict) else 0.0
            total_deposit += deposit
            alloc_items.append({"equipment_id": eq.id, "sn": eq.sn, "sku_id": eq.sku_id, "deposit": deposit, "target_point_id": t_point_id})

        new_vc = VirtualContract(
            business_id=payload.business_id,
            type=VCType.INVENTORY_ALLOCATION,
            elements={"allocation_items": alloc_items, "total_amount": 0.0},
            deposit_info={"should_receive": total_deposit, "total_deposit": 0.0},
            status=VCStatus.EXE, subject_status=SubjectStatus.FINISH,
            cash_status=CashStatus.EXE if total_deposit > 0 else CashStatus.FINISH,
            description=payload.description or f"库存拨付: {len(equipments)}台设备"
        )
        session.add(new_vc)
        session.flush()
        for eq in equipments:
            eq.operational_status = OperationalStatus.OPERATING
            eq.point_id = payload.allocation_map[eq.id]
            eq.virtual_contract_id = new_vc.id

        emit_event(session, SystemEventType.VC_CREATED, SystemAggregateType.VIRTUAL_CONTRACT, new_vc.id, {"type": new_vc.type, "equipment_count": len(equipments)})
        session.commit()
        return ActionResult(success=True, data={"vc_id": new_vc.id}, message=f"库存拨付完成")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))
