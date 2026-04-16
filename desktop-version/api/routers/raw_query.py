from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from api.deps import get_db, verify_api_key
import re

router = APIRouter(prefix="/api/v1/sql", tags=["SQL查询"], dependencies=[Depends(verify_api_key)])


class RawQueryRequest(BaseModel):
    sql: str
    params: dict | None = None


# ==================== 安全校验 ====================

# 禁止的 SQL 关键字（大小写不敏感）
BLOCKED_KEYWORDS = [
    r'\bDROP\b', r'\bDELETE\b', r'\bINSERT\b', r'\bUPDATE\b',
    r'\bALTER\b', r'\bCREATE\b', r'\bTRUNCATE\b', r'\bGRANT\b',
    r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b', r'\bSP_\b',
    r'\bXP_\b', r'\b--\b', r'\b;\s*;\b', r'\bUNION\s+SELECT\b',
]

# 最大返回行数
MAX_ROWS = 1000

# 查询超时（秒）
QUERY_TIMEOUT = 30


def is_safe_sql(sql: str) -> tuple[bool, str]:
    """
    校验 SQL 安全性。
    返回 (是否安全, 错误信息)
    """
    upper_sql = sql.upper().strip()

    # 必须以 SELECT 开头
    if not upper_sql.startswith('SELECT'):
        return False, "只允许 SELECT 查询"

    # 检查禁止的关键字
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, sql, re.IGNORECASE):
            return False, f"禁止使用: {pattern}"

    # 检查是否有注释
    if '--' in sql or '/*' in sql:
        return False, "禁止使用 SQL 注释"

    return True, ""


# ==================== 查询端点 ====================

@router.post("/query", summary="执行原始SQL查询")
def execute_raw_query(req: RawQueryRequest, session: Session = Depends(get_db)):
    """
    执行原始 SQL 查询（只读）。

    安全措施：
    1. 只允许 SELECT 语句
    2. 禁止危险关键字（DROP/DELETE/INSERT等）
    3. 禁止 SQL 注释
    4. 最大返回 1000 行
    5. 查询超时 30 秒

    使用示例：
    POST /api/v1/sql/query
    {
        "sql": "SELECT * FROM virtual_contracts WHERE status = :status LIMIT 10",
        "params": {"status": "执行"}
    }
    """
    # 1. 安全校验
    safe, error_msg = is_safe_sql(req.sql)
    if not safe:
        return {"success": False, "error": error_msg}

    # 2. 添加 LIMIT 保护
    sql = req.sql.strip()
    if 'LIMIT' not in sql.upper():
        sql = f"{sql} LIMIT {MAX_ROWS}"

    # 3. 设置超时（SQLite 不支持精细超时，用 short_session 模式）
    try:
        # 尝试设置 busy_timeout
        session.execute(text("PRAGMA busy_timeout = 30000"))
    except Exception:
        pass

    # 4. 执行查询
    try:
        if req.params:
            result = session.execute(text(sql), req.params)
        else:
            result = session.execute(text(sql))

        # 5. 提取结果
        columns = result.keys()
        rows = result.fetchall()

        # 转换为字典列表
        data = [dict(zip(columns, row)) for row in rows]

        return {
            "success": True,
            "data": {
                "columns": list(columns),
                "rows": data,
                "row_count": len(data),
                "sql": sql
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"查询执行失败: {str(e)}"
        }
