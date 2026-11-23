"""
调用AirSim APIs执行SPFActionSpace输出的相对变化量
"""
from spf.base.thread_manager import SPFCtrlThreadManager
from spf.base.base_controller import BaseController
from spf.spf_action_space import SPFActionSpace
import airsim
from typing import Callable, Optional
# from config import SPFAirSimConfig
import numpy as np
import logging

class SPFController(BaseController):
    def __init__(
            self, 
            vlm: Callable[[str, np.ndarray], str], 
            cfg_path: str = None,
            image_width: int = 1920, 
            image_height: int = 1080, 
            airsim_ip: str = "127.0.0.1", 
            airsim_port: int = 41451,
            vehicle_name: str = "", 

            output_dir: Optional[str] = None):
        super().__init__()
        self.platform_client = self._get_platform_client(ip=airsim_ip, port=airsim_port)
        self.vehicle_name = vehicle_name

        self.action_space = SPFActionSpace(n_samples=6, cfg_path=cfg_path)

        self.logger = logging.getLogger("SPFController")

    def _get_platform_client(self, airsim_ip, airsim_port):
        client = airsim.MultirotorClient(ip=airsim_ip, port=airsim_port)
        return client

    @property
    def _connect(self):
        self.platform_client.confirmConnection()
        self.platform_client.enableApiControl(True, self.vehicle_name)
        self.platform_client.armDisarm(True, self.vehicle_name)
        self._connected=True

    def takeoff(self):
        self.platform_client.takeoffAsync(vehicle_name=self.vehicle_name).join()

    def land(self):
        self.platform_client.hoverAsync(vehicle_name=self.vehicle_name).join()
        self.platform_client.landAsync(vehicle_name=self.vehicle_name).join()

    # ------------ 控制逻辑与专用线程管理 -------------
    def execute_cmd(self, cmd):
        if not cmd: return 

        cmd_type, params = cmd
        try:
            if cmd_type == "rotate_yaw":
                angle, yaw_rate = params['angle'], params['yaw_rate', 30.0]
                duration = abs(angle) / yaw_rate
                rate = yaw_rate if angle >0 else -yaw_rate

                self.platform_client.rotateByYawRateAsync(rate, duration, vehicle_name=self.vehicle_name).join()
                self.platform_client.hoverAsync(vehicle_name=self.vehicle_name).join()

            elif cmd_type == "move_velocity_body":
                yaw_mode = airsim.YawMode(is_rate=True, yaw_or_rate=params.get("yaw_rate",0))
                self.platform_client.moveByVelocityBodyFrameAsync(
                    params["vx"],
                    params["vy"],
                    params["vz"],
                    params["duration"],
                    airsim.DrivetrainType.MaxDegreeOfFreedom,
                    yaw_mode,
                    vehicle_name = self.vehicle_name).join()
                self.platform_client.hoverAsync().join()        
        except Exception as e:
            self.logger.exception("Command execution failed: %s", e)

    def _create_ctrl_thread_manager(self) -> SPFCtrlThreadManager:
        return SPFCtrlThreadManager(self.execute_cmd, name="airsim-control")

    def _shutdown(self):
        self.land()
        self.platform_client.armDisarm(False, self.vehicle_name)
        self.platform_client.enableApiControl(False, self.vehicle_name)

    # ------------- workflow: 看图 -> 决策 -> cmd ----------
    def workflow(self, current_frame: np.adrray, instruct: str):
        try:
            actions = self.action_projector.get_vlm_points(current_frame, instruct)
            if not actions:
                raise ValueError("No valid actions identified!\n")

            action = actions[0]
            if action is None:
                raise ValueError(f"Action {action} is invalid action!\n")

            self._submit_action(action)
            return f"\n=== SINGLE ACTION MODE ===\n\n→ Moving: ({action.dx:.2f}, {action.dy:.2f}, {action.dz:.2f})"
        except Exception as e:
            self.logger.error("ERROR: %s", e)
            return "Error processing cmd! Check log file\n"

    def _submit_action(self, action):
        for cmd in self.action_space.action_to_cmds(action):
            self.submit_cmd(cmd)