import _extends from "@babel/runtime/helpers/esm/extends";
import classNames from 'classnames';
import * as React from 'react';
import StopLoadingIcon from "../StopLoading";
import ActionButton, { ActionButtonContext } from "./ActionButton";
function LoadingButton(props, ref) {
  const {
    prefixCls
  } = React.useContext(ActionButtonContext);
  const {
    className
  } = props;
  return /*#__PURE__*/React.createElement(ActionButton, _extends({
    icon: null,
    color: "primary",
    variant: "text",
    shape: "circle"
  }, props, {
    className: classNames(className, `${prefixCls}-loading-button`),
    action: "onCancel",
    ref: ref
  }), /*#__PURE__*/React.createElement(StopLoadingIcon, {
    className: `${prefixCls}-loading-icon`
  }));
}
export default /*#__PURE__*/React.forwardRef(LoadingButton);