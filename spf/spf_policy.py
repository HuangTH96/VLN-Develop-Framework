import json
import logging
import math
import os
import time
from typing import Callable, Optional, Tuple

import numpy as np

from spf.base.base_policy import BasePolicy
from spf.observation import Observation
from spf.spf_action import SPFAction

log = logging.getLogger("spf-policy")

PROMPT = """You are a drone navigation expert analyzing a drone camera view.

Task: {instruction}

First, identify ALL objects in the image that match the description "{instruction}".
Then, select the MOST RELEVANT target object and place a single point DIRECTLY ON that object.

Return in this exact JSON format:
[{{"point": [y, x], "depth": depth_value, "label": "action description"}}]

Coordinate system:
- x: 0-1000 scale (500=center, >500=right, <500=left)
- y: 0-1000 scale (lower values=higher in image/sky)
- depth: 1-10 scale where:
    * 1: Object is very close/large in frame
    * 10: Object is far away/small in frame

IMPORTANT:
- Place the point PRECISELY on the center of the target object
- Choose the largest/closest matching object if multiple exist
- Assess the depth based on how much of the frame the object occupies
- Your accuracy in point placement is critical for navigation success"""

def clean_response_text(text: str) -> str:
    """去掉 markdown 代码围栏。"""
    if "```json" in text:
        s = text.find("```json") + 7
        text = text[s:text.find("```", s)].strip()
    elif "```" in text:
        s = text.find("```") + 3
        text = text[s:text.find("```", s)].strip()
    return text

def parse_vlm_response(response: str) -> Tuple[float, float, float, str]:
    """
    输出格式为：(y, x, depth, label)
    """

    item = json.loads(clean_response_text(response))[0]
    y, x = item['point']

    clip = lambda v, lower_bound, upper_bound: min(max(float(v), lower_bound), upper_bound)     # 截断越界值 
    # TODO: 如果没有有效深度值，则返回-1，后续需要处理   
    return clip(y, 0, 1000), clip(x, 0, 1000), clip(item.get('depth', -1.0), 1, 10), str(item.get('label', ''))

def cal_adaptive_detph(vlm_depth: float) -> float:
    """
    自适应模式的深度系数：

    <= 2表示目标太近，返回0，不动；
    <= 5 线型；
    >5 增长变缓，最大 2.0
    """
    if vlm_depth == -1.0:
        raise ValueError(f"{vlm_depth} is invalid vlm_depth, check parse_vlm_response\n")

    if vlm_depth <= 2:      
        return 0.0 

    if vlm_depth <= 5:
        return vlm_depth / 10.0 *2

    return 1.0 + (vlm_depth -5 ) / 5.0

def reverse_project_point(
        px: float,
        py: float,
        depth: float,
        width: int,
        height: int,
        fov_horizontal: float
) -> Tuple[float, float, float]:
    """
    将目标点在图像中的位置 px, py 转变成相机坐标系中的位置 （ dx 右， dy 前=depth，dz 上）

    Args:
    
    - px, py 目标点在图像坐标系中的位置
    - depth VLM对目标点的深度预测
    - width, height 图像的尺寸
    - fov_horizontal 相机的视野范围
    """
    fov_factor = math.tan(math.radians(fov_horizontal / 2))     # 真实物理世界中的视野半径 depth * fov_factor 
    x_off, y_off = px - width/2, height/2 - py                  # 像素坐标归中

    return (
        (x_off / (width / 2)) * depth * fov_factor,             # 像素归一化后，根据depth计算得到该点在真实世界中的位移
        depth,
        (y_off / (height / 2)) * depth * fov_factor
    )

# ----------- SPF policy --------
class SPFPolicy(BasePolicy):
    def __init__(
            self,
            vlm: Callable[[str, np.ndarray], str],
            adaptive_mode: bool = False,
            fov_horizontal: float = 108.0,
            output_dir: Optional[str] = None
        ) -> str:
        """
            Args:

        - vlm(prompt, image_bgr),
        - fov_horizontal 值是默认值，如果观测里带了 fov_horizontal ，则优先使用观测得到的
        - output_dir 不为空时，将每次决策的标注图和JSON都保存下来
        """
        super.__init__()
        self.vlm = vlm
        self.adaptive_mode = adaptive_mode
        self.fov_horizontal = fov_horizontal

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

    @classmethod
    def load_config(
        cls,
        vlm: Callable[[str, np.ndarray], str],
        cfg:dict
    ) -> "SPFPolicy":
        return cls(
            vlm, 
            adaptive_mode = cfg.get('adaptive_mode', False),
            fov_horizontal = cfg.get('fov_horizontal', 108.0),
            output_dir = cfg.get('output_dir')
        )

    def act(self, obs:Observation) -> Optional[Observation]:
        instruction = self._require_instruction()
        h, w = obs.image.shape[:2]
        fov = obs.fov_horizontal or self.fov_horizontal     # 如果观测不含有相机视野范围，则使用策略标注的视野范围

        try:
            raw = self.vlm(PROMPT.format(instruction=instruction))
            log.info("VLM response: {raw}}")
            y, x, vlm_depth, label = parse_vlm_response(raw)
        except Exception as e:
            log.error("No decision from VLM: {e}")
            return None

        px, py = int(x / 1000.0 * w), int(y / 1000.0 * h)   # 确定目标点在图像坐标系中的位置
        if self.adaptive_mode:
            adaptive_depth: Optional[float] = cal_adaptive_detph(vlm_depth)
            depth = adaptive_depth
        else:
            adaptive_depth = None
            depth = vlm_depth / 10.0 * 2.0  # 深度最大的尺度单位为10，对应2m的深度距离

        dx, dy, dz = reverse_project_point(px, py, depth, w, h, fov)

        action = SPFAction(
            dx=dx,
            dy=dy,
            dz=dz,
            action_type="move",     # TODO: move_by_velocity?
            screen_x=px,
            screen_y=py,
            adaptive_depth=adaptive_depth,
            vlm_depth=vlm_depth if self.adaptive_mode else None
        )

        log.info(f"target={label}, pixel=({px}, {py}), vlm_depth={vlm_depth}\n")
        if self.output_dir:
            self._save_decision(obs.image, instruction, action)

        return action

    def _save_decision(self, img:np.ndarray, instruction: str, a: SPFAction) -> None:
        import cv2                              # 只有在开启保存时才需要
        ts = time.strftime("%Y%m%d_%H%M%S")     # 年月日_时分秒
        viz = img.copy()
        
        cv2.circle(viz, (int(a.screen_x), int(a.screen_y)), 10, (0, 255, 0), -1)
        cv2.putText(viz, f"({a.dx:.1f}, {a.dy:.1f}, {a.dz:.1f})", (int(a.screen_x) + 15, int(a.screen_y)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.imwrite(f"{self.output_dir}/decision_{ts}.jpg", viz)

        data = {"timestamp": ts, "instruction": instruction, "adaptive_mode": self.adaptive_mode,
                "action": {k: v for k, v in dict(dx=a.dx, dy=a.dy, dz=a.dz, screen_x=a.screen_x, screen_y=a.screen_y,
                                                 adaptive_depth=a.adaptive_depth, vlm_depth=a.vlm_depth).items() if v is not None}}
        with open(f"{self.output_dir}/decision_{ts}.json", "w") as f:
            json.dump(data, f, indent=2)