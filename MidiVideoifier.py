import sys
from re import findall, split
from collections import deque
import mido
import numpy as np
import moviepy.editor as me
import matplotlib.pyplot as plt

plt.rcParams['font.family'] = 'Sarasa Mono SC'
plt.rcParams['font.size'] = 10.5  # 10.5pt 五号字；9pt 小五号字
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['figure.subplot.left'] = 0.11  #0.05
plt.rcParams['figure.subplot.right'] = 0.89  #0.98
plt.rcParams['figure.subplot.bottom'] = 0.15  #0.1
plt.rcParams['figure.subplot.top'] = 0.91  #0.93
plt.rcParams['figure.facecolor'] = (1, 1, 1, 0)
plt.rcParams['figure.dpi'] = 300
plt.rcParams['axes.facecolor'] = (1, 1, 1, 0)
plt.rcParams['axes.titlesize'] = 'medium'
plt.rcParams['legend.fontsize'] = 'medium'
plt.rcParams['interactive'] = 'False'


# region Paragraph
class Paragraph():
    '''
    段落文本类
    '''

    def __init__(
        self,
        para_range: list[float],
        text: str = '',
        ) -> None:
        '''
        Parameters
        ---
        Para_range:
            - 文本段落的持续范围，其计量单位是小节时间 `tBar`  
            形如 [1, 5] ，表示小节时间1到5的范围，长度为4
        text:
            - 文本内容。支持换行符
        '''
        self.range = para_range
        self.text = text

    def __repr__(self) -> str:
        _s_range = f' {self.range} '
        _s = f'''
|== Paragraph {_s_range:=>36}==|
{self.text}


|---------------------------------------------------|
'''
        return _s

    # endregion


# region MidiPattern
class MidiPattern():
    '''
    Midi段落类
    '''

    def __init__(
            self,
            midi_range: list[float],
            channels: dict = {},
            para_range: list[float] = None,
            pitch_clip_range: list[float] = None
        ) -> None:
        '''
        Parameters
        ---
        midi_range:
            - Midi段落的持续范围，其计量单位是小节时间 `tBar`  
            形如 [1, 5] ，表示小节时间1到5的范围，长度为4
        channels:
            - 选择的乐器轨道  
            形如 {'str vln #1': 'Violin I'}  
            前者为Midi文件中的命名，后者为显示时的替换名称
        para_range:
            - 该Midi段落所关联的文本段落的**总**范围
        pitch_clip_range:
            - 该Midi段落的音高最大范围（选择音符时会过滤掉超出该范围的音高，但不代表最终的显示范围）
        
        Properties
        ---
        disp_range:
            - 该Midi段落的总显示范围，即汇总后的para_range
        mtracks:
            - 该Midi段落所包含的所有音符，且按轨道名称分类
        '''
        self.range = midi_range
        self.channels = channels
        self.disp_range = para_range
        self.pitch_clip_range = pitch_clip_range
        self.mtracks: dict[str, np.ndarray] = None
        self.pitch_range: list[float] = None

    def get_div_id(self) -> str:
        '''
        生成用于唯一化标识Midi段落的字符串ID
        '''
        return f'{self.range}{self.channels}'

    def update_disp_range(self, para_range: list[float]):
        '''
        更新Midi段落的显示范围（取外边界）
        '''
        if para_range[1] > self.disp_range[1]:
            self.disp_range[1] = para_range[1]
        if para_range[0] < self.disp_range[0]:
            self.disp_range[0] = para_range[0]

    def __repr__(self) -> str:
        _s = f'''
== MidiPattern =====================================
range           : {self.range}
disp_range      : {self.disp_range}
channels        : {self.channels}
pitch_clip_range: {self.pitch_clip_range}
pitch_range     : {self.pitch_range}
mtracks         :
{self.mtracks}
'''
        return _s

    # endregion


