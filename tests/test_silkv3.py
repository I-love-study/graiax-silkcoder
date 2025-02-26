import asyncio
import subprocess
import time
from io import BytesIO
from pathlib import Path

import pytest

from graiax.silkcoder.silkv3 import SilkDecoder, SilkEncoder
from graiax.silkcoder.utils import get_ffmpeg, soxr_available

from .utils import get_similarity, package_pcm

resource_path = Path("tests/data/")
tmp_path = resource_path / "tmp"

original_audio = resource_path / "ぼっちぼろまる feat.もっさ - つよがるガール (Anime Edit).m4a"
original_audio_long = resource_path / "八奈見杏菜(CV.遠野ひかる)  - LOVE 2000.m4a"

pcm = tmp_path / "test.pcm"
pcm_long = tmp_path / "test_long.pcm"
pcm_48000 = tmp_path / "test_48000.pcm"


def setup_module():
    ffmpeg_path = get_ffmpeg()
    assert ffmpeg_path is not None, "Do not have ffmpeg"
    cmd = [ffmpeg_path, "-i", original_audio_long]
    if soxr_available(ffmpeg_path):
        cmd += ['-af', 'aresample=resampler=soxr']
    cmd += [
        '-ar', '24000', '-ac', '1', '-y', '-vn', '-loglevel', 'error', '-f', 's16le',
        pcm_long
    ]
    ret = subprocess.run(cmd)
    ret.check_returncode()

    cmd[cmd.index('24000')] = "48000"
    cmd[cmd.index(pcm_long)] = pcm_48000
    ret = subprocess.run(cmd)
    ret.check_returncode()
    
    cmd[cmd.index('48000')] = "24000"
    cmd[cmd.index(pcm_48000)] = pcm
    cmd[cmd.index(original_audio_long)] = original_audio
    ret = subprocess.run(cmd)
    ret.check_returncode()

class TestSilkV3:

    def test_ios_adaptive(self):
        silk = BytesIO()
        with pcm_long.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(pcm_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.87

    def test_maximum_bitrate(self):
        silk = BytesIO()
        with (pcm_long.open("rb") as f, SilkEncoder(24000, 24000, 100000, ios_adaptive=False)
              as encoder):
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(pcm_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    def test_resample(self):
        silk = BytesIO()
        with (pcm_48000.open("rb") as
              f, SilkEncoder(48000, 24000, 100000, ios_adaptive=False) as encoder):
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(pcm_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

@pytest.mark.asyncio(loop_scope="class")
class TestSilkV3Async:

    async def test_async_ios_adaptive(self):
        silk = BytesIO()
        with pcm_long.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(pcm_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.87

    async def test_async_maximum_bitrate(self):
        silk = BytesIO()
        with (pcm_long.open("rb") as
              f, SilkEncoder(24000, 24000, 100000, ios_adaptive=False) as encoder):
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(pcm_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    async def test_async_resample(self):
        silk = BytesIO()
        with (pcm_48000.open("rb") as
              f, SilkEncoder(48000, 24000, 100000, ios_adaptive=False) as encoder):
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(pcm_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    async def test_async_function(self):

        async def time_count():
            t = time.time()
            await self.test_async_ios_adaptive()
            return time.time() - t

        t = time.time()
        work_time, _ = await asyncio.gather(time_count(), asyncio.sleep(5))
        fit_in = time.time() - t
        assert fit_in - max(work_time, 5) < 0.2
