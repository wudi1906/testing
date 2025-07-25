# API自动化系统数据库管理

## 概述

本目录包含API自动化系统的完整数据库管理工具，支持数据库创建、迁移、优化、备份恢复和性能监控。

## 文件结构

```
database/
├── README.md                    # 本文档
├── schema_documentation.md      # 数据库表结构文档
├── create_tables.py            # 数据库表创建脚本
├── migration_manager.py        # 数据库迁移管理器
├── optimize_database.py        # 数据库优化工具
├── backup_restore.py           # 备份恢复工具
├── monitor_performance.py      # 性能监控工具
└── setup_database.py          # 一键数据库设置脚本
```

## 快速开始

### 1. 全新安装

如果是第一次部署系统，使用以下命令一键设置数据库：

```bash
# 设置全新数据库
python setup_database.py setup
```

这将自动完成：
- 创建所有必需的数据表
- 设置索引和约束
- 插入初始配置数据
- 创建初始备份
- 生成数据库健康报告

### 2. 升级现有数据库

如果要升级现有的数据库结构：

```bash
# 升级现有数据库
python setup_database.py upgrade
```

这将自动完成：
- 检查当前数据库状态
- 创建升级前备份
- 应用数据库迁移
- 优化数据库性能
- 验证升级结果

### 3. 检查数据库健康状态

```bash
# 检查数据库健康状态
python setup_database.py check
```

## 详细功能

### 数据库表管理

#### 创建数据库表

```bash
# 创建所有API自动化相关表
python create_tables.py create

# 重置数据库（删除并重新创建）
python create_tables.py reset

# 仅删除所有表（危险操作）
python create_tables.py drop
```

#### 表结构说明

系统包含以下核心表：

**业务表**：
- `api_documents` - API文档信息
- `api_endpoints` - API接口详情
- `api_analysis_results` - 接口分析结果
- `test_generation_tasks` - 测试生成任务
- `test_execution_sessions` - 测试执行会话
- `test_reports` - 测试报告

**系统表**：
- `agent_logs` - 智能体日志
- `agent_metrics` - 智能体性能指标
- `system_configurations` - 系统配置
- `operation_logs` - 操作日志
- `user_sessions` - 用户会话

详细的表结构说明请参考 [schema_documentation.md](schema_documentation.md)。

### 数据库迁移

#### 使用Aerich进行迁移管理

```bash
# 初始化迁移环境
python migration_manager.py init

# 生成迁移文件
python migration_manager.py migrate [migration_name]

# 应用迁移
python migration_manager.py upgrade

# 回滚迁移
python migration_manager.py downgrade [version]

# 查看迁移状态
python migration_manager.py status

# 查看迁移历史
python migration_manager.py history
```

#### 完整数据库设置

```bash
# 完整设置流程（推荐）
python migration_manager.py setup

# 验证表结构
python migration_manager.py verify

# 重置数据库（危险操作）
python migration_manager.py reset
```

### 数据库优化

#### 性能分析

```bash
# 分析表性能
python optimize_database.py analyze

# 生成数据库健康报告
python optimize_database.py report
```

#### 数据清理

```bash
# 预览清理操作（dry-run）
python optimize_database.py cleanup 30

# 执行清理（清理30天前的数据）
python optimize_database.py cleanup 30 execute
```

#### 索引优化

```bash
# 优化索引
python optimize_database.py optimize

# 清理数据库
python optimize_database.py vacuum
```

### 备份和恢复

#### 创建备份

```bash
# 创建完整备份
python backup_restore.py backup [backup_name]

# 创建增量备份
python backup_restore.py incremental "2024-01-01 00:00:00"
```

#### 恢复备份

```bash
# 恢复备份（替换模式）
python backup_restore.py restore backup_file.json.gz replace

# 恢复备份（合并模式）
python backup_restore.py restore backup_file.json.gz merge

# 恢复备份（跳过已存在记录）
python backup_restore.py restore backup_file.json.gz skip_existing
```

#### 备份管理

