import React from 'react';
import { Result, Button } from 'antd';
import { RocketOutlined } from '@ant-design/icons';
import { motion } from 'framer-motion';

interface PlaceholderPageProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
}

const PlaceholderPage: React.FC<PlaceholderPageProps> = ({
  title,
  description = "此功能正在开发中，敬请期待！",
  icon = <RocketOutlined />
}) => {
  return (
    <div style={{ 
      height: '100%', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: '#f5f5f5'
    }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <Result
          icon={
            <motion.div
              animate={{ 
                scale: [1, 1.1, 1],
                rotate: [0, 5, -5, 0]
              }}
              transition={{ 
                duration: 2,
                repeat: Infinity,
                repeatType: "reverse"
              }}
              style={{ fontSize: '72px', color: '#1890ff' }}
            >
              {icon}
            </motion.div>
          }
          title={
            <motion.h2
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.3 }}
              style={{ color: '#262626', fontSize: '24px' }}
            >
              {title}
            </motion.h2>
          }
          subTitle={
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
              style={{ color: '#8c8c8c', fontSize: '16px' }}
            >
              {description}
            </motion.p>
          }
          extra={
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7 }}
            >
              <Button 
                type="primary" 
                size="large"
                onClick={() => window.history.back()}
              >
                返回上一页
              </Button>
            </motion.div>
          }
        />
      </motion.div>
    </div>
  );
};

export default PlaceholderPage;
