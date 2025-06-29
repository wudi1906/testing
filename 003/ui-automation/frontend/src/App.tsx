import React, { Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { App as AntdApp } from 'antd';
import { Toaster } from 'react-hot-toast';

// 页面组件
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard/Dashboard';
import TestCreation from './pages/Web/TestCreation/TestCreation';
import TestExecution from './pages/Web/TestExecution/TestExecution';
import UnifiedTestExecution from './pages/Web/TestExecution/UnifiedTestExecution';
import TestResults from './pages/Web/TestResults/TestResults';
import TestReports from './pages/Web/TestReports/TestReports';
import PageManagement from './pages/Web/PageManagement/PageManagement';
import WebModule from './pages/Web';
import Settings from './pages/Settings/Settings';
import PlaceholderPage from './components/Common/PlaceholderPage';
import LoadingSpinner from './components/Common/LoadingSpinner';

// 样式
import './App.css';
import './styles/global.css';



const App: React.FC = () => {
  return (
    <AntdApp>
      <div className="app">
        <Suspense fallback={<LoadingSpinner />}>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Dashboard />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="test/create" element={<TestCreation />} />
              <Route path="test/execution" element={<UnifiedTestExecution />} />
              <Route path="test/execution/:sessionId" element={<UnifiedTestExecution />} />
              <Route path="test/execution-legacy" element={<TestExecution />} />
              <Route path="test/execution-legacy/:sessionId" element={<TestExecution />} />
              <Route path="test/results" element={<TestResults />} />
              <Route path="test/results/:sessionId" element={<TestResults />} />
              <Route path="test/reports" element={<TestReports />} />

              {/* Web自动化路由 */}
              <Route path="web/pages" element={<PageManagement />} />
              <Route path="web/*" element={<WebModule />} />

              {/* Android自动化路由 */}
              <Route path="android/create" element={<TestCreation />} />
              <Route path="android/execution" element={<TestExecution />} />
              <Route path="android/results" element={<TestResults />} />
              <Route path="android/reports" element={<TestReports />} />

              {/* 管理模块路由 */}
              <Route path="management/projects" element={
                <PlaceholderPage
                  title="项目管理"
                  description="项目管理功能正在开发中，将支持项目创建、配置和团队管理等功能。"
                />
              } />
              <Route path="management/users" element={
                <PlaceholderPage
                  title="用户管理"
                  description="用户管理功能正在开发中，将支持用户权限、角色分配和团队协作等功能。"
                />
              } />

              {/* 需求模块路由 */}
              <Route path="requirements/management" element={
                <PlaceholderPage
                  title="需求管理"
                  description="需求管理功能正在开发中，将支持需求收集、分析和跟踪等功能。"
                />
              } />
              <Route path="requirements/list" element={
                <PlaceholderPage
                  title="需求列表"
                  description="需求列表功能正在开发中，将提供需求的统一查看和管理界面。"
                />
              } />
              <Route path="requirements/ai-analysis" element={
                <PlaceholderPage
                  title="AI需求分析"
                  description="AI需求分析功能正在开发中，将使用AI技术自动分析和优化需求。"
                />
              } />

              {/* 接口自动化路由 */}
              <Route path="api/create" element={
                <PlaceholderPage
                  title="接口自动化 - 创建测试"
                  description="接口自动化测试创建功能正在开发中，将支持API测试用例的设计和配置。"
                />
              } />
              <Route path="api/execution" element={
                <PlaceholderPage
                  title="接口自动化 - 执行测试"
                  description="接口自动化测试执行功能正在开发中，将支持API测试的批量执行和监控。"
                />
              } />
              <Route path="api/results" element={
                <PlaceholderPage
                  title="接口自动化 - 测试结果"
                  description="接口自动化测试结果功能正在开发中，将提供详细的API测试结果分析。"
                />
              } />
              <Route path="api/reports" element={
                <PlaceholderPage
                  title="接口自动化 - 测试报告"
                  description="接口自动化测试报告功能正在开发中，将生成专业的API测试报告。"
                />
              } />

              {/* 测试用例模块路由 */}
              <Route path="testcases/generation" element={
                <PlaceholderPage
                  title="用例生成"
                  description="AI驱动的测试用例生成功能正在开发中，将自动生成高质量的测试用例。"
                />
              } />
              <Route path="testcases/list" element={
                <PlaceholderPage
                  title="用例列表"
                  description="测试用例列表管理功能正在开发中，将提供用例的统一管理界面。"
                />
              } />

              {/* 性能测试模块路由 */}
              <Route path="performance/scenario" element={
                <PlaceholderPage
                  title="场景设计"
                  description="性能测试场景设计功能正在开发中，将支持复杂性能测试场景的可视化设计。"
                />
              } />
              <Route path="performance/analysis" element={
                <PlaceholderPage
                  title="性能分析"
                  description="性能分析功能正在开发中，将提供详细的性能指标分析和优化建议。"
                />
              } />

              {/* 缺陷分析模块路由 */}
              <Route path="defects/collection" element={
                <PlaceholderPage
                  title="数据采集"
                  description="缺陷数据采集功能正在开发中，将自动收集和分析系统缺陷数据。"
                />
              } />
              <Route path="defects/detection" element={
                <PlaceholderPage
                  title="缺陷检测"
                  description="智能缺陷检测功能正在开发中，将使用AI技术自动识别潜在缺陷。"
                />
              } />

              <Route path="settings" element={<Settings />} />
            </Route>
          </Routes>
        </Suspense>

        {/* 全局通知 */}
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: '#363636',
              color: '#fff',
            },
            success: {
              duration: 3000,
              iconTheme: {
                primary: '#52c41a',
                secondary: '#fff',
              },
            },
            error: {
              duration: 5000,
              iconTheme: {
                primary: '#ff4d4f',
                secondary: '#fff',
              },
            },
          }}
        />
      </div>
    </AntdApp>
  );
};

export default App;
