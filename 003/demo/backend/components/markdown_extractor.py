"""
Markdown文本提取器
从marker转换结果中提取和处理markdown格式文本
"""

import re
import json
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MarkdownContent:
    """Markdown内容数据类"""
    text: str
    images: Dict[str, Any]
    metadata: Dict[str, Any]
    tables: List[str]
    headers: List[str]
    links: List[str]
    code_blocks: List[str]
    math_expressions: List[str]


class MarkdownExtractor:
    """Markdown文本提取器"""
    
    def __init__(self):
        # 正则表达式模式
        self.patterns = {
            'headers': re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE),
            'links': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
            'images': re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
            'code_blocks': re.compile(r'```[\s\S]*?```', re.MULTILINE),
            'inline_code': re.compile(r'`([^`]+)`'),
            'math_blocks': re.compile(r'\$\$[\s\S]*?\$\$', re.MULTILINE),
            'inline_math': re.compile(r'\$([^$]+)\$'),
            'tables': re.compile(r'^\|.*\|$', re.MULTILINE),
            'bold': re.compile(r'\*\*([^*]+)\*\*'),
            'italic': re.compile(r'\*([^*]+)\*'),
            'strikethrough': re.compile(r'~~([^~]+)~~'),
        }
    
    def extract_from_rendered(self, rendered_result: Any) -> MarkdownContent:
        """从marker渲染结果中提取markdown内容"""
        try:
            # 处理不同类型的渲染结果
            if hasattr(rendered_result, 'markdown'):
                # 标准markdown输出
                text = rendered_result.markdown
                images = getattr(rendered_result, 'images', {})
                metadata = getattr(rendered_result, 'metadata', {})
            elif hasattr(rendered_result, 'children'):
                # JSON格式输出
                text, images, metadata = self._extract_from_json(rendered_result)
            else:
                # 字符串格式
                text = str(rendered_result)
                images = {}
                metadata = {}
            
            return self._analyze_markdown_content(text, images, metadata)
            
        except Exception as e:
            raise Exception(f"提取markdown内容失败: {str(e)}")
    
    def _extract_from_json(self, json_result: Any) -> Tuple[str, Dict, Dict]:
        """从JSON格式结果中提取内容"""
        text_parts = []
        images = {}
        metadata = getattr(json_result, 'metadata', {})
        
        def extract_text_recursive(block):
            if hasattr(block, 'children') and block.children:
                for child in block.children:
                    extract_text_recursive(child)
            
            # 提取文本内容
            if hasattr(block, 'html'):
                # 从HTML中提取纯文本
                html_content = block.html
                # 简单的HTML到文本转换
                text_content = re.sub(r'<[^>]+>', '', html_content)
                if text_content.strip():
                    text_parts.append(text_content.strip())
            
            # 提取图片
            if hasattr(block, 'images') and block.images:
                images.update(block.images)
        
        if hasattr(json_result, 'children'):
            for page in json_result.children if isinstance(json_result.children, list) else [json_result]:
                extract_text_recursive(page)
        
        return '\n\n'.join(text_parts), images, metadata
    
    def _analyze_markdown_content(self, text: str, images: Dict, metadata: Dict) -> MarkdownContent:
        """分析markdown内容，提取各种元素"""
        
        # 提取标题
        headers = [match.group(1) for match in self.patterns['headers'].finditer(text)]
        
        # 提取链接
        links = [match.group(2) for match in self.patterns['links'].finditer(text)]
        
        # 提取代码块
        code_blocks = [match.group(0) for match in self.patterns['code_blocks'].finditer(text)]
        
        # 提取数学表达式
        math_blocks = [match.group(0) for match in self.patterns['math_blocks'].finditer(text)]
        inline_math = [match.group(1) for match in self.patterns['inline_math'].finditer(text)]
        math_expressions = math_blocks + inline_math
        
        # 提取表格
        tables = self._extract_tables(text)
        
        return MarkdownContent(
            text=text,
            images=images,
            metadata=metadata,
            tables=tables,
            headers=headers,
            links=links,
            code_blocks=code_blocks,
            math_expressions=math_expressions
        )
    
    def _extract_tables(self, text: str) -> List[str]:
        """提取表格内容"""
        tables = []
        lines = text.split('\n')
        current_table = []
        in_table = False
        
        for line in lines:
            if self.patterns['tables'].match(line):
                if not in_table:
                    in_table = True
                    current_table = [line]
                else:
                    current_table.append(line)
            else:
                if in_table:
                    # 表格结束
                    if current_table:
                        tables.append('\n'.join(current_table))
                    current_table = []
                    in_table = False
        
        # 处理最后一个表格
        if current_table:
            tables.append('\n'.join(current_table))
        
        return tables
    
    def get_plain_text(self, markdown_content: MarkdownContent) -> str:
        """获取纯文本内容（去除markdown格式）"""
        text = markdown_content.text
        
        # 移除代码块
        text = self.patterns['code_blocks'].sub('', text)
        
        # 移除数学表达式
        text = self.patterns['math_blocks'].sub('', text)
        text = self.patterns['inline_math'].sub(r'\1', text)
        
        # 移除图片
        text = self.patterns['images'].sub('', text)
        
        # 移除链接格式，保留文本
        text = self.patterns['links'].sub(r'\1', text)
        
        # 移除格式标记
        text = self.patterns['bold'].sub(r'\1', text)
        text = self.patterns['italic'].sub(r'\1', text)
        text = self.patterns['strikethrough'].sub(r'\1', text)
        text = self.patterns['inline_code'].sub(r'\1', text)
        
        # 移除标题标记
        text = self.patterns['headers'].sub(r'\1', text)
        
        # 清理多余的空行
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def get_structured_content(self, markdown_content: MarkdownContent) -> Dict[str, Any]:
        """获取结构化内容"""
        return {
            'full_text': markdown_content.text,
            'plain_text': self.get_plain_text(markdown_content),
            'headers': markdown_content.headers,
            'tables': markdown_content.tables,
            'links': markdown_content.links,
            'code_blocks': markdown_content.code_blocks,
            'math_expressions': markdown_content.math_expressions,
            'images': markdown_content.images,
            'metadata': markdown_content.metadata,
            'statistics': {
                'total_characters': len(markdown_content.text),
                'total_words': len(markdown_content.text.split()),
                'headers_count': len(markdown_content.headers),
                'tables_count': len(markdown_content.tables),
                'links_count': len(markdown_content.links),
                'code_blocks_count': len(markdown_content.code_blocks),
                'math_expressions_count': len(markdown_content.math_expressions),
                'images_count': len(markdown_content.images)
            }
        }
    
    def save_content(self, markdown_content: MarkdownContent, output_path: str) -> None:
        """保存内容到文件"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 保存markdown文件
        with open(output_path.with_suffix('.md'), 'w', encoding='utf-8') as f:
            f.write(markdown_content.text)
        
        # 保存结构化数据
        structured_data = self.get_structured_content(markdown_content)
        with open(output_path.with_suffix('.json'), 'w', encoding='utf-8') as f:
            json.dump(structured_data, f, ensure_ascii=False, indent=2)
        
        # 保存图片
        if markdown_content.images:
            images_dir = output_path.parent / 'images'
            images_dir.mkdir(exist_ok=True)
            
            for image_name, image_data in markdown_content.images.items():
                if isinstance(image_data, bytes):
                    image_path = images_dir / image_name
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
    
    def search_content(self, markdown_content: MarkdownContent, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """在内容中搜索"""
        flags = 0 if case_sensitive else re.IGNORECASE
        pattern = re.compile(re.escape(query), flags)
        
        results = []
        lines = markdown_content.text.split('\n')
        
        for i, line in enumerate(lines):
            matches = list(pattern.finditer(line))
            for match in matches:
                results.append({
                    'line_number': i + 1,
                    'line_content': line,
                    'match_start': match.start(),
                    'match_end': match.end(),
                    'matched_text': match.group()
                })
        
        return results
