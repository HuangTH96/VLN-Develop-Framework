from abc import ABC, abstractmethod
from typing import Any,Optional
from spf.base.thread_manager import CtrlThreadManager

class BaseController(ABC):
    def __init__(self):
        self._ctrl_thread_manager: Optional[CtrlThreadManager] = None
        self.platform_client = self._get_platform_client()

    # ---------- 平台层实现 ----------
    @abstractmethod
    @property
    def _connect(self) -> None:
        """连接平台并准备好接收命令 """

    @abstractmethod
    def takeoff(self) -> None: ...

    @abstractmethod
    def land(self) -> None: ...

    @abstractmethod
    def execute_cmd(self, cmd: Any) -> None:
        """阻塞地执行一条命令。作为 control_thread 的handler，运行在工作线程里，不在主线程中直接调用。"""

    @abstractmethod
    def _create_ctrl_thread_manager(self) -> CtrlThreadManager:
        """返回一个以 self.execute_cmd 为 handler 的线程管理器（决定排队策略）。"""

    @abstractmethod
    def _shutdown(self) -> None:
        """线程停下之后的收尾：悬停、降落、解除控制等。"""

    @abstractmethod
    def _get_platform_client(self):
        """ 生成平台相关的client，如 airsim.MultirotorClient() """

    # ---------- 通用部分 ----------
    @property
    def ctrl_thread_manager(self) -> CtrlThreadManager:
        """首次访问时才创建，避免在子类属性还没初始化完就启动线程。"""
        if self._ctrl_thread_manager is None:
            self._ctrl_thread_manager = self._create_ctrl_thread_manager()
        return self._ctrl_thread_manager

    def submit_cmd(self, cmd: Any) -> None:
        """提交命令，不阻塞。"""
        self._ctrl_thread_manager.submit(cmd)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """已提交的命令全部执行完成才返回 True，超时返回 False。"""
        return self._ctrl_thread_manager.wait_idle(timeout)

    def stop(self) -> None:
        """先停工作线程，再做平台收尾。线程可能还在执行长命令，_shutdown 里的悬停会打断它。"""
        if self._ctrl_thread_manager is not None and not self._ctrl_thread_manager.stop():
            self.logger.warning("%s worker still running a command; shutdown will interrupt it", self.platform)
        self._shutdown()

    @abstractmethod
    def workflow(self) -> None: