from typing import Union, Literal
from dataclasses import dataclass
import numpy as np
from melody_machine.visualizer.base_types import ColorPalette
import matplotlib.pyplot as plt


@dataclass
class CONFIG():
    StartBar = 5  # .flp工程中的音频实际起始小节号
    InitBar = 1  # 视频中的起始记数小节号
    BeginTime = 1  # 开幕大标题的显示时长（秒）
    CountDown = 3  # 倒计时个数
    Title = None  # 开幕大标题文本
    Saying = None  # 开幕格言文本
    Name = '—— Gray Frezicical'  # 落款
    h = 1080  # 视频的高度（像素）
    w = 2160  # 视频的宽度（像素）
    FontPath = 'C:/Users/Gray/AppData/Local/Microsoft/Windows/Fonts/sarasa-mono-sc-regular.ttf'  # 字体路径
    spb = 4  # steps per beat
    bpB = 4  # beats per Bar
    bpM = 120  # beats per Minutes
    tpb = 96  # ticks per beat / timebase
    pitch_clip_range = [33, 93]  # 全局音符音高范围[A2,A7]
    expand_range = [4, 4]  # 音高上下拓展显示范围
    min_pitch_range = [10, 10]  # 音高上下最小范围
    subclip_tBar = None  # 输出视频的裁剪范围（小节）
    subclip_tMov = None  # 输出视频的裁剪范围（秒）
    spB = spb * bpB
    BpM = bpM / bpB
    step = tpb // 4  # Fl studio中可视的最小单位长度 24
    beat = step * spb
    Bar = beat * bpB
    # type_visualizer: Literal[
    #     'BaseVisualizer',
    #     'MovieVisualizer',
    #     ] = 'MovieVisualizer'  # 视频生成器类型
    subclip_tBar = None  # 输出视频的裁剪范围（小节）
    subclip_tMov = None  # 输出视频的裁剪范围（秒）


@dataclass
class COLOR():
    # 颜色
    COLOR_BG = np.array([49 / 255, 56 / 255, 62 / 255])
    COLOR_BLACK_KEY = np.array([0.23, 0.23, 0.23])
    COLOR_WHITE_KEY = np.array([0.9, 0.9, 0.9])
    COLOR_WHITE_C = np.array([0.75, 0.75, 0.75])
    COLOR_LIGHT_ROW = np.array([0.5, 0.5, 0.5, 0.1])
    COLOR_DARK_ROW = np.array([0.2, 0.2, 0.2, 0.0])
    COLOR_EDGE = np.array([0.5, 0.5, 0.5])
    COLOR_NOTE_FACE = np.array([0.9, 0.9, 0.9])
    # COLOR_NOTES_FACE = ['#9ed1a5', '#9fd3ba', '#a1d6d0', '#a3cad8']
    # COLOR_NOTES_FACE = [plt.get_cmap('tab20')(x) for x in range(20)]
    COLOR_NOTES_FACE = ColorPalette([
        plt.get_cmap('tab20')(x) for x in [5, 1, 3, 9, 17, 15]
        ])
    # COLOR_NOTES_FACE = [plt.get_cmap('tab20')(x) for x in [4, 0, 2, 8, 16, 14]]
    COLOR_NOTE_EDGE = np.array([*COLOR_BG, 0.9])
    COLOR_TICK = np.array([0.9, 0.9, 0.9])
    COLOR_GRID_MAJOR = np.array([0.8, 0.8, 0.8])
    COLOR_GRID_MINOR = np.array([0.6, 0.6, 0.6])
    COLOR_TIME_LINE = np.array([0.1, 0.5, 0.7])