# region Script
class Script():
    '''
    记录了所有手稿中信息的类
    '''

    def __init__(self, data: str = None, file_path: str = None) -> None:
        '''
        Parameters
        ---
        data:
            - 读取好的字符串
        file_path:
            - 文件路径
        '''
        self.session_data = {
            'StartBar': 5,  # .flp工程中的音频实际起始小节号
            'InitBar': 1,  # 视频中的起始记数小节号
            'BeginTime': 1,  # 开幕大标题的显示时长（秒）
            'CountDown': 3,  # 倒计时个数
            'Title': '',  # 开幕大标题文本
            'Saying': '',  # 开幕格言文本
            'Name': '—— Gray Frezicical',  # 落款
            'h': 1080,  # 视频的高度（像素）
            'w': 2160,  # 视频的宽度（像素）
            'FontPath':  # 字体路径  \
            'C:/Users/Gray/AppData/Local/Microsoft/Windows/Fonts/sarasa-mono-sc-regular.ttf',
            'spb': 4,  # steps per beat
            'bpB': 4,  # beats per Bar
            'bpM': 120,  # beats per Minutes
            'tpb': 96,  # ticks per beat / timebase
            'pitch_clip_range': [33, 93],  # 全局音符音高范围[A2,A7]
            'expand_range': [4, 4],  # 音高上下拓展显示范围
            'min_pitch_range': [10, 10],  # 音高上下最小范围
            'subclip_tBar': None,  # 输出视频的裁剪范围（小节）
            'subclip_tMov': None,  # 输出视频的裁剪范围（秒）
            }
        self.paragraphs: list[Paragraph] = [Paragraph([0, 0])]
        self.midi_patterns: list[MidiPattern] = [MidiPattern([0, 0])]
        # 因为 `same` 关键字允许手稿复制上一段文本，
        # 故放入一个初始段落防止报错
        self.label_count = {}
        # 记录每个符号的数量
        # 目前还没有开发相关功能

        if None is data:  # data为空
            with open(file_path, encoding='utf-8') as f:
                data = f.read()
        self._parse_data(data)

        if len(self.session_data['Title']) == 0:
            self.session_data['BeginTime'] = 0

    def _parse_data(self, data: str):
        '''
        解析手稿原始数据  
        !Warning 该函数按行解析，且只能解析一层的内容  
        手稿应按 前言 -> 正文1 -> 正文2 的方式组织
        '''

        def pop_stack(ASL: list, stack: list):
            '''
            若stack存入了数据，则将整个stack复制追加到ASL中
            '''
            if len(stack) > 0:  # stack有内容
                ASL.append(stack.copy())
            stack.clear()
            # 因为采用clear没有更改stack的指针所以前面要用copy

        ASL, stack = [], []  # 抽象语法列表, 临时队列
        midi_pattern_pool: set[str] = set()  # Midi段落登记表
        cur_div = None  # 当前行所处文本范围
        # ↓ 按行扫描数据
        for s in split('\n+', data) + [None]:
            # 按行分割并增加结束符 `None`
            # 行分割方式会去除任意长度的换行符
            # 空白行请使用空白字符占位
            if s is None:  # 到达数据末尾
                pop_stack(ASL, stack)  # 将文末前的内容追加到ASL中
                break
            if s.startswith('---'):
                if cur_div is None:
                    cur_div = '---'  # 进入前言div
                    self.count_label('---')
                    pop_stack(ASL, stack)
                    continue
                else:
                    cur_div = None  # 离开前言div
                    pop_stack(ASL, stack)  # 追加前言的内容
                    continue
            elif (
                s.startswith('//')  # 通用注释行
                or (cur_div == '---' and s.startswith('#'))  # 前言注释行
                ):
                continue
            elif s.startswith('# '):  # 标题行
                cur_div = '#'  # 进入正文段落div
                self.count_label('#')
                pop_stack(ASL, stack)
            stack.append(s)  # 记录当前div内的内容
        # ↓ 对ASL进行处理处理
        self.session_data = self._init_front_matter(ASL[0])  # 前言
        StartBar = self.session_data['StartBar']  # 音频起始小节
        InitBar = self.session_data['InitBar']  # 视频显示起始小节
        for items in ASL[1:]:
            meta: list[str] = findall('(?:`(.*?)`)+', items[0])
            # ↑ 每个文本段的控制字形如 `ctrl` ，按顺序截取所有控制字
            if len(meta) == 0:
                raise RuntimeError('该段落没有设置起止时间')
            # == 文本时间范围分析
            if '+' in meta[0]:  # 相对时间控制，基于上一段落追加
                acc = findall('\s*(\d+\.*\d*)\s*', meta[0])[0]
                A = self.paragraphs[-1].range[1]
                B = A + float(acc)
            else:  # 绝对时间控制，提取任何由`,`或`~`凑对的两个数
                A, B = findall(
                    '(\d+\.*\d*)\s*[,~]\s*(\d+\.*\d*)', meta[0]
                    )[0]
                A = float(A) - StartBar + InitBar
                B = float(B) - StartBar + InitBar
            para_range = [A, B]  # 该范围单位是**小节时间tBar**
            text = '\n'.join(items[1:])  # 生成文本段的文本
            self.paragraphs.append(
                Paragraph(
                    para_range=para_range.copy(),
                    # ↑ 后面可能会被midi_range改变，因此采用copy
                    text=text,
                    )
                )

            # == MIDI块属性分析
            midi_range = para_range  # 默认情况下Midi范围就是段落范围
            channels = {}  # 选取的Midi轨道
            ctrls = {}  # 其他参数
            if len(meta) == 1:  # 该段落仅有文本控制字
                continue
            if len(meta) >= 2:  # 该段落选取了Midi轨道
                if meta[1].lower() in ['keep', 'same']:
                    channels = self.midi_patterns[-1].channels
                elif meta[1].lower() in ['all']:
                    channels = {'all': None}
                else:
                    for s_item in split('\s*[;,]\s*', meta[1]):
                        # ↑ 按`;`和`,`拆分值
                        if ':' in s_item:  # 使用了替换名
                            k, v = findall(
                                '^\s*(.+?)\s*:\s*(.+?)\s*$', s_item
                                )[0]
                            channels[k] = v
                        else:  # 未使用替换名，但是仍会以原名存为字典形式
                            k = findall('^\s*(.+?)\s*$', s_item)[0]
                            channels[k] = k
            # 第3个控制字可以是midi范围或是其他参数
            # ↓ 控制字总数大于等于3时，若第二位不是`!`开头的其他参数，
            # ↓ 那么必然只有3位，meta[2]就是midi范围
            if len(meta) >= 3 and not meta[2].startswith('!'):
                if meta[2].lower() in ['keep', 'same']:
                    midi_range = self.midi_patterns[-1].range
                else:  # 绝对时间控制，提取任何由`,`或`~`凑对的两个数
                    A, B = findall(
                        '(\d+\.*\d*)\s*[,~]\s*(\d+\.*\d*)', meta[2]
                        )[0]
                    A = float(A) - StartBar + InitBar
                    B = float(B) - StartBar + InitBar
                    midi_range = [A, B]
            # ↓ 控制字总数大于等于3时，若meta最后一位是`!`开头的其他参数，
            # ↓ 不论最终有几位，meta[-1]就是其他参数
            if len(meta) >= 3 and meta[-1].startswith('!'):
                ctrls = self._parse_other_control(meta[-1])
            mp_div_id = f'{midi_range}{channels}'  # 生成Midi段落的唯一标识符
            # ↓ 当且仅当该Midi段落是第一次出现，则新建一个到队列中
            if mp_div_id not in midi_pattern_pool:
                midi_pattern_pool.add(mp_div_id)
                self.midi_patterns.append(
                    MidiPattern(
                        midi_range=midi_range,
                        channels=channels,
                        para_range=para_range.copy(),
                        **ctrls
                        )
                    )
            # ↓ 否则说明有别的文本也采用了相同的Midi段落，那么就更新显示范围
            else:
                self.midi_patterns[-1].update_disp_range(para_range)
        # 弹出初始化时增加的占位段落
        self.paragraphs.pop(0)
        self.midi_patterns.pop(0)

    def _init_front_matter(self, items: list[str]):
        '''
        处理前言中的键值对  
        !Warning 值录入采用eval方式，存在安全隐患  
        或许可以采用json来解析
        '''
        for s_item in items:
            k, v = findall('^(.+?)\s*:\s*(.+)$', s_item)[0]
            self.session_data[k] = eval(v)
        return self.session_data

    def _parse_other_control(self, s_items: str):
        '''
        处理控制字的其他参数 
        !Warning 值录入采用eval方式，存在安全隐患  
        或许可以采用json来解析
        '''
        ctrls = {}
        items = findall(
            '!\s*([^=]+?)\s*=\s*([^!]+?)\s*(?=\s*!|$)', s_items
            )
        for k, v in items:
            ctrls[k] = eval(v)
        return ctrls

    def count_label(self, label):
        if label in self.label_count:
            self.label_count[label] += 1
        else:
            self.label_count[label] = 1

    # endregion


