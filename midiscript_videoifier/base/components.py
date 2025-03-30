import numpy as np


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
