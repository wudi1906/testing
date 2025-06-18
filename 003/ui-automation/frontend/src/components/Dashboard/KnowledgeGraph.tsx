import React, { useEffect, useRef, useState } from 'react';
import { Card, Select, Button, Space, Typography, Tag } from 'antd';
import { motion } from 'framer-motion';
import * as d3 from 'd3';
import {
  FullscreenOutlined,
  ReloadOutlined,
  ZoomInOutlined,
  ZoomOutOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;

interface Node {
  id: string;
  name: string;
  type: 'system' | 'module' | 'test' | 'agent' | 'service';
  category: string;
  size: number;
  color: string;
  description?: string;
}

interface Link {
  source: string;
  target: string;
  type: 'depends' | 'calls' | 'generates' | 'executes' | 'analyzes';
  strength: number;
}

interface KnowledgeGraphProps {
  width?: number;
  height?: number;
}

const KnowledgeGraph: React.FC<KnowledgeGraphProps> = ({ 
  width = 800, 
  height = 600 
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const [selectedView, setSelectedView] = useState<string>('system');
  const [isFullscreen, setIsFullscreen] = useState(false);

  // 系统架构数据
  const systemData = {
    nodes: [
      // 核心系统
      { id: 'ui-system', name: 'UI自动化测试系统', type: 'system', category: '核心系统', size: 40, color: '#1890ff', description: '主系统' },
      
      // 前端模块
      { id: 'dashboard', name: '仪表盘', type: 'module', category: '前端模块', size: 25, color: '#52c41a', description: '数据展示' },
      { id: 'test-creation', name: '测试创建', type: 'module', category: '前端模块', size: 30, color: '#52c41a', description: '测试用例生成' },
      { id: 'test-execution', name: '测试执行', type: 'module', category: '前端模块', size: 30, color: '#52c41a', description: '测试运行' },
      { id: 'test-results', name: '测试结果', type: 'module', category: '前端模块', size: 25, color: '#52c41a', description: '结果分析' },
      
      // 后端服务
      { id: 'multimodal-service', name: '多模态分析服务', type: 'service', category: '后端服务', size: 35, color: '#722ed1', description: 'AI分析' },
      { id: 'execution-service', name: '执行服务', type: 'service', category: '后端服务', size: 30, color: '#722ed1', description: '测试执行' },
      { id: 'playwright-service', name: 'Playwright服务', type: 'service', category: '后端服务', size: 28, color: '#722ed1', description: '浏览器自动化' },
      { id: 'script-manager', name: '脚本管理器', type: 'service', category: '后端服务', size: 25, color: '#722ed1', description: '脚本存储' },
      
      // AI智能体
      { id: 'analysis-agent', name: '分析智能体', type: 'agent', category: 'AI智能体', size: 30, color: '#fa8c16', description: 'UI分析' },
      { id: 'generation-agent', name: '生成智能体', type: 'agent', category: 'AI智能体', size: 30, color: '#fa8c16', description: '脚本生成' },
      { id: 'monitoring-agent', name: '监控智能体', type: 'agent', category: 'AI智能体', size: 25, color: '#fa8c16', description: '执行监控' },
      { id: 'playwright-agent', name: 'Playwright智能体', type: 'agent', category: 'AI智能体', size: 28, color: '#fa8c16', description: 'Playwright代码生成' },
      
      // 测试类型
      { id: 'yaml-test', name: 'YAML测试', type: 'test', category: '测试类型', size: 20, color: '#13c2c2', description: 'MidScene.js YAML' },
      { id: 'playwright-test', name: 'Playwright测试', type: 'test', category: '测试类型', size: 20, color: '#13c2c2', description: 'Playwright脚本' },
      { id: 'web-test', name: 'Web测试', type: 'test', category: '测试类型', size: 22, color: '#13c2c2', description: '网页自动化' },
      { id: 'android-test', name: 'Android测试', type: 'test', category: '测试类型', size: 22, color: '#13c2c2', description: '移动端自动化' }
    ] as Node[],
    
    links: [
      // 前端到后端
      { source: 'test-creation', target: 'multimodal-service', type: 'calls', strength: 0.8 },
      { source: 'test-execution', target: 'execution-service', type: 'calls', strength: 0.9 },
      { source: 'test-execution', target: 'playwright-service', type: 'calls', strength: 0.7 },
      { source: 'dashboard', target: 'script-manager', type: 'calls', strength: 0.6 },
      
      // 服务间调用
      { source: 'multimodal-service', target: 'analysis-agent', type: 'calls', strength: 0.9 },
      { source: 'multimodal-service', target: 'generation-agent', type: 'calls', strength: 0.8 },
      { source: 'execution-service', target: 'monitoring-agent', type: 'calls', strength: 0.7 },
      { source: 'playwright-service', target: 'playwright-agent', type: 'calls', strength: 0.9 },
      
      // 智能体生成测试
      { source: 'generation-agent', target: 'yaml-test', type: 'generates', strength: 0.8 },
      { source: 'playwright-agent', target: 'playwright-test', type: 'generates', strength: 0.8 },
      
      // 测试执行
      { source: 'yaml-test', target: 'web-test', type: 'executes', strength: 0.7 },
      { source: 'playwright-test', target: 'web-test', type: 'executes', strength: 0.8 },
      { source: 'yaml-test', target: 'android-test', type: 'executes', strength: 0.6 },
      
      // 核心依赖
      { source: 'ui-system', target: 'dashboard', type: 'depends', strength: 1.0 },
      { source: 'ui-system', target: 'test-creation', type: 'depends', strength: 1.0 },
      { source: 'ui-system', target: 'test-execution', type: 'depends', strength: 1.0 },
      { source: 'ui-system', target: 'test-results', type: 'depends', strength: 1.0 }
    ] as Link[]
  };

  const testFlowData = {
    nodes: [
      { id: 'upload', name: '上传图片/URL', type: 'test', category: '输入', size: 25, color: '#1890ff', description: '测试输入' },
      { id: 'ai-analysis', name: 'AI分析', type: 'agent', category: '分析', size: 30, color: '#fa8c16', description: '多模态分析' },
      { id: 'element-detection', name: '元素识别', type: 'agent', category: '分析', size: 25, color: '#fa8c16', description: 'UI元素检测' },
      { id: 'test-generation', name: '测试生成', type: 'agent', category: '生成', size: 30, color: '#52c41a', description: '自动生成测试' },
      { id: 'yaml-output', name: 'YAML脚本', type: 'test', category: '输出', size: 25, color: '#722ed1', description: 'MidScene.js格式' },
      { id: 'playwright-output', name: 'Playwright脚本', type: 'test', category: '输出', size: 25, color: '#722ed1', description: 'TypeScript代码' },
      { id: 'execution', name: '执行测试', type: 'service', category: '执行', size: 30, color: '#13c2c2', description: '自动化执行' },
      { id: 'monitoring', name: '实时监控', type: 'agent', category: '监控', size: 25, color: '#fa8c16', description: '执行监控' },
      { id: 'results', name: '测试结果', type: 'test', category: '输出', size: 25, color: '#52c41a', description: '执行结果' },
      { id: 'reports', name: '测试报告', type: 'test', category: '输出', size: 25, color: '#52c41a', description: 'HTML报告' }
    ] as Node[],
    
    links: [
      { source: 'upload', target: 'ai-analysis', type: 'analyzes', strength: 0.9 },
      { source: 'ai-analysis', target: 'element-detection', type: 'calls', strength: 0.8 },
      { source: 'element-detection', target: 'test-generation', type: 'calls', strength: 0.9 },
      { source: 'test-generation', target: 'yaml-output', type: 'generates', strength: 0.8 },
      { source: 'test-generation', target: 'playwright-output', type: 'generates', strength: 0.7 },
      { source: 'yaml-output', target: 'execution', type: 'executes', strength: 0.8 },
      { source: 'playwright-output', target: 'execution', type: 'executes', strength: 0.8 },
      { source: 'execution', target: 'monitoring', type: 'calls', strength: 0.7 },
      { source: 'execution', target: 'results', type: 'generates', strength: 0.9 },
      { source: 'results', target: 'reports', type: 'generates', strength: 0.8 }
    ] as Link[]
  };

  const getCurrentData = () => {
    return selectedView === 'system' ? systemData : testFlowData;
  };

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const data = getCurrentData();
    const containerWidth = isFullscreen ? window.innerWidth - 100 : width;
    const containerHeight = isFullscreen ? window.innerHeight - 200 : height;

    // 创建力导向图
    const simulation = d3.forceSimulation(data.nodes)
      .force("link", d3.forceLink(data.links).id((d: any) => d.id).distance(100).strength(0.5))
      .force("charge", d3.forceManyBody().strength(-300))
      .force("center", d3.forceCenter(containerWidth / 2, containerHeight / 2))
      .force("collision", d3.forceCollide().radius(30));

    // 创建缩放行为
    const zoom = d3.zoom()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        container.attr("transform", event.transform);
      });

    svg.call(zoom as any);

    const container = svg.append("g");

    // 创建箭头标记
    const defs = svg.append("defs");
    
    const arrowMarker = defs.append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 15)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto");

    arrowMarker.append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#999");

    // 绘制连接线
    const link = container.append("g")
      .selectAll("line")
      .data(data.links)
      .enter().append("line")
      .attr("stroke", "#999")
      .attr("stroke-opacity", 0.6)
      .attr("stroke-width", (d: any) => Math.sqrt(d.strength * 5))
      .attr("marker-end", "url(#arrowhead)");

    // 绘制节点
    const node = container.append("g")
      .selectAll("g")
      .data(data.nodes)
      .enter().append("g")
      .call(d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended) as any);

    // 节点圆圈
    node.append("circle")
      .attr("r", (d: any) => d.size)
      .attr("fill", (d: any) => d.color)
      .attr("stroke", "#fff")
      .attr("stroke-width", 2)
      .style("filter", "drop-shadow(2px 2px 4px rgba(0,0,0,0.3))")
      .on("mouseover", function(event, d: any) {
        d3.select(this).transition().duration(200).attr("r", d.size * 1.2);
        
        // 显示tooltip
        const tooltip = d3.select("body").append("div")
          .attr("class", "graph-tooltip")
          .style("opacity", 0)
          .style("position", "absolute")
          .style("background", "rgba(0, 0, 0, 0.8)")
          .style("color", "white")
          .style("padding", "8px")
          .style("border-radius", "4px")
          .style("font-size", "12px")
          .style("pointer-events", "none")
          .style("z-index", "1000");

        tooltip.transition().duration(200).style("opacity", 1);
        tooltip.html(`<strong>${d.name}</strong><br/>${d.description || d.category}`)
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 10) + "px");
      })
      .on("mouseout", function(event, d: any) {
        d3.select(this).transition().duration(200).attr("r", d.size);
        d3.selectAll(".graph-tooltip").remove();
      });

    // 节点标签
    node.append("text")
      .text((d: any) => d.name)
      .attr("x", 0)
      .attr("y", (d: any) => d.size + 15)
      .attr("text-anchor", "middle")
      .attr("font-size", "12px")
      .attr("font-weight", "500")
      .attr("fill", "#333");

    // 节点图标（根据类型显示不同图标）
    node.append("text")
      .text((d: any) => {
        switch(d.type) {
          case 'system': return '🏢';
          case 'module': return '📱';
          case 'service': return '⚙️';
          case 'agent': return '🤖';
          case 'test': return '🧪';
          default: return '📄';
        }
      })
      .attr("x", 0)
      .attr("y", 5)
      .attr("text-anchor", "middle")
      .attr("font-size", "16px");

    // 更新位置
    simulation.on("tick", () => {
      link
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);

      node.attr("transform", (d: any) => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    return () => {
      simulation.stop();
    };
  }, [selectedView, width, height, isFullscreen]);

  const handleZoomIn = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().scaleBy as any, 1.5
    );
  };

  const handleZoomOut = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().scaleBy as any, 0.75
    );
  };

  const handleReset = () => {
    const svg = d3.select(svgRef.current);
    svg.transition().call(
      d3.zoom().transform as any,
      d3.zoomIdentity
    );
  };

  return (
    <Card 
      title="系统知识图谱" 
      className="knowledge-graph-card"
      extra={
        <Space>
          <Select
            value={selectedView}
            onChange={setSelectedView}
            style={{ width: 120 }}
          >
            <Option value="system">系统架构</Option>
            <Option value="flow">测试流程</Option>
          </Select>
          <Button icon={<ZoomInOutlined />} onClick={handleZoomIn} />
          <Button icon={<ZoomOutOutlined />} onClick={handleZoomOut} />
          <Button icon={<ReloadOutlined />} onClick={handleReset} />
          <Button 
            icon={<FullscreenOutlined />} 
            onClick={() => setIsFullscreen(!isFullscreen)}
          />
        </Space>
      }
    >
      <div className="graph-legend" style={{ marginBottom: 16 }}>
        <Space wrap>
          <Tag color="#1890ff">🏢 系统</Tag>
          <Tag color="#52c41a">📱 模块</Tag>
          <Tag color="#722ed1">⚙️ 服务</Tag>
          <Tag color="#fa8c16">🤖 智能体</Tag>
          <Tag color="#13c2c2">🧪 测试</Tag>
        </Space>
      </div>
      
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
        style={{ 
          width: isFullscreen ? '100vw' : '100%', 
          height: isFullscreen ? '100vh' : height,
          position: isFullscreen ? 'fixed' : 'relative',
          top: isFullscreen ? 0 : 'auto',
          left: isFullscreen ? 0 : 'auto',
          zIndex: isFullscreen ? 1000 : 'auto',
          background: isFullscreen ? '#fff' : 'transparent'
        }}
      >
        <svg
          ref={svgRef}
          width={isFullscreen ? window.innerWidth : width}
          height={isFullscreen ? window.innerHeight - 100 : height}
          style={{ border: '1px solid #f0f0f0', borderRadius: '8px' }}
        />
      </motion.div>
    </Card>
  );
};

export default KnowledgeGraph;
