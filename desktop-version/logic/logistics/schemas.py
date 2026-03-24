from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class CreateLogisticsPlanSchema(BaseModel):
    vc_id: int = Field(..., description="关联虚拟合同ID")
    orders: List[Dict] = Field(..., description="快递单列表 [{tracking_number, items, address_info}]")

class ConfirmInboundSchema(BaseModel):
    log_id: int = Field(..., description="物流记录ID")
    sn_list: List[str] = Field([], description="设备序列号列表(物料类可为空)")

class UpdateExpressOrderSchema(BaseModel):
    order_id: int = Field(..., description="快递单ID")
    tracking_number: str = Field(..., description="快递单号")
    address_info: dict = Field(..., description="地址信息")

class ExpressOrderStatusSchema(BaseModel):
    order_id: int = Field(..., description="快递单ID")
    target_status: str = Field(..., description="目标状态: 待发货/在途/签收")
    logistics_id: int = Field(..., description="物流记录ID(状态机需要)")
