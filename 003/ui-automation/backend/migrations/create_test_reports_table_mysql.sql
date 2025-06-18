-- 创建测试报告表 (MySQL版本)
CREATE TABLE IF NOT EXISTS test_reports (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    
    -- 基本信息
    script_id VARCHAR(255) NOT NULL,
    script_name VARCHAR(255) NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='测试报告表';

-- 插入示例数据
INSERT INTO test_reports (
    script_id, script_name, session_id, execution_id, status, return_code,
    start_time, end_time, duration, total_tests, passed_tests, failed_tests,
    skipped_tests, success_rate, report_path, report_url, report_size,
    screenshots, videos, artifacts, error_message, logs,
    execution_config, environment_variables
) VALUES (
    'sample_001',
    '示例测试脚本',
    'session_001',
    'exec_001',
    'passed',
    0,
    NOW() - INTERVAL 5 MINUTE,
    NOW(),
    300.5,
    5,
    5,
    0,
    0,
    100.00,
    '/path/to/report.html',
    '/api/v1/web/reports/view/exec_001',
    2048,
    JSON_ARRAY('screenshot1.png', 'screenshot2.png'),
    JSON_ARRAY('video1.mp4'),
    JSON_ARRAY('log1.txt', 'config.json'),
    NULL,
    JSON_ARRAY('测试开始', '执行脚本', '测试通过', '生成报告', '测试完成'),
    JSON_OBJECT('headed', false, 'timeout', 30, 'base_url', 'https://example.com'),
    JSON_OBJECT('NODE_ENV', 'test', 'DEBUG', 'true')
) ON DUPLICATE KEY UPDATE
    script_name = VALUES(script_name),
    updated_at = CURRENT_TIMESTAMP;
