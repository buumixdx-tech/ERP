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
def list_rules(
    ids: Optional[str] = None,
    related_id: Optional[int] = None,
    related_type: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    page: int = 1,
    size: int = 50,
    session: Session = Depends(get_db)
):
    """时间规则列表查询
    - ids: 多值查询，如 "1,2,3"
    - date_from/date_to: 创建时间范围，格式 "YYYY-MM-DD"
    """
    from api.deps import paginate

    q = session.query(TimeRule)

    # 多值查询
    if ids:
        id_list = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if id_list:
            q = q.filter(TimeRule.id.in_(id_list))

    # 精确过滤
    if related_id is not None:
        q = q.filter(TimeRule.related_id == related_id)
    if related_type:
        q = q.filter(TimeRule.related_type == related_type)
    if status:
        q = q.filter(TimeRule.status == status)

    # 时间范围
    if date_from:
        q = q.filter(TimeRule.created_at >= date_from)
    if date_to:
        q = q.filter(TimeRule.created_at <= date_to)

    q = q.order_by(TimeRule.id.desc())
    return {"success": True, "data": paginate(session, q, page, size)}

@router.get("/{rule_id}", summary="时间规则详情")
def get_rule(rule_id: int, session: Session = Depends(get_db)):
    obj = session.query(TimeRule).get(rule_id)
    if not obj:
        return {"success": False, "error": "未找到时间规则"}
    return {"success": True, "data": row_to_dict(obj)}
