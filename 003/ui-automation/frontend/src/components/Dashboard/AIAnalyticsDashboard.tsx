import React, { useEffect, useRef, useState } from 'react';
import { Card, Row, Col, Progress, Typography, Tag, Space, Statistic, Button } from 'antd';
import { motion } from 'framer-motion';
import * as echarts from 'echarts';
import {
  ExperimentOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  TrophyOutlined,
  BugOutlined,
  ClockCircleOutlined,
  ReloadOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface AIAnalyticsProps {
  autoRefresh?: boolean;
  data?: {
    aiAccuracy: number;
    elementDetection: number;
    scriptGeneration: number;
    executionSuccess: number;
    timeEfficiency: number;
    defectPrediction: number;
  };
}

const AIAnalyticsDashboard: React.FC<AIAnalyticsProps> = ({
  autoRefresh = true,
  data = {
    aiAccuracy: 94.8,
    elementDetection: 97.2,
    scriptGeneration: 89.5,
    executionSuccess: 96.1,
    timeEfficiency: 87.3,
    defectPrediction: 82.7
  }
}) => {
  const radarChartRef = useRef<HTMLDivElement>(null);
  const heatmapRef = useRef<HTMLDivElement>(null);
  const gaugeChartRef = useRef<HTMLDivElement>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    // AI能力雷达图
    if (radarChartRef.current) {
      const chart = echarts.init(radarChartRef.current);
      
      const option = {
        backgroundColor: 'transparent',
        title: {
          text: 'AI能力分析',
          left: 'center',
          textStyle: {
            color: '#333',
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          trigger: 'item',
          formatter: (params: any) => {
            return `${params.name}: ${params.value}%`;
          }
        },
        radar: {
          indicator: [
            { name: '图像识别', max: 100 },
            { name: '元素定位', max: 100 },
            { name: '脚本生成', max: 100 },
            { name: '执行准确性', max: 100 },
            { name: '异常检测', max: 100 },
            { name: '性能优化', max: 100 }
          ],
          shape: 'polygon',
          radius: '70%',
          axisName: {
            color: '#666',
            fontSize: 12
          },
          splitArea: {
            areaStyle: {
              color: ['rgba(24, 144, 255, 0.1)', 'rgba(24, 144, 255, 0.05)']
            }
          },
          splitLine: {
            lineStyle: {
              color: 'rgba(24, 144, 255, 0.3)'
            }
          }
        },
        series: [{
          name: 'AI能力',
          type: 'radar',
          data: [{
            value: [94.8, 97.2, 89.5, 96.1, 85.3, 87.3],
            name: '当前能力',
            areaStyle: {
              color: 'rgba(24, 144, 255, 0.3)'
            },
            lineStyle: {
              color: '#1890ff',
              width: 2
            },
            itemStyle: {
              color: '#1890ff'
            }
          }]
        }]
      };

      chart.setOption(option);
      
      const handleResize = () => chart.resize();
      window.addEventListener('resize', handleResize);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.dispose();
      };
    }
  }, [data]);

  useEffect(() => {
    // 测试执行热力图
    if (heatmapRef.current) {
      const chart = echarts.init(heatmapRef.current);
      
      // 生成热力图数据
      const hours = [];
      const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
      for (let i = 0; i < 24; i++) {
        hours.push(i + ':00');
      }

      const data = [];
      for (let i = 0; i < 7; i++) {
        for (let j = 0; j < 24; j++) {
          const value = Math.floor(Math.random() * 100);
          data.push([j, i, value]);
        }
      }

      const option = {
        backgroundColor: 'transparent',
        title: {
          text: '测试执行热力图',
          left: 'center',
          textStyle: {
            color: '#333',
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          position: 'top',
          formatter: (params: any) => {
            return `${days[params.data[1]]} ${hours[params.data[0]]}<br/>执行次数: ${params.data[2]}`;
          }
        },
        grid: {
          height: '60%',
          top: '15%'
        },
        xAxis: {
          type: 'category',
          data: hours,
          splitArea: {
            show: true
          },
          axisLabel: {
            color: '#666',
            fontSize: 10
          }
        },
        yAxis: {
          type: 'category',
          data: days,
          splitArea: {
            show: true
          },
          axisLabel: {
            color: '#666',
            fontSize: 12
          }
        },
        visualMap: {
          min: 0,
          max: 100,
          calculable: true,
          orient: 'horizontal',
          left: 'center',
          bottom: '5%',
          inRange: {
            color: ['#e6f7ff', '#1890ff', '#0050b3']
          },
          textStyle: {
            color: '#666'
          }
        },
        series: [{
          name: '执行次数',
          type: 'heatmap',
          data: data,
          label: {
            show: false
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 10,
              shadowColor: 'rgba(0, 0, 0, 0.5)'
            }
          }
        }]
      };

      chart.setOption(option);
      
      const handleResize = () => chart.resize();
      window.addEventListener('resize', handleResize);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.dispose();
      };
    }
  }, []);

  useEffect(() => {
    // AI效率仪表盘
    if (gaugeChartRef.current) {
      const chart = echarts.init(gaugeChartRef.current);
      
      const option = {
        backgroundColor: 'transparent',
        series: [
          {
            name: 'AI效率',
            type: 'gauge',
            startAngle: 180,
            endAngle: 0,
            center: ['50%', '75%'],
            radius: '90%',
            min: 0,
            max: 100,
            splitNumber: 8,
            axisLine: {
              lineStyle: {
                width: 6,
                color: [
                  [0.25, '#ff4d4f'],
                  [0.5, '#fa8c16'],
                  [0.75, '#52c41a'],
                  [1, '#1890ff']
                ]
              }
            },
            pointer: {
              icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
              length: '12%',
              width: 20,
              offsetCenter: [0, '-60%'],
              itemStyle: {
                color: 'auto'
              }
            },
            axisTick: {
              length: 12,
              lineStyle: {
                color: 'auto',
                width: 2
              }
            },
            splitLine: {
              length: 20,
              lineStyle: {
                color: 'auto',
                width: 5
              }
            },
            axisLabel: {
              color: '#464646',
              fontSize: 12,
              distance: -60,
              formatter: function (value: number) {
                if (value === 87.3) {
                  return '当前效率';
                }
                return value + '';
              }
            },
            title: {
              offsetCenter: [0, '-10%'],
              fontSize: 16,
              color: '#333'
            },
            detail: {
              fontSize: 30,
              offsetCenter: [0, '-35%'],
              valueAnimation: true,
              formatter: function (value: number) {
                return Math.round(value) + '%';
              },
              color: 'auto'
            },
            data: [
              {
                value: data.timeEfficiency,
                name: 'AI整体效率'
              }
            ]
          }
        ]
      };

      chart.setOption(option);
      
      const handleResize = () => chart.resize();
      window.addEventListener('resize', handleResize);
      
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.dispose();
      };
    }
  }, [data]);

  const handleRefresh = async () => {
    setRefreshing(true);
    // 模拟数据刷新
    await new Promise(resolve => setTimeout(resolve, 1000));
    setRefreshing(false);
  };

  const aiMetrics = [
    {
      title: 'AI识别准确率',
      value: data.aiAccuracy,
      icon: <ExperimentOutlined />,
      color: '#1890ff',
      status: 'excellent'
    },
    {
      title: '元素检测率',
      value: data.elementDetection,
      icon: <RobotOutlined />,
      color: '#52c41a',
      status: 'excellent'
    },
    {
      title: '脚本生成成功率',
      value: data.scriptGeneration,
      icon: <ThunderboltOutlined />,
      color: '#fa8c16',
      status: 'good'
    },
    {
      title: '执行成功率',
      value: data.executionSuccess,
      icon: <TrophyOutlined />,
      color: '#722ed1',
      status: 'excellent'
    },
    {
      title: '缺陷预测准确率',
      value: data.defectPrediction,
      icon: <BugOutlined />,
      color: '#13c2c2',
      status: 'good'
    },
    {
      title: '时间效率提升',
      value: data.timeEfficiency,
      icon: <ClockCircleOutlined />,
      color: '#eb2f96',
      status: 'good'
    }
  ];

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'excellent': return '#52c41a';
      case 'good': return '#fa8c16';
      case 'warning': return '#faad14';
      case 'danger': return '#ff4d4f';
      default: return '#d9d9d9';
    }
  };

  return (
    <div className="ai-analytics-dashboard">
      {/* 标题和刷新按钮 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <ExperimentOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            AI智能分析仪表板
          </Title>
        </Col>
        <Col>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={handleRefresh}
            loading={refreshing}
          >
            刷新数据
          </Button>
        </Col>
      </Row>

      {/* AI指标卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {aiMetrics.map((metric, index) => (
          <Col span={4} key={index}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="ai-metric-card" hoverable>
                <div className="metric-content">
                  <div className="metric-icon" style={{ color: metric.color }}>
                    {metric.icon}
                  </div>
                  <div className="metric-info">
                    <Text type="secondary" style={{ fontSize: '12px' }}>
                      {metric.title}
                    </Text>
                    <div style={{ display: 'flex', alignItems: 'center', marginTop: 4 }}>
                      <Text strong style={{ fontSize: '18px', color: metric.color }}>
                        {metric.value}%
                      </Text>
                      <Tag 
                        color={getStatusColor(metric.status)} 
                        style={{ marginLeft: 8, fontSize: '10px' }}
                      >
                        {metric.status === 'excellent' ? '优秀' : 
                         metric.status === 'good' ? '良好' : 
                         metric.status === 'warning' ? '警告' : '危险'}
                      </Tag>
                    </div>
                    <Progress 
                      percent={metric.value} 
                      showInfo={false} 
                      strokeColor={metric.color}
                      size="small"
                      style={{ marginTop: 8 }}
                    />
                  </div>
                </div>
              </Card>
            </motion.div>
          </Col>
        ))}
      </Row>

      {/* 图表区域 */}
      <Row gutter={[24, 24]}>
        <Col span={8}>
          <Card className="chart-card">
            <div ref={radarChartRef} style={{ width: '100%', height: '350px' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="chart-card">
            <div ref={heatmapRef} style={{ width: '100%', height: '350px' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="chart-card">
            <div ref={gaugeChartRef} style={{ width: '100%', height: '350px' }} />
          </Card>
        </Col>
      </Row>

      {/* AI洞察 */}
      <Row style={{ marginTop: 24 }}>
        <Col span={24}>
          <Card title="AI智能洞察" className="insight-card">
            <Row gutter={[16, 16]}>
              <Col span={8}>
                <div className="insight-item">
                  <div className="insight-icon">🎯</div>
                  <div className="insight-content">
                    <Text strong>元素识别优化建议</Text>
                    <br />
                    <Text type="secondary">
                      检测到复杂UI界面的识别准确率可提升3.2%，建议增加训练样本
                    </Text>
                  </div>
                </div>
              </Col>
              <Col span={8}>
                <div className="insight-item">
                  <div className="insight-icon">⚡</div>
                  <div className="insight-content">
                    <Text strong>执行效率分析</Text>
                    <br />
                    <Text type="secondary">
                      周三14:00-16:00为测试执行高峰期，建议优化资源分配
                    </Text>
                  </div>
                </div>
              </Col>
              <Col span={8}>
                <div className="insight-item">
                  <div className="insight-icon">🔍</div>
                  <div className="insight-content">
                    <Text strong>缺陷预测改进</Text>
                    <br />
                    <Text type="secondary">
                      移动端测试的缺陷预测准确率较低，建议加强模型训练
                    </Text>
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default AIAnalyticsDashboard;
