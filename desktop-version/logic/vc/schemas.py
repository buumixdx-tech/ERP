from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Dict
from datetime import datetime
from logic.time_rules.schemas import TimeRuleSchema

class VCItemSchema(BaseModel):
    sku_id: int = Field(..., description="SKU ID")
    sku_name: str = Field(..., min_length=1, description="SKU名称")
    point_id: Optional[int] = Field(None, description="目标点位ID")
    point_name: Optional[str] = Field(None, description="目标点位名称")
    qty: float = Field(..., gt=0, description="数量")
    price: float = Field(..., ge=0, description="单价")
    deposit: float = Field(default=0.0, ge=0, description="单台押金")
    sn: str = Field("-", description="设备序列号(物料填'-')")

    @field_validator('sku_name', 'point_name', 'sn')
    @classmethod
    def clean_strings(cls, v):
        if isinstance(v, str):
            return v.strip()
        return v

class CreateProcurementVCSchema(BaseModel):
    business_id: int = Field(..., description="关联业务ID")
    sc_id: Optional[int] = Field(None, description="供应链协议ID")
    items: List[VCItemSchema] = Field(..., description="采购明细列表")
    total_amt: float = Field(..., ge=0, description="总金额")
    total_deposit: float = Field(..., ge=0, description="总押金")
    payment: Dict = Field(..., description="结算条款")
    description: Optional[str] = Field("", description="备注")

    @model_validator(mode='after')
    def validate_totals(self) -> 'CreateProcurementVCSchema':
        calc_amt = sum(item.qty * item.price for item in self.items)
        calc_dep = sum(item.qty * item.deposit for item in self.items)
        if abs(calc_amt - self.total_amt) > 0.01:
            raise ValueError(f"总计金额 ¥{self.total_amt} 与明细计算值 ¥{calc_amt:.2f} 不符")
        if abs(calc_dep - self.total_deposit) > 0.01:
            raise ValueError(f"总计押金 ¥{self.total_deposit} 与明细计算值 ¥{calc_dep:.2f} 不符")
        return self

class CreateStockProcurementVCSchema(BaseModel):
    sc_id: int = Field(..., description="供应链协议ID")
    items: List[VCItemSchema] = Field(..., description="采购明细")
    total_amt: float = Field(..., ge=0, description="总金额")
    payment: Dict = Field(..., description="结算条款")
    description: Optional[str] = Field("", description="备注")

class AllocateInventorySchema(BaseModel):
    business_id: int = Field(..., description="目标业务ID")
    allocation_map: Dict[int, int] = Field(..., description="设备ID到目标点位ID的映射")
    description: Optional[str] = Field("", description="备注")

class CreateMaterialSupplyVCSchema(BaseModel):
    business_id: int = Field(..., description="关联业务ID")
    order: Dict = Field(..., description="供应订单")
    description: Optional[str] = Field("", description="备注")

class CreateReturnVCSchema(BaseModel):
    target_vc_id: int = Field(..., description="退货目标虚拟合同ID")
    return_direction: str = Field(..., description="退货方向")
    return_items: List[VCItemSchema] = Field(..., description="退货明细")
    goods_amount: float = Field(..., ge=0, description="退货货款金额")
    deposit_amount: float = Field(..., ge=0, description="退还押金金额")
    logistics_cost: float = Field(..., ge=0, description="物流费用")
    logistics_bearer: str = Field(..., description="物流费承担方")
    total_refund: float = Field(..., ge=0, description="总退款金额")
    reason: Optional[str] = Field("", description="退货原因")
    description: Optional[str] = Field("", description="备注")

class CreateMatProcurementVCSchema(BaseModel):
    sc_id: int = Field(..., description="供应链协议ID")
    items: List[VCItemSchema] = Field(..., description="物料采购明细")
    total_amt: float = Field(..., gt=0, description="总金额")
    payment: Dict = Field(..., description="结算条款")
    description: Optional[str] = Field("", description="备注")

class UpdateVCSchema(BaseModel):
    id: int = Field(..., description="VC ID")
    description: Optional[str] = Field(None, description="备注")
    elements: Optional[Dict] = Field(None, description="核心数据负载")
    deposit_info: Optional[Dict] = Field(None, description="押金信息")

class DeleteVCSchema(BaseModel):
    id: int = Field(..., description="VC ID")

