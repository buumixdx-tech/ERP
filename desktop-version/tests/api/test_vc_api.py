"""
虚拟合同 API 端点单元测试
"""

import pytest
from fastapi.testclient import TestClient


# API 测试需要的请求头（从 api/deps.py 获取默认值）
API_HEADERS = {"x-api-key": "dev-key"}


class TestVCAPI:
    """虚拟合同 API 测试"""

    def test_list_vcs_returns_pagination(self, client: TestClient):
        """✅ 列表接口返回分页数据"""
        # Given & When
        response = client.get(
            "/api/v1/vc/list?page=1&size=10",
            headers=API_HEADERS
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page" in data["data"]
        assert "size" in data["data"]

    def test_list_vcs_with_filters(self, client: TestClient):
        """✅ 列表接口支持筛选"""
        # Given & When
        response = client.get(
            "/api/v1/vc/list?status=执行&page=1&size=10",
            headers=API_HEADERS
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_vc_detail_not_found(self, client: TestClient):
        """✅ 获取不存在的 VC 返回错误"""
        # Given & When
        response = client.get(
            "/api/v1/vc/99999",
            headers=API_HEADERS
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_vc_detail_includes_relations(self, client: TestClient):
        """✅ 详情接口包含关联数据"""
        # Given: 需要先创建一个 VC
        # 先创建必要的测试数据
        from models import ChannelCustomer, Business, VirtualContract, get_session
        
        session = get_session()
        try:
            # 创建测试数据
            customer = ChannelCustomer(name="API测试客户")
            session.add(customer)
            session.flush()

            business = Business(
                customer_id=customer.id,
                status="业务开展",
                details={}
            )
            session.add(business)
            session.flush()

            vc = VirtualContract(
                business_id=business.id,
                type="设备采购",
                elements={"total_amount": 10000},
                deposit_info={},
                status="执行",
                subject_status="执行",
                cash_status="执行"
            )
            session.add(vc)
            session.commit()
            vc_id = vc.id
        finally:
            session.close()

        # When: 获取详情
        response = client.get(
            f"/api/v1/vc/{vc_id}",
            headers=API_HEADERS
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "status_logs" in data["data"]
        assert "logistics" in data["data"]
        assert "cash_flows" in data["data"]

    def test_update_vc_not_found(self, client: TestClient):
        """❌ 更新不存在的 VC"""
        # Given
        payload = {
            "vc_id": 99999,
            "description": "测试",
            "elements": {},
            "deposit_info": {}
        }

        # When
        response = client.post(
            "/api/v1/vc/update",
            json=payload,
            headers=API_HEADERS
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_delete_vc_not_found(self, client: TestClient):
        """❌ 删除不存在的 VC"""
        # Given
        payload = {"vc_id": 99999}

        # When
        response = client.post(
            "/api/v1/vc/delete",
            json=payload,
            headers=API_HEADERS
        )

        # Then
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


# 为 pytest 提供的 client fixture
@pytest.fixture(scope="session")
def client():
    """创建测试客户端"""
    from api.app import create_app
    
    app = create_app()
    return TestClient(app)