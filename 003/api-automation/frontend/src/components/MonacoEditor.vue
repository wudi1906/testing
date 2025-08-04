<template>
  <div class="monaco-editor-container">
    <div class="editor-header" v-if="showHeader">
      <div class="editor-info">
        <n-tag type="info" size="small">{{ language.toUpperCase() }}</n-tag>
        <span class="line-info">{{ lineCount }} 行 | {{ charCount }} 字符</span>
      </div>
      <div class="editor-actions">
        <n-button size="small" @click="formatCode" :loading="formatting">
          <template #icon>
            <n-icon><Icon icon="mdi:code-braces" /></n-icon>
          </template>
          格式化
        </n-button>
        <n-button size="small" @click="toggleMinimap">
          <template #icon>
            <n-icon><Icon icon="mdi:map" /></n-icon>
          </template>
          {{ showMinimap ? '隐藏' : '显示' }}小地图
        </n-button>
        <n-button size="small" @click="toggleWordWrap">
          <template #icon>
            <n-icon><Icon icon="mdi:wrap" /></n-icon>
          </template>
          {{ wordWrap ? '取消' : '启用' }}换行
        </n-button>
      </div>
    </div>
    <div 
      ref="editorContainer" 
      class="editor-content"
      :style="{ height: height + 'px' }"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed, nextTick } from 'vue'
import { NButton, NTag, NIcon } from 'naive-ui'
import { Icon } from '@iconify/vue'
import * as monaco from 'monaco-editor'

// Props
const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  language: {
    type: String,
    default: 'python'
  },
  theme: {
    type: String,
    default: 'vs-dark'
  },
  height: {
    type: Number,
    default: 400
  },
  readonly: {
    type: Boolean,
    default: false
  },
  showHeader: {
    type: Boolean,
    default: true
  },
  options: {
    type: Object,
    default: () => ({})
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur'])

// Refs
const editorContainer = ref(null)
const editor = ref(null)
const formatting = ref(false)
const showMinimap = ref(true)
const wordWrap = ref(false)

// Computed
const lineCount = computed(() => {
  if (!editor.value) return 0
  return editor.value.getModel()?.getLineCount() || 0
})

const charCount = computed(() => {
  return props.modelValue.length
})

// 默认编辑器选项
const defaultOptions = {
  automaticLayout: true,
  fontSize: 14,
  fontFamily: 'Consolas, "Courier New", monospace',
  lineNumbers: 'on',
  roundedSelection: false,
  scrollBeyondLastLine: false,
  readOnly: false,
  theme: 'vs-dark',
  minimap: {
    enabled: true
  },
  wordWrap: 'off',
  tabSize: 4,
  insertSpaces: true,
  detectIndentation: false,
  folding: true,
  foldingStrategy: 'indentation',
  showFoldingControls: 'always',
  bracketPairColorization: {
    enabled: true
  },
  guides: {
    indentation: true,
    bracketPairs: true
  },
  suggest: {
    enabled: true,
    showKeywords: true,
    showSnippets: true
  },
  quickSuggestions: {
    other: true,
    comments: true,
    strings: true
  },
  parameterHints: {
    enabled: true
  },
  hover: {
    enabled: true
  }
}

// 初始化编辑器
const initEditor = async () => {
  if (!editorContainer.value) return

  try {
    // 合并选项
    const editorOptions = {
      ...defaultOptions,
      ...props.options,
      value: props.modelValue,
      language: props.language,
      theme: props.theme,
      readOnly: props.readonly
    }

    // 创建编辑器实例
    editor.value = monaco.editor.create(editorContainer.value, editorOptions)

    // 监听内容变化
    editor.value.onDidChangeModelContent(() => {
      const value = editor.value.getValue()
      emit('update:modelValue', value)
      emit('change', value)
    })

    // 监听焦点事件
    editor.value.onDidFocusEditorText(() => {
      emit('focus')
    })

    editor.value.onDidBlurEditorText(() => {
      emit('blur')
    })

    // 设置Python语言特定配置
    if (props.language === 'python') {
      setupPythonLanguage()
    }

    console.log('Monaco Editor 初始化成功')
  } catch (error) {
    console.error('Monaco Editor 初始化失败:', error)
  }
}

// 设置Python语言特定配置
const setupPythonLanguage = () => {
  // 设置Python语言配置
  monaco.languages.setLanguageConfiguration('python', {
    comments: {
      lineComment: '#',
      blockComment: ['"""', '"""']
    },
    brackets: [
      ['{', '}'],
      ['[', ']'],
      ['(', ')']
    ],
    autoClosingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"', notIn: ['string'] },
      { open: "'", close: "'", notIn: ['string', 'comment'] }
    ],
    surroundingPairs: [
      { open: '{', close: '}' },
      { open: '[', close: ']' },
      { open: '(', close: ')' },
      { open: '"', close: '"' },
      { open: "'", close: "'" }
    ],
    indentationRules: {
      increaseIndentPattern: /^\s*(class|def|if|elif|else|for|while|with|try|except|finally|async def).*:\s*$/,
      decreaseIndentPattern: /^\s*(elif|else|except|finally)\b.*$/
    }
  })

  // 添加Python代码片段
  monaco.languages.registerCompletionItemProvider('python', {
    provideCompletionItems: (model, position) => {
      const suggestions = [
        {
          label: 'test_function',
          kind: monaco.languages.CompletionItemKind.Snippet,
          insertText: [
            'def test_${1:function_name}():',
            '    """${2:Test description}"""',
            '    # Arrange',
            '    ${3:# Setup test data}',
            '    ',
            '    # Act',
            '    ${4:# Execute the function}',
            '    ',
            '    # Assert',
            '    ${5:# Verify the result}',
            '    assert ${6:condition}'
          ].join('\n'),
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          documentation: '创建一个测试函数模板'
        },
        {
          label: 'api_test',
          kind: monaco.languages.CompletionItemKind.Snippet,
          insertText: [
            'def test_${1:api_endpoint}():',
            '    """测试 ${2:API端点描述}"""',
            '    import requests',
            '    ',
            '    # 准备测试数据',
            '    url = "${3:http://localhost:8000/api/endpoint}"',
            '    headers = {"Content-Type": "application/json"}',
            '    data = {${4:}}',
            '    ',
            '    # 发送请求',
            '    response = requests.${5:get}(url, headers=headers, json=data)',
            '    ',
            '    # 验证响应',
            '    assert response.status_code == ${6:200}',
            '    assert response.json()${7:}'
          ].join('\n'),
          insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
          documentation: '创建一个API测试模板'
        }
      ]
      return { suggestions }
    }
  })
}

