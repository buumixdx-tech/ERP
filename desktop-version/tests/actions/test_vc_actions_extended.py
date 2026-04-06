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
    VCElementSchema,
)


class TestMatProcurementVCAction:
    """物料采购执行单测试"""

    def test_create_mat_procurement_success(self, db_session, sample_supplier):
        """✅ 正常创建物料采购单"""
        from models import SupplyChain, Point
        from logic.constants import SKUType

        # 创建供应商仓库（发货点）和我们仓库（收货点）
        sup_wh = Point(name="测试供应商仓", type="供应商仓", supplier_id=sample_supplier.id)
        db_session.add(sup_wh)
        our_wh = Point(name="总部仓", type="自有仓")
        db_session.add(our_wh)
        db_session.flush()

        sc = SupplyChain(
            supplier_id=sample_supplier.id,
            supplier_name=sample_supplier.name,
            type=SKUType.MATERIAL,
            pricing_config={"物料A": 10}
        )
        db_session.add(sc)
        db_session.flush()

        payload = CreateMatProcurementVCSchema(
            sc_id=sc.id,
            elements=[
                VCElementSchema(
                    shipping_point_id=0,
                    receiving_point_id=our_wh.id,
                    sku_id=1,
                    qty=100,
                    price=10,
                    deposit=0,
                    subtotal=1000
                )
            ],
            total_amt=1000,
            payment={"prepayment_ratio": 0.3}
        )

        result = create_mat_procurement_vc_action(db_session, payload)

        assert result.success is True, f"创建失败: {result.error}"


class TestStockProcurementVCAction:
    """库存采购执行单测试"""

    def test_create_stock_procurement_success(self, db_session, sample_supply_chain, sample_supplier):
        """✅ 正常创建库存采购单（不关联客户）"""
        from models import Point

        # 创建供应商仓库（发货点）和我们仓库（收货点）
        sup_wh = Point(name="测试供应商仓", type="供应商仓", supplier_id=sample_supplier.id)
        db_session.add(sup_wh)
        our_wh = Point(name="总部仓", type="自有仓")
        db_session.add(our_wh)
        db_session.flush()

        payload = CreateStockProcurementVCSchema(
            sc_id=sample_supply_chain.id,
            elements=[
                VCElementSchema(
                    shipping_point_id=0,
                    receiving_point_id=our_wh.id,
                    sku_id=1,
                    qty=5,
                    price=2000,
                    deposit=200,
                    subtotal=10000
                )
            ],
            total_amt=10000,
            payment={"prepayment_ratio": 0.5}
        )

        result = create_stock_procurement_vc_action(db_session, payload)

        assert result.success is True, f"创建失败: {result.error}"


class TestAllocateInventoryAction:
    """库存拨付测试"""

    def test_allocate_inventory_business_not_found(self, db_session):
        """❌ 业务不存在"""
        payload = AllocateInventorySchema(
            business_id=99999,
            elements=[
                VCElementSchema(
                    shipping_point_id=1,
                    receiving_point_id=2,
                    sku_id=1,
                    qty=1,
                    price=0,
                    deposit=0,
                    subtotal=0
                )
            ]
        )

        result = allocate_inventory_action(db_session, payload)

        assert result.success is False