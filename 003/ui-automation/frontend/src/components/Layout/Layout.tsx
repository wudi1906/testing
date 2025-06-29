import React, { useState, useEffect, useRef } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout as AntdLayout,
  Menu,
  Button,
  Avatar,
  Dropdown,
  Space,
  Badge,
  Tooltip,
  Typography,
  Divider
} from 'antd';
import {
  DashboardOutlined,
  ExperimentOutlined,
  PlayCircleOutlined,
  BarChartOutlined,
  FileTextOutlined,
  TableOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  RobotOutlined,
  ThunderboltOutlined,
  GlobalOutlined,
  MobileOutlined,
  TeamOutlined,
  ProjectOutlined,
  UnorderedListOutlined,
  PieChartOutlined,
  EditOutlined,
  BulbOutlined,
  ApiOutlined,
  DashboardFilled,
  BugOutlined,
  LineChartOutlined,
  DatabaseOutlined,
  SearchOutlined
} from '@ant-design/icons';
import { motion } from 'framer-motion';

import './Layout.css';

const { Header, Sider, Content } = AntdLayout;
const { Text } = Typography;

interface MenuItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path?: string;
  children?: MenuItem[];
  type?: 'group' | 'item';
}

const menuItems: MenuItem[] = [
  {
    key: 'dashboard',
    icon: <DashboardOutlined />,
    label: '仪表盘',
    path: '/dashboard',
    type: 'item'
  },
  {
    key: 'management',
    label: '管理',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'project-management',
        icon: <ProjectOutlined />,
        label: '项目管理',
        path: '/management/projects',
        type: 'item'
      },
      {
        key: 'user-management',
        icon: <TeamOutlined />,
        label: '用户管理',
        path: '/management/users',
        type: 'item'
      }
    ]
  },
  {
    key: 'requirements',
    label: '需求',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'requirement-management',
        icon: <EditOutlined />,
        label: '需求管理',
        path: '/requirements/management',
        type: 'item'
      },
      {
        key: 'requirement-list',
        icon: <UnorderedListOutlined />,
        label: '需求列表',
        path: '/requirements/list',
        type: 'item'
      },
      {
        key: 'ai-requirement-analysis',
        icon: <BulbOutlined />,
        label: 'AI需求分析',
        path: '/requirements/ai-analysis',
        type: 'item'
      }
    ]
  },
  {
    key: 'web-automation',
    label: 'Web',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'web-page-management',
        icon: <TableOutlined />,
        label: '页面管理',
        path: '/web/pages',
        type: 'item'
      },
      {
        key: 'web-test-create',
        icon: <ExperimentOutlined />,
        label: '创建测试',
        path: '/web/create',
        type: 'item'
      },
      {
        key: 'web-test-execution',
        icon: <PlayCircleOutlined />,
        label: '执行测试',
        path: '/web/execution',
        type: 'item'
      },
      {
        key: 'web-test-results',
        icon: <BarChartOutlined />,
        label: '测试结果',
        path: '/web/results',
        type: 'item'
      },
      {
        key: 'web-test-reports',
        icon: <FileTextOutlined />,
        label: '测试报告',
        path: '/web/reports',
        type: 'item'
      }
    ]
  },
  {
    key: 'android-automation',
    label: 'Android',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'android-test-create',
        icon: <ExperimentOutlined />,
        label: '创建测试',
        path: '/android/create',
        type: 'item'
      },
      {
        key: 'android-test-execution',
        icon: <PlayCircleOutlined />,
        label: '执行测试',
        path: '/android/execution',
        type: 'item'
      },
      {
        key: 'android-test-results',
        icon: <BarChartOutlined />,
        label: '测试结果',
        path: '/android/results',
        type: 'item'
      },
      {
        key: 'android-test-reports',
        icon: <FileTextOutlined />,
        label: '测试报告',
        path: '/android/reports',
        type: 'item'
      }
    ]
  },
  {
    key: 'api-automation',
    label: '接口测试',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'api-test-create',
        icon: <ExperimentOutlined />,
        label: '创建测试',
        path: '/api/create',
        type: 'item'
      },
      {
        key: 'api-test-execution',
        icon: <PlayCircleOutlined />,
        label: '执行测试',
        path: '/api/execution',
        type: 'item'
      },
      {
        key: 'api-test-results',
        icon: <BarChartOutlined />,
        label: '测试结果',
        path: '/api/results',
        type: 'item'
      },
      {
        key: 'api-test-reports',
        icon: <FileTextOutlined />,
        label: '测试报告',
        path: '/api/reports',
        type: 'item'
      }
    ]
  },
  {
    key: 'test-cases',
    label: '测试用例',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'case-generation',
        icon: <BulbOutlined />,
        label: '用例生成',
        path: '/testcases/generation',
        type: 'item'
      },
      {
        key: 'case-list',
        icon: <UnorderedListOutlined />,
        label: '用例列表',
        path: '/testcases/list',
        type: 'item'
      }
    ]
  },
  {
    key: 'performance-testing',
    label: '性能测试',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'scenario-design',
        icon: <DashboardFilled />,
        label: '场景设计',
        path: '/performance/scenario',
        type: 'item'
      },
      {
        key: 'performance-analysis',
        icon: <LineChartOutlined />,
        label: '性能分析',
        path: '/performance/analysis',
        type: 'item'
      }
    ]
  },
  {
    key: 'defect-analysis',
    label: '缺陷分析',
    type: 'group',
    icon: null,
    children: [
      {
        key: 'data-collection',
        icon: <DatabaseOutlined />,
        label: '数据采集',
        path: '/defects/collection',
        type: 'item'
      },
      {
        key: 'defect-detection',
        icon: <SearchOutlined />,
        label: '缺陷检测',
        path: '/defects/detection',
        type: 'item'
      }
    ]
  },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: '系统设置',
    path: '/settings',
    type: 'item'
  }
];

