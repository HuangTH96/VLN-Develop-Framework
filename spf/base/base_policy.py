from abc import ABC, abstractmethod
from typing import Optional

from spf.base.base_action import BaseAction
from spf.observation import Observation

class BasePolicy(ABC):
    """ 算法基类
    
    使用方法：

    1. 重置任务 policy.reset("instruction")
    2. 构建观测 obs = Observation(image=frame, fov_horizontal=108)
    3. 获取动作 act = policy.act(obs)
    
    Attributes:
        instruction(str) 自然语言命令
    """
    def __init__(self):
        self.instruction: Optional[str] = None

    def reset(self, instruction: str) -> None:
        """重新开始一个新任务。
        
        Args:
            instruction(str)
        """
        self.instruction = instruction

    @abstractmethod
    def act(self, obs: Observation) -> Optional[BaseAction]:
        """ 获取下一步动作。

        Args:
            obs(Observation) 环境观测

        Returns:
            高维抽象动作        
        """

    def _require_instruction(self) -> str:
        if self.instruction is None:
            raise RuntimeError(f"{type(self).__name__}.reset(instruction) must be called before act()")
        return self.instruction