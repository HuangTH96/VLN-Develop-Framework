""" 用于线程管理 

1. 提交item.
2. 单个工作线程按顺序一次运行一个 handler(item)
3. wait_idle() 仅在最后一个提交的item完成后才返回。
"""

import threading
import logging
import queue
from typing import Any, Callable
from abc import ABC, abstractmethod
from command import Command

class CtrlThreadManager(ABC):
    """
    单工作线程执行器。
    
    基类实现全部通用机制，只把"提交策略"留给子类。
    
    构造时不启动线程：子类先把自己的属性设置完，最后一行调用 self.start()。
    """
    def __init__(self, handler: Callable[[Any],None], poll: float = 5.0, thread_name: str = 'base_thread', logger_name: str = "base_logger"):
        if handler is None:
            raise ValueError("Need a handler function!\n")
        elif not callable(handler):
            raise ValueError(f"Handler {handler} is not callable!")
        self._handler, self._poll = handler, poll                                   # handler 是实际处理 item 的回调函数

        self._stop_evt = threading.Event()                                          # 停止信号：set() 只是把标志置真，由 _run 循环自己检查后退出
        self._cv = threading.Condition()                                            # with self._cv: 锁定代码块，同一时刻只允许一个线程进入代码块；这里都用来保护 self._pending 变量 
        self._pending = 0                                                           # 多线程共享变量，记录任务个数                                              
        self._cmds: "queue.Queue" = queue.Queue()
        self._thread = threading.Thread(target=self._run, name=thread_name, daemon=True)   # 创建一个后台线程运行 self._run，命名为 name，当主程序结束时，后台线程也会自动销毁

        # logger
        self.logger = logging.getLogger(logger_name)

    def start(self):
        self._thread.start()

    @abstractmethod
    def submit(self, cmd: Command) -> None:
        """ 提交一个任务，不阻塞 """

    def _run(self) -> None:
        """ 死循环，从指令队列中提取指令，调用 handler(cmds) 执行，完成后标记 """
        while not self._stop_evt.is_set():
            try:
                cmd = self._cmds.get(timeout=self._poll)
            except queue.Empty:
                continue

            try:
                self._handler(cmd)  # 实际上是 BaseController.execute_cmd
            except Exception:  # a failing command must not kill the worker
                # TODO: 和BaseController 一样，使用_record_error 记录
                self.logger.exception("Command handler failed")
            finally:
                self._done(1)

    def _done(self, n:int) -> None:
        with self._cv:              # 获取独占锁
            self._pending -= n      # 记录完成了n个任务
            self._cv.notify_all()   # 唤醒所有在 wait_idle 里等待的线程

    def wait_idle(self, timeout: float = 30.0) -> bool:
        """True when everything submitted so far has finished; False on timeout."""
        with self._cv:
            return self._cv.wait_for(lambda: self._pending == 0, timeout)

    def _clear(self) -> int:
        """Drop items that have not started yet (the running one cannot be cancelled). Returns how many were dropped."""
        n = 0
        while True:
            try:
                self._tasks.get_nowait()
            except queue.Empty:
                break
            n += 1
        if n:
            self._done(n)
        return n
    
    def stop(self, timeout = 5.0) -> bool:
        self._stop_evt.set()
        self._clear()
        if self._thread.ident is not None:  # 从未start的线程不能join
            self._thread.join(timeout)

        return not self._thread.is_alive()
    
    # 状态查询
    def pending(self) -> int:
        with self._cv:
            return self._pending

    def is_alive(self) -> bool:
        return self._thread.is_alive()

class SPFCtrlThreadManager(CtrlThreadManager):
    """SPF 的策略：先进先出，每条命令都排队，按顺序逐条执行完。"""

    def __init__(
            self, 
            handler: Callable[[Any],None], 
            poll: float = 0.1, 
            thread_name: str = 'spf-controller', 
            logger_name: str = "spf-logger"
        ):
        super.__init__(
            handler = handler, 
            poll = poll, 
            thread_name=thread_name, 
            logger_name = logger_name
        )

        self.start()
    
    def submit(self, item:Command) -> None:
        if self._stop_evt.is_set():
            raise RuntimeError("ThreadManager is stopped!")
        
        with self._cv:
            self._pending += 1
        
        self._tasks.put(item)       # 将新任务存入到任务队列中