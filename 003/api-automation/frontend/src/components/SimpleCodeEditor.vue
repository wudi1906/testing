<template>
  <div class="simple-code-editor">
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
        <n-button size="small" @click="toggleLineNumbers">
          <template #icon>
            <n-icon><Icon icon="mdi:format-list-numbered" /></n-icon>
          </template>
          {{ showLineNumbers ? '隐藏' : '显示' }}行号
        </n-button>
        <n-button size="small" @click="toggleWordWrap">
          <template #icon>
            <n-icon><Icon icon="mdi:wrap" /></n-icon>
          </template>
          {{ wordWrap ? '取消' : '启用' }}换行
        </n-button>
      </div>
    </div>
    
    <div class="editor-container" :style="{ height: height + 'px' }">
      <div class="line-numbers" v-if="showLineNumbers">
        <div 
          v-for="n in lineCount" 
          :key="n" 
          class="line-number"
          :class="{ active: n === currentLine }"
        >
          {{ n }}
        </div>
      </div>
      
      <textarea
        ref="textareaRef"
        v-model="internalValue"
        class="code-textarea"
        :class="{
          'with-line-numbers': showLineNumbers,
          'word-wrap': wordWrap
        }"
        :placeholder="placeholder"
        @input="onInput"
        @scroll="onScroll"
        @keydown="onKeyDown"
        @focus="onFocus"
        @blur="onBlur"
        @click="updateCurrentLine"
        @keyup="updateCurrentLine"
        spellcheck="false"
        autocomplete="off"
        autocorrect="off"
        autocapitalize="off"
      ></textarea>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { NButton, NTag, NIcon } from 'naive-ui'
import { Icon } from '@iconify/vue'

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
  placeholder: {
    type: String,
    default: '# 请输入代码...'
  }
})

// Emits
const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur'])

// Refs
const textareaRef = ref(null)
const internalValue = ref(props.modelValue)
const formatting = ref(false)
const showLineNumbers = ref(true)
const wordWrap = ref(false)
const currentLine = ref(1)

// Computed
const lineCount = computed(() => {
  return internalValue.value.split('\n').length
})

const charCount = computed(() => {
  return internalValue.value.length
})

// Methods
const onInput = (event) => {
  internalValue.value = event.target.value
  emit('update:modelValue', internalValue.value)
  emit('change', internalValue.value)
}

const onScroll = () => {
  // 同步行号滚动
  const textarea = textareaRef.value
  const lineNumbers = textarea.parentElement.querySelector('.line-numbers')
  if (lineNumbers) {
    lineNumbers.scrollTop = textarea.scrollTop
  }
}

const onKeyDown = (event) => {
  // 处理Tab键缩进
  if (event.key === 'Tab') {
    event.preventDefault()
    const textarea = event.target
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    
    if (event.shiftKey) {
      // Shift+Tab: 减少缩进
      const lines = internalValue.value.split('\n')
      const startLine = internalValue.value.substring(0, start).split('\n').length - 1
      const endLine = internalValue.value.substring(0, end).split('\n').length - 1
      
      for (let i = startLine; i <= endLine; i++) {
        if (lines[i].startsWith('    ')) {
          lines[i] = lines[i].substring(4)
        } else if (lines[i].startsWith('\t')) {
          lines[i] = lines[i].substring(1)
        }
      }
      
      internalValue.value = lines.join('\n')
      emit('update:modelValue', internalValue.value)
    } else {
      // Tab: 增加缩进
      const beforeCursor = internalValue.value.substring(0, start)
      const afterCursor = internalValue.value.substring(end)
      
      if (start === end) {
        // 单行缩进
        internalValue.value = beforeCursor + '    ' + afterCursor
        nextTick(() => {
          textarea.selectionStart = textarea.selectionEnd = start + 4
        })
      } else {
        // 多行缩进
        const lines = internalValue.value.split('\n')
        const startLine = beforeCursor.split('\n').length - 1
        const endLine = internalValue.value.substring(0, end).split('\n').length - 1
        
        for (let i = startLine; i <= endLine; i++) {
          lines[i] = '    ' + lines[i]
        }
        
        internalValue.value = lines.join('\n')
      }
      
      emit('update:modelValue', internalValue.value)
    }
  }
  
  // 处理Enter键自动缩进
  if (event.key === 'Enter') {
    const textarea = event.target
    const start = textarea.selectionStart
    const beforeCursor = internalValue.value.substring(0, start)
    const currentLineText = beforeCursor.split('\n').pop()
    
    // 计算当前行的缩进
    const indent = currentLineText.match(/^(\s*)/)[1]
    
    // 如果当前行以冒号结尾，增加一级缩进
    let newIndent = indent
    if (currentLineText.trim().endsWith(':')) {
      newIndent += '    '
    }
    
    setTimeout(() => {
      const afterCursor = internalValue.value.substring(start + 1)
      internalValue.value = internalValue.value.substring(0, start + 1) + newIndent + afterCursor
      textarea.selectionStart = textarea.selectionEnd = start + 1 + newIndent.length
      emit('update:modelValue', internalValue.value)
    }, 0)
  }
}

