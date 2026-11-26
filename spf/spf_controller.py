"""
调用AirSim APIs执行SPFActionSpace输出的相对变化量
"""
from typing import List, Optional

import airsim

from spf.base.thread_manager import SPFCtrlThreadManager
from spf.base.base_controller import BaseController
from spf.spf_action_space import SPFActionSpace
from spf.utils import load_config
from spf.base.command import Command
from spf.spf_action import SPFAction

class SPFController(BaseController):

    platform = "AirSim"

    def __init__(
            self, 
            cfg_path: str,
            action_space: Optional[SPFActionSpace] = None
    ):
        
        super().__init__()

        cfg = load_config(cfg_path)
        self.vehicle_name = cfg.get("vehicle_name", "")
        self.airsim_ip: str = cfg.get("airsim_ip", "")
        self.airsim_port: int = cfg.get("airsim_port", 41451)
        self.action_space = action_space or SPFActionSpace(cfg_path=cfg_path)

    # ------- 平台层 --------
    def _get_platform_client(self):
        return airsim.MultirotorClient(ip=self.airsim_ip, port=self.airsim_port)

    def _platform_connect(self) -> None:
        self.platform_client.confirmConnection()
        self.platform_client.enableApiControl(True, self.vehicle_name)
        self.platform_client.armDisarm(True, self.vehicle_name)
        self.logger.info(f"AirSim is connected ({self.airsim_ip}:{self.airsim_port}, vehicle={self.vehicle_name})")

    def _create_ctrl_thread_manager(self) -> SPFCtrlThreadManager:
        return SPFCtrlThreadManager(self.execute_cmd, name="airsim-control")

    def takeoff(self) -> None:
        self.platform_client.takeoffAsync(vehicle_name=self.vehicle_name).join()

    def land(self) -> None:
        self.platform_client.hoverAsync(vehicle_name=self.vehicle_name).join()
        self.platform_client.landAsync(vehicle_name=self.vehicle_name).join()

    def _shutdown(self) -> None:
        self.land()
        self.platform_client.armDisarm(False, self.vehicle_name)
        self.platform_client.enableApiControl(False, self.vehicle_name)

    def execute_cmd(self, cmd: Command):
        if not cmd: return 

        cmd_type, params = cmd
        client, vn = self.platform_client, self.vehicle_name
        try:
            if cmd_type == "rotate_yaw":
                angle, yaw_rate = params['angle'], params['yaw_rate', 30.0]
                duration = abs(angle) / yaw_rate
                rate = yaw_rate if angle >0 else -yaw_rate  # AirSim：顺时针为正

                client.rotateByYawRateAsync(rate, duration, vehicle_name=vn).join()
                client.hoverAsync(vehicle_name=vn).join()

            elif cmd_type == "move_velocity_body":
                yaw_mode = airsim.YawMode(is_rate=True, yaw_or_rate=params.get("yaw_rate",0))
                client.moveByVelocityBodyFrameAsync(
                    params["vx"],
                    params["vy"],
                    params["vz"],
                    params["duration"],
                    airsim.DrivetrainType.MaxDegreeOfFreedom,
                    yaw_mode,
                    vehicle_name = vn).join()
                client.hoverAsync().join()        
            else:
                raise ValueError(f"unkown command type: {cmd_type}")
        except Exception as e:
            self._record_error(e)

    # ---------- high-level action -> low-level command -----
    def submit_action(self, action: SPFAction) -> List[Command]:
        """ 把一个 SPFAction 翻译成 Command，并提交，返回提交的命令列表，空列表表示不动 """
        if not isinstance(action, SPFAction):
            raise TypeError(f"expected SPFAction, got {type(action).__name__}")

        cmds = self.action_space.action_to_cmds(action)
        for cmd in cmds:
            self.submit_cmd(cmd)
        return cmds