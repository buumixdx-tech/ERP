import sqlite3
import os

def init_business_data(db_path="data/test.db"):
    """
    按照指定顺序清空数据库表，进行业务初始化。
    """
    if not os.path.exists(db_path):
        alt_path = os.path.join("data", db_path)
        if os.path.exists(alt_path):
            db_path = alt_path
        else:
            print(f"❌ 错误: 未找到数据库文件 {db_path}")
            return

    # 您指定的清空顺序
    tables_to_clear = [
        "express_orders",
        "logistics",
        "material_inventory",
        "equipment_inventory",
        "cash_flows",
        "cash_flow_ledger",
        "financial_journal",
        "vc_status_logs",
        "virtual_contracts",
        "time_rules"
    ]

    print(f"🚀 开始初始化数据库: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 1. 暂时关闭外键约束
        cursor.execute("PRAGMA foreign_keys = OFF;")

        for table in tables_to_clear:
            try:
                # 检查表是否存在
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
                if not cursor.fetchone():
                    print(f"⚠️ 跳过: 表 '{table}' 不存在。")
                    continue

                # 清空表数据
                cursor.execute(f"DELETE FROM {table};")
                
                # 重置自增 ID (仅当 sqlite_sequence 存在时)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence';")
                if cursor.fetchone():
                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")
                
                print(f"✅ 已清空表: {table}")
            except Exception as e:
                print(f"❌ 清空表 {table} 时出错: {e}")

        # 2. 重新开启外键约束
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        conn.commit()
        conn.close()
        print("\n✨ 业务初始化完成！选定表已清空并重置 ID。")

    except Exception as e:
        print(f"💥 数据库连接错误: {e}")

if __name__ == "__main__":
    init_business_data()
