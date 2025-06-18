#!/usr/bin/env python3
"""
测试数据库连接脚本
验证数据库连接是否正常工作
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_database_connection():
    """测试数据库连接"""
    print("🔍 测试数据库连接...")
    
    try:
        # 导入配置
        from app.core.config import get_settings
        settings = get_settings()
        
        print(f"📋 使用数据库URL: {settings.database_url.split('@')[-1] if '@' in settings.database_url else settings.database_url}")
        
        # 导入数据库管理器
        from app.database.connection import db_manager
        
        # 初始化数据库连接
        print("🚀 初始化数据库连接...")
        await db_manager.initialize()
        
        # 测试连接
        print("🔗 测试数据库连接...")
        async with db_manager.get_session() as session:
            from sqlalchemy import text
            result = await session.execute(text("SELECT 1 as test, NOW() as current_time"))
            row = result.fetchone()
            
            if row:
                print(f"✅ 数据库连接成功!")
                print(f"   测试查询结果: {row.test}")
                print(f"   数据库时间: {row.current_time}")
            else:
                print("❌ 数据库连接失败: 无法获取查询结果")
                return False
        
        # 测试数据库信息
        print("\n📊 获取数据库信息...")
        async with db_manager.get_session() as session:
            # 获取数据库版本
            result = await session.execute(text("SELECT VERSION() as version"))
            version_row = result.fetchone()
            if version_row:
                print(f"   数据库版本: {version_row.version}")
            
            # 获取当前数据库名
            result = await session.execute(text("SELECT DATABASE() as db_name"))
            db_row = result.fetchone()
            if db_row:
                print(f"   当前数据库: {db_row.db_name}")
            
            # 获取表列表
            result = await session.execute(text("SHOW TABLES"))
            tables = result.fetchall()
            if tables:
                print(f"   数据库表数量: {len(tables)}")
                print("   表列表:")
                for table in tables:
                    print(f"     - {table[0]}")
            else:
                print("   数据库中暂无表")
        
        print("\n✅ 数据库连接测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # 清理连接
        try:
            await db_manager.close()
            print("🔄 数据库连接已关闭")
        except:
            pass

async def test_database_creation():
    """测试数据库表创建"""
    print("\n🔍 测试数据库表创建...")
    
    try:
        from app.database.connection import init_database
        
        print("🚀 初始化数据库表...")
        await init_database()
        
        print("✅ 数据库表创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        return False

async def main():
    """主函数"""
    print("🚀 开始数据库连接测试...")
    
    # 测试基本连接
    connection_ok = await test_database_connection()
    
    if connection_ok:
        # 测试表创建
        await test_database_creation()
    
    print("\n✅ 所有测试完成")

if __name__ == "__main__":
    asyncio.run(main())
