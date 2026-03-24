"""
Pytest 配置和 Fixtures
提供测试所需的数据库会话、测试数据等
"""

import pytest
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, SupplyChain


# 测试数据库配置
TEST_DB_URL = "sqlite:///data/test.db"


@pytest.fixture(scope="session")
def engine():
    """创建测试数据库引擎（会话级别，所有测试共享）"""
    # 确保测试数据库目录存在
    db_path = "data/test.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 如果存在旧测试数据库，先删除
    if os.path.exists(db_path):
        os.remove(db_path)
    
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False}
    )
    
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # 测试结束后清理
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(engine):
    """每个测试函数独立的数据库会话（函数级别）"""
    Session = sessionmaker(bind=engine)
    session = Session()
    
    # 开启事务
    # 注意：我们不 commit，让测试在事务中运行，测试结束后自动回滚
    
    yield session
    
    # 测试后回滚，清理所有更改
    session.rollback()
    session.close()


@pytest.fixture
def sample_customer(db_session):
    """创建测试用客户数据"""
    from models import ChannelCustomer
    
    customer = ChannelCustomer(
        name="测试客户有限公司",
        info="这是一个测试客户"
    )
    db_session.add(customer)
    db_session.flush()  # 获取 ID
    
    return customer


@pytest.fixture
def sample_supplier(db_session):
    """创建测试用供应商数据"""
    from models import Supplier
    
    supplier = Supplier(
        name="测试供应商有限公司",
        category="设备",
        address="测试地址"
    )
    db_session.add(supplier)
    db_session.flush()
    
    return supplier


@pytest.fixture
def sample_sku(db_session, sample_supplier):
    """创建测试用 SKU 数据"""
    from models import SKU
    
    sku = SKU(
        supplier_id=sample_supplier.id,
        name="测试设备-001",
        type_level1="设备",
        type_level2="主机",
        model="TEST-001",
        description="测试用设备"
    )
    db_session.add(sku)
    db_session.flush()
    
    return sku


@pytest.fixture
def sample_business(db_session, sample_customer):
    """创建测试用业务数据"""
    from models import Business
    from logic.constants import BusinessStatus
    
    business = Business(
        customer_id=sample_customer.id,
        status=BusinessStatus.ACTIVE,
        details={"备注": "测试业务"}
    )
    db_session.add(business)
    db_session.flush()
    
    return business


@pytest.fixture
def sample_supply_chain(db_session, sample_supplier):
    """创建测试用供应链数据"""
    from logic.constants import SKUType
    
    sc = SupplyChain(
        supplier_id=sample_supplier.id,
        supplier_name=sample_supplier.name,
        type=SKUType.EQUIPMENT,
        pricing_config={"测试设备-001": 1000}
    )
    db_session.add(sc)
    db_session.flush()
    
    return sc


@pytest.fixture
def sample_virtual_contract(db_session, sample_business):
    """创建测试用虚拟合同数据"""
    from models import VirtualContract
    
    vc = VirtualContract(
        business_id=sample_business.id,
        type="设备采购",
        elements={
            "skus": [{"name": "测试设备", "qty": 10, "price": 1000}],
            "total_amount": 10000
        },
        deposit_info={
            "should_receive": 1000,
            "total_deposit": 0
        },
        status="执行",
        subject_status="执行",
        cash_status="执行"
    )
    db_session.add(vc)
    db_session.flush()
    
    return vc