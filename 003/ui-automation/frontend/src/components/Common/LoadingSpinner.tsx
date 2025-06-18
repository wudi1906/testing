import React from 'react';
import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';
import './LoadingSpinner.css';

const { Text } = Typography;

interface LoadingSpinnerProps {
  size?: 'small' | 'default' | 'large';
  tip?: string;
  spinning?: boolean;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'default',
  tip = '加载中...',
  spinning = true,
  children,
  className = '',
  style = {}
}) => {
  const antIcon = <LoadingOutlined style={{ fontSize: getSizeValue(size) }} spin />;

  function getSizeValue(size: string) {
    switch (size) {
      case 'small': return 16;
      case 'large': return 32;
      default: return 24;
    }
  }

  if (children) {
    return (
      <Spin
        spinning={spinning}
        tip={tip}
        indicator={antIcon}
        className={`loading-spinner-wrapper ${className}`}
        style={style}
      >
        {children}
      </Spin>
    );
  }

  return (
    <div className={`loading-spinner-container ${className}`} style={style}>
      <Spin
        spinning={spinning}
        indicator={antIcon}
        size={size}
      />
      {tip && (
        <Text type="secondary" className="loading-tip">
          {tip}
        </Text>
      )}
    </div>
  );
};

export default LoadingSpinner;
