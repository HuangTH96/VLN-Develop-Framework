from typing import List, Tuple, Any, Dict, Generic, TypeVar
from abc import ABC, abstractmethod

from spf.base.base_action import BaseAction
from spf.base.command import Command

# 用泛型绑定动作类型
A = TypeVar("A", bound=BaseAction)

class BaseActionSpace(ABC, Generic[A]):
    """ 动作空间翻译层基类。

    作为一个无状态的纯函数抽象层，负责将算法输出的抽象动作转换为底层平台通用的命令列表。该组件不包含任何状态，不保存位子，也不直接和特定平台交互

    Generic Args:
        A(BaseAction): 绑定该动作空间所支持的具体抽象类子类
    """

    @abstractmethod
    def action_to_cmds(self, action: A) -> List[Command]:
        """ 将高层算法的抽象动作转化为可执行的底层命令序列。

        Args:
            action(A): 导航算法输出的抽象动作序列，必须是 BaseAction 的子类

        Returns:
            List[Command]: 翻译后生成的通用命令列表，将由控制器一次分发执行。每个命令的格式为 Tuple[str, Dict[str, Any]]
        """
        pass