import asyncio
import subprocess
import sys
from typing import Dict, List, Optional, Union

from .utils import CoderError, get_ffmpeg, soxr_available

PIPE = subprocess.PIPE
Num = Union[int, float]

ffmpeg_coder = get_ffmpeg()
if ffmpeg_coder is not None:
    soxr = soxr_available(ffmpeg_coder)
    ffmpeg_available = True
else:
    # 因为不知道到底有没有 ffmpeg，所以默认不使用 soxr
    ffmpeg_coder, soxr = "ffmpeg", False
    ffmpeg_available = False


def get_ffmpeg_encode_cmd(audio_format: Optional[str], ss: Num, t: Num,
                          ffmpeg_para: Optional[List[str]]):
    cmd = [ffmpeg_coder]
    if audio_format is not None: cmd += ['-f', audio_format]

    input_cmd = ["-read_ahead_limit", "-1", "-i", "cache:pipe:0"]

    cmd += [
        '-ss',
        str(ss if isinstance(ss, int) else round(ss, 3)), *input_cmd, '-t',
        str(t if isinstance(t, int) else round(t, 3))
    ] if t > 0 else input_cmd
    if ffmpeg_para: cmd += ffmpeg_para
    if soxr: cmd += ['-af', 'aresample=resampler=soxr']
    cmd += ['-ar', '24000', '-ac', '1', '-y', '-vn', '-loglevel', 'error', '-f', 's16le', '-']
    return cmd


def ffmpeg_encode(data: bytes,
                  audio_format: Optional[str] = None,
                  ss: Num = 0,
                  t: Num = -1,
                  ffmpeg_para: Optional[List[str]] = None):
    cmd = get_ffmpeg_encode_cmd(audio_format, ss, t, ffmpeg_para)
    shell = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p_out, p_err = shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


async def async_ffmpeg_encode(data: bytes,
                              audio_format: Optional[str] = None,
                              ss: Num = 0,
                              t: Num = -1,
                              ffmpeg_para: Optional[List[str]] = None):
    cmd = get_ffmpeg_encode_cmd(audio_format, ss, t, ffmpeg_para)
    shell = await asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p_out, p_err = await shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


def get_ffmpeg_decode_cmd(audio_format: str, ffmpeg_para: Optional[List[str]],
                          rate: Optional[Union[int, str]],
                          metadata: Optional[Dict[str, Union[str, Num]]]):
    cmd = [ffmpeg_coder, '-f', 's16le', '-ar', '24000', '-ac', '1', '-i', 'pipe:']
    if audio_format is not None: cmd += ['-f', audio_format]
    if rate is not None: cmd += ['-b:a', str(rate)]
    if metadata is not None:
        for k, v in metadata.items():
            cmd += ["-metadata", f"{k}={v}"]
    if ffmpeg_para is not None: cmd += [str(a) for a in ffmpeg_para]
    if sys.platform == 'darwin' and audio_format == 'mp3':
        cmd += ["-write_xing", "0"]

    cmd += ['-y', '-loglevel', 'error', 'pipe:']
    return cmd


def ffmpeg_decode(data,
                  audio_format: str,
                  ffmpeg_para: Optional[List[str]] = None,
                  rate: Optional[Union[int, str]] = None,
                  metadata: Optional[Dict[str, Union[str, Num]]] = None):
    cmd = get_ffmpeg_decode_cmd(audio_format, ffmpeg_para, rate, metadata)
    shell = subprocess.Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p_out, p_err = shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


async def async_ffmpeg_decode(data,
                              audio_format: str,
                              ffmpeg_para: Optional[List[str]] = None,
                              rate: Optional[Union[int, str]] = None,
                              metadata: Optional[Dict[str, Union[str, Num]]] = None):
    cmd = get_ffmpeg_decode_cmd(audio_format, ffmpeg_para, rate, metadata)
    shell = await asyncio.create_subprocess_exec(*cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p_out, p_err = await shell.communicate(input=data)
    if shell.returncode != 0:
        raise CoderError(f"ffmpeg error:\n{p_err.decode(errors='ignore')}")
    return p_out


__all__ = [
    "ffmpeg_encode", "ffmpeg_decode", "async_ffmpeg_encode", "async_ffmpeg_decode",
    "ffmpeg_available"
]
