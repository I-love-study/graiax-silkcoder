import asyncio
import subprocess
import sys
from typing import List, Union

from .utils import CoderError, get_ffmpeg, soxr_available

ffmpeg_coder = get_ffmpeg()
if ffmpeg_coder is not None:
    soxr = soxr_available(ffmpeg_coder)
else:
    # 因为不知道到底有没有 ffmpeg，所以默认不使用 soxr
    ffmpeg_coder, soxr = "ffmpeg", False


def get_ffmpeg_encode_cmd(audio_format: str, codec: str, ss: int, t: int, ffmpeg_para: List[str]):
    cmd = [ffmpeg_coder]
    if audio_format is not None: cmd += ['-f', audio_format]
    if codec: cmd += ["-acodec", codec]

    input_cmd = ["-read_ahead_limit", "-1", "-i", "cache:pipe:0"]

    cmd += ['-ss', str(ss), *input_cmd, '-t', str(t)] if t else input_cmd
    if ffmpeg_para: cmd += ffmpeg_para
    if soxr: cmd += ['-af', 'aresample=resampler=soxr']
    cmd += ['-ar', '24000', '-ac', '1', '-y', '-vn', '-loglevel', 'error', '-f', 's16le', '-']
    return cmd


def ffmpeg_encode(data: bytes,
                  audio_format: str = None,
                  codec: str = None,
                  ss: int = None,
                  t: int = None,
                  ffmpeg_para: List[str] = None):
    cmd = get_ffmpeg_encode_cmd(audio_format, codec, ss, t, ffmpeg_para)
    shell = subprocess.Popen(cmd,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    p_out, p_err = shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


async def async_ffmpeg_encode(data: bytes,
                              audio_format: str = None,
                              codec: str = None,
                              ss: int = None,
                              t: int = None,
                              ffmpeg_para: List[str] = None):
    cmd = get_ffmpeg_encode_cmd(audio_format, codec, ss, t, ffmpeg_para)
    shell = await asyncio.create_subprocess_exec(*cmd,
                                                 stdin=asyncio.subprocess.PIPE,
                                                 stdout=asyncio.subprocess.PIPE,
                                                 stderr=asyncio.subprocess.PIPE)
    p_out, p_err = await shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


def get_ffmpeg_decode_cmd(audio_format: str, codec: str, ffmpeg_para: List[str], rate: Union[int,
                                                                                             str]):
    cmd = [ffmpeg_coder, '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', 'cache:pipe:0']
    if audio_format is not None: cmd += ['-f', audio_format]
    if codec: cmd += ["-acodec", codec]
    if rate is not None: cmd += ['-ab', str(rate)]
    if ffmpeg_para is not None: cmd += [str(a) for a in ffmpeg_para]
    if sys.platform == 'darwin' and codec == 'mp3':
        cmd += ["-write_xing", "0"]

    cmd += ['-y', '-loglevel', 'error', '-']
    return cmd


def ffmpeg_decode(data,
                  audio_format: str = None,
                  codec: str = None,
                  ffmpeg_para: List[str] = None,
                  rate: Union[int, str] = None):
    cmd = get_ffmpeg_decode_cmd(audio_format, codec, ffmpeg_para, rate)
    shell = subprocess.Popen(cmd,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    p_out, p_err = shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


async def async_ffmpeg_decode(data: bytes,
                              audio_format: str = None,
                              codec: str = None,
                              ffmpeg_para: List[str] = None,
                              rate: Union[int, str] = None):
    """
    通过ffmpeg导出为其它格式的音频数据
    file可以是路径/BytesIO实例
    如果file为None则返回二进制数据
    """
    cmd = get_ffmpeg_decode_cmd(audio_format, codec, ffmpeg_para, rate)

    shell = await asyncio.create_subprocess_exec(*cmd)
    p_out, p_err = await shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


__all__ = ["ffmpeg_encode", "ffmpeg_decode", "async_ffmpeg_encode", "async_ffmpeg_decode"]