# region Movie
class Movie():
    '''
    最终成型的视频类
    '''

    def __init__(
            self,
            midivisualizer: "MidiVisualizer",
            audio_fp: str = None,
            **kwds
        ) -> None:
        self.MV: MidiVisualizer = midivisualizer
        self.audio = None
        self.arr_clip = []
        self.h = 1080
        self.w = 2160
        self.BeginTime = 1
        self.CountDown = 3
        self.InitBar = 1
        self.bpB = 4
        self.Title = ''
        self.Saying = ''
        self.Name = '—— Gray Frezicical'
        self.FontPath = 'C:/Users/Gray/AppData/Local/Microsoft/Windows/Fonts/sarasa-mono-sc-regular.ttf'
        self.movie_length = None

        if None is not audio_fp:
            self.audio = me.AudioFileClip(audio_fp)
        else:
            self.audio: me.AudioFileClip = None
        for k, v in kwds.items():
            if k in self.__dict__:
                self.__dict__[k] = v
        if self.audio is None:
            self.movie_length = 4 * 60 + self.BeginTime
        else:
            self.movie_length = self.audio.duration + self.BeginTime

    # yapf: disable
    def make_section_Background(self):
        '''
        设置背景
        '''
        vc_bg = me.ImageClip(
            np.ones((self.h, self.w, 3)) * MidiVisualizer.COLOR_BG * 255
            )
        vc_bg: me.ImageClip = vc_bg.set_duration(self.movie_length)
        if self.audio is not None:
            self.audio = self.audio.set_start(self.MV.BeginTime)
            vc_bg = vc_bg.set_audio(self.audio)
        self.arr_clip.append(vc_bg)

    def make_section_Title(self):
        '''
        设置开头
        '''
        if (len(self.Title) == 0) or (self.Title.lower() == 'omit'):
            # 跳过开头
            return
        tc_title = me.TextClip(
            self.Title,
            color='#EAEAEA',
            font=self.FontPath,
            fontsize=96,
            align='center',
            )
        tc_title: me.TextClip = tc_title.set_position(
            ('center', 0.3), relative=True)
        tc_title: me.TextClip = tc_title.set_duration(
            self.MV.spanBar2True(1)+self.BeginTime)
        self.arr_clip.append(tc_title)

        if (len(self.Saying)== 0) or (self.Title.lower() == 'omit'):
            # 跳过格言
            return
        tc_saying = me.TextClip(
            self.Saying,
            color='#C1C1C1',
            font=self.FontPath,
            fontsize=48,
            align='center',
            )
        tc_saying: me.TextClip = tc_saying.set_position(
            ('center', 0.67),relative=True)
        tc_saying: me.TextClip = tc_saying.set_duration(
            self.MV.spanBar2True(
                (self.bpB-self.CountDown)/self.bpB)+self.BeginTime)
        self.arr_clip.append(tc_saying)

        tc_name = me.TextClip(
            self.Name,
            color='#C1C1C1',
            font=self.FontPath,
            fontsize=48,
            align='center',
            )
        tc_name: me.TextClip = tc_name.set_position(
            (0.65, 0.8),relative=True)
        tc_name: me.TextClip = tc_name.set_duration(
            self.MV.spanBar2True(
                (self.bpB-self.CountDown)/self.bpB)+self.BeginTime)
        self.arr_clip.append(tc_name)

    def make_section_CountDown(self):
        '''
        设置倒计时
        '''
        tc_circle = me.TextClip(
            '●',
            color = '#222222',
            font = self.FontPath,
            fontsize = 400,
            align='center',
            ).set_position(
                ('center',0.4),relative=True
            ).set_duration(
                self.MV.spanBar2True(self.CountDown/self.bpB)
            ).set_start(
                self.MV.timeBar2Mov(
                    (self.bpB - self.CountDown) / self.bpB + self.InitBar))
        self.arr_clip.append(tc_circle)
        for i in range(self.CountDown,0,-1):
            tc_count_down = me.TextClip(
                f'{i}',
                color = '#CCCCCC',
                font = self.FontPath,
                fontsize = 106,
                align='center',
                ).set_position(
                    ('center',0.566),relative=True
                ).set_duration(
                    self.MV.spanBar2True(1/self.bpB)
                ).set_start(
                    self.MV.timeBar2Mov(
                        (self.bpB-i)/self.bpB+self.InitBar))
            self.arr_clip.append(tc_count_down)

    def make_section_Midi(self, midi_patterns:list[MidiPattern]):
        for midi_pattern in midi_patterns:
            print(f'processing MidiPattern {midi_pattern.range}\n{midi_pattern.channels}\n')
            self.MV.put_midi_data(midi_pattern)
            vc_mid = self.MV.get_video_clip_sytle_A(midi_pattern)
            vc_mid = vc_mid.set_position(
                (0.095,0.47),relative=True
                ).set_duration(
                    self.MV.spanBar2True(
                        midi_pattern.disp_range[1]-midi_pattern.disp_range[0])
                ).set_start(self.MV.timeBar2Mov(midi_pattern.disp_range[0]))
            self.arr_clip.append(vc_mid)

    def make_section_Midi_Style_B(self, midi_patterns:list[MidiPattern]):
        '''
        采用底图ImageClip加上滚动时间轴的方式
        '''
        for midi_pattern in midi_patterns:
            self.MV.put_midi_data(midi_pattern)
            frame = self.MV.get_fig_static(midi_pattern)
            vc_mid = me.ImageClip(frame
                ).set_position(
                    (0.095,0.47),relative=True
                ).set_duration(
                    self.MV.spanBar2True(
                        midi_pattern.disp_range[1]-midi_pattern.disp_range[0])
                ).set_start(self.MV.timeBar2Mov(midi_pattern.disp_range[0]))
            self.arr_clip.append(vc_mid)

            vc_timeline = self.MV.get_video_clip_sytle_B(
                midi_pattern
                ).set_position(
                    (0.095,0.47),relative=True
                ).set_duration(
                    self.MV.spanBar2True(
                        midi_pattern.disp_range[1]-midi_pattern.disp_range[0])
                ).set_start(self.MV.timeBar2Mov(midi_pattern.disp_range[0]))
            self.arr_clip.append(vc_mid)
            self.arr_clip.append(vc_timeline)

    def make_section_Para(self, paragraphs:list[Paragraph]):
        for paragraph in paragraphs:
            tc_anno = me.TextClip(
                paragraph.text,
                color = '#EAEAEA',
                font = self.FontPath,
                fontsize = 64,
                align='West',
                ).set_position(
                    (0.115,0.13),relative=True
                ).set_duration(
                    self.MV.spanBar2True(
                        paragraph.range[1]-paragraph.range[0])
                ).set_start(self.MV.timeBar2Mov(paragraph.range[0]))
            self.arr_clip.append(tc_anno)
            # print(f'processing Paragraph {paragraph.range}\n{paragraph.text}\n\n')
            print(f'processing Paragraph {paragraph}\n')
    # yapf: enable
    # endregion


