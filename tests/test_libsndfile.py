import subprocess
from io import BytesIO
from pathlib import Path

from graiax.silkcoder.libsndfile import sndfile_encode_stream
from graiax.silkcoder.utils import get_ffmpeg
from graiax.silkcoder.silkv3 import SilkDecoder
from utils import get_similarity, package_pcm

resource_path = Path("tests/data/")
tmp_path = resource_path / "tmp"
tmp_path.mkdir(exist_ok=True)
original_audio = resource_path / "八奈見杏菜(CV.遠野ひかる)  - LOVE 2000.m4a"


def setup_module():
    ffmpeg_path = get_ffmpeg()
    assert ffmpeg_path is not None, "Do not have ffmpeg"
    cmd = [
        ffmpeg_path, "-i", original_audio, '-y', '-vn', '-loglevel', 'error',
        tmp_path / "test.flac"
    ]
    ret = subprocess.run(cmd)
    ret.check_returncode()


def teardown_module():
    for file in tmp_path.iterdir():
        file.unlink(missing_ok=True)
    tmp_path.rmdir()


def test_sndfile_encode():
    silk = BytesIO()
    flac_file = tmp_path / "test.flac"
    sndfile_encode_stream(flac_file, silk, ios_adaptive=False)
    silk.seek(0)
    pcm2 = BytesIO()
    with SilkDecoder(24000) as decoder:
        decoder.decode_stream(silk, pcm2)

    package_pcm(pcm2.getvalue(), wav2 := BytesIO(), 1, 2, 24000)

    wav2.seek(0)

    similarity = get_similarity(original_audio, wav2)
    print(similarity)
    assert similarity > 0.87
