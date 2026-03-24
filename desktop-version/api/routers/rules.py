from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from api.deps import get_db, verify_api_key, row_to_dict
from models import TimeRule
from logic.time_rules import (
    save_rule_action, delete_rule_action,
    TimeRuleSchema
)

router = APIRouter(prefix="/api/v1/rules", tags=["时间规则"], dependencies=[Depends(verify_api_key)])


@router.post("/save", summary="保存/更新时间规则")
def save_rule(payload: TimeRuleSchema, session: Session = Depends(get_db)):
    """创建或更新时间规则。id 为空则创建，非空则更新。"""
    return save_rule_action(session, payload).model_dump()


class DeleteRuleRequest(BaseModel):
    rule_id: int

@router.post("/delete", summary="删除时间规则")
def delete_rule(req: DeleteRuleRequest, session: Session = Depends(get_db)):
    return delete_rule_action(session, req.rule_id).model_dump()


# ==================== 查询端点 ====================

@router.get("/list", summary="时间规则列表")
def list_rules(related_id: Optional[int] = None, related_type: Optional[str] = None, status: Optional[str] = None, session: Session = Depends(get_db)):
    q = session.query(TimeRule)
    if related_id is not None:
        q = q.filter(TimeRule.related_id == related_id)
    if related_type:
        q = q.filter(TimeRule.related_type == related_type)
    if status:
        q = q.filter(TimeRule.status == status)
    return {"success": True, "data": {"items": [row_to_dict(r) for r in q.all()]}}
