"""统一错误体。

所有接口的错误响应统一为 ``{"code": "<机器码>", "message": "<面向用户的中文提示>"}``，
由 ``app.main`` 中注册的异常处理器转换为 HTTP 响应。
"""

from __future__ import annotations


class ApiError(Exception):
    """业务异常。

    Attributes:
        status_code: HTTP 状态码（400/401/403/404/413/429/500/501）。
        code: 机器码，供前端分支判断。
        message: 面向用户的中文提示。
    """

    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
