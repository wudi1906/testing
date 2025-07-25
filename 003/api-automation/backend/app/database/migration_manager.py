"""
数据库迁移管理器
用于管理API自动化相关的数据库迁移
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
from loguru import logger
from tortoise import Tortoise
from aerich import Command

from app.core.config import settings


class MigrationManager:
    """数据库迁移管理器"""
    
    def __init__(self):
        self.aerich_config = {
            "connections": {"default": settings.DATABASE_URL},
            "apps": {
                "models": {
                    "models": ["app.models.api_automation", "aerich.models"],
                    "default_connection": "default",
                }
            },
        }
    
    async def init_aerich(self):
        """初始化Aerich"""
        try:
            command = Command(tortoise_config=self.aerich_config, app="models")
            await command.init()
            logger.info("Aerich初始化成功")
        except Exception as e:
            logger.error(f"Aerich初始化失败: {str(e)}")
            raise
    
    async def generate_migration(self, name: str = None):
        """生成迁移文件"""
        try:
            command = Command(tortoise_config=self.aerich_config, app="models")
            await command.migrate(name=name)
            logger.info(f"迁移文件生成成功: {name}")
        except Exception as e:
            logger.error(f"生成迁移文件失败: {str(e)}")
            raise
    
    async def apply_migrations(self):
        """应用迁移"""
        try:
            command = Command(tortoise_config=self.aerich_config, app="models")
            await command.upgrade()
            logger.info("迁移应用成功")
        except Exception as e:
            logger.error(f"应用迁移失败: {str(e)}")
            raise
    
    async def rollback_migration(self, version: int = 1):
        """回滚迁移"""
        try:
            command = Command(tortoise_config=self.aerich_config, app="models")
            await command.downgrade(version=version)
            logger.info(f"迁移回滚成功: {version}")
        except Exception as e:
            logger.error(f"回滚迁移失败: {str(e)}")
            raise
    
    async def get_migration_history(self) -> List[Dict[str, Any]]:
        """获取迁移历史"""
        try:
            command = Command(tortoise_config=self.aerich_config, app="models")
            history = await command.history()
            return history
        except Exception as e:
            logger.error(f"获取迁移历史失败: {str(e)}")
            return []
    
    async def check_migration_status(self) -> Dict[str, Any]:
        """检查迁移状态"""
        try:
            # 初始化Tortoise
            await Tortoise.init(config=self.aerich_config)
            
            # 检查aerich表是否存在
            from aerich.models import Aerich
            
            try:
                migrations = await Aerich.all()
                applied_migrations = [m.version for m in migrations]
                
                # 获取所有迁移文件
                migration_dir = Path("migrations/models")
                migration_files = []
                if migration_dir.exists():
                    for file in migration_dir.glob("*.py"):
                        if file.name != "__init__.py":
                            migration_files.append(file.stem)
                
                pending_migrations = [m for m in migration_files if m not in applied_migrations]
                
                return {
                    "applied_migrations": applied_migrations,
                    "pending_migrations": pending_migrations,
                    "total_migrations": len(migration_files),
                    "applied_count": len(applied_migrations),
                    "pending_count": len(pending_migrations)
                }
                
            except Exception:
                # aerich表不存在，说明还没有初始化
                return {
                    "applied_migrations": [],
                    "pending_migrations": [],
                    "total_migrations": 0,
                    "applied_count": 0,
                    "pending_count": 0,
                    "status": "not_initialized"
                }
                
        except Exception as e:
            logger.error(f"检查迁移状态失败: {str(e)}")
            return {"error": str(e)}
        finally:
            await Tortoise.close_connections()
    
    async def create_api_automation_migration(self):
        """创建API自动化专用迁移"""
        try:
            # 检查是否已经存在API自动化相关的表
            await Tortoise.init(config=self.aerich_config)
            
            # 检查agent_logs表是否存在
            conn = Tortoise.get_connection("default")
            
            # SQLite检查表是否存在
            result = await conn.execute_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_logs'"
            )
            
            if result[1]:  # 表已存在
                logger.info("API自动化表已存在，跳过创建")
                return False
            
            # 表不存在，需要创建迁移
            logger.info("开始创建API自动化迁移...")
            
            # 生成迁移
            await self.generate_migration("api_automation_init")
            
            return True
            
        except Exception as e:
            logger.error(f"创建API自动化迁移失败: {str(e)}")
            raise
        finally:
            await Tortoise.close_connections()
    
    async def setup_database(self):
        """设置数据库（完整流程）"""
        try:
            logger.info("开始设置数据库...")
            
            # 1. 检查迁移状态
            status = await self.check_migration_status()
            
            if status.get("status") == "not_initialized":
                logger.info("数据库未初始化，开始初始化...")
                await self.init_aerich()
            
            # 2. 应用迁移
            logger.info("应用迁移...")
            await self.apply_migrations()
            
            # 3. 验证表是否创建成功
            await self.verify_tables()
            
            logger.info("数据库设置完成")
            
        except Exception as e:
            logger.error(f"设置数据库失败: {str(e)}")
            raise
    
    async def verify_tables(self):
        """验证表是否创建成功"""
        try:
            await Tortoise.init(config=self.aerich_config)
            conn = Tortoise.get_connection("default")
            
            # 检查关键表是否存在
            required_tables = [
                "agent_logs",
                "log_analyses", 
                "test_scripts",
                "test_execution_results",
                "alert_rules",
                "alerts"
            ]
            
            existing_tables = []
            missing_tables = []
            
            for table in required_tables:
                result = await conn.execute_query(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                )
                
                if result[1]:
                    existing_tables.append(table)
                else:
                    missing_tables.append(table)
            
            logger.info(f"已存在的表: {existing_tables}")
            
            if missing_tables:
                logger.warning(f"缺失的表: {missing_tables}")
                return False
            else:
                logger.info("所有必需的表都已创建")
                return True
                
        except Exception as e:
            logger.error(f"验证表失败: {str(e)}")
            return False
        finally:
            await Tortoise.close_connections()
    
    async def reset_database(self):
        """重置数据库（危险操作）"""
        try:
            logger.warning("开始重置数据库...")
            
            await Tortoise.init(config=self.aerich_config)
            conn = Tortoise.get_connection("default")
            
            # 删除所有API自动化相关的表
            tables_to_drop = [
                "alerts",
                "alert_rules", 
                "test_execution_results",
                "test_scripts",
                "log_analyses",
                "agent_logs"
            ]
            
            for table in tables_to_drop:
                try:
                    await conn.execute_query(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"删除表: {table}")
                except Exception as e:
                    logger.warning(f"删除表 {table} 失败: {str(e)}")
            
            # 删除aerich记录
            try:
                await conn.execute_query(
                    "DELETE FROM aerich WHERE app = 'models' AND version LIKE '%api_automation%'"
                )
                logger.info("清理aerich记录")
            except Exception as e:
                logger.warning(f"清理aerich记录失败: {str(e)}")
            
            logger.warning("数据库重置完成")
            
        except Exception as e:
            logger.error(f"重置数据库失败: {str(e)}")
            raise
        finally:
            await Tortoise.close_connections()


async def main():
    """主函数"""
    manager = MigrationManager()
    
    if len(sys.argv) < 2:
        print("用法: python migration_manager.py <command>")
        print("命令:")
        print("  init        - 初始化Aerich")
        print("  migrate     - 生成迁移文件")
        print("  upgrade     - 应用迁移")
        print("  downgrade   - 回滚迁移")
        print("  status      - 检查迁移状态")
        print("  history     - 查看迁移历史")
        print("  setup       - 完整设置数据库")
        print("  verify      - 验证表结构")
        print("  reset       - 重置数据库（危险）")
        return
    
    command = sys.argv[1]
    
    try:
        if command == "init":
            await manager.init_aerich()
        elif command == "migrate":
            name = sys.argv[2] if len(sys.argv) > 2 else None
            await manager.generate_migration(name)
        elif command == "upgrade":
            await manager.apply_migrations()
        elif command == "downgrade":
            version = int(sys.argv[2]) if len(sys.argv) > 2 else 1
            await manager.rollback_migration(version)
        elif command == "status":
            status = await manager.check_migration_status()
            print(f"迁移状态: {status}")
        elif command == "history":
            history = await manager.get_migration_history()
            print(f"迁移历史: {history}")
        elif command == "setup":
            await manager.setup_database()
        elif command == "verify":
            result = await manager.verify_tables()
            print(f"表验证结果: {result}")
        elif command == "reset":
            confirm = input("确认要重置数据库吗？这将删除所有数据！(yes/no): ")
            if confirm.lower() == "yes":
                await manager.reset_database()
            else:
                print("操作已取消")
        else:
            print(f"未知命令: {command}")
            
    except Exception as e:
        logger.error(f"执行命令失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
