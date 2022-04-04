import os
import subprocess
import wave
from io import BytesIO
from pathlib import Path
from typing import Union, Optional

try:
    import imageio_ffmpeg
    imageio_ffmpeg_exists = True
except ImportError:
    imageio_ffmpeg_exists = False


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
    f = data[1:11] if data.startswith(b'\x02') else data[:9]
    return f == b"#!SILK_V3"


def soxr_available(ffmpeg_path: str):
    p = subprocess.Popen(ffmpeg_path,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         encoding="utf-8")
    return "--enable-libsoxr" in p.communicate()[1]


def which(program):
    """类似于 UNIX 中的 which 命令"""
    # Add .exe program extension for windows support
    if os.name == "nt" and not program.endswith(".exe"):
        program += ".exe"

    envdir_list = [os.curdir] + os.environ["PATH"].split(os.pathsep)

    for envdir in envdir_list:
        program_path = os.path.join(envdir, program)
        if os.path.isfile(program_path) and os.access(program_path, os.X_OK):
            return program_path


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