```bash
# 列出所有备份
python backup_restore.py list

# 删除指定备份
python backup_restore.py delete backup_file.json.gz
```

### 性能监控

#### 实时监控

```bash
# 开始性能监控（默认60秒间隔）
python monitor_performance.py start

# 自定义监控间隔（30秒）
python monitor_performance.py start 30
```

#### 性能报告

```bash
# 生成性能报告
python monitor_performance.py report

# 收集当前指标
python monitor_performance.py metrics
```

### 维护例程

#### 定期维护

```bash
# 执行完整维护例程
python setup_database.py maintain
```

维护例程包括：
- 创建维护备份
- 清理旧数据
- 优化索引
- 清理数据库
- 分析性能
- 清理旧备份

## 配置说明

### 数据库连接

在 `app/core/config.py` 中配置数据库连接：

```python
DATABASE_URL = "postgresql://user:password@localhost:5432/api_automation"
```

支持的数据库：
- PostgreSQL（推荐）
- SQLite（开发环境）

### 性能调优参数

在 `monitor_performance.py` 中可以调整监控阈值：

```python
alert_thresholds = {
    'slow_query_threshold': 1000,  # 慢查询阈值（毫秒）
    'connection_threshold': 80,     # 连接数阈值（百分比）
    'table_size_threshold': 1024,   # 表大小阈值（MB）
    'index_usage_threshold': 0.1    # 索引使用率阈值
}
```

## 最佳实践

### 1. 定期备份

建议设置定时任务，每天自动创建备份：

```bash
# 添加到crontab
0 2 * * * cd /path/to/project && python backend/app/database/backup_restore.py backup daily_backup_$(date +\%Y\%m\%d)
```

### 2. 性能监控

在生产环境中启用性能监控：

```bash
# 后台运行监控
nohup python monitor_performance.py start 300 > monitor.log 2>&1 &
```

### 3. 定期维护

每周执行一次维护例程：

```bash
# 添加到crontab
0 3 * * 0 cd /path/to/project && python backend/app/database/setup_database.py maintain
```

### 4. 数据清理

根据业务需求定期清理旧数据：

```bash
# 每月清理90天前的日志
0 4 1 * * cd /path/to/project && python backend/app/database/optimize_database.py cleanup 90 execute
```

## 故障排除

### 常见问题

#### 1. 表创建失败

```bash
# 检查数据库连接
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# 检查数据库权限
python -c "from tortoise import Tortoise; import asyncio; asyncio.run(Tortoise.init(db_url='your_db_url', modules={}))"
```

#### 2. 迁移失败

```bash
# 检查迁移状态
python migration_manager.py status

# 手动回滚
python migration_manager.py downgrade 1
```

#### 3. 性能问题

```bash
# 分析慢查询
python monitor_performance.py metrics

# 检查索引使用
python optimize_database.py analyze
```

#### 4. 备份恢复失败

```bash
# 验证备份文件
python -c "import gzip, json; print(json.load(gzip.open('backup_file.json.gz', 'rt'))['metadata'])"

# 检查表结构兼容性
python migration_manager.py verify
```

### 日志查看

系统使用loguru进行日志记录，日志级别可以通过环境变量控制：

```bash
export LOG_LEVEL=DEBUG
python setup_database.py check
```

### 紧急恢复

如果数据库损坏，可以使用以下步骤恢复：

1. 停止应用服务
2. 使用最新备份恢复数据
3. 检查数据完整性
4. 重启应用服务

```bash
# 紧急恢复流程
python setup_database.py reset
python backup_restore.py restore latest_backup.json.gz replace
python setup_database.py check
```

## 联系支持

如果遇到无法解决的问题，请：

1. 收集错误日志
2. 运行健康检查：`python setup_database.py check`
3. 生成性能报告：`python monitor_performance.py report`
4. 联系技术支持团队

## 版本历史

- v1.0.0 - 初始版本，包含基础表结构
- v1.1.0 - 添加性能监控和优化工具
- v1.2.0 - 增强备份恢复功能
- v1.3.0 - 完善迁移管理和维护工具
