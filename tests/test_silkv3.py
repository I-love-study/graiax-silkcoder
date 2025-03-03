from __future__ import annotations

import asyncio
import subprocess
from typing import TYPE_CHECKING
import time
from io import BytesIO

import pytest

from graiax.silkcoder.silkv3 import SilkDecoder, SilkEncoder
from graiax.silkcoder.utils import get_ffmpeg, soxr_available

from .utils import get_similarity, package_pcm, original_audio, original_audio_long

if TYPE_CHECKING:
    from _typeshed import StrOrBytesPath


def create_file(src: StrOrBytesPath, det: StrOrBytesPath, samplerate: int = 24000, to: int = -1):
    ffmpeg_path = get_ffmpeg()
    assert ffmpeg_path is not None, "Do not have ffmpeg"
    cmd = [ffmpeg_path, "-i", src]
    if soxr_available(ffmpeg_path):
        cmd += ['-af', 'aresample=resampler=soxr']
    if to != -1:
        cmd += ['-to', str(to)]
    cmd += [
        '-ar', str(samplerate), '-ac', '1', '-y', '-vn', '-loglevel', 'error', '-f', 's16le',
        det
    ]
    ret = subprocess.run(cmd)
    ret.check_returncode()


@pytest.fixture(scope="module")
def audio(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test.pcm"
    create_file(original_audio, fn)
    return fn

@pytest.fixture(scope="module")
def audio_long(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test_long.pcm"
    create_file(original_audio_long, fn)
    return fn

@pytest.fixture(scope="module")
def audio_48000(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test_48000.pcm"
    create_file(original_audio_long, fn, 48000)
    return fn

@pytest.fixture(scope="module")
def audio_fast(tmp_path_factory):
    fn = tmp_path_factory.mktemp("audio") / "test_fast.pcm"
    create_file(original_audio, fn, to=16)
    return fn


class TestSilkV3:

    @pytest.mark.fast
    def test_fast(self, audio_fast):
        silk = BytesIO()
        with audio_fast.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_fast.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    def test_ios_adaptive(self, audio_long):
        silk = BytesIO()
        with audio_long.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.87

    def test_maximum_bitrate(self, audio_long):
        silk = BytesIO()
        with (audio_long.open("rb") as
              f, SilkEncoder(24000, 24000, 100000, ios_adaptive=False) as encoder):
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    def test_resample(self, audio_48000, audio_long):
        silk = BytesIO()
        with (audio_48000.open("rb") as
              f, SilkEncoder(48000, 24000, 100000, ios_adaptive=False) as encoder):
            encoder.encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97


@pytest.mark.asyncio(loop_scope="class")
class TestSilkV3Async:

    @pytest.mark.fast
    async def test_async_fast(self, audio_fast):
        silk = BytesIO()
        with audio_fast.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_fast.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.87

    async def test_async_ios_adaptive(self, audio_long):
        silk = BytesIO()
        with audio_long.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.87

    async def test_async_maximum_bitrate(self, audio_long):
        silk = BytesIO()
        with (audio_long.open("rb") as
              f, SilkEncoder(24000, 24000, 100000, ios_adaptive=False) as encoder):
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    async def test_async_resample(self, audio_48000, audio_long):
        silk = BytesIO()
        with (audio_48000.open("rb") as
              f, SilkEncoder(48000, 24000, 100000, ios_adaptive=False) as encoder):
            await encoder.async_encode_stream(f, silk)
        silk.seek(0)
        pcm2 = BytesIO()
        with SilkDecoder(24000) as decoder:
            decoder.decode_stream(silk, pcm2)

        package_pcm(audio_long.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
        package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

        wav1.seek(0)
        wav2.seek(0)

        similarity = get_similarity(wav1, wav2)
        assert similarity > 0.97

    async def test_async_function(self, audio_long):

        async def time_count():
            t = time.time()
            await self.test_async_ios_adaptive(audio_long)
            return time.time() - t

        t = time.time()
        work_time, _ = await asyncio.gather(time_count(), asyncio.sleep(5))
        fit_in = time.time() - t
        assert fit_in - max(work_time, 5) < 0.2
