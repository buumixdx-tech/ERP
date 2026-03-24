"""
虚拟合同扩展 Actions 单元测试
测试未覆盖的 VC 相关 Action
"""

import pytest
from logic.vc import (
    create_mat_procurement_vc_action,
    create_stock_procurement_vc_action,
    allocate_inventory_action,
    CreateMatProcurementVCSchema,
    CreateStockProcurementVCSchema,
    AllocateInventorySchema,
    VCItemSchema,
)


class TestMatProcurementVCAction:
    """物料采购执行单测试"""

    def test_create_mat_procurement_success(self, db_session, sample_supplier):
        """✅ 正常创建物料采购单"""
        # 创建物料协议
        from models import SupplyChain
        from logic.constants import SKUType
        sc = SupplyChain(
            supplier_id=sample_supplier.id,
            supplier_name=sample_supplier.name,
            type=SKUType.MATERIAL,
            pricing_config={"物料A": 10}
        )
        db_session.add(sc)
        db_session.flush()

        # Given
        payload = CreateMatProcurementVCSchema(
            sc_id=sc.id,
            items=[
                VCItemSchema(
                    sku_id=1,
                    sku_name="物料A",
                    qty=100,
                    price=10,
                    deposit=0
                )
            ],
            total_amt=1000,
            payment={"prepayment_ratio": 0.3}
        )

        # When
        result = create_mat_procurement_vc_action(db_session, payload)

        # Then
        assert result.success is True


class TestStockProcurementVCAction:
    """库存采购执行单测试"""

    def test_create_stock_procurement_success(self, db_session, sample_supply_chain):
        """✅ 正常创建库存采购单（不关联客户）"""
        # Given
        payload = CreateStockProcurementVCSchema(
            sc_id=sample_supply_chain.id,
            items=[
                VCItemSchema(
                    sku_id=1,
                    sku_name="设备B",
                    qty=5,
                    price=2000,
                    deposit=200
                )
            ],
            total_amt=10000,
            payment={"prepayment_ratio": 0.5}
        )

        # When
        result = create_stock_procurement_vc_action(db_session, payload)

        # Then
        assert result.success is True


class TestAllocateInventoryAction:
    """库存拨付测试"""

    def test_allocate_inventory_business_not_found(self, db_session):
        """❌ 业务不存在"""
        payload = AllocateInventorySchema(
            business_id=99999,
            allocation_map={1: 1}
        )

        result = allocate_inventory_action(db_session, payload)

        assert result.success is False