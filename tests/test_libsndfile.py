import asyncio
import subprocess
import time
from io import BytesIO

import pytest

from graiax.silkcoder.libsndfile import SndfileDecode, SndfileEncoder
from graiax.silkcoder.utils import get_ffmpeg

from .utils import get_similarity, original_audio, original_audio_long

def create_file(src, det, to:int = -1):
    ffmpeg_path = get_ffmpeg()
    assert ffmpeg_path is not None, "Do not have ffmpeg"
    cmd = [ffmpeg_path, "-i", src]
    if to > 0:
        cmd += ['-to', str(to)]
    cmd += ['-y', '-vn', '-loglevel', 'error', det]
    ret = subprocess.run(
        [ffmpeg_path, "-i", src, '-y', '-vn', '-loglevel', 'error', det])
    ret.check_returncode()


@pytest.fixture(scope="module")
def audio(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test.flac"
    create_file(original_audio, fn)
    return fn

@pytest.fixture(scope="module")
def audio_long(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test_long.flac"
    create_file(original_audio_long, fn)
    return fn

@pytest.fixture(scope="module")
def audio_short(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test_short.flac"
    create_file(original_audio, fn, 16)
    return fn


class TestSndfile:

    @pytest.mark.fast
    def test_fast(self, audio_short):
        silk = BytesIO()
        SndfileEncoder(ios_adaptive=False).encode_stream(audio_short, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        SndfileDecode().decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(audio_short, flac_2)
        assert similarity > 0.97

    def test_sndfile_encode_decode(self, audio_long):
        silk = BytesIO()
        SndfileEncoder(ios_adaptive=False).encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        SndfileDecode().decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(audio_long, flac_2)
        assert similarity > 0.97


    def test_sndfile_ios_adaptive(self, audio_long):
        silk = BytesIO()
        SndfileEncoder(ios_adaptive=True).encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        SndfileDecode().decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(original_audio_long, flac_2)
        assert similarity > 0.87

    def test_sndfile_input_file(self, audio, tmp_path):
        SndfileEncoder().encode_stream(audio, tmp_path / "t_input.silk")
        SndfileDecode().decode_stream(tmp_path / "t_input.silk", tmp_path / "t_input.flac")
        similarity = get_similarity(original_audio, tmp_path / "t_input.flac")
        assert similarity > 0.98

@pytest.mark.asyncio(loop_scope="class")
class TestAsyncSndfile:

    @pytest.mark.fast
    async def test_sndfile_fast(self, audio_short):
        silk = BytesIO()
        await SndfileEncoder(ios_adaptive=False).async_encode_stream(audio_short, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        await SndfileDecode().async_decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(audio_short, flac_2)
        assert similarity > 0.97

    async def test_sndfile_encode_decode(self, audio_long):
        silk = BytesIO()
        await SndfileEncoder(ios_adaptive=False).async_encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        await SndfileDecode().async_decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(audio_long, flac_2)
        assert similarity > 0.97


    async def test_sndfile_ios_adaptive(self, audio_long):
        silk = BytesIO()
        await SndfileEncoder(ios_adaptive=True).async_encode_stream(audio_long, silk)
        silk.seek(0)
        flac_2 = BytesIO()
        flac_2.name = "test.flac"  # 通过 name 来让 soundfile 理解 编码目标
        await SndfileDecode().async_decode_stream(silk, flac_2)
        flac_2.seek(0)
        similarity = get_similarity(original_audio_long, flac_2)
        assert similarity > 0.87

    async def test_sndfile_input_file(self, audio, tmp_path):
        await SndfileEncoder().async_encode_stream(audio, tmp_path / "t_input.silk")
        await SndfileDecode().async_decode_stream(tmp_path / "t_input.silk", tmp_path / "t_input.flac")
        similarity = get_similarity(audio, tmp_path / "t_input.flac")
        assert similarity > 0.98

    async def test_async_function(self, audio_long):

        async def time_count():
            t = time.time()
            await self.test_sndfile_ios_adaptive(audio_long)
            return time.time() - t

        t = time.time()
        work_time, _ = await asyncio.gather(time_count(), asyncio.sleep(5))
        fit_in = time.time() - t
        assert fit_in - max(work_time, 5) < 0.2