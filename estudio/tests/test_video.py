import io
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from video import converter

def png(w=16,h=16):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+b'\x70\x30\x90'*w)*h))+chunk(b'IEND',b'')

def archive(entries):
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        for name,data in entries:z.writestr(name,data)
    return buf.getvalue()

class VideoTests(unittest.TestCase):
    def test_rejects_paths_gaps_mismatched_sizes_and_invalid_fps(self):
        for entries in [[('../outside.png',png())],[('quadro_0001.png',png())],
            [('quadro_0000.png',png()),('quadro_0001.png',png(18,16))],
            [('quadro_0000.png',png(17,16))]]:
            with self.assertRaises(ValueError):converter(archive(entries),25,executable='unused')
        with self.assertRaises(ValueError):converter(b'',24,executable='unused')

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'ffmpeg/ffprobe required')
    def test_actual_h264_preserves_frame_count_timing_and_attribution(self):
        payload=archive([(f'quadro_{i:04d}.png',png()) for i in range(4)]+[('ATRIBUICAO.txt',b'QA attribution')])
        data=converter(payload,5)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'test.mp4';path.write_bytes(data)
            info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
        self.assertEqual(info['streams'][0]['codec_name'],'h264')
        self.assertEqual(info['streams'][0]['nb_frames'],'4')
        self.assertAlmostEqual(float(info['format']['duration']),0.8,places=2)
        self.assertEqual(info['format']['tags']['comment'],'QA attribution')

if __name__=='__main__':unittest.main()
