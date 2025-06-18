#!/usr/bin/env python3
"""
创建数据库脚本
用于创建项目所需的数据库
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def create_database():
    """创建数据库"""
    print("🔍 创建数据库...")
    
    try:
        # 导入配置
        from app.core.config import get_settings
        settings = get_settings()
        
        # 解析数据库连接信息
        database_url = settings.database_url
        print(f"📋 数据库连接URL: {database_url.split('@')[-1] if '@' in database_url else database_url}")
        
        # 提取数据库信息
        import re
        match = re.match(r'mysql\+aiomysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
        if not match:
            print("❌ 无法解析数据库连接URL")
            return False
        
        username, password, host, port, database_name = match.groups()
        
        print(f"📊 数据库信息:")
        print(f"   主机: {host}:{port}")
        print(f"   用户: {username}")
        print(f"   数据库名: {database_name}")
        
        # 连接到MySQL服务器（不指定数据库）
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import text
        
        # 创建连接到MySQL服务器的URL（不包含数据库名）
        server_url = f"mysql+aiomysql://{username}:{password}@{host}:{port}"
        
        print("🚀 连接到MySQL服务器...")
        engine = create_async_engine(server_url)
        
        async with engine.begin() as conn:
            # 检查数据库是否存在
            result = await conn.execute(
                text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :db_name"),
                {"db_name": database_name}
            )
            existing_db = result.fetchone()
            
            if existing_db:
                print(f"✅ 数据库 '{database_name}' 已存在")
            else:
                # 创建数据库
                print(f"🔨 创建数据库 '{database_name}'...")
                await conn.execute(text(f"CREATE DATABASE `{database_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                print(f"✅ 数据库 '{database_name}' 创建成功")
        
        await engine.dispose()
        
        # 测试连接到新创建的数据库
        print("🔗 测试数据库连接...")
        test_engine = create_async_engine(database_url)
        
        async with test_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test, NOW() as current_time"))
            row = result.fetchone()
            
            if row:
                print(f"✅ 数据库连接测试成功!")
                print(f"   测试查询结果: {row.test}")
                print(f"   数据库时间: {row.current_time}")
            else:
                print("❌ 数据库连接测试失败")
                return False
        
        await test_engine.dispose()
        
        print("✅ 数据库创建和测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据库创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def create_tables():
    """创建数据库表"""
    print("\n🔍 创建数据库表...")
    
    try:
        from app.database.connection import init_database
        
        print("🚀 初始化数据库表...")
        await init_database()
        
        print("✅ 数据库表创建成功")
        return True
        
    except Exception as e:
        print(f"❌ 数据库表创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主函数"""
    print("🚀 开始数据库初始化...")
    
    # 创建数据库
    db_created = await create_database()
    
    if db_created:
        # 创建表
        await create_tables()
    
    print("\n✅ 数据库初始化完成")

if __name__ == "__main__":
    asyncio.run(main())
