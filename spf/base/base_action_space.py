from typing import List, Tuple, Any, Dict, Generic, TypeVar
from abc import ABC, abstractmethod

from .base_action import BaseAction
from command import Command

# 用泛型绑定动作类型
A = TypeVar("A", bound=BaseAction)

# Command = Tuple[str, Dict[str, Any]]

class BaseActionSpace(ABC, Generic[A]):
    """
    翻译层：算法动作 -> 命令列表。无状态的纯函数，不碰平台、不保存位姿。
    """

    @abstractmethod
    def action_to_cmds(self, action: A) -> List[Command]:
        pass