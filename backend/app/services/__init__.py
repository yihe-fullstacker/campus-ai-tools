"""业务层（能力函数层）。

每个模块对外暴露一个能力函数，api 层只调用这些函数，不直接读写其他模块的内部状态；
后续 Agent 化时每个能力函数可直接注册为 Tool。
"""


class ServiceNotImplemented(NotImplementedError):
    """模块尚未实现；api 层会将其转换为 501 响应。"""
