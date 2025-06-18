/**
 * 测试JSON数据 - 用于验证JSON格式化显示功能
 */

export const testJsonMessages = [
  {
    message_id: "msg-1",
    type: "message",
    source: "UI分析专家",
    content: `开始分析UI界面结构...

识别到以下UI元素：

\`\`\`json
{
  "ui_elements": [
    {
      "id": "login_form",
      "type": "form",
      "elements": [
        {
          "id": "username_input",
          "type": "input",
          "placeholder": "请输入用户名",
          "required": true,
          "validation": {
            "minLength": 3,
            "maxLength": 20,
            "pattern": "^[a-zA-Z0-9_]+$"
          }
        },
        {
          "id": "password_input",
          "type": "password",
          "placeholder": "请输入密码",
          "required": true,
          "validation": {
            "minLength": 6,
            "maxLength": 50
          }
        },
        {
          "id": "login_button",
          "type": "button",
          "text": "登录",
          "style": {
            "backgroundColor": "#1890ff",
            "color": "white",
            "borderRadius": "4px"
          }
        }
      ]
    }
  ],
  "page_info": {
    "title": "用户登录",
    "url": "https://example.com/login",
    "viewport": {
      "width": 1280,
      "height": 960
    }
  }
}
\`\`\`

分析完成，共识别到3个交互元素。`,
    region: "analysis",
    platform: "web",
    is_final: false,
    timestamp: new Date(Date.now() - 5000).toISOString()
  },
  {
    message_id: "msg-2",
    type: "message",
    source: "交互流程设计师",
    content: `基于UI分析结果，设计用户交互流程：

\`\`\`json
{
  "user_flows": [
    {
      "flow_id": "normal_login",
      "name": "正常登录流程",
      "description": "用户使用正确的用户名和密码登录",
      "steps": [
        {
          "step": 1,
          "action": "input",
          "target": "#username_input",
          "value": "testuser",
          "description": "输入用户名"
        },
        {
          "step": 2,
          "action": "input",
          "target": "#password_input",
          "value": "password123",
          "description": "输入密码"
        },
        {
          "step": 3,
          "action": "click",
          "target": "#login_button",
          "description": "点击登录按钮"
        },
        {
          "step": 4,
          "action": "verify",
          "target": "body",
          "expected": "登录成功",
          "description": "验证登录成功"
        }
      ],
      "expected_result": {
        "status": "success",
        "redirect_url": "/dashboard",
        "message": "登录成功"
      }
    },
    {
      "flow_id": "error_login",
      "name": "错误登录流程",
      "description": "用户使用错误的密码登录",
      "steps": [
        {
          "step": 1,
          "action": "input",
          "target": "#username_input",
          "value": "testuser",
          "description": "输入用户名"
        },
        {
          "step": 2,
          "action": "input",
          "target": "#password_input",
          "value": "wrongpassword",
          "description": "输入错误密码"
        },
        {
          "step": 3,
          "action": "click",
          "target": "#login_button",
          "description": "点击登录按钮"
        },
        {
          "step": 4,
          "action": "verify",
          "target": ".error-message",
          "expected": "用户名或密码错误",
          "description": "验证错误提示"
        }
      ],
      "expected_result": {
        "status": "error",
        "error_code": "INVALID_CREDENTIALS",
        "message": "用户名或密码错误"
      }
    }
  ]
}
\`\`\`

设计了2个主要的用户流程，覆盖正常和异常场景。`,
    region: "interaction",
    platform: "web",
    is_final: false,
    timestamp: new Date(Date.now() - 3000).toISOString()
  },
  {
    message_id: "msg-3",
    type: "message",
    source: "YAML脚本生成器",
    content: `基于分析结果生成MidScene.js YAML测试脚本：

\`\`\`yaml
name: 用户登录功能测试
description: 测试用户登录的正常和异常流程

web:
  url: "https://example.com/login"
  viewportWidth: 1280
  viewportHeight: 960
  waitForNetworkIdle:
    timeout: 2000
    continueOnNetworkIdleError: true
  aiActionContext: "用户登录页面，包含用户名输入框、密码输入框和登录按钮"

tasks:
  - name: "正常登录流程测试"
    continueOnError: false
    flow:
      - aiInput: "testuser"
        locate: "用户名输入框，占位符显示'请输入用户名'"
        deepThink: true
      - aiInput: "password123"
        locate: "密码输入框，占位符显示'请输入密码'"
        deepThink: true
      - aiTap: "蓝色的登录按钮，位于表单底部"
        deepThink: true
      - aiAssert: "页面显示登录成功信息或跳转到仪表板"
        errorMsg: "登录失败，未显示成功信息"

  - name: "错误密码登录测试"
    continueOnError: false
    flow:
      - aiInput: "testuser"
        locate: "用户名输入框"
      - aiInput: "wrongpassword"
        locate: "密码输入框"
      - aiTap: "登录按钮"
      - aiAssert: "页面显示错误提示信息'用户名或密码错误'"
        errorMsg: "未显示预期的错误提示信息"
\`\`\`

同时生成测试配置信息：

\`\`\`json
{
  "test_config": {
    "test_suite": "login_functionality",
    "total_tasks": 2,
    "estimated_duration": "45秒",
    "browser_config": {
      "headless": false,
      "viewport": {
        "width": 1280,
        "height": 960
      },
      "timeout": 30000
    },
    "reporting": {
      "format": ["html", "json"],
      "output_dir": "./test-results",
      "screenshots": true,
      "video": false
    }
  }
}
\`\`\`

脚本生成完成！包含2个测试任务，预计执行时间45秒。`,
    region: "generation",
    platform: "web",
    is_final: true,
    timestamp: new Date().toISOString()
  }
];

