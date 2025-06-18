// 测试数据：模拟实际的流式输出顺序
export const mockStreamingMessages = [
  {
    message_id: "msg-1",
    type: "message",
    source: "UI专家",
    content: "<think>我需要分析这个界面的UI元素，首先观察整体布局</think>开始分析UI界面结构...",
    region: "analysis",
    platform: "web",
    is_final: false,
    timestamp: "2025-06-02T14:28:01.000Z"
  },
  {
    message_id: "msg-2", 
    type: "message",
    source: "UI专家",
    content: "识别到登录表单，包含用户名和密码输入框。<think>这个表单看起来是标准的登录界面，我需要分析每个元素的定位方式</think>",
    region: "analysis",
    platform: "web", 
    is_final: false,
    timestamp: "2025-06-02T14:28:02.000Z"
  },
  {
    message_id: "msg-3",
    type: "message", 
    source: "交互分析师",
    content: "<think>基于UI专家的分析，我需要设计用户交互流程</think>设计测试交互流程：\n1. 输入用户名\n2. 输入密码\n3. 点击登录按钮",
    region: "interaction",
    platform: "web",
    is_final: false,
    timestamp: "2025-06-02T14:28:03.000Z"
  },
  {
    message_id: "msg-4",
    type: "message",
    source: "交互分析师", 
    content: "验证交互元素的可访问性。<think>我需要确保所有的交互元素都能被正确识别和操作</think>所有元素均可正常交互。",
    region: "interaction",
    platform: "web",
    is_final: false,
    timestamp: "2025-06-02T14:28:04.000Z"
  },
  {
    message_id: "msg-5",
    type: "message",
    source: "质量审查员",
    content: "<think>我需要审查前面专家们的分析结果，确保测试用例的完整性</think>审查测试用例设计...\n\n发现以下测试场景：\n- 正常登录流程\n- 错误处理验证",
    region: "quality",
    platform: "web", 
    is_final: false,
    timestamp: "2025-06-02T14:28:05.000Z"
  },
  {
    message_id: "msg-6",
    type: "message",
    source: "YAML生成器",
    content: "<think>基于所有专家的分析，我现在开始生成YAML测试脚本</think>开始生成MidScene.js YAML脚本...\n\n```yaml\nname: 登录功能测试\nsteps:\n  - action: type\n    target: '[placeholder=\"用户名\"]'\n    value: 'testuser'\n```",
    region: "generation", 
    platform: "web",
    is_final: true,
    timestamp: "2025-06-02T14:28:06.000Z"
  }
];

// 模拟实时流式数据接收
export const simulateStreamingData = (
  onMessage: (message: any) => void,
  onComplete: () => void
) => {
  let index = 0;
  
  const sendNextMessage = () => {
    if (index < mockStreamingMessages.length) {
      onMessage(mockStreamingMessages[index]);
      index++;
      setTimeout(sendNextMessage, 1000); // 每秒发送一条消息
    } else {
      onComplete();
    }
  };
  
  setTimeout(sendNextMessage, 500); // 延迟500ms开始
};
