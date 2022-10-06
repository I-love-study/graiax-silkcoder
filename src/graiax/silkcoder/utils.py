import os
import subprocess
import sys
import wave
from io import BytesIO
from enum import Enum
from pathlib import Path
from shutil import which
from typing import Union, Optional

try:
    import imageio_ffmpeg
    imageio_ffmpeg_exists = True
except ImportError:
    imageio_ffmpeg_exists = False

try:
    import soundfile
    import soxr
    libsndfile_available = True
except (ImportError, OSError):
    libsndfile_available = False

class ArgTypeMixin(Enum):

    @classmethod
    def argtype(cls, s: str) -> Enum:
        try:
            return cls[s]
        except KeyError as e:
            raise ValueError("Not support Value") from e

    def __str__(self):
        return self.name

class Codec(ArgTypeMixin, Enum):
    wave = 0
    ffmpeg = 1
    libsndfile = 2

def choose_encoder(input_bytes: bytes):
    if iswave(input_bytes):
        return Codec.wave
    elif libsndfile_available and is_libsndfile_supported(input_bytes):
        return Codec.libsndfile
    else:
        # 什么叫做万金油啊（叉腰）
        return Codec.ffmpeg


def choose_decoder(audio_format: str):
    audio_format = audio_format.upper()
    if audio_format == 'WAV':
        return Codec.wave
    elif libsndfile_available and is_libsndfile_supported(audio_format):
        return Codec.libsndfile
    else:
        return Codec.ffmpeg


class CoderError(Exception):
    """所有编码/解码的错误"""
    pass


def input_transform(input_: Union[os.PathLike, str, BytesIO, bytes]) -> bytes:
    if isinstance(input_, (os.PathLike, str)):
        return Path(input_).read_bytes()
    elif isinstance(input_, BytesIO):
        return input_.getvalue()
    elif isinstance(input_, bytes):
        return input_
    else:
        raise ValueError("Unsupport format")


def output_transform(output_: Union[os.PathLike, str, BytesIO, None],
                     data: bytes) -> Optional[bytes]:
    if isinstance(output_, (os.PathLike, str)):
        Path(output_).write_bytes(data)
    elif isinstance(output_, BytesIO):
        output_.write(data)
    elif output_ is None:
        return data
    else:
        raise ValueError("Unsupport format")


def iswave(data: bytes):
    """判断音频是否能通过wave标准库解析"""
    try:
        wave.open(BytesIO(data))
        return True
    except (EOFError, wave.Error):
        return False


def issilk(data: bytes):
    """判断音频是否为silkv3格式"""
    f = data[1:10] if data.startswith(b'\x02') else data[:9]
    return f == b"#!SILK_V3"


def is_libsndfile_supported(data: Union[bytes, str]):
    """判断是否被当前libsndfile所支持
    当传入 bytes 的时候，判断是否能被 libsndfile 解析
    当传入 str 的时候，判断该字符串是否在 available_formats 中"""
    if not libsndfile_available:
        return False
    if isinstance(data, bytes):
        try:
            soundfile.info(BytesIO(data))
            return True
        except RuntimeError:
            return False
    elif isinstance(data, str):
        return data in soundfile.available_formats()


def soxr_available(ffmpeg_path: str):
    p = subprocess.Popen(ffmpeg_path,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         encoding="utf-8")
    return "--enable-libsoxr" in p.communicate()[1]

def get_ffmpeg():
    """获取本机拥有的编解码器"""
    if which("ffmpeg"):
        return "ffmpeg"
    elif imageio_ffmpeg_exists:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except RuntimeError:
            Warning("Couldn't find ffmpeg, maybe it'll not work")
    else:
        # 找不到，先警告一波
        Warning("Couldn't find ffmpeg, maybe it'll not work")


def play_audio(source: Union[str, bytes]):
    if sys.platform != "win32":
        raise WindowsError("Only support Windows")

    import winsound
    import msvcrt
    import multiprocessing
    import time

    p = multiprocessing.Process(
        target=winsound.PlaySound,
        args=(source, winsound.SND_FILENAME if isinstance(source, str) else winsound.SND_MEMORY),
    )
    p.start()
    print("请按'q'中断")
    while p.is_alive() and not (msvcrt.kbhit() and msvcrt.getch() in b"qQ"):
        time.sleep(0.1)
    p.terminate()
    p.join()