"""
选择性清空数据库脚本 - 保留主数据、供应链、业务
用法: python scripts/selective_wipe.py [prod|test]
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from models import Base

# =====================================================
# 保留的表 (主数据、供应链、业务)
# =====================================================
KEEP_TABLES = {
    # 主数据
    'channel_customers',   # 渠道客户
    'suppliers',           # 供应商
    'points',              # 点位
    'skus',                # SKU
    'external_partners',    # 外部合作方
    'bank_accounts',       # 银行账户

    # 供应链
    'supply_chains',       # 供应链协议
    'supply_chain_items',   # 供应链明细

    # 业务
    'business',            # 业务
    'contracts',           # 合同
}

# =====================================================
# 清理的表 (执行/交易数据)
# =====================================================
WIPE_TABLES = {
    # 虚拟合同
    'virtual_contracts',           # 虚拟合同
    'vc_status_logs',              # VC状态日志
    'vc_history',                  # VC历史版本

    # 财务
    'finance_accounts',             # 会计科目
    'financial_journal',           # 财务凭证
    'cash_flow_ledger',            # 现金流量表
    'cash_flows',                  # 资金流水

    # 物流
    'logistics',                   # 物流
    'express_orders',              # 快递单

    # 库存
    'equipment_inventory',         # 设备库存
    'material_inventory',          # 物料库存

    # 规则引擎
    'time_rules',                  # 时间规则

    # 系统
    'system_events',              # 系统事件
}


def selective_wipe(env='prod'):
    """选择性清空数据库，保留指定表"""
    # 确定数据库路径
    if env == 'prod':
        db_path = os.path.join('data', 'business_system.db')
    elif env == 'test':
        db_path = os.path.join('data', 'test.db')
    else:
        print(f"❌ 无效的环境: {env}")
        return

    db_uri = f'sqlite:///{db_path}'
    abs_db_path = os.path.abspath(db_path)

    if not os.path.exists(abs_db_path):
        print(f"❌ 未找到数据库: {abs_db_path}")
        return

    print(f"目标数据库: {abs_db_path}")
    print("=" * 60)
    print("KEEP tables:")
    for t in sorted(KEEP_TABLES):
        print(f"   [KEEP] {t}")
    print()
    print("WIPE tables:")
    for t in sorted(WIPE_TABLES):
        print(f"   [WIPE] {t}")
    print("=" * 60)

    confirm = input("Enter 'WIPE' to confirm: ")
    if confirm != "WIPE":
        print("Cancelled")
        return

    try:
        engine = create_engine(db_uri, connect_args={"check_same_thread": False})

        with engine.connect() as conn:
            # 禁用外键约束
            conn.execute(text("PRAGMA foreign_keys = OFF"))
            conn.commit()

            # 清空需要清理的表
            for table in sorted(WIPE_TABLES):
                try:
                    conn.execute(text(f"DELETE FROM {table}"))
                    print(f"   [WIPED] {table}")
                except Exception as e:
                    print(f"   [FAIL] {table}: {e}")

            # 统一提交
            conn.commit()

            # 重新启用外键约束
            conn.execute(text("PRAGMA foreign_keys = ON"))
            conn.commit()

        print()
        print("Done!")

        # 验证结果
        with engine.connect() as conn:
            print()
            print("Verification:")
            print("-" * 40)

            # 检查保留表
            print("KEEP tables (should have data):")
            for table in sorted(KEEP_TABLES):
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                print(f"   {table}: {result} rows")

            print()
            print("WIPE tables (should be empty):")
            for table in sorted(WIPE_TABLES):
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                status = "[OK]" if result == 0 else "[WARN]"
                print(f"   {status} {table}: {result} rows")

    except Exception as e:
        print(f"ERROR: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="选择性清空数据库 (保留主数据/供应链/业务)")
    parser.add_argument("env", choices=["prod", "test"], help="环境 [prod / test]")
    args = parser.parse_args()
    selective_wipe(args.env)
