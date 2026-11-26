"""
调用AirSim APIs执行SPFActionSpace输出的相对变化量
"""
from typing import List, Optional

import airsim

from spf.base.thread_manager import SPFExecThreadManager
from spf.base.base_controller import BaseController
from spf.spf_action_space import SPFActionSpace
from spf.utils import load_config
from spf.base.command import Command
from spf.spf_action import SPFAction

class SPFController(BaseController):
    """ SPF 在 AirSim 平台上运行的控制器

    Attributes:
        vehicle_name(str):  飞行器的名字
        airsim_ip(str):     运行airsim的局域网ip
        airsim_port(int):   运行 airsim 的端口
        action_space(SPFActionSpace) 
    """

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
    def _get_platform_client(self) -> airsim.MultirotorClient:
        """ 生成 AirSim 多旋翼客户端
        
        Returns:
            AirSim 中内置的多旋翼客户端
        """
        return airsim.MultirotorClient(ip=self.airsim_ip, port=self.airsim_port)

    def _platform_connect(self) -> None:
        """ 连接 AirSim 多旋翼客户端
        
        确认连接 -> 支持API控制飞控 -> 上电 -> 记录AirSim运行线程的局域网和端口,以及飞行器名字
        """
        self.platform_client.confirmConnection()
        self.platform_client.enableApiControl(True, self.vehicle_name)
        self.platform_client.armDisarm(True, self.vehicle_name)
        self.logger.info(f"AirSim is connected ({self.airsim_ip}:{self.airsim_port}, vehicle={self.vehicle_name})")

    def _create_ctrl_thread_manager(self) -> SPFExecThreadManager:
        """ 创建执行线程管理器

        Returns:
            SPF执行线程管理器. 继承自 `ExecThreadManager`, 复写了 `execute_cmd` 方法
        """
        return SPFExecThreadManager(self.execute_cmd, name="airsim-control")

    def takeoff(self) -> None:
        """ 调用 AirSim API 完成起飞 """
        self.platform_client.takeoffAsync(vehicle_name=self.vehicle_name).join()

    def land(self) -> None:
        """ 调用 AirSim API 完成降落 
        
        先进入悬停态,再降落
        """
        self.platform_client.hoverAsync(vehicle_name=self.vehicle_name).join()
        self.platform_client.landAsync(vehicle_name=self.vehicle_name).join()

    def _shutdown(self) -> None:
        """ 结束 AirSim

        降落 -> 断电 -> 断开API控制        
        """
        self.land()
        self.platform_client.armDisarm(False, self.vehicle_name)
        self.platform_client.enableApiControl(False, self.vehicle_name)

    def execute_cmd(self, cmd: Command) -> None:
        """ 调用 AirSim APIs 执行命令

        调用 `airsim.MultirotorClient.rotateByYawRateAsync` 执行旋转指令, 旋转完成后进入悬停. 
        调用 `airsim.MultirotorClient.moveByVelocityBodyFrameAsync` 执行前进/后退命令,完成后进入悬停

        Args:
            cmd(Command) 具体指令

        Raises:
            ValueError: 获取到除 `rotate_yaw` 和 `move_velocity_body` 意外的指令类型
        """
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
                # is_rate = True 机头按 yaw_rate(deg/s) 角速度持续旋转
                # is_rate = False 机头在NED坐标系下,偏转 yaw(deg) 
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
        """ 将高维动作压入队列,等待执行
        
        先把 SPFAction 翻译成 Command，再提交 Command
        
        Args:
            actoin(SPFAction) 接受高维策略规划出来的动作
            
        Returns:
            提交的命令列表，空列表表示不动 
        
        Raises:
            TypeError 不接受除 SPFAction 外其他高维动作类型
        """
        if not isinstance(action, SPFAction):
            raise TypeError(f"expected SPFAction, got {type(action).__name__}")

        cmds = self.action_space.action_to_cmds(action)
        for cmd in cmds:
            self.submit_cmd(cmd)
        return cmds