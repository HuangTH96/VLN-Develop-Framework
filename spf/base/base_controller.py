from abc import ABC, abstractmethod
from typing import Optional
import logging

from spf.base.thread_manager import ExecThreadManager
from spf.base.command import Command


class BaseController(ABC):
    """平台无关的控制器骨架。根据不同的平台，具体实现Command
    
    Attributes:
        platform(str): 子类覆盖的平台标识字符串，如 'AirSim'、'PX4'
        logger(logging.logger)：当前平台的日志记录器
        platform_client(Any): 平台相关的底层客户端实例
        last_error(Optional[BaseException]): 记录最近一次发生的异常
    """

    platform: str = 'unkonwn'       # 子类覆盖，如 AirSim、 PX4

    def __init__(self):        
        self.logger = logging.getLogger(f"spf.controller.{self.platform}")
        self.platform_client = None
        self._ctrl_thread_manager: Optional[ExecThreadManager] = None
        self._connected = False
        self.last_error: Optional[BaseException] = None

    # --------- 平台层实现
    @abstractmethod
    def _get_platform_client(self):
        """ 生成平台相关的客户端实例

        Returns:
            Any: 平台客户端。如 airsim.MultirotorClient() 
        """

    @abstractmethod
    def _platform_connect(self) -> bool:
        """ 连接平台并准备接收命令
        
        Returns:
            bool: 连接成功返回True，否则返回False 
        """

    @abstractmethod
    def _create_ctrl_thread_manager(self) -> ExecThreadManager:
        """ 返回一个以 self.execute_cmd 为 handler 的线程管理器。
        
        Returns:
            ExecThreadManager: 线程管理器实例
        """

    @abstractmethod
    def _shutdown(self) -> None:
        """ 线程停止后的收尾工作。
        
        通常包含悬停、降落、解除控制等平台相关操作。
        """

    @abstractmethod
    def takeoff(self) -> None: 
        """ 触发无人机起飞 """
        ...

    @abstractmethod
    def land(self) -> None: 
        """ 触发无人机降落 """
        ...

    @abstractmethod
    def execute_cmd(self, cmd: Command) -> None:
        """ 阻塞地执行一条命令。
        
        该方法运行在工作线程里。如果执行失败，必须调用 `_record_error(e)` 记录异常 
        
        Args:
            cmd(Command): 要执行的指令对象
        """

    # ------------ 通用
    def _record_error(self, e: BaseException) -> None:
        """ 记录并打印命令执行错误

        Args:
            e(BaseException): 捕获到的异常实例
        """
        self.last_error = e
        self.logger.error("Command failed: %r", e, exc_info=e)

    def connect(self) -> None:
        """ 创建客户端并连接平台。
        
        该方法支持重复调用。如果已经连接，则直接返回。

        Raises: 
            ValueError: 当无法成功连接到目标平台时抛出
        """
        if self._connected:
            return

        self.platform_client = self._get_platform_client()
        info = self._platform_connect()

        if info:
            self._connected = True    
        else:
            raise ValueError(f"Fail to connect platform!")

    @property
    def ctrl_thread_manager(self) -> ExecThreadManager:
        """ ExecThreadManager: 获取控制线程管理器，首次访问时才会触发创建 """
        if self._ctrl_thread_manager is None:
            self._ctrl_thread_manager = self._create_ctrl_thread_manager()
            return self._ctrl_thread_manager

    def submit_cmd(self, cmd: Command):
        """提交一条命令到队列中，此操作为非阻塞。
        
        Args:
            cmd(Command): 待提交的指令对象
        """
        self.ctrl_thread_manager.submit(cmd)

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """等待已提交的命令全部执行完成。
        
        注意： 命令失败也算"完成"。如果需要检查错误，请在调用后配合 `raise_if_failed()` 使用。

        Args:
            timeout(float, optional): 最多等待的超时时间（秒）。默认30.0

        Returns:
            bool: 如果在超时前全部命令执行完毕，返回True，否则返回False
        """
        return self._ctrl_thread_manager.wait_idle(timeout)

    # def raise_if_failed(self) -> None:
    #     err, self.last_error = self.last_error, None
    #     if err is not None:
    #         raise RuntimeError(f"{self.platform} command failed: {err}")

    def stop(self) -> None:
        """ 停止控制器工作。

        此操作会遵循一下步骤：
        1. 先停工作线程。如果线程正在执行长命令，后续的平台收尾工作将会将其打断。
        2. 进行平台层面的收尾工作（调用 `_shutdown`）。
        """
        tm = self._ctrl_thread_manager
        if tm is not None and not tm.stop():
            self.logger.warning(f"{self.platform} worker still running a command; shutdown will interrupt it")

        if self._connected:
            self._shutdown()
            self._connected = False


    def get_pose(self):
        """ 获取无人机当前在世界坐标系下的姿态。

        用于判断碰撞、同步位置等闭环任务。

        Returns:
            Optional[Any]: 包含位置和朝向的姿态数据，未实现时返回None
        """
        pass