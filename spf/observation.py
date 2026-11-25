from dataclasses import dataclass
from typing import Optional

import numpy as np

@dataclass
class Observation:
    """
    一次观测，算法的统一输入。

    只放各算法都能用到的最小集合，需要时再添加新的字段
    """
    image:np.ndarray                        
    fov_horizontal: Optional[float] = None  # 相机水平视野范围(度)。None表示让策略使用默认值
    stamp: float = 0.0                      # 采集时间（秒）