# region MidiVisualizer
class MidiVisualizer():
    '''
    生成可视化的类
    '''
    # yapf: disable

    # 颜色
    COLOR_BG = np.array([49/255, 56/255, 62/255])
    COLOR_BLACK_KEY = np.array([0.23, 0.23, 0.23])
    COLOR_WHITE_KEY = np.array([0.9, 0.9, 0.9])
    COLOR_WHITE_C = np.array([0.75, 0.75, 0.75])
    COLOR_LIGHT_ROW = np.array([0.5, 0.5, 0.5, 0.1])
    COLOR_DARK_ROW = np.array([0.2, 0.2, 0.2, 0.0])
    COLOR_EDGE = np.array([0.5, 0.5, 0.5])
    COLOR_NOTE_FACE = np.array([0.9, 0.9, 0.9])
    # COLOR_NOTES_FACE = ['#9ed1a5', '#9fd3ba', '#a1d6d0', '#a3cad8']
    # COLOR_NOTES_FACE = [plt.get_cmap('tab20')(x) for x in range(20)]
    COLOR_NOTES_FACE = [plt.get_cmap('tab20')(x) for x in [5, 1, 3, 9, 17, 15]]
    # COLOR_NOTES_FACE = [plt.get_cmap('tab20')(x) for x in [4, 0, 2, 8, 16, 14]]
    COLOR_NOTE_EDGE = np.array([*COLOR_BG, 0.9])
    COLOR_TICK = np.array([0.9, 0.9, 0.9])
    COLOR_GRID_MAJOR = np.array([0.8, 0.8, 0.8])
    COLOR_GRID_MINOR = np.array([0.6, 0.6, 0.6])
    COLOR_TIME_LINE = np.array([0.1, 0.5, 0.7])

    # 键盘位置
    KEYBOARD_BLACK = (
        np.tile(np.arange(2, 9) * 12,(5, 1)) + np.array([[1, 3, 6, 8, 10]]).T
        ).flatten('F')
    KEYBOARD_WHITE = (
        np.tile(np.arange(2, 9) * 12,(7, 1)) + np.array([[0, 2, 4, 5, 7, 9, 11]]).T
        ).flatten('F')
    KEYBOARD_WHITE_C2E = (
        np.tile(np.arange(2, 9) * 12, (1, 1)) + np.array([[2]]).T
        ).flatten('F')
    KEYBOARD_WHITE_F2B = (
        np.tile(np.arange(2, 9) * 12, (1, 1)) + np.array([[8]]).T
        ).flatten('F')
    KEYBOARD_WHITE_C = (
        np.tile(np.arange(2, 9) * 12, (1, 1)) + np.array([[0.25]]).T
        ).flatten('F')
    # yapf: enable

    def __init__(
            self,
            midifile: mido.MidiFile = None,
            midi_fp: str = None,
            **kwds
        ) -> None:
        self.mtracks: dict[str, np.ndarray] = {}
        self.spb = 4  # steps per beat
        self.bpB = 4  # beats per Bar
        self.bpM = 120  # beats per Minutes
        self.tpb = None  # ticks per beat / timebase
        self.BeginTime = 1
        self.InitBar = 1
        self.h = 1080
        self.w = 2160
        self.pitch_clip_range: list[float] = [33, 93]  # [A2,A7]
        self.expand_range: list[float] = [4, 4]
        self.min_pitch_range: list[float] = [10, 10]
        ## 从脚本文件中覆写参数
        if None is midifile:
            midifile = mido.MidiFile(midi_fp)
        for k, v in kwds.items():
            if k in self.__dict__:
                self.__dict__[k] = v
        ## 计算二级参数并处理Midi轨道
        self.tpb = midifile.ticks_per_beat
        self.spB = self.spb * self.bpB
        self.BpM = self.bpM / self.bpB
        self.step = self.tpb // 4  # Fl studio中可视的最小单位长度 24
        self.beat = self.step * self.spb
        self.Bar = self.beat * self.bpB
        self._parse_midifile(midifile)

        # 固有画布定义
        (
            self.fig,
            self.ax_bg,
            self.ax_fg,
            self.art_timeline,
            ) = MidiVisualizer._init_figure(self.h / 1080)

    def _parse_midifile(self, mid: mido.MidiFile):
        for trk in mid.tracks:
            trk: mido.MidiTrack
            msg: mido.MetaMessage = trk[0]
            if 'set_tempo' == msg.type:
                self.bpM = round(60 / msg.tempo * 1000000, 1)
            if 'track_name' == msg.type:
                mtrack = self.process_miditrack(trk)
                if mtrack is not None:  # 非None
                    self.mtracks[msg.name] = mtrack

    def process_miditrack(self, track: mido.MidiTrack):
        '''
        !Warning 手稿的时间戳建议按照FL的小节记数，即1,2,...  
        MidiPattern和Paragraph将统一采用这个计数法，因此在处理Midi事件的时间标记时，会统一 + InitBar 来匹配小节时间

        而对于显示时间，也默认从InitBar开始。详见InitBar定义
        '''
        t = 0  # tick time
        note_pool = {}
        mtrack = []
        for msg in track:
            t += msg.time
            if 'note_on' == msg.type:
                note_pool[msg.note] = [msg.velocity, t]
                # if msg.note in note_pool:
                #     [value, t_start] = note_pool.pop(msg.note)
                #     mtrack.append([
                #         msg.note,  # 音高
                #         value,  # 力度
                #         t_start,  # 开始时间
                #         t,  # 结束时间
                #         t - t_start,  # 持续长度
                #         ])
                # else:
                #     note_pool[msg.note] = [msg.velocity, t]
            elif 'note_off' == msg.type:
                if msg.note in note_pool:
                    [value, t_start] = note_pool.pop(msg.note)
                    mtrack.append([
                        msg.note,  # 音高
                        value,  # 力度
                        t_start,  # 开始时间
                        t,  # 结束时间
                        t - t_start,  # 持续长度
                        ])
        if len(mtrack) > 0:
            mtrack = np.array(mtrack, dtype=np.float32)
            mtrack[:, 2:5] = mtrack[:, 2:5] / self.Bar
            mtrack[:, 2:4] = mtrack[:, 2:4] + self.InitBar
            # 将开始和结束时间 + InitBar 以匹配手稿时间
            return mtrack
        else:
            return None

    @staticmethod
    def _init_figure(scale=1.0):
        '''
        Parameter
        ---
        scale:
            - 缩放系数，相对于2160x1080而言
        '''
        plt.close()
        fig = plt.figure(
            figsize=(6.4, 1.8),
            dpi=600 * 0.47 * scale,
            facecolor=MidiVisualizer.COLOR_BG,
            )
        ax_bg: plt.Axes = fig.add_axes([0, 0.1, 1, 0.9])
        ax_mask: plt.Axes = fig.add_axes([0, 0, 1, 0.1])
        ax_fg: plt.Axes = fig.add_axes([0.05, 0.1, 0.95, 0.9])
        ax_bg.set_xlim([0, 1])
        ax_bg.axis('off')
        [x.set_visible(False) for x in ax_mask.spines.values()]
        ax_mask.xaxis.set_visible(False)
        ax_mask.yaxis.set_visible(False)
        ax_mask.set_facecolor(MidiVisualizer.COLOR_BG)
        [x.set_visible(False) for x in ax_fg.spines.values()]
        ax_fg.yaxis.set_visible(False)
        # 绘制键盘
        ax_bg.barh(
            y=MidiVisualizer.KEYBOARD_WHITE_C2E,
            width=0.05,
            height=5,
            facecolor=MidiVisualizer.COLOR_WHITE_KEY,
            edgecolor=MidiVisualizer.COLOR_EDGE,
            linewidth=0.2,
            )
        ax_bg.barh(
            y=MidiVisualizer.KEYBOARD_WHITE_F2B,
            width=0.05,
            height=7,
            facecolor=MidiVisualizer.COLOR_WHITE_KEY,
            edgecolor=MidiVisualizer.COLOR_EDGE,
            linewidth=0.2,
            )
        ax_bg.barh(
            y=MidiVisualizer.KEYBOARD_WHITE_C,
            width=0.05,
            height=1.5,
            facecolor=MidiVisualizer.COLOR_WHITE_C,
            edgecolor=MidiVisualizer.COLOR_EDGE,
            linewidth=0.2,
            )
        ax_bg.barh(
            y=MidiVisualizer.KEYBOARD_BLACK,
            width=0.03,
            height=1,
            facecolor=MidiVisualizer.COLOR_BLACK_KEY
            )

        # 绘制背景栏
        ax_bg.barh(
            y=MidiVisualizer.KEYBOARD_WHITE,
            width=0.95,
            height=1,
            left=0.05,
            facecolor=MidiVisualizer.COLOR_LIGHT_ROW,
            )
        ax_bg.barh(
            y=MidiVisualizer.KEYBOARD_BLACK,
            width=0.95,
            height=1,
            left=0.05,
            facecolor=MidiVisualizer.COLOR_DARK_ROW,
            )

        # 绘制小节线
        ax_fg.xaxis.set_tick_params(
            which='both', colors=MidiVisualizer.COLOR_TICK, direction='in'
            )
        ## 设置minor=True表示设置次刻度
        ax_fg.grid(
            which='minor',
            c=MidiVisualizer.COLOR_GRID_MINOR,
            ls=':',
            lw=0.2
            )
        ax_fg.grid(
            which='major',
            c=MidiVisualizer.COLOR_GRID_MAJOR,
            ls='-',
            lw=0.2
            )

        # 设置时间线
        art_timeline, *_ = ax_fg.plot(
            [],
            [],
            color=MidiVisualizer.COLOR_TIME_LINE,
            zorder=3,
            )
        return fig, ax_bg, ax_fg, art_timeline

    def sub(
            self,
            range: list[float],
            channels: dict[str, str],
            pitch_clip_range: list[float] = None
        ):
        '''
        从完整的Midi中按起始位置裁剪片段

        Parameters
        ---
        range:
            - 选择的Bar时间范围
        pitch_clip_range:
            - 音符音高最大范围。默认: [A2,A7]
        '''
        sub_mtracks: dict[str, np.ndarray] = {}
        start, end = range
        # 若没有输入pitch_clip_range则采用全局的统一值
        low, high = self.pitch_clip_range if (
            pitch_clip_range is None
            ) else pitch_clip_range
        if 'all' in channels:
            chn = {}
            for k in self.mtracks.keys():
                chn[k] = k
            chn.update(channels)
        else:
            chn = channels
        for k in chn.keys():
            mtrack = self.mtracks[k]
            sub_mtracks[k] = mtrack[np.where((mtrack[:, 3] > start)
                                                & (mtrack[:, 2] < end)
                                                & (mtrack[:, 0] > low)
                                                & (mtrack[:, 0] < high))]
            # 音符的终点在范围起点后，音符的起点在范围终点前
        return sub_mtracks

    def timeBar2Trk(self, tBar: float):
        '''
        从Bar时间换算到音乐时间
        '''
        return (tBar - self.InitBar) / self.BpM * 60

    def timeTrk2Bar(self, tTrk: float):
        '''
        从音乐时间换算到Bar时间
        '''
        return tTrk / 60 * self.BpM + 1

    def timeBar2Mov(self, tBar: float):
        '''
        从Bar时间换算到视频时间
        '''
        return (tBar - self.InitBar) / self.BpM * 60 + self.BeginTime

    def timeMov2Bar(self, tMov: float):
        '''
        从视频时间换算到Bar时间
        '''
        return (tMov - self.BeginTime) / 60 * self.BpM + self.InitBar

    def spanBar2True(self, span_tBar: float):
        '''
        将Bar时间跨度换算到真实事件跨度
        '''
        return span_tBar / self.BpM * 60

    @staticmethod
    def get_disp_pitch_range(
            pitch_range: list[float],
            expand_range: list[float] = [4, 4],
            min_pitch_range: list[float] = [10, 10]
        ):
        '''
        用于获取显示的音符范围

        Parameters
        ---
        pitch_range:
            - 原始的音高范围
        expand_range:
            - 下上边界各自需要拓宽的范围
        min_pitch_range:
            - 最小的音高范围，分下半和上半
        '''
        p_range = [
            min([
                pitch_range[0] - expand_range[0],
                round(np.mean(pitch_range)) - min_pitch_range[0]
                ]),
            max([
                pitch_range[1] + expand_range[1],
                round(np.mean(pitch_range)) + min_pitch_range[1]
                ])
            ]
        return p_range

    def put_midi_data(
        self,
        midipattern: MidiPattern,
        ):
        '''
        给一个midipattern添加其指定范围的midi数据
        '''
        midipattern.mtracks = self.sub(
            midipattern.range, midipattern.channels,
            midipattern.pitch_clip_range
            )
        key_min, key_max = None, None  # C4
        for mtrack in midipattern.mtracks.values():
            min, max = mtrack[:, 0].min(), mtrack[:, 0].max()
            if key_min is None or min < key_min:
                key_min = min
            if key_max is None or max > key_max:
                key_max = max
        midipattern.pitch_range = [key_min, key_max]

    def make_fig_static(self, midipattern: MidiPattern):
        '''
        给输入的midipattern渲染一张完整的静态背景

        Return
        ---
        rgba shape[h,w,4]
        '''
        # 初始化
        self.ax_fg._children = []
        self.ax_fg.containers = []
        self.ax_fg._current_image = None
        # self.ax_fg.clear()
        # self.ax_fg.get_legend().remove()
        # self.ax_fg.legend_ = None
        ylim = MidiVisualizer.get_disp_pitch_range(
            midipattern.pitch_range, self.expand_range,
            self.min_pitch_range
            )
        xlim = midipattern.range
        self.ax_bg.set_ylim(ylim)
        self.ax_fg.set_ylim(ylim)
        self.ax_fg.set_xlim(xlim)
        # 虽然后面设置的小节线ticks会改变该范围，但不加xlim会导致更新不正常

        # 标记音符C
        for c in MidiVisualizer.KEYBOARD_WHITE_C:
            if ylim[0] < c < ylim[1]:
                self.ax_bg.text(
                    x=0.048,
                    y=c - 0.14,
                    s=f'C{c//12:.0f}',
                    fontsize=110 / (ylim[1] - ylim[0]),
                    va='center',
                    ha='right',
                    )

        # 小节线更新
        self.ax_fg.set_xticks(
            np.arange(np.floor(xlim[0]),
                        np.ceil(xlim[1]) + 1)
            )
        self.ax_fg.set_xticks(
            np.arange(
                np.floor(xlim[0]),
                np.ceil(xlim[1]) + 1, 1 / self.bpB
                ),
            minor=True
            )

        # 绘制音符
        for chn, (lbl,trk,) in \
            enumerate(midipattern.mtracks.items()):
            self.ax_fg.barh(
                y=trk[:, 0],
                width=trk[:, 4],
                height=1,
                left=trk[:, 2],
                facecolor=MidiVisualizer.COLOR_NOTES_FACE[chn],
                edgecolor=MidiVisualizer.COLOR_NOTE_EDGE,
                linewidth=0.3,
                label=midipattern.channels[lbl],
                zorder=3
                )
        # self.ax_fg.legend()
        self.fig.canvas.draw()

    def get_fig_static(self, midipattern: MidiPattern):
        self.make_fig_static(midipattern)
        frame = np.array(self.fig.canvas.buffer_rgba())
        return frame

    def make_fig(
            self, midipattern: MidiPattern, fig: plt.Figure,
            ax_bg: plt.Axes, ax_fg: plt.Axes
        ):
        '''
        给输入的midipattern渲染一张完整的静态背景

        Return
        ---
        rgba shape[h,w,4]
        '''
        # 初始化
        ax_fg._children = []
        ax_fg.containers = []
        # ax_fg.get_legend().remove()
        ax_fg.legend_ = None
        ylim = MidiVisualizer.get_disp_pitch_range(
            midipattern.pitch_range, self.expand_range,
            self.min_pitch_range
            )
        xlim = midipattern.range
        ax_bg.set_ylim(ylim)
        ax_fg.set_ylim(ylim)
        ax_fg.set_xlim(xlim)
        # 虽然后面设置的小节线ticks会改变该范围，但不加xlim会导致更新不正常

        # 标记音符C
        for c in MidiVisualizer.KEYBOARD_WHITE_C:
            if ylim[0] < c < ylim[1]:
                ax_bg.text(
                    x=0.048,
                    y=c,
                    s=f'C{c//12:.0f}',
                    fontsize=110 / (ylim[1] - ylim[0]),
                    va='center',
                    ha='right'
                    )

        # 小节线更新
        ax_fg.set_xticks(
            np.arange(np.floor(xlim[0]),
                        np.ceil(xlim[1]) + 1)
            )
        ax_fg.set_xticks(
            np.arange(
                np.floor(xlim[0]),
                np.ceil(xlim[1]) + 1, 1 / self.bpB
                ),
            minor=True
            )

        # 绘制音符
        for chn, (lbl,trk,) in \
            enumerate(midipattern.mtracks.items()):
            ax_fg.barh(
                y=trk[:, 0],
                width=trk[:, 4],
                height=1,
                left=trk[:, 2],
                facecolor=MidiVisualizer.COLOR_NOTES_FACE[chn],
                edgecolor=MidiVisualizer.COLOR_NOTE_EDGE,
                linewidth=0.3,
                label=midipattern.channels[lbl],
                zorder=3
                )
        # ax_fg.legend()
        # fig.canvas.draw()

    def get_video_clip_sytle_A(self, midipattern: MidiPattern):
        plt.close()
        fig, ax_bg, ax_fg, art_timeline = MidiVisualizer._init_figure(
            self.h / 1080
            )
        self.make_fig(midipattern, fig, ax_bg, ax_fg)
        xlim = midipattern.disp_range
        art_timeline, *_ = ax_fg.plot(
            [],
            [],
            color=MidiVisualizer.COLOR_TIME_LINE,
            zorder=3,
            )

        def makeFrame(t: float):
            t_bar = (t / 60) * self.BpM + xlim[0]
            art_timeline.set_data([t_bar, t_bar], [0, 102])
            fig.canvas.draw()
            frame = np.array(fig.canvas.buffer_rgba())
            return frame[:, :, :3]

        vc = me.VideoClip(
            makeFrame, duration=self.spanBar2True(xlim[1] - xlim[0])
            )
        return vc

    # def get_video_clip_sytle_S(self, midipattern: MidiPattern):
    #     # fig, ax_bg, ax_fg = MidiVisualizer._init_figure(self.h / 1080)
    #     fig, ax_bg, ax_fg, art_timeline\
    #         = self.fig, self.ax_bg, self.ax_fg, self.art_timeline
    #     self.make_fig(midipattern, fig, ax_bg, ax_fg)

    #     xlim = midipattern.disp_range

    #     def makeFrame(t: float):
    #         # 相关静态量初始化
    #         xlim = midipattern.disp_range
    #         # 时间线绘制
    #         t_bar = (t / 60) * self.BpM + xlim[0]
    #         art_timeline.set_data([t_bar, t_bar], [0, 102])
    #         fig.canvas.draw()
    #         frame = np.array(fig.canvas.buffer_rgba())
    #         return frame[:, :, :3]

    #     vc = me.VideoClip(
    #         makeFrame, duration=self.spanBar2True(xlim[1] - xlim[0])
    #         )
    #     return vc

    def get_video_clip_sytle_B(self, midipattern: MidiPattern):
        plt.close()
        # fig, ax_bg, ax_fg = MidiVisualizer._init_figure(self.h / 1080)
        fig = plt.figure(
            figsize=(6.4, 1.8),
            dpi=600 * 0.47,
            facecolor=(1, 1, 1, 0),
            )
        ax_fg: plt.Axes = fig.add_axes([0.05, 0.1, 0.95, 0.9])
        # self.make_fig(midipattern, fig, ax_bg, ax_fg)
        xlim = midipattern.disp_range
        ax_fg.set_ylim([0, 1])
        ax_fg.set_xlim(xlim)
        ax_fg.axis('off')
        art_timeline, *_ = ax_fg.plot(
            [],
            [],
            color=MidiVisualizer.COLOR_TIME_LINE,
            zorder=3,
            )

        def makeFrame(t: float):
            t_bar = (t / 60) * self.BpM + xlim[0]
            art_timeline.set_data([t_bar, t_bar], [0, 1])
            fig.canvas.draw()
            frame = np.array(fig.canvas.buffer_rgba())
            return frame[:, :, :3]

        vc = me.VideoClip(
            makeFrame,
            duration=self.spanBar2True(xlim[1] - xlim[0]),
            )
        return vc

    # endregion


