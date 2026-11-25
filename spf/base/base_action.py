from abc import ABC, abstractmethod

class BaseAction(ABC):
    """ 抽象动作基类。
    
    只描述算法想做什么，不含任何平台概念。
    不同的导航算法各自继承此类并实现具体的子类，其内部字段由算法自行定义。

    Attributes:
        action_type(str): 动作的分类标识字符串
    """
    action_type: str 

    @abstractmethod
    def __str(self) -> str: 
        """ 将动作对象序列化为字符串。

        主要用于控制器打印日志和终端调试

        Returns:
            str: 动作的文本描述
        """
        pass