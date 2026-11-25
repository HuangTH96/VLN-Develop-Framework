from abc import ABC, abstractmethod
from typing import Optional

from spf.base.base_action import BaseAction
from spf.observation import Observation

class BasePolicy(ABC):
    """
    算法本体：观测 + 指令 -> 抽象动作。

    使用方法：

    1. 重置任务 policy.reset("instruction")
    2. 构建观测 obs = Observation(image=frame, fov_horizontal=108)
    3. 获取动作 act = policy.act(obs)
    """
    def __init__(self):
        self.instruction: Optional[str] = None

    def reset(self, instruction: str) -> None:
        """
        重新开始一个新任务。
        """
        self.instruction = instruction

    @abstractmethod
    def act(self, obs: Observation) -> Optional[BaseAction]:
        """
        返回下一步动作。

        这里可能会用到MLLM，会很慢，因此不要在控制器的工作线程（BaseController._thread）中调用
        """

    def _require_instruction(self) -> str:
        if self.instruction is None:
            raise RuntimeError(f"{type(self).__name__}.reset(instruction) must be called before act()")
        return self.instruction