import json
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse
from api.deps import get_db, verify_api_key, row_to_dict
from models import get_session, SystemEvent

router = APIRouter(prefix="/api/v1/events", tags=["事件"], dependencies=[Depends(verify_api_key)])


@router.get("/stream", summary="SSE 实时事件流")
async def event_stream():
    """订阅系统事件的 Server-Sent Events 流。AI Agent 可通过此端点实时接收业务事件。"""
    async def generate():
        last_id = 0
        while True:
            session = get_session()
            try:
                events = session.query(SystemEvent).filter(
                    SystemEvent.id > last_id,
                    SystemEvent.pushed_to_ai == False
                ).order_by(SystemEvent.id).limit(20).all()

                for event in events:
                    data = {
                        "id": event.id,
                        "event_type": event.event_type,
                        "aggregate_type": event.aggregate_type,
                        "aggregate_id": event.aggregate_id,
                        "payload": event.payload,
                        "created_at": event.created_at.isoformat() if event.created_at else None,
                    }
                    yield {
                        "id": str(event.id),
                        "event": event.event_type,
                        "data": json.dumps(data, ensure_ascii=False),
                    }
                    event.pushed_to_ai = True
                    last_id = event.id

                if events:
                    session.commit()
            finally:
                session.close()

            await asyncio.sleep(2)

    return EventSourceResponse(generate())


@router.get("/recent", summary="最近事件（轮询回退）")
def get_recent_events(limit: int = 50, since_id: int = 0, session: Session = Depends(get_db)):
    """轮询获取最近事件。适用于不支持 SSE 的客户端。"""
    events = session.query(SystemEvent).filter(
        SystemEvent.id > since_id
    ).order_by(SystemEvent.id.desc()).limit(limit).all()
    return {
        "success": True,
        "data": {
            "items": [row_to_dict(e) for e in reversed(events)],
            "latest_id": events[0].id if events else since_id,
        }
    }
