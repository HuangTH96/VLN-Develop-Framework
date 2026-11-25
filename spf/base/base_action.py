from abc import ABC, abstractmethod

class BaseAction(ABC):
    """
    抽象动作：只描述算法想做什么，不含任何平台概念。

    不同算法各写一个子类，字段自己定义
    """
    action_type: str 

    @abstractmethod
    def __str(self) -> str: 
        pass