// 格式化代码
const formatCode = async () => {
  if (!editor.value) return
  
  formatting.value = true
  try {
    await editor.value.getAction('editor.action.formatDocument').run()
  } catch (error) {
    console.error('代码格式化失败:', error)
  } finally {
    formatting.value = false
  }
}

// 切换小地图
const toggleMinimap = () => {
  showMinimap.value = !showMinimap.value
  if (editor.value) {
    editor.value.updateOptions({
      minimap: { enabled: showMinimap.value }
    })
  }
}

// 切换自动换行
const toggleWordWrap = () => {
  wordWrap.value = !wordWrap.value
  if (editor.value) {
    editor.value.updateOptions({
      wordWrap: wordWrap.value ? 'on' : 'off'
    })
  }
}

// 监听props变化
watch(() => props.modelValue, (newValue) => {
  if (editor.value && editor.value.getValue() !== newValue) {
    editor.value.setValue(newValue || '')
  }
})

watch(() => props.language, (newLanguage) => {
  if (editor.value) {
    monaco.editor.setModelLanguage(editor.value.getModel(), newLanguage)
  }
})

watch(() => props.theme, (newTheme) => {
  if (editor.value) {
    monaco.editor.setTheme(newTheme)
  }
})

// 生命周期
onMounted(async () => {
  await nextTick()
  await initEditor()
})

onUnmounted(() => {
  if (editor.value) {
    editor.value.dispose()
  }
})

// 暴露方法
defineExpose({
  formatCode,
  toggleMinimap,
  toggleWordWrap,
  getEditor: () => editor.value
})
</script>

<style scoped>
.monaco-editor-container {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  background: #1e1e1e;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #2d2d30;
  border-bottom: 1px solid #3e3e42;
}

.editor-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.line-info {
  font-size: 12px;
  color: #cccccc;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.editor-content {
  width: 100%;
}

/* 深色主题下的样式调整 */
:deep(.monaco-editor) {
  background: #1e1e1e !important;
}

:deep(.monaco-editor .margin) {
  background: #1e1e1e !important;
}

:deep(.monaco-editor .monaco-editor-background) {
  background: #1e1e1e !important;
}
</style>
