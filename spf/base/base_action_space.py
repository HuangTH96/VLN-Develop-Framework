""" 翻译层，将 ActionPoint 转换成变化量 """
import math
from dataclasses import dataclass
from typing import List, Tuple, Optional
from abc import ABC, abstractmethod

@dataclass
class ActionPoint:
    """Represents a relative movement action in 3D space"""
    dx: float   # 左右相对位移，右为正
    dy: float   # 前后相对位移，前为正
    dz: float   # 上下相对位移，上为正
    action_type: str
    screen_x: float = 0.0  # 2D projected coordinates for visualization
    screen_y: float = 0.0
    detected_obstacles: Optional[list] = None  # Store detected obstacles (obstacle_mode only)
    yaw_only: bool = False  # Flag for yaw-only movement (when object is too close)

    def __str__(self):
        if self.yaw_only:
            return f"Action({self.action_type}): YAW ONLY - Object too close ({self.dx:.1f}, {self.dy:.1f}, {self.dz:.1f})"
        else:
            return f"Action({self.action_type}): Move({self.dx:.1f}, {self.dy:.1f}, {self.dz:.1f})"


class BaseActionSpace(ABC):
    def __init__(self, n_samples: int=0):
        self.n_samples = self.n_samples
        self.movement_unit = 1.0    # 1 unit = 1000ms of movement
        self.camera_fov = 90.0  # degrees
        self.max_movement = 2.0  # maximum movement in any direction

        # Add state tracking
        self.current_position = [0.0, 0.0, 0.0]  # [x, y, z]
        self.current_yaw = 0.0  # degrees

    @abstractmethod
    def action_to_cmds(self, action: ActionPoint) -> List[Tuple[str, int]]:
        """Convert a relative movement action into drone commands"""
        pass    

    def updata_state(self, action: str, duration_ms: float) -> dict:
        """Update drone state based on executed action and duration"""

        duration = duration_ms /1000
        move_rate = 1.0         # 每秒动1m
        yaw_rate = 51.4         # 7s转一圈
        vertical_rate = 1.0

        # update state based on action
        if action == "yaw_left":
            self.current_yaw = (self.current_yaw - yaw_rate * duration) % 360
        elif action == 'yaw_right':
            self.current_yaw = (self.current_yaw + yaw_rate * duration) % 360
        elif action == 'pitch_forward':
            # Move in direction of current yaw
            yaw_rad = math.radians(self.current_yaw)
            self.current_position[0] += move_rate * duration * math.sin(yaw_rad)
            self.current_position[1] += move_rate * duration * math.cos(yaw_rad)
        elif action == 'pitch_back':
            # Move opposite to current yaw
            yaw_rad = math.radians(self.current_yaw)
            self.current_position[0] -= move_rate * duration * math.sin(yaw_rad)
            self.current_position[1] -= move_rate * duration * math.cos(yaw_rad)
        elif action == 'increase_throttle':
            self.current_position[2] += vertical_rate * duration
        elif action == 'decrease_throttle':
            self.current_position[2] -= vertical_rate * duration

        return {
            "position": self.current_position.copy(),
            "yaw": self.current_yaw,
            "last_action": action,
            "duration": duration_ms
        }