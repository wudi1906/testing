#!/usr/bin/env python3
"""
批量修复Vue文件中的图标使用问题
"""
import os
import re
from pathlib import Path


def fix_icons_in_file(file_path):
    """修复单个文件中的图标问题"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # 1. 添加 Icon 导入（如果还没有）
        if 'import { Icon }' not in content and '<mdi:' in content:
            # 查找现有的导入语句
            import_pattern = r"(import.*from\s+['\"]vue['\"])"
            if re.search(import_pattern, content):
                content = re.sub(
                    import_pattern,
                    r"\1\nimport { Icon } from '@iconify/vue'",
                    content,
                    count=1
                )
            else:
                # 如果没有找到vue导入，在script setup后添加
                script_pattern = r"(<script setup>)"
                if re.search(script_pattern, content):
                    content = re.sub(
                        script_pattern,
                        r"\1\nimport { Icon } from '@iconify/vue'",
                        content,
                        count=1
                    )
        
        # 2. 修复图标使用方式
        # 将 <mdi:icon-name /> 替换为 <Icon icon="mdi:icon-name" />
        icon_pattern = r'<(mdi:[a-zA-Z0-9-]+)\s*/>'
        content = re.sub(icon_pattern, r'<Icon icon="\1" />', content)
        
        # 3. 修复在n-icon中的使用
        # 将 <n-icon><mdi:icon-name /></n-icon> 替换为 <n-icon><Icon icon="mdi:icon-name" /></n-icon>
        nicon_pattern = r'<n-icon><(mdi:[a-zA-Z0-9-]+)\s*/></n-icon>'
        content = re.sub(nicon_pattern, r'<n-icon><Icon icon="\1" /></n-icon>', content)
        
        # 4. 修复component :is的使用
        # 将 <component :is="mdi:icon-name" /> 替换为 <Icon :icon="icon-name" />
        component_pattern = r'<component\s+:is="(mdi:[a-zA-Z0-9-]+)"\s*/>'
        content = re.sub(component_pattern, r'<Icon icon="\1" />', content)
        
        # 如果内容有变化，写回文件
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ 修复了 {file_path}")
            return True
        else:
            print(f"- 跳过 {file_path} (无需修复)")
            return False
            
    except Exception as e:
        print(f"✗ 修复 {file_path} 失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("开始批量修复图标使用问题...")
    
    # 查找所有需要修复的Vue文件
    api_automation_dir = Path("frontend/src/views/api-automation")
    
    if not api_automation_dir.exists():
        print(f"目录不存在: {api_automation_dir}")
        return
    
    vue_files = list(api_automation_dir.rglob("*.vue"))
    
    if not vue_files:
        print("没有找到Vue文件")
        return
    
    print(f"找到 {len(vue_files)} 个Vue文件")
    
    fixed_count = 0
    for vue_file in vue_files:
        if fix_icons_in_file(vue_file):
            fixed_count += 1
    
    print(f"\n修复完成！共修复了 {fixed_count} 个文件")


if __name__ == "__main__":
    main()
