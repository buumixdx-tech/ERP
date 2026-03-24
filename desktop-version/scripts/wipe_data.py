import argparse
import os
import sys

# 将项目根目录添加到系统路径以导入项目内模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from models import Base

def wipe_database(env):
    """
    根据环境参数彻底清空并重建数据库
    """
    # 确定数据库路径和 URI
    if env == 'prod':
        db_path = os.path.join('data', 'business_system.db')
        db_uri = f'sqlite:///{db_path}'
        print(f"⚠️ 目标：【生产环境】数据库 -> {db_path}")
    elif env == 'test':
        db_path = os.path.join('data', 'test.db')
        db_uri = f'sqlite:///{db_path}'
        print(f"⚠️ 目标：【测试环境】数据库 -> {db_path}")
    else:
        print("❌ 无效的环境参数。")
        return

    abs_db_path = os.path.abspath(db_path)
    
    # 检测数据库是否存在
    if not os.path.exists(abs_db_path):
        print(f"❌ 未找到数据库文件: {abs_db_path}")
        return

    # 安全确认机制
    print("=" * 60)
    print("🔥 危险警告: 此操作将抹除指定数据库内的**所有**数据且不可恢复！")
    print("如果表与表之间有关联外键，本方法直接重建全量表结构，会连同依赖全部彻底重置。")
    print("=" * 60)
    
    confirm = input(f"请输入 'ERASE' 确认清空 {env} 数据库：")
    
    if confirm != "ERASE":
        print("✋ 操作已取消。")
        return

    try:
        # 重置逻辑：通过 SQLAlchemy 直接删除所有表并重构，而非使用 DELETE，避免外键约束导致报错死锁。
        engine = create_engine(db_uri)
        
        print("🗑️ 正在销毁现有表及所有数据...")
        Base.metadata.drop_all(bind=engine)
        
        print("🏗️ 正在重新建立全新的表结构...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ 数据库数据抹除与初始化完成！")
    except Exception as e:
        print(f"❌ 抹除失败：{e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="闪饮ERP数据强力清除脚本 (包含外键约束重置)")
    parser.add_argument("env", choices=["prod", "test"], help="要抹除的环境 [prod / test]")
    
    args = parser.parse_args()
    wipe_database(args.env)
