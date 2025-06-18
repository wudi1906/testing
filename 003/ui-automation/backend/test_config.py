#!/usr/bin/env python3
"""
测试配置加载脚本
验证环境变量是否正确从.env文件中读取
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_env_loading():
    """测试环境变量加载"""
    print("🔍 测试环境变量加载...")
    
    # 手动加载.env文件
    env_file = project_root / ".env"
    if env_file.exists():
        print(f"✅ 找到.env文件: {env_file}")
        
        # 读取.env文件内容
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        print("\n📋 .env文件中的数据库相关配置:")
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and any(key in line for key in ['DATABASE', 'MYSQL']):
                print(f"  {line}")
    else:
        print("❌ 未找到.env文件")
        return False
    
    return True

def test_config_class():
    """测试配置类"""
    print("\n🔍 测试配置类...")
    
    try:
        from app.core.config import get_settings
        settings = get_settings()
        
        print("\n📋 配置类中的数据库配置:")
        print(f"  DATABASE_URL: {settings.DATABASE_URL}")
        print(f"  MYSQL_HOST: {settings.MYSQL_HOST}")
        print(f"  MYSQL_PORT: {settings.MYSQL_PORT}")
        print(f"  MYSQL_USER: {settings.MYSQL_USER}")
        print(f"  MYSQL_PASSWORD: {settings.MYSQL_PASSWORD}")
        print(f"  MYSQL_DATABASE: {settings.MYSQL_DATABASE}")
        
        print(f"\n🔗 最终数据库连接URL: {settings.database_url}")
        
        # 检查是否使用了环境变量
        if settings.DATABASE_URL:
            print("✅ 使用了DATABASE_URL环境变量")
        else:
            print("⚠️ 未使用DATABASE_URL环境变量，使用MySQL配置构建")
            
        return True
        
    except Exception as e:
        print(f"❌ 配置类测试失败: {e}")
        return False

def test_os_environ():
    """测试os.environ中的环境变量"""
    print("\n🔍 测试os.environ中的环境变量...")
    
    db_vars = ['DATABASE_URL', 'MYSQL_HOST', 'MYSQL_PORT', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE']
    
    print("\n📋 os.environ中的数据库环境变量:")
    for var in db_vars:
        value = os.getenv(var)
        if value:
            # 隐藏密码
            if 'PASSWORD' in var or 'URL' in var:
                masked_value = value[:10] + "***" if len(value) > 10 else "***"
                print(f"  {var}: {masked_value}")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: 未设置")

def main():
    """主函数"""
    print("🚀 开始测试数据库配置...")
    
    # 测试环境变量加载
    if not test_env_loading():
        return
    
    # 测试os.environ
    test_os_environ()
    
    # 测试配置类
    if not test_config_class():
        return
    
    print("\n✅ 配置测试完成")

if __name__ == "__main__":
    main()
