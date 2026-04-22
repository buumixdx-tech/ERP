"""
services 模块单元测试
测试 get_returnable_items 等跨模块业务逻辑
"""

import pytest
from datetime import datetime
from logic import services
from logic.constants import (
    VCType, VCStatus, ReturnDirection, OperationalStatus, DeviceStatus
)
from models import VirtualContract, EquipmentInventory, MaterialInventory, SKU, Point, CashFlow


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def equip_vc(db_session, sample_business, sample_sku):
    """设备采购型虚拟合同（含 EquipmentInventory 实物档案）"""
    vc = VirtualContract(
        business_id=sample_business.id,
        type=VCType.EQUIPMENT_PROCUREMENT,
        elements={
            "elements": [
                {
                    "id": "ei_sn_001",
                    "sku_id": sample_sku.id,
                    "qty": 3,
                    "price": 1000,
                    "deposit": 100,
                    "subtotal": 3000,
                    "sn_list": []
                }
            ],
            "total_amount": 3000
        },
        deposit_info={"should_receive": 300, "total_deposit": 0},
        status=VCStatus.EXE,
        subject_status="发货",
        cash_status=VCStatus.EXE
    )
    db_session.add(vc)
    db_session.flush()

    # 创建 3 台设备的实物档案（均在运营中）
    for i in range(3):
        eq = EquipmentInventory(
            virtual_contract_id=vc.id,
            sku_id=sample_sku.id,
            sn=f"SN-EQ-{i+1:03d}",
            operational_status=OperationalStatus.OPERATING,
            device_status=DeviceStatus.NORMAL,
            deposit_amount=100
        )
        db_session.add(eq)
    db_session.flush()
    return vc


@pytest.fixture
def stock_vc(db_session, sample_business, sample_sku):
    """库存采购型虚拟合同（含 STOCK 状态 EquipmentInventory）"""
    vc = VirtualContract(
        business_id=sample_business.id,
        type=VCType.STOCK_PROCUREMENT,
        elements={
            "elements": [
                {
                    "id": "si_sn_001",
                    "sku_id": sample_sku.id,
                    "qty": 2,
                    "price": 800,
                    "deposit": 50,
                    "subtotal": 1600,
                    "sn_list": []
                }
            ],
            "total_amount": 1600
        },
        deposit_info={"should_receive": 100, "total_deposit": 0},
        status=VCStatus.EXE,
        subject_status="发货",
        cash_status=VCStatus.EXE
    )
    db_session.add(vc)
    db_session.flush()

    # 2 台设备在库存状态
    for i in range(2):
        eq = EquipmentInventory(
            virtual_contract_id=vc.id,
            sku_id=sample_sku.id,
            sn=f"SN-STOCK-{i+1:03d}",
            operational_status=OperationalStatus.STOCK,
            device_status=DeviceStatus.NORMAL,
            deposit_amount=50
        )
        db_session.add(eq)
    db_session.flush()
    return vc


@pytest.fixture
def material_procurement_vc(db_session, sample_business, sample_sku):
    """物料采购型虚拟合同（含批次信息，精确追溯）"""
    # 创建两个点位
    point_a = Point(name="仓库A", customer_id=sample_business.customer_id)
    point_b = Point(name="仓库B", customer_id=sample_business.customer_id)
    db_session.add(point_a)
    db_session.add(point_b)
    db_session.flush()

    vc = VirtualContract(
        business_id=sample_business.id,
        type=VCType.MATERIAL_PROCUREMENT,
        elements={
            "elements": [
                {
                    "sku_id": sample_sku.id,
                    "sku_name": sample_sku.name,
                    "qty": 20,
                    "price": 10,
                    "receiving_point_id": point_a.id,
                    "batch_no": "BATCH-A"
                },
                {
                    "sku_id": sample_sku.id,
                    "sku_name": sample_sku.name,
                    "qty": 30,
                    "price": 10,
                    "receiving_point_id": point_b.id,
                    "batch_no": "BATCH-B"
                }
            ],
            "total_amount": 500
        },
        deposit_info={"should_receive": 0, "total_deposit": 0},
        status=VCStatus.EXE,
        subject_status="执行",
        cash_status=VCStatus.EXE
    )
    db_session.add(vc)
    db_session.flush()

    # 物料库存批次（用于参考，不参与退货计算）
    mat_inv_a = MaterialInventory(
        sku_id=sample_sku.id,
        batch_no="BATCH-A",
        point_id=point_a.id,
        qty=20.0
    )
    mat_inv_b = MaterialInventory(
        sku_id=sample_sku.id,
        batch_no="BATCH-B",
        point_id=point_b.id,
        qty=15.0
    )
    db_session.add(mat_inv_a)
    db_session.add(mat_inv_b)
    db_session.flush()
    return vc


