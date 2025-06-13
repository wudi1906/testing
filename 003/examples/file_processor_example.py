"""
文件处理器使用示例
演示如何使用基于marker的文件处理组件来提取markdown格式文本
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent))

from components.config import MarkerConfig
from components.file_processor import FileProcessor, AsyncFileProcessor


async def basic_example():
    """基础使用示例"""
    print("=== 基础文件处理示例 ===")
    
    # 创建配置
    config = MarkerConfig(
        output_format="markdown",
        use_llm=False,  # 不使用LLM以简化示例
        format_lines=True,
        debug=False
    )
    
    # 创建文件处理器
    processor = FileProcessor(config=config)
    
    # 处理示例文件
    test_file = "examples/table.png"  # 使用现有的测试文件
    
    if Path(test_file).exists():
        try:
            print(f"正在处理文件: {test_file}")
            
            # 处理文件
            markdown_content = await processor.process_file(test_file)
            
            # 获取结构化内容
            structured_content = processor.markdown_extractor.get_structured_content(markdown_content)
            
            print(f"处理完成!")
            print(f"文本长度: {structured_content['statistics']['total_characters']} 字符")
            print(f"单词数量: {structured_content['statistics']['total_words']}")
            print(f"标题数量: {structured_content['statistics']['headers_count']}")
            print(f"表格数量: {structured_content['statistics']['tables_count']}")
            print(f"图片数量: {structured_content['statistics']['images_count']}")
            
            # 显示前500个字符的内容
            preview_text = structured_content['plain_text'][:500]
            print(f"\n内容预览:\n{preview_text}...")
            
            # 保存结果
            output_path = "output/basic_example"
            processor.save_content(markdown_content, output_path)
            print(f"\n结果已保存到: {output_path}")
            
        except Exception as e:
            print(f"处理失败: {str(e)}")
    else:
        print(f"测试文件不存在: {test_file}")


async def advanced_example_with_llm():
    """使用LLM的高级示例"""
    print("\n=== 使用LLM的高级处理示例 ===")
    
    # 检查是否有API密钥
    api_key = os.getenv("QWEN_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("跳过LLM示例 - 未设置API密钥")
        print("请设置环境变量 QWEN_API_KEY 或 OPENAI_API_KEY")
        return
    
    # 创建带LLM的配置
    config = MarkerConfig(
        output_format="markdown",
        use_llm=True,
        format_lines=True,
        redo_inline_math=True,
        qwen_api_key=os.getenv("QWEN_API_KEY", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        debug=False
    )
    
    # 创建文件处理器
    processor = FileProcessor(config=config)
    
    # 处理示例文件
    test_file = "examples/account.pdf"  # 使用现有的PDF文件
    
    if Path(test_file).exists():
        try:
            print(f"正在使用LLM处理文件: {test_file}")
            
            # 处理文件
            markdown_content = await processor.process_file(test_file)
            
            # 获取结构化内容
            structured_content = processor.markdown_extractor.get_structured_content(markdown_content)
            
            print(f"LLM处理完成!")
            print(f"文本长度: {structured_content['statistics']['total_characters']} 字符")
            print(f"表格数量: {structured_content['statistics']['tables_count']}")
            print(f"数学表达式数量: {structured_content['statistics']['math_expressions_count']}")
            
            # 显示表格内容
            if structured_content['tables']:
                print(f"\n发现的表格:")
                for i, table in enumerate(structured_content['tables'][:2]):  # 只显示前2个表格
                    print(f"表格 {i+1}:")
                    print(table[:200] + "..." if len(table) > 200 else table)
                    print()
            
            # 保存结果
            output_path = "output/llm_example"
            processor.save_content(markdown_content, output_path)
            print(f"结果已保存到: {output_path}")
            
        except Exception as e:
            print(f"LLM处理失败: {str(e)}")
    else:
        print(f"测试文件不存在: {test_file}")


async def batch_processing_example():
    """批量处理示例"""
    print("\n=== 批量文件处理示例 ===")
    
    # 创建配置
    config = MarkerConfig(
        output_format="markdown",
        use_llm=False,
        format_lines=True
    )
    
    # 创建异步文件处理器
    processor = AsyncFileProcessor(config=config, max_concurrent=2)
    
    # 查找示例文件
    examples_dir = Path("examples")
    test_files = []
    
    for pattern in ["*.pdf", "*.png", "*.jpg"]:
        test_files.extend(examples_dir.glob(pattern))
    
    if test_files:
        print(f"找到 {len(test_files)} 个测试文件")
        
        try:
            # 并发处理多个文件
            results = await processor.process_multiple_files_concurrent(test_files[:3])  # 只处理前3个文件
            
            print("批量处理结果:")
            for result in results:
                if result['status'] == 'success':
                    stats = result['markdown_content']['statistics']
                    print(f"✓ {Path(result['file_path']).name}: {stats['total_characters']} 字符")
                else:
                    print(f"✗ {Path(result['file_path']).name}: {result['error']}")
                    
        except Exception as e:
            print(f"批量处理失败: {str(e)}")
    else:
        print("未找到测试文件")


async def search_example():
    """内容搜索示例"""
    print("\n=== 内容搜索示例 ===")
    
    # 创建配置
    config = MarkerConfig(output_format="markdown")
    processor = FileProcessor(config=config)
    
    # 处理文件
    test_file = "examples/table.png"
    
    if Path(test_file).exists():
        try:
            print(f"处理文件并搜索内容: {test_file}")
            
            # 处理文件
            markdown_content = await processor.process_file(test_file)
            
            # 搜索关键词
            search_terms = ["table", "data", "value"]
            
            for term in search_terms:
                results = processor.search_in_content(markdown_content, term, case_sensitive=False)
                if results:
                    print(f"\n搜索 '{term}' 找到 {len(results)} 个结果:")
                    for result in results[:3]:  # 只显示前3个结果
                        print(f"  行 {result['line_number']}: {result['line_content'][:100]}...")
                else:
                    print(f"\n搜索 '{term}': 未找到结果")
                    
        except Exception as e:
            print(f"搜索示例失败: {str(e)}")
    else:
        print(f"测试文件不存在: {test_file}")


async def configuration_example():
    """配置示例"""
    print("\n=== 配置管理示例 ===")
    
    # 创建基础配置
    config = MarkerConfig()
    processor = FileProcessor(config=config)
    
    print("默认配置:")
    current_config = processor.get_config()
    for key, value in current_config.items():
        print(f"  {key}: {value}")
    
    print("\n支持的文件格式:")
    supported_formats = processor.get_supported_formats()
    for category, extensions in supported_formats.items():
        print(f"  {category}: {', '.join(extensions)}")
    
    # 更新配置
    print("\n更新配置...")
    processor.update_config(
        output_format="json",
        format_lines=True,
        debug=True
    )
    
    print("更新后的配置:")
    updated_config = processor.get_config()
    for key, value in updated_config.items():
        if key in ["output_format", "format_lines", "debug"]:
            print(f"  {key}: {value}")


async def main():
    """主函数"""
    print("文件处理器组件示例")
    print("=" * 50)
    
    # 创建输出目录
    Path("output").mkdir(exist_ok=True)
    
    try:
        # 运行各种示例
        await basic_example()
        await advanced_example_with_llm()
        await batch_processing_example()
        await search_example()
        await configuration_example()
        
        print("\n" + "=" * 50)
        print("所有示例运行完成!")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n运行示例时出错: {str(e)}")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
