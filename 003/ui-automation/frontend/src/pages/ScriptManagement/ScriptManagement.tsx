import React from 'react';
import { motion } from 'framer-motion';
import { message } from 'antd';

import ScriptManager from '../../components/ScriptManager/ScriptManager';
import './ScriptManagement.css';

const ScriptManagement: React.FC = () => {
  const handleExecuteScript = (scriptId: string) => {
    message.info(`执行脚本: ${scriptId}`);
    // 这里可以添加执行脚本的逻辑
    // 例如：跳转到执行页面或直接执行
  };

  const handleBatchExecute = (scriptIds: string[]) => {
    message.info(`批量执行 ${scriptIds.length} 个脚本`);
    // 这里可以添加批量执行的逻辑
  };

  return (
    <div className="script-management-container">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <ScriptManager
          showUpload={true}
          onExecuteScript={handleExecuteScript}
          onBatchExecute={handleBatchExecute}
        />
      </motion.div>
    </div>
  );
};

export default ScriptManagement;
