import sys
from re import findall, split
from .components import Paragraph, MidiPattern
from typing import Union, Literal
from pathlib import Path
from ..utils import find_library_path, load_from_config

DEFAULT_CONFIG_PATH = find_library_path(
    'midiscript_videoifier'
    ) / 'configs' / 'default.py'


class Script():
    '''
    记录了所有手稿中信息的类
    '''

    def __init__(
            self,
            data: str = None,
            file_path: str = None,
            config: Union[str, dict, Path] = DEFAULT_CONFIG_PATH
        ) -> None:
        '''
        Parameters
        ---
        data:
            - 读取好的字符串
        file_path:
            - 文件路径
        '''
        if isinstance(config, str):
            config = Path(config)
        if isinstance(config, Path):
            cfg = load_from_config(config)['CONFIG']
            session_data = {
                k: v
                for k, v in cfg.__dict__.items() if not k.startswith('__')
                }
        elif isinstance(config, dict):
            session_data = config

        print(
            # f"Loading Chord DB from {(library_path / 'chord_db.csv').absolute()}"
            f'''Loading Config from "{DEFAULT_CONFIG_PATH}"'''
            )
        self.session_data = session_data
        # self.session_data = {
        #     'StartBar': 5,  # .flp工程中的音频实际起始小节号
        #     'InitBar': 1,  # 视频中的起始记数小节号
        #     'BeginTime': 1,  # 开幕大标题的显示时长（秒）
        #     'CountDown': 3,  # 倒计时个数
        #     'Title': '',  # 开幕大标题文本
        #     'Saying': '',  # 开幕格言文本
        #     'Name': '—— Gray Frezicical',  # 落款
        #     'h': 1080,  # 视频的高度（像素）
        #     'w': 2160,  # 视频的宽度（像素）
        #     'FontPath':  # 字体路径  \
        #     'C:/Users/Gray/AppData/Local/Microsoft/Windows/Fonts/sarasa-mono-sc-regular.ttf',
        #     'spb': 4,  # steps per beat
        #     'bpB': 4,  # beats per Bar
        #     'bpM': 120,  # beats per Minutes
        #     'tpb': 96,  # ticks per beat / timebase
        #     'pitch_clip_range': [33, 93],  # 全局音符音高范围[A2,A7]
        #     'expand_range': [4, 4],  # 音高上下拓展显示范围
        #     'min_pitch_range': [10, 10],  # 音高上下最小范围
        #     'subclip_tBar': None,  # 输出视频的裁剪范围（小节）
        #     'subclip_tMov': None,  # 输出视频的裁剪范围（秒）
        #     }
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
            elif (s.startswith('//')  # 通用注释行
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
