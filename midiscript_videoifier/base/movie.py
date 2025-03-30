import numpy as np
import moviepy as me
import melody_machine as mm
from .components import Paragraph, MidiPattern
from pathlib import Path
from typing import Union, Literal
from moviepy.Clip import Clip
from moviepy import VideoClip, CompositeAudioClip
from moviepy.tools import compute_position
from ..utils import layer_mix

from ..configs.default import CONFIG, COLOR


class Movie():
    '''
    最终成型的视频类
    '''

    def __init__(
            self,
            song: mm.Song,
            BeginTime: int = None,
            CountDown: int = None,
            InitBar: int = None,
            Title: str = None,
            Saying: str = None,
            Name: str = None,
            FontPath: str = None,
            h: int = None,
            w: int = None,
            spb: int = None,
            bpB: int = None,
            bpM: int = None,
            tpb: int = None,
            subclip_tBar: list[float] = None,
            subclip_tMov: list[float] = None,
            audio_fp: Union[str, Path] = None,
            **kwds
        ) -> None:
        self.song = song
        self.visualizer = song.visualizer
        self.arr_clip: list[Clip] = []
        self.h = h or CONFIG.h
        self.w = w or CONFIG.w
        self.bpB = bpB or CONFIG.bpB
        self.BeginTime = BeginTime or CONFIG.BeginTime
        self.CountDown = CountDown or CONFIG.CountDown
        self.InitBar = InitBar or CONFIG.InitBar
        self.Title = Title or CONFIG.Title
        self.Saying = Saying or CONFIG.Saying
        self.Name = Name or CONFIG.Name
        self.FontPath = FontPath or CONFIG.FontPath
        self.subclip_tBar = subclip_tBar or CONFIG.subclip_tBar
        self.subclip_tMov = subclip_tMov or CONFIG.subclip_tMov
        if None is not audio_fp:
            self.audio = me.AudioFileClip(audio_fp)
        else:
            self.audio = None
        for k, v in kwds.items():
            if k in self.__dict__:
                self.__dict__[k] = v

    @property
    def duration(self):
        if None is not self.audio:
            duration = self.audio.duration + self.BeginTime
        else:
            duration = 0
            for clip in self.arr_clip:
                duration = max(duration, clip.end)
        return duration

    def generate_movie(
            self,
            subclip_tBar: list[float] = None,
            subclip_tMov: list[float] = None
        ):
        comp_vc = CompositeClip(self.arr_clip, size=(self.w, self.h))
        subclip_tBar = subclip_tBar or self.subclip_tBar
        subclip_tMov = subclip_tMov or self.subclip_tMov
        if None is not subclip_tBar:
            comp_vc = comp_vc.subclipped(
                self.visualizer.timeBar2Mov(subclip_tBar[0]),
                self.visualizer.timeBar2Mov(subclip_tBar[1])
                )
        elif None is not subclip_tMov:
            comp_vc = comp_vc.subclipped(
                subclip_tMov[0],
                subclip_tMov[1],
                )
        return comp_vc

    def make_section_Background(self):
        '''
        设置背景，在最后再追加背景，否则时间不正确
        '''
        vc_bg = me.ImageClip(
            (np.ones((self.h, self.w, 3)) * COLOR.COLOR_BG
                * 255).astype(np.int8)
            )
        if self.duration < self.BeginTime:
            print(
                "Warning: Background duration is shorter than BeginTime."
                )
        vc_bg: me.ImageClip = vc_bg.with_duration(self.duration
                                                 ).with_layer_index(-1)
        if self.audio is not None:
            self.audio = self.audio.with_start(self.BeginTime)
            vc_bg = vc_bg.with_audio(self.audio)
        self.arr_clip.insert(0, vc_bg)

    def make_section_Title(self):
        '''
        生成开头
        '''
        if (None is self.Title) or ('omit' == self.Title.lower()):
            # 跳过开头
            return
        tc_title = me.TextClip(
            text=self.Title,
            color='#EAEAEA',
            font=self.FontPath,
            font_size=96,
            text_align='center',  # margin=(0, 9.6),
            )
        tc_title: me.TextClip = tc_title.with_position(('center', 0.27),
                                                        relative=True)
        tc_title: me.TextClip = tc_title.with_duration(
            self.song.visualizer.spanBar2True(1) + self.BeginTime
            )
        self.arr_clip.append(tc_title)

        if (None is self.Saying) or ('omit' == self.Saying.lower()):
            # 跳过格言
            return
        tc_saying = me.TextClip(
            text=self.Saying,
            color='#C1C1C1',
            font=self.FontPath,
            font_size=48,
            text_align='center',  # margin=(0, 4.8),
            )
        tc_saying: me.TextClip = tc_saying.with_position(('center', 0.64),
                                                            relative=True)
        tc_saying: me.TextClip = tc_saying.with_duration(
            self.song.visualizer.spanBar2True((self.bpB - self.CountDown)
                                                / self.bpB)
            + self.BeginTime
            )
        self.arr_clip.append(tc_saying)

        tc_name = me.TextClip(
            text=self.Name,
            color='#C1C1C1',
            font=self.FontPath,
            font_size=48,
            text_align='center',  # margin=(0, 4.8),
            )
        tc_name: me.TextClip = tc_name.with_position((0.65, 0.75),
                                                        relative=True)
        tc_name: me.TextClip = tc_name.with_duration(
            self.song.visualizer.spanBar2True((self.bpB - self.CountDown)
                                                / self.bpB)
            + self.BeginTime
            )
        self.arr_clip.append(tc_name)

    def make_section_CountDown(self):
        '''
        设置倒计时
        '''
        tc_circle = me.TextClip(
            text='●',
            color='#222222',
            font=self.FontPath,
            font_size=400,
            text_align='center',  # margin=(400 * 0.1, 400 * 0.1)
            ).with_position(
                ('center', 0.404), relative=True
                ).with_duration(
                    self.visualizer.spanBar2True(
                        self.CountDown / self.bpB
                        )
                    ).with_start(
                        self.visualizer
                        .timeBar2Mov((self.bpB - self.CountDown) / self.bpB
                                        + self.InitBar)
                        )
        self.arr_clip.append(tc_circle)
        for i in range(self.CountDown, 0, -1):
            tc_count_down = me.TextClip(
                text=f'{i}',
                color='#CCCCCC',
                font=self.FontPath,
                font_size=106,
                text_align='center',  # margin=(106 * 0.1, 106 * 0.1)
                ).with_position(
                    ('center', 0.575), relative=True
                    ).with_duration(
                        self.visualizer.spanBar2True(1 / self.bpB)
                        ).with_start(
                            self.visualizer.timeBar2Mov((self.bpB - i)
                                                        / self.bpB
                                                        + self.InitBar)
                            )
            self.arr_clip.append(tc_count_down)

    def make_section_Midi(self, midi_patterns: list[MidiPattern]):
        for mp in midi_patterns:
            print(f'processing MidiPattern {mp.range}\n{mp.channels}\n')
            self.visualizer.channel_alt_name = mp.channels
            vc_mid = self.song[
                mp.range[0]:mp.range[1],
                list(mp.channels.keys()),
                ].generate_clip(mp.disp_range)
            vc_mid = vc_mid.with_position(
                (0.095, 0.47), relative=True
                ).with_duration(
                    self.visualizer
                    .spanBar2True(mp.disp_range[1] - mp.disp_range[0])
                    ).with_start(
                        self.visualizer.timeBar2Mov(mp.disp_range[0])
                        )
            self.arr_clip.append(vc_mid)

    def make_section_Para(self, paragraphs: list[Paragraph]):
        for paragraph in paragraphs:
            tc_anno = me.TextClip(
                text=paragraph.text,
                color='#EAEAEA',
                font=self.FontPath,
                font_size=64,
                # size = (1664, 940),
                text_align='left',
                interline=64 * 0.3,  # margin=(0,64*0.18),
                ).with_position(
                    (0.115, 0.13),
                    relative=True,
                    ).with_duration(
                        self.visualizer.spanBar2True(
                            paragraph.range[1] - paragraph.range[0]
                            )
                        ).with_start(
                            self.visualizer.timeBar2Mov(
                                paragraph.range[0]
                                )
                            )
            self.arr_clip.append(tc_anno)
            # print(f'processing Paragraph {paragraph.range}\n{paragraph.text}\n\n')
            print(f'processing Paragraph {paragraph}\n')


