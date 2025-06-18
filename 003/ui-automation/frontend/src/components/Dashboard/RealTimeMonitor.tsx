import React, { useEffect, useRef, useState } from 'react';
import { Card, Row, Col, Badge, Typography, Space, Button, Alert, Timeline, Tag } from 'antd';
import { motion } from 'framer-motion';
import * as echarts from 'echarts';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ThunderboltOutlined,
  MonitorOutlined,
  ReloadOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface RealTimeMonitorProps {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

interface TestExecution {
  id: string;
  name: string;
  status: 'running' | 'success' | 'failed' | 'pending';
  progress: number;
  startTime: string;
  duration?: number;
  type: 'web' | 'android' | 'api';
}

interface SystemMetric {
  name: string;
  value: number;
  unit: string;
  status: 'normal' | 'warning' | 'danger';
  trend: 'up' | 'down' | 'stable';
}

const RealTimeMonitor: React.FC<RealTimeMonitorProps> = ({
  autoRefresh = true,
  refreshInterval = 5000
}) => {
  const realTimeChartRef = useRef<HTMLDivElement>(null);
  const systemMetricsRef = useRef<HTMLDivElement>(null);
  const [isMonitoring, setIsMonitoring] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // 模拟实时数据
  const [executions, setExecutions] = useState<TestExecution[]>([
    {
      id: '1',
      name: '登录功能测试',
      status: 'running',
      progress: 65,
      startTime: '14:23:15',
      type: 'web'
    },
    {
      id: '2',
      name: 'Android购物车测试',
      status: 'running',
      progress: 32,
      startTime: '14:20:08',
      type: 'android'
    },
    {
      id: '3',
      name: '用户注册API测试',
      status: 'success',
      progress: 100,
      startTime: '14:18:45',
      duration: 45,
      type: 'api'
    },
    {
      id: '4',
      name: '支付流程测试',
      status: 'pending',
      progress: 0,
      startTime: '14:25:00',
      type: 'web'
    }
  ]);

  const [systemMetrics, setSystemMetrics] = useState<SystemMetric[]>([
    { name: 'CPU使用率', value: 45.2, unit: '%', status: 'normal', trend: 'stable' },
    { name: '内存使用率', value: 67.8, unit: '%', status: 'warning', trend: 'up' },
    { name: '网络延迟', value: 23, unit: 'ms', status: 'normal', trend: 'down' },
    { name: '并发执行数', value: 8, unit: '个', status: 'normal', trend: 'stable' },
    { name: '成功率', value: 96.5, unit: '%', status: 'normal', trend: 'up' },
    { name: '平均响应时间', value: 1.2, unit: 's', status: 'normal', trend: 'stable' }
  ]);

  // 实时数据更新
  useEffect(() => {
    if (!autoRefresh || !isMonitoring) return;

    const interval = setInterval(() => {
      // 更新执行进度
      setExecutions(prev => prev.map(exec => {
        if (exec.status === 'running') {
          const newProgress = Math.min(exec.progress + Math.random() * 10, 100);
          return {
            ...exec,
            progress: newProgress,
            status: newProgress >= 100 ? 'success' : 'running'
          };
        }
        return exec;
      }));

      // 更新系统指标
      setSystemMetrics(prev => prev.map(metric => ({
        ...metric,
        value: Math.max(0, metric.value + (Math.random() - 0.5) * 5),
        trend: Math.random() > 0.5 ? 'up' : Math.random() > 0.5 ? 'down' : 'stable'
      })));

      setLastUpdate(new Date());
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [autoRefresh, isMonitoring, refreshInterval]);

  useEffect(() => {
    // 实时执行趋势图
    if (realTimeChartRef.current) {
      const chart = echarts.init(realTimeChartRef.current);
      
      // 生成最近30分钟的数据
      const times = [];
      const successData = [];
      const failedData = [];
      const runningData = [];
      
      for (let i = 29; i >= 0; i--) {
        const time = new Date(Date.now() - i * 60000);
        times.push(time.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
        successData.push(Math.floor(Math.random() * 10) + 5);
        failedData.push(Math.floor(Math.random() * 3));
        runningData.push(Math.floor(Math.random() * 5) + 2);
      }

      const option = {
        backgroundColor: 'transparent',
        title: {
          text: '实时执行趋势',
          left: 'center',
          textStyle: {
            color: '#333',
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#1890ff',
          textStyle: {
            color: '#fff'
          }
        },
        legend: {
          data: ['成功', '失败', '执行中'],
          bottom: 10,
          textStyle: {
            color: '#666'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: times,
          axisLabel: {
            color: '#666',
            fontSize: 10
          },
          axisLine: {
            lineStyle: {
              color: '#e8e8e8'
            }
          }
        },
        yAxis: {
          type: 'value',
          axisLabel: {
            color: '#666'
          },
          axisLine: {
            lineStyle: {
              color: '#e8e8e8'
            }
          },
          splitLine: {
            lineStyle: {
              color: '#f0f0f0'
            }
          }
        },
        series: [
          {
            name: '成功',
            type: 'line',
            smooth: true,
            data: successData,
            lineStyle: {
              color: '#52c41a',
              width: 2
            },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(82, 196, 26, 0.3)'
                }, {
                  offset: 1, color: 'rgba(82, 196, 26, 0.1)'
                }]
              }
            }
          },
          {
            name: '失败',
            type: 'line',
            smooth: true,
            data: failedData,
            lineStyle: {
              color: '#ff4d4f',
              width: 2
            },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(255, 77, 79, 0.3)'
                }, {
                  offset: 1, color: 'rgba(255, 77, 79, 0.1)'
                }]
              }
            }
          },
          {
            name: '执行中',
            type: 'line',
            smooth: true,
            data: runningData,
            lineStyle: {
              color: '#1890ff',
              width: 2
            },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(24, 144, 255, 0.3)'
                }, {
                  offset: 1, color: 'rgba(24, 144, 255, 0.1)'
                }]
              }
            }
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
  }, [lastUpdate]);

  useEffect(() => {
    // 系统指标仪表盘
    if (systemMetricsRef.current) {
      const chart = echarts.init(systemMetricsRef.current);
      
      const option = {
        backgroundColor: 'transparent',
        title: {
          text: '系统资源监控',
          left: 'center',
          textStyle: {
            color: '#333',
            fontSize: 16,
            fontWeight: 'bold'
          }
        },
        tooltip: {
          formatter: '{a} <br/>{b} : {c}%'
        },
        series: [
          {
            name: 'CPU',
            type: 'gauge',
            center: ['20%', '55%'],
            radius: '60%',
            min: 0,
            max: 100,
            startAngle: 225,
            endAngle: -45,
            axisLine: {
              lineStyle: {
                width: 8,
                color: [
                  [0.7, '#52c41a'],
                  [0.9, '#fa8c16'],
                  [1, '#ff4d4f']
                ]
              }
            },
            pointer: {
              itemStyle: {
                color: 'auto'
              }
            },
            axisTick: {
              distance: -15,
              length: 8,
              lineStyle: {
                color: '#fff',
                width: 2
              }
            },
            splitLine: {
              distance: -20,
              length: 15,
              lineStyle: {
                color: '#fff',
                width: 4
              }
            },
            axisLabel: {
              color: 'auto',
              distance: 35,
              fontSize: 10
            },
            detail: {
              valueAnimation: true,
              formatter: '{value}%',
              color: 'auto',
              fontSize: 14,
              offsetCenter: [0, '70%']
            },
            title: {
              fontSize: 12,
              offsetCenter: [0, '90%']
            },
            data: [
              {
                value: systemMetrics[0]?.value || 0,
                name: 'CPU使用率'
              }
            ]
          },
          {
            name: '内存',
            type: 'gauge',
            center: ['50%', '55%'],
            radius: '60%',
            min: 0,
            max: 100,
            startAngle: 225,
            endAngle: -45,
            axisLine: {
              lineStyle: {
                width: 8,
                color: [
                  [0.7, '#52c41a'],
                  [0.9, '#fa8c16'],
                  [1, '#ff4d4f']
                ]
              }
            },
            pointer: {
              itemStyle: {
                color: 'auto'
              }
            },
            axisTick: {
              distance: -15,
              length: 8,
              lineStyle: {
                color: '#fff',
                width: 2
              }
            },
            splitLine: {
              distance: -20,
              length: 15,
              lineStyle: {
                color: '#fff',
                width: 4
              }
            },
            axisLabel: {
              color: 'auto',
              distance: 35,
              fontSize: 10
            },
            detail: {
              valueAnimation: true,
              formatter: '{value}%',
              color: 'auto',
              fontSize: 14,
              offsetCenter: [0, '70%']
            },
            title: {
              fontSize: 12,
              offsetCenter: [0, '90%']
            },
            data: [
              {
                value: systemMetrics[1]?.value || 0,
                name: '内存使用率'
              }
            ]
          },
          {
            name: '网络',
            type: 'gauge',
            center: ['80%', '55%'],
            radius: '60%',
            min: 0,
            max: 100,
            startAngle: 225,
            endAngle: -45,
            axisLine: {
              lineStyle: {
                width: 8,
                color: [
                  [0.7, '#52c41a'],
                  [0.9, '#fa8c16'],
                  [1, '#ff4d4f']
                ]
              }
            },
            pointer: {
              itemStyle: {
                color: 'auto'
              }
            },
            axisTick: {
              distance: -15,
              length: 8,
              lineStyle: {
                color: '#fff',
                width: 2
              }
            },
            splitLine: {
              distance: -20,
              length: 15,
              lineStyle: {
                color: '#fff',
                width: 4
              }
            },
            axisLabel: {
              color: 'auto',
              distance: 35,
              fontSize: 10
            },
            detail: {
              valueAnimation: true,
              formatter: '{value}ms',
              color: 'auto',
              fontSize: 14,
              offsetCenter: [0, '70%']
            },
            title: {
              fontSize: 12,
              offsetCenter: [0, '90%']
            },
            data: [
              {
                value: systemMetrics[2]?.value || 0,
                name: '网络延迟'
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
  }, [systemMetrics]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running': return <PlayCircleOutlined style={{ color: '#1890ff' }} />;
      case 'success': return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed': return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'pending': return <ClockCircleOutlined style={{ color: '#fa8c16' }} />;
      default: return <ClockCircleOutlined />;
    }
  };

  const getTypeTag = (type: string) => {
    const colors = {
      web: 'blue',
      android: 'green',
      api: 'orange'
    };
    const labels = {
      web: 'Web',
      android: 'Android',
      api: 'API'
    };
    return <Tag color={colors[type as keyof typeof colors]}>{labels[type as keyof typeof labels]}</Tag>;
  };

  return (
    <div className="real-time-monitor">
      {/* 监控状态头部 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0 }}>
            <MonitorOutlined style={{ marginRight: 8, color: '#1890ff' }} />
            实时监控中心
            <Badge 
              status={isMonitoring ? "processing" : "default"} 
              text={isMonitoring ? "监控中" : "已暂停"}
              style={{ marginLeft: 12 }}
            />
          </Title>
        </Col>
        <Col>
          <Space>
            <Text type="secondary">
              最后更新: {lastUpdate.toLocaleTimeString()}
            </Text>
            <Button
              icon={isMonitoring ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
              onClick={() => setIsMonitoring(!isMonitoring)}
            >
              {isMonitoring ? '暂停监控' : '开始监控'}
            </Button>
            <Button icon={<ReloadOutlined />}>
              手动刷新
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 系统状态警告 */}
      {systemMetrics.some(m => m.status === 'warning' || m.status === 'danger') && (
        <Alert
          message="系统资源警告"
          description="检测到系统资源使用率较高，请关注系统性能状态"
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 24 }}
        />
      )}

      {/* 图表区域 */}
      <Row gutter={[24, 24]} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card className="chart-card">
            <div ref={realTimeChartRef} style={{ width: '100%', height: '300px' }} />
          </Card>
        </Col>
        <Col span={8}>
          <Card className="chart-card">
            <div ref={systemMetricsRef} style={{ width: '100%', height: '300px' }} />
          </Card>
        </Col>
      </Row>

      {/* 执行状态和活动日志 */}
      <Row gutter={[24, 24]}>
        <Col span={12}>
          <Card title="当前执行状态" className="execution-status-card">
            <Space direction="vertical" style={{ width: '100%' }}>
              {executions.map(exec => (
                <motion.div
                  key={exec.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="execution-item"
                >
                  <Row justify="space-between" align="middle">
                    <Col span={16}>
                      <Space>
                        {getStatusIcon(exec.status)}
                        <Text strong>{exec.name}</Text>
                        {getTypeTag(exec.type)}
                      </Space>
                      <div style={{ marginTop: 4 }}>
                        <Text type="secondary" style={{ fontSize: '12px' }}>
                          开始时间: {exec.startTime}
                          {exec.duration && ` | 耗时: ${exec.duration}s`}
                        </Text>
                      </div>
                    </Col>
                    <Col span={8} style={{ textAlign: 'right' }}>
                      <div style={{ width: '100px' }}>
                        <div style={{ fontSize: '12px', marginBottom: 4 }}>
                          {exec.progress}%
                        </div>
                        <div style={{ 
                          height: '4px', 
                          background: '#f0f0f0', 
                          borderRadius: '2px',
                          overflow: 'hidden'
                        }}>
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${exec.progress}%` }}
                            transition={{ duration: 0.5 }}
                            style={{
                              height: '100%',
                              background: exec.status === 'success' ? '#52c41a' : 
                                         exec.status === 'failed' ? '#ff4d4f' : '#1890ff',
                              borderRadius: '2px'
                            }}
                          />
                        </div>
                      </div>
                    </Col>
                  </Row>
                </motion.div>
              ))}
            </Space>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="系统活动日志" className="activity-log-card">
            <Timeline
              items={[
                {
                  color: 'green',
                  children: (
                    <div>
                      <Text strong>用户注册API测试</Text> 执行完成
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        14:19:30 | 耗时: 45s | 成功率: 100%
                      </Text>
                    </div>
                  ),
                },
                {
                  color: 'blue',
                  children: (
                    <div>
                      <Text strong>Android购物车测试</Text> 正在执行
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        14:20:08 | 进度: 32% | 预计剩余: 2分钟
                      </Text>
                    </div>
                  ),
                },
                {
                  color: 'blue',
                  children: (
                    <div>
                      <Text strong>登录功能测试</Text> 正在执行
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        14:23:15 | 进度: 65% | 预计剩余: 1分钟
                      </Text>
                    </div>
                  ),
                },
                {
                  color: 'gray',
                  children: (
                    <div>
                      <Text strong>支付流程测试</Text> 等待执行
                      <br />
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        14:25:00 | 队列位置: 1
                      </Text>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default RealTimeMonitor;
