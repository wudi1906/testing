-- 手动处理外键约束问题
-- 这个脚本专门用于解决外键约束导致的表删除问题

-- 1. 查看所有引用test_reports的外键约束
SELECT 
    CONSTRAINT_NAME,
    TABLE_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE 
WHERE REFERENCED_TABLE_NAME = 'test_reports'
AND TABLE_SCHEMA = DATABASE();

-- 2. 禁用外键检查
SET FOREIGN_KEY_CHECKS = 0;

-- 3. 手动删除已知的外键约束
-- 删除report_tags表的外键约束
ALTER TABLE report_tags DROP FOREIGN KEY IF EXISTS report_tags_ibfk_1;

-- 如果有其他外键约束，也在这里删除
-- ALTER TABLE other_table DROP FOREIGN KEY IF EXISTS other_constraint_name;

-- 4. 现在可以安全删除test_reports表
DROP TABLE IF EXISTS test_reports;

-- 5. 重新启用外键检查
SET FOREIGN_KEY_CHECKS = 1;

-- 6. 验证表已删除
SELECT COUNT(*) as table_exists 
FROM information_schema.tables 
WHERE table_schema = DATABASE() 
AND table_name = 'test_reports';

-- 如果返回0，说明表已成功删除
-- 现在可以运行其他脚本来重新创建表
