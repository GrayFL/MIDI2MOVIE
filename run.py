from midiscript_videoifier import *
import melody_machine as mm
from pathlib import Path
import sys

if __name__ == '__main__':
    args = sys.argv
    fp = args[-1]
    fp = Path(fp)
    script = Script(file_path=fp)
    # midi_fp = script.session_data['midi_fp']
    # audio_fp = script.session_data['audio_fp']
    output_fp = fp.parent / (fp.stem + '.mp4')
    output_fp = script.session_data.get('output_fp', output_fp)
    song = mm.Song(script.session_data['midi_fp'], **script.session_data)
    mov = Movie(song=song, **script.session_data)
    print(mov.__dict__)
    mov.arr_clip.clear()
    mov.make_section_Title()
    mov.make_section_CountDown()
    mov.make_section_Para(script.paragraphs)
    mov.make_section_Midi(script.midi_patterns)
    mov.make_section_Background()
    comp_vc = mov.generate_movie()
    comp_vc.write_videofile(
        output_fp,
        audio_bitrate='192k',
        fps=60,
        threads=6,
        codec='h264_nvenc',
        bitrate=f'{12000}k',
        preset='p7',
        )
