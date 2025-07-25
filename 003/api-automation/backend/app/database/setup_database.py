#!/usr/bin/env python3
"""
数据库设置脚本
一键设置API自动化系统的完整数据库环境
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.create_tables import create_api_automation_tables
from app.database.migration_manager import MigrationManager
from app.database.optimize_database import (
    analyze_table_performance, 
    generate_database_report
)
from app.database.backup_restore import BackupRestoreManager


class DatabaseSetup:
    """数据库设置管理器"""
    
    def __init__(self):
        self.migration_manager = MigrationManager()
        self.backup_manager = BackupRestoreManager()
    
    async def setup_fresh_database(self):
        """设置全新数据库"""
        try:
            logger.info("=== 开始设置全新数据库 ===")
            
            # 1. 创建数据库表
            logger.info("步骤 1: 创建数据库表...")
            await create_api_automation_tables()
            
            # 2. 验证表结构
            logger.info("步骤 2: 验证表结构...")
            verification_result = await self.migration_manager.verify_tables()
            if not verification_result:
                raise Exception("表结构验证失败")
            
            # 3. 生成初始备份
            logger.info("步骤 3: 创建初始备份...")
            backup_path = await self.backup_manager.create_full_backup("initial_setup")
            logger.info(f"初始备份已创建: {backup_path}")
            
            # 4. 生成数据库报告
            logger.info("步骤 4: 生成数据库报告...")
            report = await generate_database_report()
            
            logger.info("=== 数据库设置完成 ===")
            logger.info("数据库已准备就绪，可以开始使用API自动化系统")
            
            return True
            
        except Exception as e:
            logger.error(f"数据库设置失败: {str(e)}")
            return False
    
    async def upgrade_existing_database(self):
        """升级现有数据库"""
        try:
            logger.info("=== 开始升级现有数据库 ===")
            
            # 1. 检查当前状态
            logger.info("步骤 1: 检查数据库状态...")
            status = await self.migration_manager.check_migration_status()
            logger.info(f"当前状态: {status}")
            
            # 2. 创建升级前备份
            logger.info("步骤 2: 创建升级前备份...")
            backup_path = await self.backup_manager.create_full_backup("pre_upgrade")
            logger.info(f"升级前备份已创建: {backup_path}")
            
            # 3. 应用迁移
            logger.info("步骤 3: 应用数据库迁移...")
            await self.migration_manager.apply_migrations()
            
            # 4. 验证升级结果
            logger.info("步骤 4: 验证升级结果...")
            verification_result = await self.migration_manager.verify_tables()
            if not verification_result:
                logger.warning("表结构验证失败，但升级可能仍然成功")
            
            # 5. 优化数据库
            logger.info("步骤 5: 优化数据库性能...")
            from app.database.optimize_database import optimize_indexes, vacuum_database
            await optimize_indexes()
            await vacuum_database()
            
            # 6. 生成升级后报告
            logger.info("步骤 6: 生成升级后报告...")
            report = await generate_database_report()
            
            logger.info("=== 数据库升级完成 ===")
            
            return True
            
        except Exception as e:
            logger.error(f"数据库升级失败: {str(e)}")
            logger.error("如果遇到问题，可以使用备份进行恢复")
            return False
    
    async def reset_database(self, confirm: bool = False):
        """重置数据库"""
        try:
            if not confirm:
                logger.warning("重置数据库将删除所有数据！")
                response = input("确认要重置数据库吗？输入 'YES' 确认: ")
                if response != "YES":
                    logger.info("操作已取消")
                    return False
            
            logger.warning("=== 开始重置数据库 ===")
            
            # 1. 创建重置前备份
            logger.info("步骤 1: 创建重置前备份...")
            try:
                backup_path = await self.backup_manager.create_full_backup("pre_reset")
                logger.info(f"重置前备份已创建: {backup_path}")
            except Exception as e:
                logger.warning(f"创建备份失败: {str(e)}")
            
            # 2. 重置数据库
            logger.info("步骤 2: 重置数据库...")
            await self.migration_manager.reset_database()
            
            # 3. 重新设置数据库
            logger.info("步骤 3: 重新设置数据库...")
            await self.setup_fresh_database()
            
            logger.warning("=== 数据库重置完成 ===")
            
            return True
            
        except Exception as e:
            logger.error(f"数据库重置失败: {str(e)}")
            return False
    
    async def check_database_health(self):
        """检查数据库健康状态"""
        try:
            logger.info("=== 数据库健康检查 ===")
            
            # 1. 检查表结构
            logger.info("检查表结构...")
            verification_result = await self.migration_manager.verify_tables()
            logger.info(f"表结构验证: {'通过' if verification_result else '失败'}")
            
            # 2. 检查迁移状态
            logger.info("检查迁移状态...")
            migration_status = await self.migration_manager.check_migration_status()
            logger.info(f"迁移状态: {migration_status}")
            
            # 3. 分析性能
            logger.info("分析数据库性能...")
            performance_stats = await analyze_table_performance()
            
            # 4. 生成健康报告
            logger.info("生成健康报告...")
            health_report = await generate_database_report()
            
            # 5. 检查备份
            logger.info("检查备份状态...")
            backups = await self.backup_manager.list_backups()
            logger.info(f"可用备份数量: {len(backups)}")
            
            logger.info("=== 健康检查完成 ===")
            
            return {
                'table_verification': verification_result,
                'migration_status': migration_status,
                'performance_stats': performance_stats,
                'health_report': health_report,
                'backup_count': len(backups)
            }
            
        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return None
    
    async def maintenance_routine(self):
        """数据库维护例程"""
        try:
            logger.info("=== 开始数据库维护 ===")
            
            # 1. 创建维护前备份
            logger.info("步骤 1: 创建维护备份...")
            backup_path = await self.backup_manager.create_full_backup("maintenance")
            
            # 2. 清理旧数据
            logger.info("步骤 2: 清理旧数据...")
            from app.database.optimize_database import cleanup_old_data
            cleanup_stats = await cleanup_old_data(days=30, dry_run=False)
            logger.info(f"清理统计: {cleanup_stats}")
            
            # 3. 优化索引
            logger.info("步骤 3: 优化索引...")
            from app.database.optimize_database import optimize_indexes
            await optimize_indexes()
            
            # 4. 清理数据库
            logger.info("步骤 4: 清理数据库...")
            from app.database.optimize_database import vacuum_database
            await vacuum_database()
            
            # 5. 分析性能
            logger.info("步骤 5: 分析性能...")
            await analyze_table_performance()
            
            # 6. 清理旧备份（保留最近10个）
            logger.info("步骤 6: 清理旧备份...")
            backups = await self.backup_manager.list_backups()
            if len(backups) > 10:
                old_backups = backups[10:]  # 保留最新的10个
                for backup in old_backups:
                    await self.backup_manager.delete_backup(backup['file_path'])
                    logger.info(f"删除旧备份: {backup['backup_name']}")
            
            logger.info("=== 数据库维护完成 ===")
            
            return True
            
        except Exception as e:
            logger.error(f"数据库维护失败: {str(e)}")
            return False


async def main():
    """主函数"""
    setup = DatabaseSetup()
    
    if len(sys.argv) < 2:
        print("用法: python setup_database.py <command>")
        print("命令:")
        print("  setup      - 设置全新数据库")
        print("  upgrade    - 升级现有数据库")
        print("  reset      - 重置数据库（危险操作）")
        print("  check      - 检查数据库健康状态")
        print("  maintain   - 执行数据库维护")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "setup":
            success = await setup.setup_fresh_database()
            sys.exit(0 if success else 1)
        
        elif command == "upgrade":
            success = await setup.upgrade_existing_database()
            sys.exit(0 if success else 1)
        
        elif command == "reset":
            success = await setup.reset_database()
            sys.exit(0 if success else 1)
        
        elif command == "check":
            result = await setup.check_database_health()
            if result:
                print("数据库健康检查完成")
                print(f"表验证: {'通过' if result['table_verification'] else '失败'}")
                print(f"备份数量: {result['backup_count']}")
            sys.exit(0 if result else 1)
        
        elif command == "maintain":
            success = await setup.maintenance_routine()
            sys.exit(0 if success else 1)
        
        else:
            print(f"未知命令: {command}")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("操作被用户中断")
        sys.exit(1)
    except Exception as e:
        logger.error(f"执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
