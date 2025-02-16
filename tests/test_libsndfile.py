import subprocess
from io import BytesIO
from pathlib import Path

from graiax.silkcoder.libsndfile import SndfileEncoder, SndfileDecode
from graiax.silkcoder.utils import get_ffmpeg
from utils import get_similarity

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


def test_sndfile_encode_decode():
    silk = BytesIO()
    flac_file = tmp_path / "test.flac"
    SndfileEncoder(ios_adaptive=False).encode_stream(flac_file, silk)
    silk.seek(0)
    flac_2 = BytesIO()
    flac_2.name = "test.flac" # 通过 name 来让 soundfile 理解 编码目标
    SndfileDecode().decode_stream(silk, flac_2)
    flac_2.seek(0)
    similarity = get_similarity(original_audio, flac_2)
    assert similarity > 0.97

def test_sndfile_ios_adaptive():
    silk = BytesIO()
    flac_file = tmp_path / "test.flac"
    SndfileEncoder(ios_adaptive=True).encode_stream(flac_file, silk)
    silk.seek(0)
    flac_2 = BytesIO()
    flac_2.name = "test.flac" # 通过 name 来让 soundfile 理解 编码目标
    SndfileDecode().decode_stream(silk, flac_2)
    flac_2.seek(0)
    similarity = get_similarity(original_audio, flac_2)
    assert similarity > 0.87

