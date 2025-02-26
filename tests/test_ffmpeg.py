import subprocess
from io import BytesIO
from pathlib import Path

from graiax.silkcoder.ffmpeg import FFMpegEncoder, FFMpegDecoder
from graiax.silkcoder.utils import get_ffmpeg
from .utils import get_similarity

resource_path = Path("tests/data/")
tmp_path = resource_path / "tmp"

original_audio = resource_path / "ぼっちぼろまる feat.もっさ - つよがるガール (Anime Edit).m4a"
original_audio_long = resource_path / "八奈見杏菜(CV.遠野ひかる)  - LOVE 2000.m4a"

audio = tmp_path / "test.flac"
audio_long = tmp_path / "test_long.flac"


def setup_module():
    ffmpeg_path = get_ffmpeg()
    assert ffmpeg_path is not None, "Do not have ffmpeg"
    ret = subprocess.run(
        [ffmpeg_path, "-i", original_audio, '-y', '-vn', '-loglevel', 'error', audio])
    ret.check_returncode()

    ret = subprocess.run([
        ffmpeg_path, "-i", original_audio_long, '-y', '-vn', '-loglevel', 'error',
        audio_long
    ])
    ret.check_returncode()


class TestFFMpeg:

    def test_ffmpeg_encode_decode(self):
        silk = BytesIO()
        FFMpegEncoder(ios_adaptive=False).encode_stream(audio_long, silk)
        silk.seek(0)
        wav = tmp_path / "test_ffmpeg_encode_decode.wav"
        FFMpegDecoder("wav").decode_stream(silk, wav)
        similarity = get_similarity(original_audio_long, wav)
        assert similarity > 0.97

    def test_sndfile_ios_adaptive(self):
        silk = BytesIO()
        FFMpegEncoder(ios_adaptive=True).encode_stream(audio_long, silk)
        silk.seek(0)
        wav = tmp_path / "test_sndfile_ios_adaptive.wav"
        FFMpegDecoder("wav").decode_stream(silk, wav)
        similarity = get_similarity(original_audio_long, wav)
        assert similarity > 0.86

    def test_ffmpeg_input_file(self):
        FFMpegEncoder().encode_stream(audio_long,
                                      tmp_path / "test_ffmpeg_input_file.silk")
        FFMpegDecoder().decode_stream(tmp_path / "test_ffmpeg_input_file.silk",
                                      tmp_path / "test_ffmpeg_input_file.flac")
        similarity = get_similarity(audio_long,
                                    tmp_path / "test_ffmpeg_input_file.flac")
        assert similarity > 0.86
