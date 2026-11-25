from abc import ABC, abstractmethod
from typing import Optional
import logging

from spf.base.thread_manager import CtrlThreadManager
from spf.base.command import Command


class BaseController(ABC):
    """平台无关的控制器骨架。
    
    只管：连接、命令异步排队、等待完成、统一停止、错误可见。
    算法的输出（动作）由外部翻译成命令（Command）后再 submit_cmd。

    线程约定：
      - 主线程调用：connect / takeoff / land / submit_cmd / wait_idle / raise_if_failed / stop
      - 工作线程调用：execute_cmd（阻塞执行一条命令，不在主线程直接调用）
    """

    platform: str = 'unkonwn'       # 子类覆盖，如 AirSim、 PX4

    def __init__(self):        
        self.logger = logging.getLogger(f"spf.controller.{self.platform}")
        self.platform_client = None
        self._ctrl_thread_manager: Optional[CtrlThreadManager] = None
        self._connected = False
        self.last_error: Optional[BaseException] = None

    # --------- 平台层实现
    @abstractmethod
    def _get_platform_client(self):
        """ 生成平台相关的client，如 airsim.MultirotorClient() """

    @abstractmethod
    def _platform_connect(self) -> bool:
        """ 连接平台并准备好接收命令，连接成功返回True，否则返回False """

    @abstractmethod
    def _create_ctrl_thread_manager(self) -> CtrlThreadManager:
        """返回一个以 self.execute_cmd 为 handler 的线程管理器（决定排队策略）。"""

    @abstractmethod
    def _shutdown(self) -> None:
        """线程停下之后的收尾：悬停、降落、解除控制等。"""

    @abstractmethod
    def takeoff(self) -> None: ...

    @abstractmethod
    def land(self) -> None: ...

    @abstractmethod
    def execute_cmd(self, cmd: Command) -> None:
        """ 阻塞地执行一条命令，运行在工作线程里。失败时调用 self._record_error(e) """

    # ------------ 通用
    def _record_error(self, e: BaseException) -> None:
        self.last_error = e
        self.logger.error("Command failed: %r", e, exc_info=e)

    def connect(self) -> None:
        """ 创建 client 并连接，可重复调用。"""
        if self._connected:
            return

        self.platform_client = self._get_platform_client()
        info = self._platform_connect()

        if info:
            self._connected = True    
        else:
            raise ValueError(f"Fail to connect platform!")

    @property
    def ctrl_thread_manager(self) -> CtrlThreadManager:
        """ 首次访问时才创建 """
        if self._ctrl_thread_manager is None:
            self._ctrl_thread_manager = self._create_ctrl_thread_manager()
            return self._ctrl_thread_manager

    def submit_cmd(self, cmd: Command):
        """提交一条命令，不阻塞。"""
        self.ctrl_thread_manager.submit(cmd)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """
        已提交的命令全部执行完成才返回 True，超时返回 False。
        
        注意：命令失败也算"完成"，请随后调用 raise_if_failed()。
        """
        return self._ctrl_thread_manager.wait_idle(timeout)

    # def raise_if_failed(self) -> None:
    #     err, self.last_error = self.last_error, None
    #     if err is not None:
    #         raise RuntimeError(f"{self.platform} command failed: {err}")

    def stop(self) -> None:
        """
        1. 先停工作线程
        2. 再做平台收尾。
        
        线程可能还在执行长命令，_shutdown 里的悬停会打断它。
        """
        tm = self._ctrl_thread_manager
        if tm is not None and not tm.stop():
            self.logger.warning(f"{self.platform} worker still running a command; shutdown will interrupt it")

        if self._connected:
            self._shutdown()
            self._connected = False


    def get_pose(self):
        """ 
        获取uav当前位置，用于判断碰撞等任务
        """
        pass