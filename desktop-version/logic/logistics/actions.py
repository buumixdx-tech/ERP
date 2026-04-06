from sqlalchemy.orm import Session
from models import Logistics, ExpressOrder, VirtualContract
from logic.constants import LogisticsStatus, TimeRuleRelatedType, SystemEventType, SystemAggregateType, VCStatus, VCType
from logic.time_rules import RuleManager
from logic.inventory import inventory_module  # noqa: F401 - inventory_module is in logic/inventory.py (legacy file)
from logic.state_machine import logistics_state_machine
from logic.finance import finance_module
from logic.events.dispatcher import emit_event
from .schemas import CreateLogisticsPlanSchema, ConfirmInboundSchema, UpdateExpressOrderSchema, ExpressOrderStatusSchema
from logic.base import ActionResult

VC_STATUS_BLOCKED_FOR_LOGISTICS = [VCStatus.FINISH, VCStatus.TERMINATED, VCStatus.CANCELLED]

def create_logistics_plan_action(session: Session, payload: CreateLogisticsPlanSchema) -> ActionResult:
    """创建物流发货计划 Action"""
    try:
        if not payload.orders:
            return ActionResult(success=False, error="订单列表不能为空")
        
        vc = session.query(VirtualContract).get(payload.vc_id)
        if not vc:
            return ActionResult(success=False, error="未找到虚拟合同")
        
        if vc.status in VC_STATUS_BLOCKED_FOR_LOGISTICS:
            return ActionResult(success=False, error=f"该合同状态为【{vc.status}】，不允许新建物流")
        
        for order_data in payload.orders:
            tracking = order_data.get("tracking_number", "").strip()
            if not tracking:
                return ActionResult(success=False, error="快递单号不能为空")
            
            addr = order_data.get("address_info", {})
            if not addr:
                return ActionResult(success=False, error="地址信息不能为空")
            
            phone = addr.get("收货方联系电话", addr.get("发货方联系电话", "")).strip()
            if not phone:
                return ActionResult(success=False, error="联系电话不能为空")

        log = session.query(Logistics).filter(Logistics.virtual_contract_id == vc.id).first()
        if not log:
            log = Logistics(virtual_contract_id=vc.id, status=LogisticsStatus.PENDING)
            session.add(log)
            session.flush()
            RuleManager(session).sync_from_parent(TimeRuleRelatedType.LOGISTICS, log.id)
        
        for order_data in payload.orders:
            eo = ExpressOrder(
                logistics_id=log.id,
                tracking_number=order_data["tracking_number"],
                items=order_data["items"],
                address_info=order_data["address_info"],
                status=LogisticsStatus.PENDING
            )
            session.add(eo)
        
        emit_event(session, SystemEventType.LOGISTICS_PLAN_CREATED, SystemAggregateType.LOGISTICS, log.id, {
            "vc_id": vc.id,
            "order_count": len(payload.orders)
        })
        
        session.commit()
        return ActionResult(success=True, data={"log_id": log.id}, message="物流计划已下达")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def confirm_inbound_action(session: Session, payload: ConfirmInboundSchema) -> ActionResult:
    """确认收货/入库 Action"""
    try:
        log = session.query(Logistics).get(payload.log_id)
        if not log: return ActionResult(success=False, error="未找到物流记录")

        # 获取 VC 类型，设备/库存采购必须提供 SN，物料类允许为空
        vc = session.query(VirtualContract).get(log.virtual_contract_id)
        requires_sn = vc and vc.type in [VCType.EQUIPMENT_PROCUREMENT, VCType.STOCK_PROCUREMENT]

        if requires_sn and not payload.sn_list:
            return ActionResult(success=False, error="序列号列表不能为空")

        if payload.sn_list and len(payload.sn_list) != len(set(payload.sn_list)):
            return ActionResult(success=False, error="序列号列表中包含重复项")
        
        if log.status == LogisticsStatus.FINISH:
            return ActionResult(success=False, error="该物流单已完成入库，请勿重复操作")

        from models import EquipmentInventory
        existing_sns = []
        # 仅在采购类 VC 时检查 SN 冲突，退货类 VC 的 SN 已在库存中（更新 location 而非新建）
        if payload.sn_list and vc and vc.type in [VCType.EQUIPMENT_PROCUREMENT, VCType.STOCK_PROCUREMENT]:
            existing_sns = session.query(EquipmentInventory.sn).filter(EquipmentInventory.sn.in_(payload.sn_list)).all()
        if existing_sns:
            conflict_sns = [s[0] for s in existing_sns]
            return ActionResult(success=False, error=f"SN 冲突：以下序列号已存在于系统库存中 {conflict_sns}")

        old_status = log.status
        log.status = LogisticsStatus.FINISH
        
        inventory_module(log.id, equipment_sn_json=payload.sn_list, session=session)
        logistics_state_machine(log.id, session=session)
        finance_module(logistics_id=log.id, session=session)
        
        if old_status != LogisticsStatus.FINISH:
            emit_event(session, SystemEventType.LOGISTICS_STATUS_CHANGED, SystemAggregateType.LOGISTICS, log.id, {
                "from": old_status,
                "to": LogisticsStatus.FINISH,
                "vc_id": log.virtual_contract_id,
                "sn_count": len(payload.sn_list)
            })
        
        session.commit()
        return ActionResult(success=True, message="收货入库及财务同步完成")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def update_express_order_action(session: Session, payload: UpdateExpressOrderSchema) -> ActionResult:
    """更新快递单信息 Action"""
    try:
        o = session.query(ExpressOrder).get(payload.order_id)
        if not o:
            return ActionResult(success=False, error="未找到快递单")
        
        o.tracking_number = payload.tracking_number
        o.address_info = payload.address_info
        
        emit_event(session, SystemEventType.EXPRESS_ORDER_UPDATED, SystemAggregateType.EXPRESS_ORDER, o.id, {"tracking": o.tracking_number})
        
        session.commit()
        return ActionResult(success=True, message="信息已更新")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def update_express_order_status_action(session: Session, payload: ExpressOrderStatusSchema) -> ActionResult:
    """推进快递单状态 Action"""
    try:
        o = session.query(ExpressOrder).get(payload.order_id)
        if not o:
            return ActionResult(success=False, error="未找到快递单")
        
        old_status = o.status
        o.status = payload.target_status
        
        logistics_state_machine(payload.logistics_id, o.id, session=session)
        
        emit_event(session, SystemEventType.EXPRESS_ORDER_STATUS_CHANGED, SystemAggregateType.EXPRESS_ORDER, o.id, {"from": old_status, "to": payload.target_status})
        
        session.commit()
        return ActionResult(success=True, message=f"快递单已推进至 {payload.target_status}")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def bulk_progress_express_orders_action(session: Session, order_ids: list, target_status: str, logistics_id: int) -> ActionResult:
    """批量推进快递单状态 Action"""
    try:
        for oid in order_ids:
            o = session.query(ExpressOrder).get(oid)
            if o:
                o.status = target_status
                logistics_state_machine(logistics_id, o.id, session=session)
        
        emit_event(session, SystemEventType.EXPRESS_ORDER_BULK_PROGRESS, SystemAggregateType.LOGISTICS, logistics_id, {"count": len(order_ids), "to": target_status})
        
        session.commit()
        return ActionResult(success=True, message=f"已成功批量推进 {len(order_ids)} 个快递单")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))
