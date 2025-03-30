from pathlib import Path
from importlib.util import find_spec
import numpy as np


def find_library_path(library_name):
    spec = find_spec(library_name)
    library_path = Path(spec.origin).parent
    return library_path


def load_from_config(config_path):
    with open(config_path, 'r', encoding='utf-8') as f:
        config_content = f.read()
    config = {}
    exec(config_content, config)
    return config


def add_alpha_channel(image: np.ndarray):
    # 检查图像是否已有透明通道
    assert image.ndim == 3
    if image.shape[2] == 3:
        # 创建一个全为 255 的一维数组，表示完全不透明
        alpha = np.ones((image.shape[0], image.shape[1]),
                        dtype=image.dtype) * 255
        # 合并通道
        image_with_alpha = np.dstack((image, alpha))
        return image_with_alpha
    return image


def layer_mix(bg: np.ndarray, fg: np.ndarray):
    if fg.shape[2] == 3:
        # 无透明通道
        mix = fg
    elif bg.shape[2] == 3:
        alpha_f = fg[..., [-1]] / 255
        mix = fg[..., :3] * alpha_f + bg * (1-alpha_f)
    elif bg.shape[2] == 4:
        alpha_f = fg[..., [-1]] / 255
        alpha_b = bg[..., [-1]] / 255
        alpha_r = alpha_f + alpha_b * (1-alpha_f)
        mix = (
            bg[..., :3] * alpha_b * (1-alpha_f) + fg[..., :3] * alpha_f
            ) / alpha_r
        mix = np.dstack([mix, alpha_r * 255])
    return mix.astype(np.uint8)