# region self
if __name__ == '__main__':
    args = sys.argv
    fp = args[-1]
    print(args)
    script = Script(file_path=fp)
    # midi_fp = script.session_data['midi_fp']
    # audio_fp = script.session_data['audio_fp']
    output_fp = script.session_data['output_fp']
    mv = MidiVisualizer(**script.session_data)
    mov = Movie(mv, **script.session_data)
    print(mov.__dict__)
    mov.arr_clip.clear()
    mov.make_section_Background()
    mov.make_section_Title()
    mov.make_section_CountDown()
    mov.make_section_Para(script.paragraphs)
    mov.make_section_Midi(script.midi_patterns)
    comp_vc = me.CompositeVideoClip(mov.arr_clip, size=(mov.w, mov.h))
    if None is not script.session_data['subclip_tBar']:
        subclip_tBar = script.session_data['subclip_tBar']
        comp_vc = comp_vc.subclip(
            mv.timeBar2Mov(subclip_tBar[0]),
            mv.timeBar2Mov(subclip_tBar[1])
            )
    elif None is not script.session_data['subclip_tMov']:
        subclip_tMov = script.session_data['subclip_tMov']
        comp_vc = comp_vc.subclip(
            subclip_tMov[0],
            subclip_tMov[1],
            )
    comp_vc.write_videofile(
        output_fp,
        audio_bitrate='192k',
        fps=60,
        threads=12,
        codec='h264_nvenc',
        bitrate=f'{12000}k'
        )
    # endregion
