from dataclasses import dataclass

@dataclass
class BaseObservation:
    """ 基础观测类

    Attributes:
        stamp               时间戳
        fov_horizontal      相机的水平视野（度）
    """
    stamp: float = 0.0
