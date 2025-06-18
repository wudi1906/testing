#!/usr/bin/env python3
"""
创建或更新test_reports表结构
"""
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.database.connection import db_manager
from app.database.models.reports import TestReport
from app.core.logging import get_logger

logger = get_logger(__name__)


async def check_table_exists():
    """检查test_reports表是否存在"""
    try:
        async with db_manager.get_session() as session:
            # 检查表是否存在
            result = await session.execute("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'test_reports'
            """)
            count = result.scalar()
            return count > 0
    except Exception as e:
        logger.error(f"检查表是否存在失败: {str(e)}")
        return False


async def get_table_columns():
    """获取test_reports表的列信息"""
    try:
        async with db_manager.get_session() as session:
            result = await session.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'test_reports'
                ORDER BY ORDINAL_POSITION
            """)
            columns = result.fetchall()
            return {col[0]: {"type": col[1], "nullable": col[2], "default": col[3]} for col in columns}
    except Exception as e:
        logger.error(f"获取表列信息失败: {str(e)}")
        return {}


async def create_test_reports_table():
    """创建test_reports表"""
    try:
        async with db_manager.get_session() as session:
            # 删除表（如果存在）
            await session.execute("DROP TABLE IF EXISTS test_reports")
            
            # 创建新表
            create_sql = """
            CREATE TABLE test_reports (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                
                -- 基本信息
                script_id VARCHAR(255) NOT NULL COMMENT '脚本ID',
                script_name VARCHAR(255) NOT NULL COMMENT '脚本名称',
                session_id VARCHAR(255) NOT NULL COMMENT '执行会话ID',
                execution_id VARCHAR(255) NOT NULL COMMENT '执行ID',
                
                -- 执行结果
                status VARCHAR(50) NOT NULL COMMENT '执行状态: passed/failed/error',
                return_code INT DEFAULT 0 COMMENT '返回码',
                
                -- 时间信息
                start_time DATETIME NULL COMMENT '开始时间',
                end_time DATETIME NULL COMMENT '结束时间',
                duration DECIMAL(10,3) DEFAULT 0.000 COMMENT '执行时长(秒)',
                
                -- 测试结果统计
                total_tests INT DEFAULT 0 COMMENT '总测试数',
                passed_tests INT DEFAULT 0 COMMENT '通过测试数',
                failed_tests INT DEFAULT 0 COMMENT '失败测试数',
                skipped_tests INT DEFAULT 0 COMMENT '跳过测试数',
                success_rate DECIMAL(5,2) DEFAULT 0.00 COMMENT '成功率',
                
                -- 报告文件信息
                report_path TEXT COMMENT '报告文件路径',
                report_url TEXT COMMENT '报告访问URL',
                report_size BIGINT DEFAULT 0 COMMENT '报告文件大小(字节)',
                
                -- 产物信息 (JSON格式)
                screenshots JSON COMMENT '截图文件列表',
                videos JSON COMMENT '视频文件列表',
                artifacts JSON COMMENT '其他产物文件列表',
                
                -- 错误信息
                error_message TEXT COMMENT '错误信息',
                logs JSON COMMENT '执行日志',
                
                -- 环境信息 (JSON格式)
                execution_config JSON COMMENT '执行配置',
                environment_variables JSON COMMENT '环境变量',
                
                -- 元数据
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                
                -- 索引
                INDEX idx_script_id (script_id),
                INDEX idx_session_id (session_id),
                INDEX idx_execution_id (execution_id),
                INDEX idx_status (status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试报告表'
            """
            
            await session.execute(create_sql)
            await session.commit()
            
            logger.info("✅ test_reports表创建成功！")
            return True
            
    except Exception as e:
        logger.error(f"❌ 创建test_reports表失败: {str(e)}")
        return False


async def verify_table_structure():
    """验证表结构"""
    try:
        async with db_manager.get_session() as session:
            # 测试插入一条记录
            from datetime import datetime
            
            test_sql = """
            INSERT INTO test_reports (
                script_id, script_name, session_id, execution_id, status, return_code,
                start_time, end_time, duration, total_tests, passed_tests, failed_tests,
                skipped_tests, success_rate, report_path, report_url, report_size,
                screenshots, videos, artifacts, error_message, logs,
                execution_config, environment_variables
            ) VALUES (
                'test_001', '测试脚本', 'session_001', 'exec_001', 'passed', 0,
                NOW(), NOW(), 5.2, 3, 3, 0, 0, 100.00,
                '/path/to/report.html', '/api/v1/web/reports/view/exec_001', 1024,
                JSON_ARRAY('screenshot1.png'), JSON_ARRAY('video1.mp4'), JSON_ARRAY('log1.txt'),
                NULL, JSON_ARRAY('测试开始', '测试完成'),
                JSON_OBJECT('headed', false), JSON_OBJECT('NODE_ENV', 'test')
            )
            """
            
            await session.execute(test_sql)
            await session.commit()
            
            # 查询验证
            result = await session.execute("SELECT COUNT(*) FROM test_reports WHERE script_id = 'test_001'")
            count = result.scalar()
            
            if count > 0:
                logger.info("✅ 表结构验证成功！")
                
                # 删除测试数据
                await session.execute("DELETE FROM test_reports WHERE script_id = 'test_001'")
                await session.commit()
                logger.info("✅ 测试数据已清理")
                
                return True
            else:
                logger.error("❌ 表结构验证失败")
                return False
                
    except Exception as e:
        logger.error(f"❌ 验证表结构失败: {str(e)}")
        return False


async def main():
    """主函数"""
    print("=== test_reports表结构检查和创建工具 ===")
    
    try:
        # 初始化数据库连接
        await db_manager.initialize()
        print("✅ 数据库连接成功")
        
        # 检查表是否存在
        table_exists = await check_table_exists()
        
        if table_exists:
            print("📋 test_reports表已存在")
            
            # 获取现有表结构
            columns = await get_table_columns()
            print(f"📊 当前表有 {len(columns)} 个字段")
            
            # 检查关键字段
            required_fields = ['script_id', 'script_name', 'session_id', 'execution_id', 'status', 
                             'report_path', 'report_url', 'logs', 'execution_config']
            missing_fields = [field for field in required_fields if field not in columns]
            
            if missing_fields:
                print(f"⚠️  缺少字段: {missing_fields}")
                recreate = input("是否重新创建表？(y/N): ").lower().strip()
                if recreate in ['y', 'yes']:
                    if await create_test_reports_table():
                        await verify_table_structure()
                else:
                    print("❌ 表结构不完整，请手动修复或重新创建")
                    return
            else:
                print("✅ 表结构完整")
                
        else:
            print("📋 test_reports表不存在，正在创建...")
            if await create_test_reports_table():
                await verify_table_structure()
            else:
                print("❌ 创建表失败")
                return
        
        print("=== 检查完成 ===")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
