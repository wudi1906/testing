#!/usr/bin/env python3
"""
初始化测试报告数据库 (MySQL版本)
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.connection import db_manager
from app.database.models.reports import TestReport


async def init_database():
    """初始化MySQL数据库"""
    try:
        print("正在初始化测试报告MySQL数据库...")

        # 初始化数据库连接
        await db_manager.initialize()

        print("✅ MySQL数据库初始化成功！")
        print(f"数据库连接: {db_manager.database_url}")

        # 测试数据库连接
        async with db_manager.get_session() as session:
            from sqlalchemy import select, func
            stmt = select(func.count(TestReport.id))
            result = await session.execute(stmt)
            count = result.scalar()
            print(f"当前报告数量: {count}")

    except Exception as e:
        print(f"❌ MySQL数据库初始化失败: {str(e)}")
        return False

    return True


async def create_sample_report():
    """创建示例报告"""
    try:
        print("正在创建示例报告...")

        from datetime import datetime

        sample_report = TestReport(
            script_id="sample_001",
            script_name="示例测试脚本",
            session_id="session_001",
            execution_id="exec_001",
            status="passed",
            return_code=0,
            start_time=datetime.now(),
            end_time=datetime.now(),
            duration=5.2,
            total_tests=3,
            passed_tests=3,
            failed_tests=0,
            skipped_tests=0,
            success_rate=100.0,
            report_path="/path/to/report.html",
            report_url="/api/v1/web/reports/view/exec_001",
            report_size=1024,
            screenshots=["screenshot1.png", "screenshot2.png"],
            videos=["video1.mp4"],
            artifacts=["log1.txt"],
            error_message=None,
            logs=["测试开始", "测试通过", "测试完成"],
            execution_config={"headed": False, "timeout": 30},
            environment_variables={"NODE_ENV": "test"}
        )

        async with db_manager.get_session() as session:
            session.add(sample_report)
            await session.commit()
            await session.refresh(sample_report)
            print(f"✅ 示例报告创建成功，ID: {sample_report.id}")

    except Exception as e:
        print(f"❌ 创建示例报告失败: {str(e)}")
        return False

    return True


async def main():
    """主函数"""
    print("=== 测试报告MySQL数据库初始化工具 ===")

    # 初始化数据库
    if not await init_database():
        sys.exit(1)

    # 询问是否创建示例报告
    create_sample = input("是否创建示例报告？(y/N): ").lower().strip()
    if create_sample in ['y', 'yes']:
        await create_sample_report()

    print("=== 初始化完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
