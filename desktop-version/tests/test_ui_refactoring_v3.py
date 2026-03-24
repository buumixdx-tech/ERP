import pytest
from datetime import datetime
from models import get_session, Business, ChannelCustomer, Supplier, SKU, Point, BankAccount, VirtualContract, Logistics, ExpressOrder, TimeRule
from logic.constants import VCType, VCStatus, SubjectStatus, CashStatus, CashFlowType, AccountOwnerType, PointType
from logic.master.queries import get_customers_for_ui, get_suppliers_for_ui, get_points_for_ui, get_bank_accounts_for_ui
from logic.logistics.queries import get_logistics_list_for_ui, get_express_orders_by_logistics
from logic.vc.queries import get_vc_list_for_overview, get_vc_by_id
from logic.business.queries import get_business_detail
from logic.time_rules.queries import get_time_rules_for_ui

def test_get_time_rules_for_ui_fields():
    """验证时间规则查询包含必备字段"""
    results = get_time_rules_for_ui(limit=5)
    if results:
        rule = results[0]
        assert "id" in rule
        assert "status_label" in rule
        assert "created_at" in rule
    session = get_session()
    # 确保至少有一个数据
    p = session.query(Point).first()
    if not p:
        pytest.skip("No Point data for testing")
    
    results = get_points_for_ui(limit=5)
    assert isinstance(results, list)
    if results:
        point_dict = results[0]
        assert isinstance(point_dict, dict)
        assert "id" in point_dict
        assert "owner_label" in point_dict
        assert "customer_name" in point_dict
        assert "type" in point_dict
        assert "address" in point_dict

def test_get_suppliers_for_ui_fields():
    """验证供应商查询包含 category 字段"""
    results = get_suppliers_for_ui(limit=1)
    if results:
        sup = results[0]
        assert "category" in sup
        assert isinstance(sup["category"], str)

def test_get_bank_accounts_for_ui_fields():
    """验证银行账户查询包含 owner_label 和 holder_name"""
    results = get_bank_accounts_for_ui(limit=1)
    if results:
        acc = results[0]
        assert "owner_label" in acc
        assert "holder_name" in acc
        assert "account_no" in acc
        # 验证账号不是脱敏的（用于编辑器）
        assert "*" not in acc["account_no"] or len(acc["account_no"]) > 10

def test_get_logistics_list_for_ui_fields():
    """验证物流列表包含基础字段且不报属性错误"""
    results = get_logistics_list_for_ui(limit=1)
    if results:
        log = results[0]
        assert "id" in log
        assert "status" in log
        assert "timestamp" in log
        assert "vc_description" in log

def test_get_express_orders_by_logistics_fields():
    """验证快递单查询包含 created_at (映射自 timestamp)"""
    # 找一个有快递单的物流 ID
    session = get_session()
    eo = session.query(ExpressOrder).first()
    if eo:
        results = get_express_orders_by_logistics(eo.logistics_id)
        assert isinstance(results, list)
        if results:
            order = results[0]
            assert "created_at" in order
            # 验证时间格式
            assert ":" in order["created_at"]

def test_get_business_detail_fields():
    """验证业务详情包含顶层 customer_id"""
    session = get_session()
    biz = session.query(Business).first()
    if biz:
        detail = get_business_detail(biz.id)
        assert detail is not None
        assert "customer_id" in detail
        assert "id" in detail
        assert isinstance(detail["customer"], dict)

def test_calculate_cashflow_progress_robustness():
    """测试计算进度对 None 值的防御性"""
    from logic.services import calculate_cashflow_progress
    session = get_session()
    
    # 构造一个极简 VC 字典，模拟缺失 elements
    mock_vc = {
        "id": 9999,
        "type": VCType.EQUIPMENT_PROCUREMENT,
        "elements": None,
        "deposit_info": None
    }
    
    # 不应报错
    progress = calculate_cashflow_progress(session, mock_vc, [])
    assert "goods" in progress
    assert progress["goods"]["total"] == 0.0
    assert progress["deposit"]["should"] == 0.0

def test_get_suggested_cashflow_parties_dict_support():
    """测试建议收付方适配字典对象"""
    from logic.services import get_suggested_cashflow_parties
    session = get_session()
    
    mock_vc = {
        "id": 8888,
        "type": VCType.MATERIAL_SUPPLY,
        "business_id": None,
        "elements": {"total_amount": 1000}
    }
    
    # 不应报 AttributeError: 'dict' object has no attribute 'type'
    parties = get_suggested_cashflow_parties(session, mock_vc, cf_type=CashFlowType.FULFILLMENT)
    assert len(parties) == 4
    # 物料供应建议收付方：付款方是客户
    assert parties[0] == AccountOwnerType.CUSTOMER

if __name__ == "__main__":
    pytest.main([__file__])
