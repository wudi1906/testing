import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import WebTestCreation from './components/WebTestCreation/WebTestCreation';
import WebTestCreationOptimized from './components/WebTestCreation/WebTestCreationOptimized';
import WebTestExecutionOptimized from './components/WebTestExecution/WebTestExecutionOptimized';
// 导入Web模块下的页面组件
import TestCreation from './TestCreation/TestCreation';
import TestExecution from './TestExecution/TestExecution';
import UnifiedTestExecution from './TestExecution/UnifiedTestExecution';
import TestResults from './TestResults/TestResults';
import TestReports from './TestReports/TestReports';

const WebModule: React.FC = () => {
  return (
    <Routes>
      {/* Web测试创建页面 - 原版本 */}
      <Route path="create" element={<WebTestCreation />} />

      {/* Web测试创建页面 - 优化版本 */}
      <Route path="create-optimized" element={<WebTestCreationOptimized />} />

      {/* Web测试执行页面 - 原版本 */}
      <Route path="execution-legacy" element={<TestExecution />} />
      <Route path="execution-legacy/:sessionId" element={<TestExecution />} />

      {/* Web测试执行页面 - 统一版本（新的默认版本） */}
      <Route path="execution" element={<UnifiedTestExecution />} />
      <Route path="execution/:sessionId" element={<UnifiedTestExecution />} />

      {/* Web测试执行页面 - 优化版本 */}
      <Route path="execution-optimized" element={<WebTestExecutionOptimized />} />

      {/* Web测试结果页面 */}
      <Route path="results" element={<TestResults />} />
      <Route path="results/:sessionId" element={<TestResults />} />

      {/* Web测试报告页面 */}
      <Route path="reports" element={<TestReports />} />

      {/* 默认重定向到优化版创建页面 */}
      <Route path="" element={<Navigate to="create-optimized" replace />} />
    </Routes>
  );
};

export default WebModule;
