import { type ImageProps } from 'antd';
import React from 'react';
import type { Attachment } from '..';
export interface FileListCardProps {
    prefixCls?: string;
    item: Attachment;
    onRemove?: (item: Attachment) => void;
    className?: string;
    style?: React.CSSProperties;
    imageProps?: ImageProps;
}
declare const _default: React.ForwardRefExoticComponent<FileListCardProps & React.RefAttributes<HTMLDivElement>>;
export default _default;