@pytest.fixture
def material_supply_vc_new_structure(db_session, sample_business, sample_sku):
    """物料供应型虚拟合同（新结构 elements[]，含 Point 记录）"""
    # 创建一个 Point 记录用于关联（直接用字符串 type，避免费型枚举存储问题）
    point = Point(
        name="客户点位-A",
        customer_id=sample_business.customer_id,
        type="运营点位"
    )
    db_session.add(point)
    db_session.flush()

    vc = VirtualContract(
        business_id=sample_business.id,
        type=VCType.MATERIAL_SUPPLY,
        elements={
            "elements": [
                {
                    "sku_id": sample_sku.id,
                    "sku_name": sample_sku.name,
                    "qty": 30,
                    "price": 15,
                    "receiving_point_id": point.id
                }
            ],
            "total_amount": 450
        },
        deposit_info={"should_receive": 0, "total_deposit": 0},
        status=VCStatus.EXE,
        subject_status="发货",
        cash_status=VCStatus.EXE
    )
    db_session.add(vc)
    db_session.flush()
    return vc


@pytest.fixture
def material_supply_vc_old_structure(db_session, sample_business, sample_sku):
    """物料供应型虚拟合同（旧结构 points[]）"""
    vc = VirtualContract(
        business_id=sample_business.id,
        type=VCType.MATERIAL_SUPPLY,
        elements={
            "points": [
                {
                    "pointName": "旧仓库-测试",
                    "items": [
                        {"sku_id": sample_sku.id, "sku_name": sample_sku.name, "qty": 10, "price": 20}
                    ]
                }
            ],
            "total_amount": 200
        },
        deposit_info={"should_receive": 0, "total_deposit": 0},
        status=VCStatus.EXE,
        subject_status="发货",
        cash_status=VCStatus.EXE
    )
    db_session.add(vc)
    db_session.flush()
    return vc


# =============================================================================
# get_returnable_items — 设备采购类退货
# =============================================================================

