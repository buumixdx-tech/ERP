"""
数据库索引添加脚本
安全地为现有数据库添加性能优化索引

使用方法:
    python scripts/add_indexes.py

特性:
    - 自动跳过已存在的索引（IF NOT EXISTS）
    - 事务安全，失败自动回滚
    - 详细的执行日志
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import engine, init_db
from sqlalchemy import text


def add_indexes():
    """安全地添加索引，自动跳过已存在的索引"""
    # 重新导入 engine，确保 init_db() 后获取正确的实例
    import models
    if models.engine is None:
        print("❌ 错误: 数据库引擎未初始化")
        sys.exit(1)
    
    # 使用 models.engine 而不是导入的 engine
    global engine
    engine = models.engine
    
    # 定义所有索引
    # 格式: (索引名称, SQL创建语句)
    indexes = [
        # ========== 虚拟合同 (VirtualContract) 索引 ==========
        ("ix_vc_business_id", 
         "CREATE INDEX IF NOT EXISTS ix_vc_business_id ON virtual_contracts(business_id)"),
        
        ("ix_vc_status", 
         "CREATE INDEX IF NOT EXISTS ix_vc_status ON virtual_contracts(status)"),
        
        ("ix_vc_business_status", 
         "CREATE INDEX IF NOT EXISTS ix_vc_business_status ON virtual_contracts(business_id, status)"),
        
        ("ix_vc_type", 
         "CREATE INDEX IF NOT EXISTS ix_vc_type ON virtual_contracts(type)"),
        
        ("ix_vc_status_timestamp", 
         "CREATE INDEX IF NOT EXISTS ix_vc_status_timestamp ON virtual_contracts(status_timestamp)"),
        
        ("ix_vc_supply_chain", 
         "CREATE INDEX IF NOT EXISTS ix_vc_supply_chain ON virtual_contracts(supply_chain_id)"),
        
        # ========== 设备库存 (EquipmentInventory) 索引 ==========
        ("ix_eq_vc_id", 
         "CREATE INDEX IF NOT EXISTS ix_eq_vc_id ON equipment_inventory(virtual_contract_id)"),
        
        ("ix_eq_point_id", 
         "CREATE INDEX IF NOT EXISTS ix_eq_point_id ON equipment_inventory(point_id)"),
        
        ("ix_eq_op_status", 
         "CREATE INDEX IF NOT EXISTS ix_eq_op_status ON equipment_inventory(operational_status)"),
        
        ("ix_eq_sku_id", 
         "CREATE INDEX IF NOT EXISTS ix_eq_sku_id ON equipment_inventory(sku_id)"),
        
        # ========== 资金流 (CashFlow) 索引 ==========
        ("ix_cf_vc_id", 
         "CREATE INDEX IF NOT EXISTS ix_cf_vc_id ON cash_flows(virtual_contract_id)"),
        
        ("ix_cf_type", 
         "CREATE INDEX IF NOT EXISTS ix_cf_type ON cash_flows(type)"),
        
        ("ix_cf_transaction_date", 
         "CREATE INDEX IF NOT EXISTS ix_cf_transaction_date ON cash_flows(transaction_date)"),
        
        ("ix_cf_vc_type", 
         "CREATE INDEX IF NOT EXISTS ix_cf_vc_type ON cash_flows(virtual_contract_id, type)"),
    ]
    
    success_count = 0
    skip_count = 0
    error_count = 0
    
    print("=" * 70)
    print("🚀 开始添加数据库索引")
    print("=" * 70)
    print()
    
    with engine.connect() as conn:
        # 开始事务
        trans = conn.begin()
        try:
            for index_name, sql in indexes:
                try:
                    conn.execute(text(sql))
                    print(f"✅ 已创建索引: {index_name}")
                    success_count += 1
                except Exception as e:
                    error_msg = str(e).lower()
                    # 检查是否是索引已存在的错误
                    if "already exists" in error_msg or "duplicate" in error_msg:
                        print(f"⏭️  索引已存在，跳过: {index_name}")
                        skip_count += 1
                    else:
                        print(f"❌ 创建失败: {index_name} - {e}")
                        error_count += 1
            
            # 提交事务
            trans.commit()
            print()
            print("=" * 70)
            print("✨ 索引添加完成!")
            print("=" * 70)
            print(f"  成功创建: {success_count} 个")
            print(f"  已存在跳过: {skip_count} 个")
            print(f"  失败: {error_count} 个")
            print()
            print("📊 验证索引:")
            print("-" * 70)
            
            # 显示已创建的索引列表
            result = conn.execute(text("""
                SELECT name, tbl_name 
                FROM sqlite_master 
                WHERE type='index' AND name LIKE 'ix_%'
                ORDER BY tbl_name, name
            """))
            
            current_table = None
            for row in result:
                if row.tbl_name != current_table:
                    current_table = row.tbl_name
                    print(f"\n  📁 {current_table}:")
                print(f"      • {row.name}")
            
            print()
            print("=" * 70)
            
        except Exception as e:
            trans.rollback()
            print()
            print("❌ 事务回滚，发生错误:")
            print(f"   {e}")
            print()
            print("💡 建议:")
            print("   1. 检查数据库文件是否被占用")
            print("   2. 确认有足够的磁盘空间")
            print("   3. 查看详细的错误日志")
            sys.exit(1)


def verify_indexes():
    """验证索引是否正常工作"""
    print("\n🔍 运行索引验证查询...")
    print("-" * 70)
    
    with engine.connect() as conn:
        # 测试 1: 查询使用索引的情况
        result = conn.execute(text("""
            EXPLAIN QUERY PLAN 
            SELECT * FROM virtual_contracts 
            WHERE business_id = 1 AND status = '执行'
        """))
        
        plan = result.fetchone()
        if 'USING INDEX' in str(plan) or 'INDEX' in str(plan):
            print("✅ 索引验证通过: VirtualContract 复合索引生效")
        else:
            print("⚠️  警告: 可能未使用索引，查询计划:")
            print(f"   {plan}")
        
        # 测试 2: 统计索引数量
        result = conn.execute(text("""
            SELECT COUNT(*) as count 
            FROM sqlite_master 
            WHERE type='index' AND name LIKE 'ix_%'
        """))
        
        count = result.scalar()
        print(f"✅ 索引统计: 共 {count} 个优化索引")
    
    print("-" * 70)


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print("  数据库索引优化工具")
    print("  ShanYinERP-v4 Database Index Optimizer")
    print("=" * 70 + "\n")
    
    # 初始化数据库连接
    print("🔄 正在初始化数据库连接...")
    init_db()
    
    # 重新导入 engine，确保它被正确设置
    from models import engine as db_engine
    
    if db_engine is None:
        print("❌ 数据库引擎初始化失败")
        sys.exit(1)
    
    print("✅ 数据库连接成功\n")
    
    # 添加索引
    add_indexes()
    
    # 验证索引
    verify_indexes()
    
    print("\n" + "=" * 70)
    print("🎉 所有操作已完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
