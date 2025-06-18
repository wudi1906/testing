-- 创建测试报告表
CREATE TABLE IF NOT EXISTS test_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 基本信息
    script_id VARCHAR(255) NOT NULL,
    script_name VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    
    -- 执行结果
    status VARCHAR(50) NOT NULL, -- passed/failed/error
    return_code INTEGER DEFAULT 0,
    
    -- 时间信息
    start_time DATETIME,
    end_time DATETIME,
    duration REAL DEFAULT 0.0,
    
    -- 测试结果统计
    total_tests INTEGER DEFAULT 0,
    passed_tests INTEGER DEFAULT 0,
    failed_tests INTEGER DEFAULT 0,
    skipped_tests INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    
    -- 报告文件信息
    report_path TEXT,
    report_url TEXT,
    report_size INTEGER DEFAULT 0,
    
    -- 产物信息 (JSON格式)
    screenshots TEXT, -- JSON array
    videos TEXT,      -- JSON array
    artifacts TEXT,   -- JSON array
    
    -- 错误信息
    error_message TEXT,
    logs TEXT,        -- JSON array
    
    -- 环境信息 (JSON格式)
    execution_config TEXT,      -- JSON object
    environment_variables TEXT, -- JSON object
    
    -- 元数据
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_test_reports_script_id ON test_reports(script_id);
CREATE INDEX IF NOT EXISTS idx_test_reports_session_id ON test_reports(session_id);
CREATE INDEX IF NOT EXISTS idx_test_reports_execution_id ON test_reports(execution_id);
CREATE INDEX IF NOT EXISTS idx_test_reports_status ON test_reports(status);
CREATE INDEX IF NOT EXISTS idx_test_reports_created_at ON test_reports(created_at);

-- 创建触发器，自动更新updated_at字段
CREATE TRIGGER IF NOT EXISTS update_test_reports_updated_at 
    AFTER UPDATE ON test_reports
    FOR EACH ROW
BEGIN
    UPDATE test_reports SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
