"""
虚拟合同 Actions 单元测试
根据实际 Schema 定义编写的测试用例
"""

import pytest
from logic.vc import (
    create_procurement_vc_action,
    create_material_supply_vc_action,
    create_return_vc_action,
    update_vc_action,
    delete_vc_action,
    CreateProcurementVCSchema,
    CreateMaterialSupplyVCSchema,
    CreateReturnVCSchema,
    VCItemSchema,
    UpdateVCSchema,
    DeleteVCSchema
)


class TestCreateProcurementVCAction:
    """设备采购执行单创建测试"""

    def test_create_procurement_vc_success(self, db_session, sample_business, sample_sku):
        """✅ 正常创建设备采购单"""
        # Given
        payload = CreateProcurementVCSchema(
            business_id=sample_business.id,
            sc_id=None,
            items=[
                VCItemSchema(
                    sku_id=sample_sku.id,
                    sku_name="测试设备-001",
                    qty=10,
                    price=1000,
                    deposit=100
                )
            ],
            total_amt=10000,
            total_deposit=1000,
            payment={"prepayment_ratio": 0.3},
            description="测试采购单"
        )

        # When
        result = create_procurement_vc_action(db_session, payload)

        # Then
        assert result.success is True
        assert result.data is not None
        assert "vc_id" in result.data
        assert result.data["vc_id"] > 0

    def test_create_procurement_vc_business_not_found(self, db_session, sample_sku):
        """❌ 业务不存在"""
        # Given
        payload = CreateProcurementVCSchema(
            business_id=99999,
            sc_id=None,
            items=[
                VCItemSchema(
                    sku_id=sample_sku.id,
                    sku_name="测试设备",
                    qty=1,
                    price=1000,
                    deposit=0
                )
            ],
            total_amt=1000,
            total_deposit=0,
            payment={}
        )

        # When
        result = create_procurement_vc_action(db_session, payload)

        # Then
        assert result.success is False

    def test_create_procurement_vc_invalid_status(self, db_session, sample_business, sample_sku):
        """❌ 业务状态不允许下单"""
        # Given: 将业务状态改为已终止
        from models import Business
        sample_business.status = "业务终止"
        db_session.commit()

        payload = CreateProcurementVCSchema(
            business_id=sample_business.id,
            sc_id=None,
            items=[
                VCItemSchema(
                    sku_id=sample_sku.id,
                    sku_name="测试设备",
                    qty=1,
                    price=1000,
                    deposit=0
                )
            ],
            total_amt=1000,
            total_deposit=0,
            payment={}
        )

        # When
        result = create_procurement_vc_action(db_session, payload)

        # Then
        assert result.success is False


class TestCreateMaterialSupplyVCAction:
    """物料供应执行单创建测试"""

    def test_create_material_supply_business_not_found(self, db_session):
        """❌ 业务不存在"""
        payload = CreateMaterialSupplyVCSchema(
            business_id=99999,
            order={"points": [], "total_amount": 0}
        )

        result = create_material_supply_vc_action(db_session, payload)

        assert result.success is False


class TestCreateReturnVCAction:
    """退货执行单创建测试"""

    def test_create_return_vc_target_not_found(self, db_session):
        """❌ 目标 VC 不存在"""
        payload = CreateReturnVCSchema(
            target_vc_id=99999,
            return_direction="客户退我方",
            return_items=[],
            goods_amount=0,
            deposit_amount=0,
            logistics_cost=0,
            logistics_bearer="我方",
            total_refund=0,
            reason="测试"
        )

        result = create_return_vc_action(db_session, payload)

        assert result.success is False


class TestUpdateVCAction:
    """更新虚拟合同测试"""

    def test_update_vc_success(self, db_session, sample_virtual_contract):
        """✅ 正常更新 VC"""
        # Given
        new_description = "更新后的描述"
        new_elements = {"skus": [{"name": "新设备"}]}
        new_deposit_info = {"should_receive": 2000}

        # When
        payload = UpdateVCSchema(
            id=sample_virtual_contract.id,
            description=new_description,
            elements=new_elements,
            deposit_info=new_deposit_info
        )
        result = update_vc_action(db_session, payload)

        # Then
        assert result.success is True

    def test_update_vc_not_found(self, db_session):
        """❌ VC 不存在"""
        payload = UpdateVCSchema(
            id=99999,
            description="描述",
            elements={},
            deposit_info={}
        )
        result = update_vc_action(db_session, payload)

        assert result.success is False


class TestDeleteVCAction:
    """删除虚拟合同测试"""

    def test_delete_vc_success(self, db_session, sample_virtual_contract):
        """✅ 正常删除 VC"""
        # Given
        vc_id = sample_virtual_contract.id

        # When
        payload = DeleteVCSchema(id=vc_id)
        result = delete_vc_action(db_session, payload)

        # Then
        assert result.success is True

    def test_delete_vc_not_found(self, db_session):
        """❌ VC 不存在"""
        payload = DeleteVCSchema(id=99999)
        result = delete_vc_action(db_session, payload)

        assert result.success is False