class TestGetReturnableEquipment:
    """设备采购/库存采购退货：按 EquipmentInventory 实物档案计算"""

    def test_equipment_procurement_returnable_operating(self, db_session, equip_vc):
        """✅ 设备采购退货（客户→我）：返回所有 OPERATING 状态的设备"""
        result = services.get_returnable_items(
            db_session, equip_vc.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        assert len(result) == 3
        for item in result:
            assert item["qty"] == 1
            assert item["sn"].startswith("SN-EQ-")
            assert item["price"] == 0.0  # CUSTOMER_TO_US → price=0

    def test_equipment_procurement_returnable_stock(self, db_session, stock_vc):
        """✅ 设备采购退货（我→供应商）：返回所有 STOCK 状态的设备"""
        result = services.get_returnable_items(
            db_session, stock_vc.id, {ReturnDirection.US_TO_SUPPLIER}
        )
        assert len(result) == 2
        for item in result:
            assert item["qty"] == 1
            assert item["sn"].startswith("SN-STOCK-")
            # US_TO_SUPPLIER: price 从 SKU.params.unit_price 获取（sample_sku 无 params 时 fallback 为 0）
            assert item["price"] >= 0

    def test_equipment_procurement_locked_by_existing_return_sn(self, db_session, equip_vc, sample_sku):
        """✅ 已有退货单（SN 级别）锁定：被锁定的 SN 不出现在退货列表"""
        # 创建一个退货单，锁定 SN-EQ-001
        return_vc = VirtualContract(
            business_id=equip_vc.business_id,
            type=VCType.RETURN,
            related_vc_id=equip_vc.id,
            elements={
                "elements": [
                    {"sn": "SN-EQ-001", "sku_id": sample_sku.id, "qty": 1}
                ]
            },
            status=VCStatus.EXE,
            subject_status="执行",
            cash_status=VCStatus.EXE
        )
        db_session.add(return_vc)
        db_session.flush()

        result = services.get_returnable_items(
            db_session, equip_vc.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        assert len(result) == 2
        sns = {r["sn"] for r in result}
        assert "SN-EQ-001" not in sns
        assert "SN-EQ-002" in sns
        assert "SN-EQ-003" in sns

    def test_unknown_vc_id_returns_empty(self, db_session):
        """✅ 无效 VC ID：返回空列表"""
        result = services.get_returnable_items(db_session, 99999, {ReturnDirection.CUSTOMER_TO_US})
        assert result == []


# =============================================================================
# get_returnable_items — 物料采购类退货
# =============================================================================

class TestGetReturnableMaterialProcurement:
    """物料采购退货：按原始 VC elements 批次精确追溯"""

    def test_material_procurement_returnable(self, db_session, material_procurement_vc):
        """✅ 物料采购退货：按原始 VC elements 批次和数量返回"""
        result = services.get_returnable_items(
            db_session, material_procurement_vc.id, {ReturnDirection.US_TO_SUPPLIER}
        )
        # BATCH-A: 20 at 仓库A, BATCH-B: 30 at 仓库B
        assert len(result) == 2
        by_point = {r["point_name"]: r for r in result}
        assert by_point["仓库A"]["qty"] == 20
        assert by_point["仓库A"]["batch_no"] == "BATCH-A"
        assert by_point["仓库B"]["qty"] == 30
        assert by_point["仓库B"]["batch_no"] == "BATCH-B"

    def test_material_procurement_returnable_partial(self, db_session, sample_business, sample_sku):
        """✅ 物料采购退货：按原始 VC 批次数量，不受当前库存限制"""
        point_x = Point(name="仓库X", customer_id=sample_business.customer_id)
        db_session.add(point_x)
        db_session.flush()

        vc = VirtualContract(
            business_id=sample_business.id,
            type=VCType.MATERIAL_PROCUREMENT,
            elements={
                "elements": [
                    {"sku_id": sample_sku.id, "name": sample_sku.name, "qty": 5, "price": 10,
                     "receiving_point_id": point_x.id, "batch_no": "BATCH-X"}
                ]
            },
            deposit_info={"should_receive": 0, "total_deposit": 0},
            status=VCStatus.EXE,
            subject_status="执行",
            cash_status=VCStatus.EXE
        )
        db_session.add(vc)
        db_session.flush()

        mat_inv = MaterialInventory(
            sku_id=sample_sku.id,
            batch_no="BATCH-X",
            point_id=point_x.id,
            qty=3.0
        )
        db_session.add(mat_inv)
        db_session.flush()

        result = services.get_returnable_items(db_session, vc.id, {ReturnDirection.US_TO_SUPPLIER})
        assert len(result) == 1
        assert result[0]["qty"] == 5  # 退货基于 VC 批次数量，不看库存

    def test_material_procurement_locked_by_existing_return_qty(
        self, db_session, material_procurement_vc, sample_sku
    ):
        """✅ 已有退货单（数量级别）锁定：已退数量从对应批次可退量中 FIFO 扣除"""
        # BATCH-A at 仓库A: qty=20, 已有退货10 → 剩余10
        # BATCH-B at 仓库B: qty=30, 未退货 → 剩余30
        return_vc = VirtualContract(
            business_id=material_procurement_vc.business_id,
            type=VCType.RETURN,
            related_vc_id=material_procurement_vc.id,
            elements={
                "elements": [
                    {"sku_id": sample_sku.id, "point_name": "仓库A", "qty": 10}
                ]
            },
            status=VCStatus.EXE,
            subject_status="执行",
            cash_status=VCStatus.EXE
        )
        db_session.add(return_vc)
        db_session.flush()

        result = services.get_returnable_items(
            db_session, material_procurement_vc.id, {ReturnDirection.US_TO_SUPPLIER}
        )
        by_point = {r["point_name"]: r for r in result}
        assert by_point["仓库A"]["qty"] == 10  # 20 - 10 = 10
        assert by_point["仓库A"]["batch_no"] == "BATCH-A"
        assert by_point["仓库B"]["qty"] == 30  # 未退货
        assert by_point["仓库B"]["batch_no"] == "BATCH-B"


# =============================================================================
# get_returnable_items — 物料供应类退货
# =============================================================================

class TestGetReturnableMaterialSupply:
    """物料供应退货：客户退回，支持新/旧两种 elements 结构"""

    def test_material_supply_new_structure(self, db_session, material_supply_vc_new_structure):
        """✅ 物料供应退货（新结构 elements[]）：按 receiving_point_id 分组"""
        result = services.get_returnable_items(
            db_session, material_supply_vc_new_structure.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        assert len(result) == 1
        assert result[0]["qty"] == 30
        assert result[0]["point_name"] == "客户点位-A"

    def test_material_supply_old_structure(self, db_session, material_supply_vc_old_structure):
        """✅ 物料供应退货（旧结构 points[]）：使用 pointName 分组"""
        result = services.get_returnable_items(
            db_session, material_supply_vc_old_structure.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        assert len(result) == 1
        assert result[0]["point_name"] == "旧仓库-测试"
        assert result[0]["qty"] == 10

    def test_material_supply_locked_by_existing_return(
        self, db_session, material_supply_vc_new_structure, sample_sku
    ):
        """✅ 物料供应退货：已退数量从可退量中扣除"""
        point_id = material_supply_vc_new_structure.elements["elements"][0]["receiving_point_id"]
        # point_name 必须与 supply VC 的 point.name 一致，用于 matched_qtys 计算
        return_vc = VirtualContract(
            business_id=material_supply_vc_new_structure.business_id,
            type=VCType.RETURN,
            related_vc_id=material_supply_vc_new_structure.id,
            elements={
                "elements": [
                    {
                        "sku_id": sample_sku.id,
                        "receiving_point_id": point_id,
                        "point_name": "客户点位-A",  # 必须与 supply VC 的 point.name 匹配
                        "qty": 10
                    }
                ]
            },
            status=VCStatus.EXE,
            subject_status="执行",
            cash_status=VCStatus.EXE
        )
        db_session.add(return_vc)
        db_session.flush()

        result = services.get_returnable_items(
            db_session, material_supply_vc_new_structure.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        assert len(result) == 1
        assert result[0]["qty"] == 20  # 30 - 10 = 20


# =============================================================================
# get_returnable_items — 边界情况
# =============================================================================

class TestGetReturnableEdgeCases:
    """边界情况"""

    def test_cancelled_return_vc_does_not_lock(self, db_session, equip_vc, sample_sku):
        """✅ 已取消的退货单不计入锁定量"""
        return_vc = VirtualContract(
            business_id=equip_vc.business_id,
            type=VCType.RETURN,
            related_vc_id=equip_vc.id,
            elements={
                "elements": [
                    {"sn": "SN-EQ-001", "sku_id": sample_sku.id, "qty": 1}
                ]
            },
            status=VCStatus.CANCELLED,  # 已取消
            subject_status="执行",
            cash_status=VCStatus.EXE
        )
        db_session.add(return_vc)
        db_session.flush()

        result = services.get_returnable_items(
            db_session, equip_vc.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        # 取消的退货不锁定，应返回全部 3 台
        assert len(result) == 3

    def test_no_inventory_returns_empty(self, db_session, sample_business):
        """✅ 设备采购合同但无实物档案：返回空（无货可退）"""
        vc = VirtualContract(
            business_id=sample_business.id,
            type=VCType.EQUIPMENT_PROCUREMENT,
            elements={
                "elements": [
                    {"sku_id": 1, "qty": 5, "price": 1000, "deposit": 100}
                ]
            },
            deposit_info={"should_receive": 500, "total_deposit": 0},
            status=VCStatus.EXE,
            subject_status="执行",
            cash_status=VCStatus.EXE
        )
        db_session.add(vc)
        db_session.flush()

        result = services.get_returnable_items(
            db_session, vc.id, {ReturnDirection.CUSTOMER_TO_US}
        )
        assert result == []
