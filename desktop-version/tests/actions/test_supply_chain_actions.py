"""
供应链 Actions 单元测试
"""

import pytest
from logic.supply_chain import create_supply_chain_action, CreateSupplyChainSchema


class TestSupplyChainActions:
    """供应链管理测试"""

    def test_create_supply_chain_success(self, db_session, sample_supplier):
        """✅ 正常创建供应链协议"""
        # Given
        payload = CreateSupplyChainSchema(
            supplier_id=sample_supplier.id,
            supplier_name=sample_supplier.name,
            type="设备",
            pricing_config={"设备A": 1000, "设备B": 2000},
            payment_terms={"prepayment_ratio": 0.3, "balance_period": 30}
        )

        # When
        result = create_supply_chain_action(db_session, payload)

        # Then
        assert result.success is True

    def test_create_supply_chain_supplier_not_found(self, db_session):
        """❌ 供应商不存在"""
        payload = CreateSupplyChainSchema(
            supplier_id=99999,
            supplier_name="不存在的供应商",
            type="设备",
            pricing_config={"设备A": 1000},
            payment_terms={}
        )

        result = create_supply_chain_action(db_session, payload)

        assert result.success is False

    def test_create_supply_chain_with_template_rules(self, db_session, sample_supplier):
        """✅ 创建供应链时附加模板规则"""
        payload = CreateSupplyChainSchema(
            supplier_id=sample_supplier.id,
            supplier_name=sample_supplier.name,
            type="设备",
            pricing_config={"设备A": 1000},
            payment_terms={"prepayment_ratio": 0.3},
            contract_num="SC-20260001"
        )

        result = create_supply_chain_action(db_session, payload)

        assert result.success is True