export const testComplexJsonMessage = {
  message_id: "msg-complex",
  type: "message",
  source: "复杂数据分析师",
  content: `分析复杂的嵌套JSON数据结构：

这是一个包含多层嵌套的复杂JSON对象：

\`\`\`json
{
  "application": {
    "name": "UI自动化测试系统",
    "version": "2.0.0",
    "modules": {
      "web": {
        "agents": [
          {
            "name": "ImageAnalyzerAgent",
            "type": "multimodal",
            "capabilities": ["ui_analysis", "element_detection", "layout_understanding"],
            "models": {
              "primary": "ui-tars",
              "fallback": "gpt-4-vision",
              "config": {
                "temperature": 0.1,
                "max_tokens": 4000,
                "timeout": 30
              }
            }
          },
          {
            "name": "YAMLGeneratorAgent",
            "type": "text",
            "capabilities": ["script_generation", "yaml_formatting", "test_design"],
            "models": {
              "primary": "deepseek-chat",
              "config": {
                "temperature": 0.3,
                "max_tokens": 8000
              }
            }
          }
        ],
        "workflows": {
          "image_to_yaml": {
            "steps": [
              "image_upload",
              "ui_analysis",
              "interaction_design",
              "quality_review",
              "yaml_generation"
            ],
            "parallel_execution": false,
            "timeout": 300
          }
        }
      },
      "android": {
        "status": "planned",
        "agents": []
      }
    },
    "database": {
      "connections": {
        "mysql": {
          "host": "localhost",
          "port": 3306,
          "database": "ui_automation",
          "tables": ["test_cases", "execution_results", "user_sessions"]
        },
        "neo4j": {
          "uri": "bolt://localhost:7687",
          "database": "knowledge_graph"
        }
      }
    }
  }
}
\`\`\`

这个JSON包含了系统的完整配置信息，包括智能体配置、工作流定义和数据库连接等。`,
  region: "analysis",
  platform: "web",
  is_final: false,
  timestamp: new Date().toISOString()
};

export const testMixedContentMessage = {
  message_id: "msg-mixed",
  type: "message", 
  source: "混合内容分析师",
  content: `这是一个包含多种内容类型的消息：

## 分析结果概述

首先是一些普通的文本描述，然后是JSON数据：

{"simple": "json", "number": 42, "boolean": true}

接下来是格式化的JSON：

\`\`\`json
{
  "formatted": {
    "data": "这是格式化的JSON",
    "array": [1, 2, 3, 4, 5],
    "nested": {
      "level1": {
        "level2": {
          "value": "深层嵌套的值"
        }
      }
    }
  }
}
\`\`\`

还有一些YAML内容：

\`\`\`yaml
name: 测试配置
version: 1.0
settings:
  debug: true
  timeout: 30
  retries: 3
\`\`\`

最后是一些总结文本。这种混合内容应该能够正确识别和格式化显示。`,
  region: "mixed",
  platform: "web", 
  is_final: false,
  timestamp: new Date().toISOString()
};
