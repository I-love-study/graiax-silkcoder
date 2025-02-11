import subprocess
from io import BytesIO
from pathlib import Path

from graiax.silkcoder.silkv3 import SilkDecoder, SilkEncoder
from graiax.silkcoder.utils import get_ffmpeg, soxr_available
from utils import get_similarity, package_pcm

resource_path = Path("tests/data/")
tmp_path = resource_path / "tmp"
tmp_path.mkdir(exist_ok=True)
original_audio = resource_path / "八奈見杏菜(CV.遠野ひかる)  - LOVE 2000.m4a"


def setup_module():
    ffmpeg_path = get_ffmpeg()
    assert ffmpeg_path is not None, "Do not have ffmpeg"
    cmd = [ffmpeg_path, "-i", original_audio]
    if soxr_available(ffmpeg_path):
        cmd += ['-af', 'aresample=resampler=soxr']
    cmd += [
        '-ar', '24000', '-ac', '1', '-y', '-vn', '-loglevel', 'error', '-f', 's16le',
        tmp_path / "test.pcm"
    ]
    ret = subprocess.run(cmd)
    ret.check_returncode()
    cmd[cmd.index('24000')] = "48000"
    cmd[cmd.index(tmp_path / "test.pcm")] = tmp_path / "test_48000.pcm"
    ret = subprocess.run(cmd)
    ret.check_returncode()


def teardown_module():
    for file in tmp_path.iterdir():
        file.unlink(missing_ok=True)
    tmp_path.rmdir()

def test_ios_adaptive():
    pcm_file = tmp_path / "test.pcm"
    silk = BytesIO()
    with pcm_file.open("rb") as f, SilkEncoder(24000, 24000, 100000) as encoder:
        encoder.encode_stream(f, silk)
    silk.seek(0)
    pcm2 = BytesIO()
    with SilkDecoder(24000) as decoder:
        decoder.decode_stream(silk, pcm2)

    package_pcm(pcm_file.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
    package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

    wav1.seek(0)
    wav2.seek(0)

    similarity = get_similarity(wav1, wav2)
    assert similarity > 0.87


def test_maximum_bitrate():
    pcm_file = tmp_path / "test.pcm"
    silk = BytesIO()
    with (pcm_file.open("rb") as f, SilkEncoder(24000,
                                                24000,
                                                100000,
                                                ios_adaptive=False) as encoder):
        encoder.encode_stream(f, silk)
    silk.seek(0)
    pcm2 = BytesIO()
    with SilkDecoder(24000) as decoder:
        decoder.decode_stream(silk, pcm2)

    package_pcm(pcm_file.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
    package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

    wav1.seek(0)
    wav2.seek(0)

    similarity = get_similarity(wav1, wav2)
    assert similarity > 0.97


def test_resample():
    pcm_file = tmp_path / "test_48000.pcm"
    pcm2_file = tmp_path / "test.pcm"

    silk = BytesIO()
    with (pcm_file.open("rb") as f, SilkEncoder(48000,
                                                24000,
                                                100000,
                                                ios_adaptive=False) as encoder):
        encoder.encode_stream(f, silk)
    silk.seek(0)
    pcm2 = BytesIO()
    with SilkDecoder(24000) as decoder:
        decoder.decode_stream(silk, pcm2)

    package_pcm(pcm2_file.read_bytes(), wav1 := BytesIO(), 1, 2, 24000)
    package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

    wav1.seek(0)
    wav2.seek(0)

    similarity = get_similarity(wav1, wav2)
    assert similarity > 0.97