const Layout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [selectedKey, setSelectedKey] = useState('dashboard');
  const [openKeys, setOpenKeys] = useState<string[]>(['web-automation']); // 默认只展开Web自动化分组
  const [showScrollIndicator, setShowScrollIndicator] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  // 根据当前路径设置选中的菜单项
  useEffect(() => {
    const currentPath = location.pathname;
    const findMenuItem = (items: MenuItem[]): MenuItem | null => {
      for (const item of items) {
        if (item.path && (currentPath === item.path || currentPath.startsWith(item.path))) {
          return item;
        }
        if (item.children) {
          const found = findMenuItem(item.children);
          if (found) return found;
        }
      }
      return null;
    };

    const currentItem = findMenuItem(menuItems);
    if (currentItem) {
      setSelectedKey(currentItem.key);
    }
  }, [location.pathname]);

  const handleMenuClick = (key: string) => {
    const findMenuItem = (items: MenuItem[]): MenuItem | null => {
      for (const item of items) {
        if (item.key === key) return item;
        if (item.children) {
          const found = findMenuItem(item.children);
          if (found) return found;
        }
      }
      return null;
    };

    const item = findMenuItem(menuItems);
    if (item && item.path) {
      navigate(item.path);
    }
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'divider1',
      type: 'divider',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  const handleUserMenuClick = ({ key }: { key: string }) => {
    switch (key) {
      case 'logout':
        // 处理退出登录
        console.log('退出登录');
        break;
      case 'profile':
        // 处理个人资料
        console.log('个人资料');
        break;
    }
  };

  // 递归渲染菜单项
  const renderMenuItems = (items: MenuItem[]): any[] => {
    return items.map(item => {
      if (item.type === 'group' && item.children) {
        // 分组显示为可折叠的子菜单
        return {
          key: item.key,
          icon: getGroupIcon(item.key),
          label: (
            <motion.span
              whileHover={{ x: 2 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              {item.label}
            </motion.span>
          ),
          children: renderMenuItems(item.children)
        };
      } else {
        // 普通菜单项
        return {
          key: item.key,
          icon: item.icon,
          label: (
            <motion.span
              whileHover={{ x: 4 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              {item.label}
            </motion.span>
          )
        };
      }
    });
  };

  // 获取分组图标
  const getGroupIcon = (groupKey: string) => {
    const iconMap: { [key: string]: React.ReactNode } = {
      'management': <TeamOutlined />,
      'requirements': <EditOutlined />,
      'web-automation': <GlobalOutlined />,
      'android-automation': <MobileOutlined />,
      'api-automation': <ApiOutlined />,
      'test-cases': <TableOutlined />,
      'performance-testing': <LineChartOutlined />,
      'defect-analysis': <BugOutlined />
    };
    return iconMap[groupKey] || <RobotOutlined />;
  };

  // 全部展开/收起功能
  const handleToggleAll = () => {
    const allGroupKeys = menuItems
      .filter(item => item.type === 'group' && item.children)
      .map(item => item.key);

    if (openKeys.length === allGroupKeys.length) {
      // 如果全部展开，则全部收起
      setOpenKeys([]);
    } else {
      // 否则全部展开
      setOpenKeys(allGroupKeys);
    }
  };

  // 检查菜单是否需要滚动
  useEffect(() => {
    const checkScrollable = () => {
      if (menuRef.current) {
        const { scrollHeight, clientHeight } = menuRef.current;
        setShowScrollIndicator(scrollHeight > clientHeight);
      }
    };

    checkScrollable();

    // 监听窗口大小变化和菜单展开状态变化
    window.addEventListener('resize', checkScrollable);

    // 延迟检查，确保菜单渲染完成
    const timer = setTimeout(checkScrollable, 100);

    return () => {
      window.removeEventListener('resize', checkScrollable);
      clearTimeout(timer);
    };
  }, [openKeys, collapsed]); // 依赖展开状态和折叠状态

  return (
    <AntdLayout className="layout-container">
      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        width={240}
        className="layout-sider"
        theme="dark"
      >
        {/* Logo区域 */}
        <motion.div
          className="layout-logo"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <RobotOutlined className="logo-icon" />
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            >
              <Text className="logo-text">自动化测试平台</Text>
              <Text className="logo-subtitle">AI驱动的智能测试平台</Text>
            </motion.div>
          )}
        </motion.div>

        <Divider style={{ margin: '16px 0', borderColor: '#303030' }} />

        {/* 菜单控制 */}
        {!collapsed && (
          <div style={{
            padding: '0 24px 12px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <Text style={{
              color: 'rgba(255, 255, 255, 0.6)',
              fontSize: '12px',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px'
            }}>
              功能模块
            </Text>
            <Button
              type="text"
              size="small"
              icon={openKeys.length > 0 ? <MenuFoldOutlined /> : <MenuUnfoldOutlined />}
              onClick={handleToggleAll}
              style={{
                color: 'rgba(255, 255, 255, 0.6)',
                border: 'none',
                padding: '2px 6px',
                height: '24px',
                fontSize: '12px'
              }}
              title={openKeys.length > 0 ? '收起全部' : '展开全部'}
            />
          </div>
        )}

        {/* 菜单容器 */}
        <div className="menu-container">
          <Menu
            ref={menuRef}
            theme="dark"
            mode="inline"
            selectedKeys={[selectedKey]}
            openKeys={openKeys}
            className="layout-menu"
            onClick={({ key }) => handleMenuClick(key)}
            onOpenChange={(keys) => setOpenKeys(keys)}
            items={renderMenuItems(menuItems)}
          />

          {/* 滚动指示器 */}
          {showScrollIndicator && !collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{
                position: 'absolute',
                bottom: '80px',
                right: '8px',
                background: 'rgba(24, 144, 255, 0.8)',
                color: '#fff',
                padding: '4px 8px',
                borderRadius: '4px',
                fontSize: '12px',
                pointerEvents: 'none',
                zIndex: 10
              }}
            >
              可滚动
            </motion.div>
          )}
        </div>

        {/* 底部状态指示器 */}
        {!collapsed && (
          <motion.div
            className="sider-footer"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
          >
            <Space direction="vertical" size="small">
              <div className="status-item">
                <Badge status="success" />
                <Text type="secondary">AI模型在线</Text>
              </div>
              <div className="status-item">
                <Badge status="processing" />
                <Text type="secondary">智能体就绪</Text>
              </div>
            </Space>
          </motion.div>
        )}
      </Sider>

      {/* 主内容区域 */}
      <AntdLayout className="layout-main">
        {/* 顶部导航栏 */}
        <Header className="layout-header">
          <div className="header-left">
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
              className="collapse-btn"
            />

            <motion.div
              className="header-title"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.5 }}
            >
              <ThunderboltOutlined className="title-icon" />
              <Text className="title-text">
                {(() => {
                  const findMenuItem = (items: MenuItem[]): MenuItem | null => {
                    for (const item of items) {
                      if (item.key === selectedKey) return item;
                      if (item.children) {
                        const found = findMenuItem(item.children);
                        if (found) return found;
                      }
                    }
                    return null;
                  };
                  const currentItem = findMenuItem(menuItems);
                  return currentItem?.label || '仪表盘';
                })()}
              </Text>
            </motion.div>
          </div>

          <div className="header-right">
            <Space size="middle">
              {/* 通知按钮 */}
              <Tooltip title="通知">
                <Badge count={3} size="small">
                  <Button
                    type="text"
                    icon={<BellOutlined />}
                    className="header-btn"
                  />
                </Badge>
              </Tooltip>

              {/* 用户菜单 */}
              <Dropdown
                menu={{
                  items: userMenuItems,
                  onClick: handleUserMenuClick
                }}
                placement="bottomRight"
                arrow
              >
                <Space className="user-info">
                  <Avatar
                    size="small"
                    icon={<UserOutlined />}
                    className="user-avatar"
                  />
                  <Text className="user-name">测试用户</Text>
                </Space>
              </Dropdown>
            </Space>
          </div>
        </Header>

        {/* 内容区域 */}
        <Content className="layout-content">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="content-wrapper"
          >
            <Outlet />
          </motion.div>
        </Content>
      </AntdLayout>
    </AntdLayout>
  );
};

export default Layout;
