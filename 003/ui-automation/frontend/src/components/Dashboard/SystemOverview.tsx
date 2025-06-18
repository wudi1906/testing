import React, { useEffect, useRef } from 'react';
import { Card, Row, Col, Statistic, Typography, Progress } from 'antd';
import { motion } from 'framer-motion';
import * as echarts from 'echarts';
import 'echarts-gl';
import {
  RocketOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  BugOutlined,
  TrophyOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;

interface SystemOverviewProps {
  data?: {
    totalTests: number;
    successRate: number;
    activeTests: number;
    savedTime: number;
    defectsFound: number;
    efficiency: number;
  };
}

const SystemOverview: React.FC<SystemOverviewProps> = ({ 
  data = {
    totalTests: 1247,
    successRate: 96.8,
    activeTests: 8,
    savedTime: 156.7,
    defectsFound: 23,
    efficiency: 89.2
  }
}) => {
  const chart3DRef = useRef<HTMLDivElement>(null);
  const performanceChartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // 3D柱状图
    if (chart3DRef.current) {
      const chart = echarts.init(chart3DRef.current);
      
      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis3D',
          formatter: (params: any) => {
            return `${params.seriesName}<br/>${params.name}: ${params.value[2]}`;
          }
        },
        xAxis3D: {
          type: 'category',
          data: ['Web测试', 'Android测试', '接口测试', '性能测试'],
          axisLabel: {
            color: '#666',
            fontSize: 12
          }
        },
        yAxis3D: {
          type: 'category',
          data: ['今日', '本周', '本月'],
          axisLabel: {
            color: '#666',
            fontSize: 12
          }
        },
        zAxis3D: {
          type: 'value',
          min: 0,
          max: 100,
          axisLabel: {
            color: '#666',
            fontSize: 12
          }
        },
        grid3D: {
          boxWidth: 200,
          boxDepth: 80,
          boxHeight: 100,
          alpha: 15,
          beta: 30,
          viewControl: {
            autoRotate: true,
            autoRotateSpeed: 2
          },
          light: {
            main: {
              intensity: 1.2,
              shadow: true
            },
            ambient: {
              intensity: 0.3
            }
          }
        },
        series: [{
          name: '测试执行量',
          type: 'bar3D',
          data: [
            [0, 0, 45], [0, 1, 78], [0, 2, 234],
            [1, 0, 23], [1, 1, 56], [1, 2, 167],
            [2, 0, 67], [2, 1, 89], [2, 2, 298],
            [3, 0, 12], [3, 1, 34], [3, 2, 89]
          ],
          itemStyle: {
            color: (params: any) => {
              const colors = ['#1890ff', '#52c41a', '#fa8c16', '#722ed1'];
              return colors[params.data[0]];
            },
            opacity: 0.8
          },
          emphasis: {
            itemStyle: {
              color: '#ff4d4f'
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
    // 性能趋势图
    if (performanceChartRef.current) {
      const chart = echarts.init(performanceChartRef.current);
      
      const option = {
        backgroundColor: 'transparent',
        tooltip: {
          trigger: 'axis',
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          borderColor: '#1890ff',
          textStyle: {
            color: '#fff'
          }
        },
        legend: {
          data: ['成功率', '执行效率', '缺陷检出率'],
          textStyle: {
            color: '#666'
          }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '3%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', '24:00'],
          axisLine: {
            lineStyle: {
              color: '#e8e8e8'
            }
          },
          axisLabel: {
            color: '#666'
          }
        },
        yAxis: {
          type: 'value',
          axisLine: {
            lineStyle: {
              color: '#e8e8e8'
            }
          },
          axisLabel: {
            color: '#666'
          },
          splitLine: {
            lineStyle: {
              color: '#f0f0f0'
            }
          }
        },
        series: [
          {
            name: '成功率',
            type: 'line',
            smooth: true,
            data: [95, 96, 97, 98, 96, 97, 98],
            lineStyle: {
              color: '#52c41a',
              width: 3
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
            name: '执行效率',
            type: 'line',
            smooth: true,
            data: [87, 89, 91, 88, 92, 90, 89],
            lineStyle: {
              color: '#1890ff',
              width: 3
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
          },
          {
            name: '缺陷检出率',
            type: 'line',
            smooth: true,
            data: [78, 82, 85, 83, 87, 84, 86],
            lineStyle: {
              color: '#fa8c16',
              width: 3
            },
            areaStyle: {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [{
                  offset: 0, color: 'rgba(250, 140, 22, 0.3)'
                }, {
                  offset: 1, color: 'rgba(250, 140, 22, 0.1)'
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
  }, []);

  const statsData = [
    {
      title: '总测试数',
      value: data.totalTests,
      suffix: '次',
      icon: <RocketOutlined />,
      color: '#1890ff',
      trend: '+12.5%'
    },
    {
      title: '成功率',
      value: data.successRate,
      suffix: '%',
      icon: <CheckCircleOutlined />,
      color: '#52c41a',
      trend: '+2.3%'
    },
    {
      title: '活跃测试',
      value: data.activeTests,
      suffix: '个',
      icon: <ThunderboltOutlined />,
      color: '#fa8c16',
      trend: '+5'
    },
    {
      title: '节省时间',
      value: data.savedTime,
      suffix: '小时',
      icon: <ClockCircleOutlined />,
      color: '#722ed1',
      trend: '+18.7h'
    },
    {
      title: '发现缺陷',
      value: data.defectsFound,
      suffix: '个',
      icon: <BugOutlined />,
      color: '#ff4d4f',
      trend: '+3'
    },
    {
      title: '系统效率',
      value: data.efficiency,
      suffix: '%',
      icon: <TrophyOutlined />,
      color: '#13c2c2',
      trend: '+4.2%'
    }
  ];

  return (
    <div className="system-overview">
      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        {statsData.map((stat, index) => (
          <Col span={4} key={index}>
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="stat-card-3d" hoverable>
                <div className="stat-content">
                  <div className="stat-icon" style={{ color: stat.color }}>
                    {stat.icon}
                  </div>
                  <div className="stat-info">
                    <Statistic
                      title={stat.title}
                      value={stat.value}
                      suffix={stat.suffix}
                      valueStyle={{ 
                        color: stat.color, 
                        fontSize: '20px', 
                        fontWeight: 'bold' 
                      }}
                    />
                    <Text type="success" style={{ fontSize: '12px' }}>
                      {stat.trend}
                    </Text>
                  </div>
                </div>
              </Card>
            </motion.div>
          </Col>
        ))}
      </Row>

      {/* 图表区域 */}
      <Row gutter={[24, 24]}>
        <Col span={12}>
          <Card title="3D测试执行分析" className="chart-card">
            <div ref={chart3DRef} style={{ width: '100%', height: '400px' }} />
          </Card>
        </Col>
        <Col span={12}>
          <Card title="系统性能趋势" className="chart-card">
            <div ref={performanceChartRef} style={{ width: '100%', height: '400px' }} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SystemOverview;
