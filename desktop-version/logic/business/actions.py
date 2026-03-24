from sqlalchemy.orm import Session
from models import Business, Contract, VirtualContract
from .schemas import CreateBusinessSchema, UpdateBusinessStatusSchema, AdvanceBusinessStageSchema
from logic.base import ActionResult
from logic.events.dispatcher import emit_event
from datetime import datetime
from logic.constants import BusinessStatus, ContractStatus, TimeRuleRelatedType, SystemEventType, SystemAggregateType
from logic.time_rules.rule_manager import RuleManager

def create_business_action(session: Session, payload: CreateBusinessSchema) -> ActionResult:
    try:
        new_b = Business(
            customer_id=payload.customer_id, 
            status=BusinessStatus.DRAFT, 
            details={"history": [{"from": None, "to": BusinessStatus.DRAFT, "time": datetime.now().isoformat(), "comment": "初始化创建"}]}
        )
        session.add(new_b)
        session.flush()
        emit_event(session, SystemEventType.BUSINESS_CREATED, SystemAggregateType.BUSINESS, new_b.id, {"customer_id": payload.customer_id})
        session.commit()
        return ActionResult(success=True, data={"business_id": new_b.id}, message="业务项已成功创建")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def update_business_status_action(session: Session, payload: UpdateBusinessStatusSchema) -> ActionResult:
    try:
        biz = session.query(Business).get(payload.business_id)
        if not biz:
            return ActionResult(success=False, error="未找到业务记录")
        
        old_status = biz.status
        biz.status = payload.status
        if payload.details is not None:
            biz.details = payload.details
            
        emit_event(session, SystemEventType.BUSINESS_STATUS_CHANGED, SystemAggregateType.BUSINESS, biz.id, {"from": old_status, "to": payload.status})
        
        # Trigger rule propagation
        RuleManager(session).propagate_from_parent(TimeRuleRelatedType.BUSINESS, biz.id)
        
        session.commit()
        return ActionResult(success=True, message=f"业务状态已更新至 {payload.status}")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def delete_business_action(session: Session, business_id: int) -> ActionResult:
    try:
        biz = session.query(Business).get(business_id)
        if not biz:
            return ActionResult(success=False, error="未找到业务记录")
        
        vc_count = session.query(VirtualContract).filter(VirtualContract.business_id == business_id).count()
        if vc_count > 0:
            return ActionResult(success=False, error=f"该业务下有 {vc_count} 个关联虚拟合同，无法删除")
            
        session.delete(biz)
        emit_event(session, SystemEventType.BUSINESS_DELETED, SystemAggregateType.BUSINESS, business_id)
        session.commit()
        return ActionResult(success=True, message="业务已成功删除")
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))

def advance_business_stage_action(session: Session, payload: AdvanceBusinessStageSchema) -> ActionResult:
    try:
        biz = session.query(Business).get(payload.business_id)
        if not biz:
            return ActionResult(success=False, error="未找到业务记录")
            
        old_status = biz.status
        valid_transitions = {
            BusinessStatus.DRAFT: [BusinessStatus.EVALUATION, BusinessStatus.TERMINATED],
            BusinessStatus.EVALUATION: [BusinessStatus.FEEDBACK, BusinessStatus.LANDING, BusinessStatus.TERMINATED],
            BusinessStatus.FEEDBACK: [BusinessStatus.LANDING, BusinessStatus.TERMINATED],
            BusinessStatus.LANDING: [BusinessStatus.ACTIVE, BusinessStatus.TERMINATED],
            BusinessStatus.ACTIVE: [BusinessStatus.PAUSED, BusinessStatus.TERMINATED, BusinessStatus.FINISHED],
            BusinessStatus.PAUSED: [BusinessStatus.ACTIVE, BusinessStatus.TERMINATED]
        }
        
        allowed_next = valid_transitions.get(old_status, [])
        if payload.next_status not in allowed_next and payload.next_status != old_status:
            return ActionResult(success=False, error=f"非法状态跳转：不能从 {old_status} 直接进入 {payload.next_status}")

        history = biz.details.get('history', [])
        history.append({
            "from": old_status, 
            "to": payload.next_status, 
            "time": datetime.now().isoformat(), 
            "comment": payload.comment
        })
        
        new_details = biz.details.copy()
        new_details["history"] = history
        
        if old_status == BusinessStatus.LANDING:
            if payload.pricing:
                new_details["pricing"] = payload.pricing
            if payload.payment_terms:
                new_details["payment_terms"] = payload.payment_terms
            
            c_num = payload.contract_num or f"BIZ-{biz.id}-{datetime.now().strftime('%Y%m%d')}"
            existing_c = session.query(Contract).filter(Contract.contract_number == c_num).first()
            if not existing_c:
                new_contract = Contract(
                    contract_number=c_num,
                    type=f"客户销售合同",
                    status=ContractStatus.SIGNED
                )
                session.add(new_contract)
                session.flush()
                target_c_id = new_contract.id
            else:
                target_c_id = existing_c.id
            
            new_details["contract_id"] = target_c_id
            
        biz.details = new_details
        biz.status = payload.next_status
        emit_event(session, SystemEventType.BUSINESS_STAGE_ADVANCED, SystemAggregateType.BUSINESS, biz.id, {"from": old_status, "to": payload.next_status})
        
        rules_count = 0
        if old_status == BusinessStatus.LANDING and payload.payment_terms:
            rules_count = RuleManager(session).generate_rules_from_payment_terms(
                related_id=biz.id,
                related_type=TimeRuleRelatedType.BUSINESS,
                payment_terms=payload.payment_terms
            )
            
        session.commit()
        msg = f"阶段推进成功: {old_status} -> {payload.next_status}"
        if rules_count > 0:
            msg += f" (自动生成 {rules_count} 条时间规则)"
            
        return ActionResult(success=True, data={"contract_id": new_details.get("contract_id")}, message=msg)
    except Exception as e:
        session.rollback()
        return ActionResult(success=False, error=str(e))
