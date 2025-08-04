"""
响应工具模块
提供统一的API响应格式化函数
"""

from typing import Any, Optional
from fastapi.responses import JSONResponse


def success_response(
    data: Optional[Any] = None,
    msg: str = "OK",
    code: int = 200,
    **kwargs
) -> JSONResponse:
    """
    成功响应工具函数
    
    Args:
        data: 响应数据
        msg: 响应消息
        code: 响应状态码
        **kwargs: 其他参数
        
    Returns:
        JSONResponse: 格式化的成功响应
    """
    content = {
        "code": code,
        "msg": msg,
        "data": data
    }
    content.update(kwargs)
    return JSONResponse(content=content, status_code=code)


def error_response(
    msg: str = "Error",
    code: int = 400,
    data: Optional[Any] = None,
    **kwargs
) -> JSONResponse:
    """
    错误响应工具函数
    
    Args:
        msg: 错误消息
        code: 错误状态码
        data: 错误数据
        **kwargs: 其他参数
        
    Returns:
        JSONResponse: 格式化的错误响应
    """
    content = {
        "code": code,
        "msg": msg,
        "data": data
    }
    content.update(kwargs)
    return JSONResponse(content=content, status_code=code)


def paginated_response(
    data: Optional[Any] = None,
    total: int = 0,
    page: int = 1,
    page_size: int = 20,
    msg: str = "OK",
    code: int = 200,
    **kwargs
) -> JSONResponse:
    """
    分页响应工具函数
    
    Args:
        data: 响应数据
        total: 总数量
        page: 当前页码
        page_size: 每页大小
        msg: 响应消息
        code: 响应状态码
        **kwargs: 其他参数
        
    Returns:
        JSONResponse: 格式化的分页响应
    """
    content = {
        "code": code,
        "msg": msg,
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size
    }
    content.update(kwargs)
    return JSONResponse(content=content, status_code=code)