const updateCurrentLine = () => {
  if (textareaRef.value) {
    const textarea = textareaRef.value
    const start = textarea.selectionStart
    const beforeCursor = internalValue.value.substring(0, start)
    currentLine.value = beforeCursor.split('\n').length
  }
}

const onFocus = () => {
  emit('focus')
}

const onBlur = () => {
  emit('blur')
}

const formatCode = () => {
  formatting.value = true
  try {
    // 简单的Python代码格式化
    if (props.language === 'python') {
      const lines = internalValue.value.split('\n')
      const formattedLines = []
      let indentLevel = 0
      
      for (let line of lines) {
        const trimmed = line.trim()
        if (!trimmed) {
          formattedLines.push('')
          continue
        }
        
        // 减少缩进的关键字
        if (trimmed.startsWith('except') || trimmed.startsWith('elif') || 
            trimmed.startsWith('else') || trimmed.startsWith('finally')) {
          indentLevel = Math.max(0, indentLevel - 1)
        }
        
        // 添加缩进
        formattedLines.push('    '.repeat(indentLevel) + trimmed)
        
        // 增加缩进的关键字
        if (trimmed.endsWith(':') && 
            (trimmed.startsWith('def ') || trimmed.startsWith('class ') || 
             trimmed.startsWith('if ') || trimmed.startsWith('for ') || 
             trimmed.startsWith('while ') || trimmed.startsWith('with ') || 
             trimmed.startsWith('try:') || trimmed.startsWith('except') || 
             trimmed.startsWith('elif ') || trimmed.startsWith('else:'))) {
          indentLevel++
        }
      }
      
      internalValue.value = formattedLines.join('\n')
      emit('update:modelValue', internalValue.value)
    }
  } catch (error) {
    console.error('代码格式化失败:', error)
  } finally {
    formatting.value = false
  }
}

const toggleLineNumbers = () => {
  showLineNumbers.value = !showLineNumbers.value
}

const toggleWordWrap = () => {
  wordWrap.value = !wordWrap.value
}

// Watch
watch(() => props.modelValue, (newValue) => {
  if (newValue !== internalValue.value) {
    internalValue.value = newValue
  }
})

// Lifecycle
onMounted(() => {
  updateCurrentLine()
})

// Expose
defineExpose({
  formatCode,
  toggleLineNumbers,
  toggleWordWrap,
  focus: () => textareaRef.value?.focus()
})
</script>

<style scoped>
.simple-code-editor {
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  overflow: hidden;
  background: #1e1e1e;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
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

.editor-container {
  display: flex;
  position: relative;
  background: #1e1e1e;
}

.line-numbers {
  background: #1e1e1e;
  border-right: 1px solid #3e3e42;
  color: #858585;
  font-size: 14px;
  line-height: 1.5;
  padding: 10px 8px;
  text-align: right;
  user-select: none;
  min-width: 40px;
  overflow: hidden;
}

.line-number {
  height: 21px;
  line-height: 21px;
}

.line-number.active {
  background: #2d2d30;
  color: #cccccc;
}

.code-textarea {
  flex: 1;
  background: #1e1e1e;
  color: #d4d4d4;
  border: none;
  outline: none;
  resize: none;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.5;
  padding: 10px 12px;
  tab-size: 4;
  white-space: pre;
  overflow-wrap: normal;
  overflow-x: auto;
}

.code-textarea.with-line-numbers {
  padding-left: 12px;
}

.code-textarea.word-wrap {
  white-space: pre-wrap;
  overflow-wrap: break-word;
}

.code-textarea::placeholder {
  color: #6a6a6a;
}

.code-textarea:focus {
  background: #1e1e1e;
}

/* 滚动条样式 */
.code-textarea::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}

.code-textarea::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.code-textarea::-webkit-scrollbar-thumb {
  background: #424242;
  border-radius: 6px;
}

.code-textarea::-webkit-scrollbar-thumb:hover {
  background: #4f4f4f;
}

.line-numbers::-webkit-scrollbar {
  width: 0;
}
</style>
