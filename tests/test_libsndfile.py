import asyncio
import subprocess
import time
from io import BytesIO
from pathlib import Path

import pytest

from graiax.silkcoder.libsndfile import SndfileDecode, SndfileEncoder
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

class TestSndfile:
    def test_sndfile_encode_decode(self):
        silk = BytesIO()
        SndfileEncoder(ios_adaptive=False).encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        SndfileDecode().decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(original_audio_long, flac_2)
        assert similarity > 0.97


    def test_sndfile_ios_adaptive(self):
        silk = BytesIO()
        SndfileEncoder(ios_adaptive=True).encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        SndfileDecode().decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(original_audio_long, flac_2)
        assert similarity > 0.87

    def test_sndfile_input_file(self):
        SndfileEncoder().encode_stream(audio, tmp_path / "t_input.silk")
        SndfileDecode().decode_stream(tmp_path / "t_input.silk", tmp_path / "t_input.flac")
        similarity = get_similarity(original_audio, tmp_path / "t_input.flac")
        assert similarity > 0.98

@pytest.mark.asyncio(loop_scope="class")
class TestAsyncSndfile:

    async def test_sndfile_encode_decode(self):
        silk = BytesIO()
        await SndfileEncoder(ios_adaptive=False).async_encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        await SndfileDecode().async_decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(original_audio_long, flac_2)
        assert similarity > 0.97


    async def test_sndfile_ios_adaptive(self):
        silk = BytesIO()
        await SndfileEncoder(ios_adaptive=True).async_encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        await SndfileDecode().async_decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(original_audio_long, flac_2)
        assert similarity > 0.87

    async def test_sndfile_input_file(self):
        await SndfileEncoder().async_encode_stream(audio, tmp_path / "t_input.silk")
        await SndfileDecode().async_decode_stream(tmp_path / "t_input.silk", tmp_path / "t_input.flac")
        similarity = get_similarity(audio, tmp_path / "t_input.flac")
        assert similarity > 0.98

    async def test_async_function(self):

        async def time_count():
            t = time.time()
            await self.test_sndfile_ios_adaptive()
            return time.time() - t

        t = time.time()
        work_time, _ = await asyncio.gather(time_count(), asyncio.sleep(5))
        fit_in = time.time() - t
        assert fit_in - max(work_time, 5) < 0.2