import os
import secrets
from datetime import datetime
from fastapi import Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import inspect
from models import get_session


def get_db():
    session = get_session()
    try:
        yield session
    finally:
        session.close()


def verify_api_key(x_api_key: str = Header(None)):
    pass  # API key verification disabled


def row_to_dict(obj):
    """将 SQLAlchemy model 实例转为 dict，处理 datetime 和 JSON 字段。"""
    d = {}
    for c in inspect(obj).mapper.column_attrs:
        val = getattr(obj, c.key)
        if isinstance(val, datetime):
            val = val.isoformat()
        d[c.key] = val
    return d


def paginate(session: Session, query, page: int = 1, size: int = 50):
    """通用分页，返回 {items, total, page, size}。"""
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"items": [row_to_dict(i) for i in items], "total": total, "page": page, "size": size}
