from pydantic import BaseModel, Field
from typing import Optional

class CreateSupplyChainSchema(BaseModel):
    supplier_id: int = Field(..., description="供应商ID")
    supplier_name: str = Field(..., description="供应商名称")
    type: str = Field(..., description="类型: 设备/物料")
    pricing_config: dict = Field(..., description="定价配置")
    payment_terms: dict = Field(..., description="结算条款")
    contract_num: Optional[str] = Field(None, description="合同编号")

class DeleteSupplyChainSchema(BaseModel):
    id: int = Field(..., description="协议ID")
