import math
from typing import List
import logging

from base.base_action_space import BaseActionSpace
from base.command import Command
from spf_action import SPFAction
from utils import load_config

log = logging.getLogger("spf_action_space")

class SPFActionSpace(BaseActionSpace[SPFAction]):
    def __init__(
            self, 

            cfg_path: str='config.yaml'
            ):
        
        config = load_config(cfg_path)
        self.base_velocity = config.get("base_velocity", 2.0)
        self.base_yaw_rate = config.get("base_yaw_rate", 30.0)
        self.min_command_duration = config.get("min_command_duration", 2.0)

    def action_to_cmds(self, action: SPFAction) -> List[Command]:
        """
        Convert SPFAction to AirSim APIs.
        First rotate, then move
        """

        commands: List[Command] = []

        if hasattr(action, "adaptive_depth") and action.adaptive_depth is not None:
            
            if action.adaptive_depth == 0:
                print(
                    "[ADAPTIVE TIMING] Depth 0 detected - No movement commands will be generated"
                )
                return []
            
            velocity_multiplier = action.adaptive_depth
            print(
                f"[ADAPTIVE TIMING] Using depth factor {action.depth_factor:.2f} for movement velocity"
                )
        else:
            velocity_multiplier = 1.0

        velocity_scale = self.base_velocity * velocity_multiplier
        base_yaw_rate = self.base_yaw_rate * velocity_multiplier

        if math.sqrt(action.dx ** 2 + action.dy ** 2 + action.dz ** 2) < 0.01:
            print(f"Movement is too small, cannot generate command!\n")
            return []

        # Step 1: Calculate yaw angle needed to face the target
        distance_xy = math.sqrt(action.dx**2 + action.dy**2)

        if distance_xy > 0.01:
            # Calculate target angle from dx, dy
            # 从机头正前方向右转动度数
            target_angle = math.degrees(math.atan2(action.dx, action.dy))

            # Normalize to -180 to 180 range
            if target_angle > 180:
                target_angle -= 360
            elif target_angle < -180:
                target_angle += 360

            print(
                f"[YAW DEBUG] dx={action.dx:.3f}, dy={action.dy:.3f}, target_angle={target_angle:.1f}°"
            )

            # Add rotation command if angle is significant
            if abs(target_angle) > 10:
                commands.append(
                    (
                        "rotate_yaw", 
                        {
                            "angle": target_angle, 
                            "yaw_rate": base_yaw_rate
                        }
                    )
                )
                print(f"[YAW DEBUG] Adding rotation command: {target_angle:.1f}°")
            else:
                print(
                    f"[YAW DEBUG] Target angle {target_angle:.1f}° is within threshold, no yaw"
                )

        # Step 2: Move forward after rotation (or if no rotation needed)
        # Use full velocity for forward movement
        vx = velocity_scale
        vy = 0  # No sideways movement

        # 不仅仅是平飞，还要同时考虑高度
        if distance_xy > 0.01:
            # vz = (-action.dz / distance_xy) * velocity_scale
            vz = -action.dz / (distance_xy / velocity_scale)     # AirSim body frame: z is DOWN 
            duration = max(distance_xy / velocity_scale, self.min_command_duration) # 防止运动过短
        else:
            vz = 0
            duration = self.min_command_duration

        print(
            f"[MOVEMENT DEBUG] action.dz={action.dz:.3f}, vx={vx:.2f}, vz={vz:.2f}, duration={duration:.2f}s"
        )

        commands.append(
            (
                "move_velocity_body",
                {
                    "vx": vx,
                    "vy": vy,
                    "vz": vz,
                    "duration": duration,
                    "yaw_rate": 0,  # No yaw during movement, already rotated
                },
            )
        )

        return commands