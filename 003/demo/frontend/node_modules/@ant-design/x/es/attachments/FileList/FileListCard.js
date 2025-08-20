import _extends from "@babel/runtime/helpers/esm/extends";
import { CloseCircleFilled, FileExcelFilled, FileImageFilled, FileMarkdownFilled, FilePdfFilled, FilePptFilled, FileTextFilled, FileWordFilled, FileZipFilled } from '@ant-design/icons';
import { Image } from 'antd';
import classnames from 'classnames';
import React from 'react';
import { useXProviderContext } from "../../x-provider";
import { AttachmentContext } from "../context";
import useStyle from "../style";
import { previewImage } from "../util";
import AudioIcon from "./AudioIcon";
import Progress from "./Progress";
import VideoIcon from "./VideoIcon";
const EMPTY = '\u00A0';
const DEFAULT_ICON_COLOR = '#8c8c8c';
const IMG_EXTS = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'];
const PRESET_FILE_ICONS = [{
  icon: /*#__PURE__*/React.createElement(FileExcelFilled, null),
  color: '#22b35e',
  ext: ['xlsx', 'xls']
}, {
  icon: /*#__PURE__*/React.createElement(FileImageFilled, null),
  color: DEFAULT_ICON_COLOR,
  ext: IMG_EXTS
}, {
  icon: /*#__PURE__*/React.createElement(FileMarkdownFilled, null),
  color: DEFAULT_ICON_COLOR,
  ext: ['md', 'mdx']
}, {
  icon: /*#__PURE__*/React.createElement(FilePdfFilled, null),
  color: '#ff4d4f',
  ext: ['pdf']
}, {
  icon: /*#__PURE__*/React.createElement(FilePptFilled, null),
  color: '#ff6e31',
  ext: ['ppt', 'pptx']
}, {
  icon: /*#__PURE__*/React.createElement(FileWordFilled, null),
  color: '#1677ff',
  ext: ['doc', 'docx']
}, {
  icon: /*#__PURE__*/React.createElement(FileZipFilled, null),
  color: '#fab714',
  ext: ['zip', 'rar', '7z', 'tar', 'gz']
}, {
  icon: /*#__PURE__*/React.createElement(VideoIcon, null),
  color: '#ff4d4f',
  ext: ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv']
}, {
  icon: /*#__PURE__*/React.createElement(AudioIcon, null),
  color: '#8c8c8c',
  ext: ['mp3', 'wav', 'flac', 'ape', 'aac', 'ogg']
}];
function matchExt(suffix, ext) {
  return ext.some(e => suffix.toLowerCase() === `.${e}`);
}
function getSize(size) {
  let retSize = size;
  const units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB'];
  let unitIndex = 0;
  while (retSize >= 1024 && unitIndex < units.length - 1) {
    retSize /= 1024;
    unitIndex++;
  }
  return `${retSize.toFixed(0)} ${units[unitIndex]}`;
}
function FileListCard(props, ref) {
  const {
    prefixCls: customizePrefixCls,
    item,
    onRemove,
    className,
    style,
    imageProps
  } = props;
  const context = React.useContext(AttachmentContext);
  const {
    disabled
  } = context || {};
  const {
    name,
    size,
    percent,
    status = 'done',
    description
  } = item;

  // ============================= Prefix =============================
  const {
    getPrefixCls
  } = useXProviderContext();
  const prefixCls = getPrefixCls('attachment', customizePrefixCls);
  const cardCls = `${prefixCls}-list-card`;

  // ============================= Style ==============================
  const [wrapCSSVar, hashId, cssVarCls] = useStyle(prefixCls);

  // ============================== Name ==============================
  const [namePrefix, nameSuffix] = React.useMemo(() => {
    const nameStr = name || '';
    const match = nameStr.match(/^(.*)\.[^.]+$/);
    return match ? [match[1], nameStr.slice(match[1].length)] : [nameStr, ''];
  }, [name]);
  const isImg = React.useMemo(() => matchExt(nameSuffix, IMG_EXTS), [nameSuffix]);

  // ============================== Desc ==============================
  const desc = React.useMemo(() => {
    if (description) {
      return description;
    }
    if (status === 'uploading') {
      return `${percent || 0}%`;
    }
    if (status === 'error') {
      return item.response || EMPTY;
    }
    return size ? getSize(size) : EMPTY;
  }, [status, percent]);

  // ============================== Icon ==============================
  const [icon, iconColor] = React.useMemo(() => {
    for (const {
      ext,
      icon,
      color
    } of PRESET_FILE_ICONS) {
      if (matchExt(nameSuffix, ext)) {
        return [icon, color];
      }
    }
    return [/*#__PURE__*/React.createElement(FileTextFilled, {
      key: "defaultIcon"
    }), DEFAULT_ICON_COLOR];
  }, [nameSuffix]);

  // ========================== ImagePreview ==========================
  const [previewImg, setPreviewImg] = React.useState();
  React.useEffect(() => {
    if (item.originFileObj) {
      let synced = true;
      previewImage(item.originFileObj).then(url => {
        if (synced) {
          setPreviewImg(url);
        }
      });
      return () => {
        synced = false;
      };
    }
    setPreviewImg(undefined);
  }, [item.originFileObj]);

  // ============================= Render =============================
  let content = null;
  const previewUrl = item.thumbUrl || item.url || previewImg;
  const isImgPreview = isImg && (item.originFileObj || previewUrl);
  if (isImgPreview) {
    // Preview Image style
    content = /*#__PURE__*/React.createElement(React.Fragment, null, previewUrl && /*#__PURE__*/React.createElement(Image, _extends({
      alt: "preview",
      src: previewUrl
    }, imageProps)), status !== 'done' && /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-img-mask`
    }, status === 'uploading' && percent !== undefined && /*#__PURE__*/React.createElement(Progress, {
      percent: percent,
      prefixCls: cardCls
    }), status === 'error' && /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-desc`
    }, /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-ellipsis-prefix`
    }, desc))));
  } else {
    // Preview Card style
    content = /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-icon`,
      style: {
        color: iconColor
      }
    }, icon), /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-content`
    }, /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-name`
    }, /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-ellipsis-prefix`
    }, namePrefix ?? EMPTY), /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-ellipsis-suffix`
    }, nameSuffix)), /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-desc`
    }, /*#__PURE__*/React.createElement("div", {
      className: `${cardCls}-ellipsis-prefix`
    }, desc))));
  }
  return wrapCSSVar( /*#__PURE__*/React.createElement("div", {
    className: classnames(cardCls, {
      [`${cardCls}-status-${status}`]: status,
      [`${cardCls}-type-preview`]: isImgPreview,
      [`${cardCls}-type-overview`]: !isImgPreview
    }, className, hashId, cssVarCls),
    style: style,
    ref: ref
  }, content, !disabled && onRemove && /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: `${cardCls}-remove`,
    onClick: () => {
      onRemove(item);
    }
  }, /*#__PURE__*/React.createElement(CloseCircleFilled, null))));
}
export default /*#__PURE__*/React.forwardRef(FileListCard);