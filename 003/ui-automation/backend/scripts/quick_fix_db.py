#!/usr/bin/env python3
"""
快速修复数据库表结构问题
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.connection import db_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_foreign_keys():
    """检查外键约束"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute("""
                SELECT
                    CONSTRAINT_NAME,
                    TABLE_NAME,
                    COLUMN_NAME,
                    REFERENCED_TABLE_NAME,
                    REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE REFERENCED_TABLE_NAME = 'test_reports'
                AND TABLE_SCHEMA = DATABASE()
            """)
            foreign_keys = result.fetchall()

            if foreign_keys:
                print("⚠️  发现外键约束:")
                for fk in foreign_keys:
                    print(f"   {fk[1]}.{fk[2]} -> {fk[3]}.{fk[4]} (约束名: {fk[0]})")
                return foreign_keys
            else:
                print("✅ 没有发现外键约束")
                return []

    except Exception as e:
        print(f"❌ 检查外键约束失败: {str(e)}")
        return []


async def drop_foreign_keys():
    """删除外键约束"""
    try:
        async with db_manager.get_session() as session:
            # 禁用外键检查
            await session.execute("SET FOREIGN_KEY_CHECKS = 0")

            # 查找并删除外键约束
            result = await session.execute("""
                SELECT CONSTRAINT_NAME, TABLE_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE REFERENCED_TABLE_NAME = 'test_reports'
                AND TABLE_SCHEMA = DATABASE()
            """)
            foreign_keys = result.fetchall()

            for constraint_name, table_name in foreign_keys:
                try:
                    drop_sql = f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name}"
                    await session.execute(drop_sql)
                    print(f"✅ 删除外键约束: {table_name}.{constraint_name}")
                except Exception as e:
                    print(f"⚠️  删除外键约束失败: {constraint_name} - {str(e)}")

            await session.commit()
            return True

    except Exception as e:
        print(f"❌ 删除外键约束失败: {str(e)}")
        return False


async def execute_sql_file(sql_file_path: str):
    """执行SQL文件"""
    try:
        # 读取SQL文件
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        # 分割SQL语句（按分号分割）
        sql_statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

        async with db_manager.get_session() as session:
            for i, sql in enumerate(sql_statements):
                if sql.strip() and not sql.strip().startswith('--'):
                    try:
                        print(f"执行SQL语句 {i+1}/{len(sql_statements)}: {sql[:50]}...")
                        await session.execute(sql)
                        await session.commit()
                        print(f"✅ SQL语句 {i+1} 执行成功")
                    except Exception as e:
                        print(f"❌ SQL语句 {i+1} 执行失败: {str(e)}")
                        # 某些语句失败不影响整体流程
                        if any(keyword in sql.upper() for keyword in ["CREATE TABLE", "INSERT INTO"]):
                            raise

        print("✅ SQL文件执行完成")
        return True

    except Exception as e:
        print(f"❌ 执行SQL文件失败: {str(e)}")
        return False


async def test_table_operations():
    """测试表操作"""
    try:
        async with db_manager.get_session() as session:
            # 测试查询
            result = await session.execute("SELECT COUNT(*) FROM test_reports")
            count = result.scalar()
            print(f"✅ 表查询成功，当前记录数: {count}")
            
            # 测试插入
            test_sql = """
            INSERT INTO test_reports (
                script_id, script_name, session_id, execution_id, status
            ) VALUES (
                'test_quick_fix', '快速修复测试', 'session_test', 'exec_test', 'passed'
            )
            """
            await session.execute(test_sql)
            await session.commit()
            print("✅ 测试插入成功")
            
            # 删除测试数据
            await session.execute("DELETE FROM test_reports WHERE script_id = 'test_quick_fix'")
            await session.commit()
            print("✅ 测试数据清理完成")
            
            return True
            
    except Exception as e:
        print(f"❌ 表操作测试失败: {str(e)}")
        return False


async def main():
    """主函数"""
    print("=== 快速修复数据库表结构 ===")
    
    try:
        # 初始化数据库连接
        await db_manager.initialize()
        print("✅ 数据库连接成功")

        # 检查外键约束
        print("🔍 检查外键约束...")
        foreign_keys = await check_foreign_keys()

        if foreign_keys:
            print("🔧 处理外键约束...")
            await drop_foreign_keys()

        # 执行修复SQL
        sql_file = Path(__file__).parent / "safe_fix_test_reports.sql"
        if not sql_file.exists():
            print(f"❌ SQL文件不存在: {sql_file}")
            print("尝试使用备用SQL文件...")
            sql_file = Path(__file__).parent / "fix_test_reports_table.sql"
            if not sql_file.exists():
                print(f"❌ 备用SQL文件也不存在: {sql_file}")
                return

        print(f"📋 执行SQL文件: {sql_file}")
        if await execute_sql_file(str(sql_file)):
            print("✅ 表结构修复完成")
            
            # 测试表操作
            print("🧪 测试表操作...")
            if await test_table_operations():
                print("✅ 所有测试通过")
            else:
                print("❌ 表操作测试失败")
        else:
            print("❌ 表结构修复失败")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
