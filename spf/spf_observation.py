from spf.base.base_observation import BaseObservation
from typing import Optional
from dataclasses import dataclass

import numpy as np

@dataclass
class SPFObservation(BaseObservation):
    """ SPF的观测

    Attributes:
        image(np.ndarray)   2D向量表示的图像
        fov_horizontal      。AirSim默认90，D435i为108度
        stamp               时间戳
    """
    image:np.ndarray                        
    fov_horizontal: Optional[float] = None  # 相机水平视野范围(度)。None表示让策略使用默认值