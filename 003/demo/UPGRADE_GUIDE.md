# 文件处理组件升级指南

## 概述

我们已经成功将后端的文档处理逻辑从基础的PyPDF2/python-docx升级到基于marker的高级文档处理组件。这次升级带来了显著的功能增强和处理质量提升。

## 主要改进

### 🚀 功能增强

1. **支持更多文件格式**
   - 新增：PPT/PPTX, HTML, EPUB, 多种图片格式
   - 原有：PDF, DOCX, XLSX 等

2. **高质量文档转换**
   - 基于marker的AI模型，保持文档结构和格式
   - 自动识别表格、数学公式、代码块等复杂内容
   - 可选的LLM增强，进一步提升转换质量

3. **丰富的内容提取**
   - 自动提取标题、表格、链接、图片等结构化信息
   - 提供统计信息（字符数、单词数、元素计数等）
   - 支持内容搜索功能

4. **灵活的配置选项**
   - 可配置输出格式（markdown, json, html）
   - 可选择是否使用LLM增强
   - 支持OCR、格式化等高级选项

## 文件变更

### 新增文件

```
components/
├── __init__.py              # 组件包初始化
├── config.py               # 配置管理
├── markdown_extractor.py   # Markdown文本提取器
├── file_processor.py       # 主要文件处理器
├── requirements.txt        # 组件依赖
└── README.md              # 组件使用说明

examples/
└── file_processor_example.py  # 使用示例

test_new_components.py      # 测试脚本
UPGRADE_GUIDE.md           # 本升级指南
```

### 修改文件

1. **backend/document_service.py** - 完全重写
   - 移除了PyPDF2/python-docx的直接使用
   - 集成了新的marker文件处理器
   - 保持了原有API的兼容性

2. **backend/requirements.txt** - 更新依赖
   - 添加了marker-pdf依赖
   - 保留了原有依赖作为备用

3. **backend/main.py** - 增强API
   - 更新了上传接口，返回更丰富的信息
   - 新增了配置管理、格式查询、内容搜索等API

## API 变更

### 现有API增强

#### POST /upload
**原返回格式保持不变，但新增了额外信息：**

```json
{
  "status": "success",
  "message": "文件上传成功",
  "data": {
    "filename": "document.pdf",
    "content": "纯文本内容...",  // 用于聊天的文本
    "file_size": 1024000,
    "file_type": ".pdf",
    // 新增的详细信息
    "markdown_content": {
      "statistics": {
        "total_characters": 5000,
        "total_words": 800,
        "tables_count": 2,
        "images_count": 1,
        "headers_count": 5
      },
      "has_tables": true,
      "has_images": true,
      "has_math": false
    },
    "processing_info": {
      "llm_enabled": false,
      "format_enhanced": true
    }
  }
}
```

### 新增API

#### GET /upload/formats
获取支持的文件格式信息

#### POST /upload/search
在已上传的文档中搜索内容

#### GET/POST /upload/config
获取和更新文档处理配置

## 环境配置

### 必需依赖

```bash
pip install marker-pdf>=1.7.0
```

### 可选配置（LLM增强）

设置环境变量以启用LLM增强功能：

```bash
# 使用通义千问（推荐）
export QWEN_API_KEY="your-qwen-api-key"

# 或使用OpenAI
export OPENAI_API_KEY="your-openai-api-key"
```

## 使用示例

### 基础文件处理

```python
from backend.document_service import DocumentService

# 创建服务
doc_service = DocumentService()

# 处理文件
result = await doc_service.process_file_direct("document.pdf")
print(f"提取的文本: {result['content']}")
print(f"表格数量: {result['markdown_content']['statistics']['tables_count']}")
```

### 配置管理

```python
# 获取当前配置
config = doc_service.get_processing_config()

# 更新配置
doc_service.update_config(
    use_llm=True,
    format_lines=True,
    force_ocr=False
)
```

### 内容搜索

```python
# 在文档中搜索
results = await doc_service.search_in_document(
    file_path="uploads/document.pdf",
    query="关键词",
    case_sensitive=False
)
```

## 测试验证

运行测试脚本验证升级：

```bash
python test_new_components.py
```

运行完整示例：

```bash
python examples/file_processor_example.py
```

## 兼容性说明

### 向后兼容

- 原有的上传API完全兼容
- 聊天功能继续使用提取的纯文本
- 文件大小限制从10MB提升到50MB

### 性能影响

- **处理时间**: marker处理可能比原有方法稍慢，但质量显著提升
- **内存使用**: 首次使用时会下载AI模型（约3-5GB）
- **存储空间**: 模型缓存需要额外存储空间

### 降级方案

如果需要回退到原有实现，可以：

1. 恢复原有的document_service.py
2. 移除marker-pdf依赖
3. 恢复原有的requirements.txt

## 故障排除

### 常见问题

1. **ImportError: No module named 'marker'**
   ```bash
   pip install marker-pdf
   ```

2. **模型下载失败**
   - 检查网络连接
   - 确保有足够的磁盘空间（5GB+）

3. **LLM功能不工作**
   - 检查API密钥设置
   - 验证网络连接到LLM服务

4. **处理速度慢**
   - 首次运行需要下载模型
   - 考虑禁用LLM以提升速度
   - 使用GPU加速（如果可用）

### 日志调试

启用调试模式：

```python
doc_service.update_config(debug=True)
```

## 后续计划

1. **性能优化**: 实现模型预加载和缓存优化
2. **批量处理**: 支持多文件并发处理
3. **格式扩展**: 支持更多文档格式
4. **API增强**: 添加更多文档分析功能

## 支持

如有问题，请：

1. 查看组件文档：`components/README.md`
2. 运行测试脚本：`python test_new_components.py`
3. 查看示例代码：`examples/file_processor_example.py`