class CompositeClip(VideoClip):
    """
    Parameters
    ----------
    size
        The size (width, height) of the final clip.
    clips
        A list of videoclips.
  
        Clips with a higher ``layer`` attribute will be displayed
        on top of other clips in a lower layer.
        If two or more clips share the same ``layer``,
        then the one appearing latest in ``clips`` will be displayed
        on top (i.e. it has the higher layer).
  
        For each clip:
  
        - The attribute ``pos`` determines where the clip is placed.
            See ``VideoClip.set_pos``
        - The mask of the clip determines which parts are visible.
  
        Finally, if all the clips in the list have their ``duration``
        attribute set, then the duration of the composite video clip
        is computed automatically
    is_use_first_clip_as_bg_clip
        Set to True if the first clip in the list should be used as the
        'background' on which all other clips are blitted. That first clip must
        have the same size as the final clip. If it has no transparency, the final
        clip will have no mask.

    The clip with the highest FPS will be the FPS of the composite clip.
    """

    def __init__(
            self,
            clips: list[VideoClip],
            size: tuple[int, int] = None,
            is_use_first_clip_as_bg_clip=True,
            bg_clip: VideoClip = None,
            bg_color: tuple[float] = (0, 0, 0, 0),
            BeginTime: float = 0,
            **kwds
        ):
        super().__init__()
        clips = sorted(clips, key=lambda clip: clip.layer_index)
        self.size = size or clips[0].size
        fpss = [clip.fps for clip in clips if getattr(clip, "fps", None)]
        # compute duration
        ends = [clip.end for clip in clips]
        if None not in ends:
            duration = max(ends)
            self.duration = duration
            self.end = duration

        if is_use_first_clip_as_bg_clip:
            bg_clip = clips[0]
            self.clips = clips[1:]
        elif None is bg_clip:
            bg_clip = me.ImageClip(
                np.zeros([size[1], size[0], 4]) + np.array(bg_color),
                duration=self.duration
                )
            self.clips = clips
        else:
            raise LookupError("No background clip is assigned.")
        self.fps = max(fpss) if fpss else None
        # order self.clips by layer
        self.bg = bg_clip

        # compute audio
        audioclips = [v.audio for v in clips if v.audio is not None]
        if audioclips:
            self.audio = CompositeAudioClip(audioclips)

        self.BeginTime = BeginTime

    def frame_function(self, t):
        """The clips playing at time `t` are blitted over one another."""
        # Try doing clip merging with pillow
        bg_t = t - self.bg.start
        bg_frame: np.ndarray = self.bg.get_frame(bg_t).astype("uint8")

        # For each clip apply on top of current img
        current_frame = bg_frame
        for clip in self.playing_clips(t):
            clip: VideoClip
            clip_t = t - clip.start
            fg: np.ndarray = clip.get_frame(clip_t)
            if clip.mask:
                fg = np.dstack([
                    fg, clip.mask.get_frame(clip_t)[:, :, None] * 255
                    ])
            (x1, y1) = compute_position(
                clip.size,
                self.size,
                pos=clip.pos(clip_t),
                relative=clip.relative_pos
                )
            w = min(clip.size[0], self.size[0] - x1)
            h = min(clip.size[1], self.size[1] - y1)
            x2 = x1 + w
            y2 = y1 + h
            fg = fg[0:h, 0:w]
            bg = current_frame[y1:y2, x1:x2]
            current_frame[y1:y2, x1:x2] = layer_mix(bg, fg)

        frame = current_frame

        if frame.shape[2] == 4:
            return frame[:, :, :3]

        return frame

    def playing_clips(self, t=0):
        """Returns a list of the clips in the composite clips that are
        actually playing at the given time `t`.
        """
        return [clip for clip in self.clips if clip.is_playing(t)]

    def close(self):
        """Closes the instance, releasing all the resources."""
        if self.created_bg and self.bg:
            # Only close the background clip if it was locally created.
            # Otherwise, it remains the job of whoever created it.
            self.bg.close()
            self.bg = None
        if hasattr(self, "audio") and self.audio:
            self.audio.close()
            self.audio = None
