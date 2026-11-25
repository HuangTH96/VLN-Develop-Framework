from dataclasses import dataclass
from typing import Optional

from spf.base.base_action import BaseAction

@dataclass
class SPFAction(BaseAction):
    """
    SPF算法中的动作：相机坐标系下的相对位移， dx 向右为正， dy 向前为正， dz 向上为正
    """

    dx: float
    dy: float
    dz: float
    action_type: str
    screen_x: float = 0.0               # 2D 投影坐标，仅用于可视化
    screen_y: float = 0.0
    detected_obstacles: Optional[list] = None   # 仅障碍模式使用（AirSim 路径未用到）
    yaw_only: bool = False                      # 目标太近时只转向（AirSim 路径未用到）
    adaptive_depth: Optional[float] = None      # 自适应模式：换算后的深度系数
    vlm_depth: Optional[float] = None           # VLM 原始深度标签 1-10

    def __str__(self) -> str:
        if self.yaw_only:
            return f"Action({self.action_type}): YAW ONLY - Object too close ({self.dx:.1f}, {self.dy:.1f}, {self.dz:.1f})"
        return f"Action({self.action_type}): Move({self.dx:.1f}, {self.dy:.1f}, {self.dz:.1f})"