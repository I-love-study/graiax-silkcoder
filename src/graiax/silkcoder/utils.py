from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import wave
from enum import Enum
from io import BytesIO
from pathlib import Path
from shutil import which
from typing import TYPE_CHECKING, Any, Callable, Coroutine, ParamSpec, TypeVar, overload

if TYPE_CHECKING:
    from _typeshed import HasFileno, StrOrBytesPath

if sys.version_info >= (3, 13):
    from typing import TypeIs
else:
    from typing_extensions import TypeIs

from .typing import AsyncReader, AsyncWriter, Reader, Writer

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

try:
    import soundfile
    import soxr
except (ImportError, OSError):
    soundfile, soxr = None, None


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


class CoderError(Exception):
    """所有编码/解码的错误"""
    pass


def input_transform(input_: os.PathLike | str | BytesIO | bytes) -> bytes:
    if isinstance(input_, (os.PathLike, str)):
        return Path(input_).read_bytes()
    elif isinstance(input_, BytesIO):
        return input_.getvalue()
    elif isinstance(input_, bytes):
        return input_
    else:
        raise ValueError("Unsupport format")


def output_transform(output_: os.PathLike | str | BytesIO | bytes,
                     data: bytes) -> bytes | None:
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


def is_libsndfile_supported(data: bytes | str):
    """判断是否被当前libsndfile所支持
    当传入 bytes 的时候，判断是否能被 libsndfile 解析
    当传入 str 的时候，判断该字符串是否在 available_formats 中"""
    if soundfile is None:
        return False
    if isinstance(data, bytes):
        try:
            soundfile.info(BytesIO(data))
            return True
        except RuntimeError:
            return False
    elif isinstance(data, str):
        return data.upper() in soundfile.available_formats()
    else:
        raise ValueError("Unsupport Data")


def soxr_available(ffmpeg_path: StrOrBytesPath):
    p = subprocess.Popen(ffmpeg_path,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         encoding="utf-8")
    return "--enable-libsoxr" in p.communicate()[1]


def get_ffmpeg():
    """获取本机拥有的编解码器"""
    if which("ffmpeg"):
        return "ffmpeg"
    elif imageio_ffmpeg is not None:
        try:
            return imageio_ffmpeg.get_ffmpeg_exe()
        except RuntimeError:
            Warning("Couldn't find ffmpeg, maybe it'll not work")
    else:
        # 找不到，先警告一波
        Warning("Couldn't find ffmpeg, maybe it'll not work")


def play_audio(source: str | bytes):
    if sys.platform != "win32":
        raise WindowsError("Only support Windows")

    import msvcrt
    import multiprocessing
    import time
    import winsound

    p = multiprocessing.Process(
        target=winsound.PlaySound,
        args=(source, winsound.SND_FILENAME
              if isinstance(source, str) else winsound.SND_MEMORY),
    )
    p.start()
    print("请按'q'中断")
    while p.is_alive() and not (msvcrt.kbhit() and msvcrt.getch() in b"qQ"):
        time.sleep(0.1)
    p.terminate()
    p.join()


# Fxxxing Type Hint

P = ParamSpec("P")
R = TypeVar("R")


@overload
async def async_func(func: Callable[P, Coroutine[Any, Any, R]], *args: P.args,
                     **kwargs: P.kwargs) -> R:
    ...


@overload
async def async_func(func: Callable[P, R | Coroutine[Any, Any, R]], *args: P.args,
                     **kwargs: P.kwargs) -> R:
    ...


@overload
async def async_func(func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
    ...


async def async_func(func, *args, **kwargs):
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


@overload
def create_async_func(
        func: Callable[P, Coroutine[Any, Any,
                                    R]]) -> Callable[P, Coroutine[Any, Any, R]]:
    ...


@overload
def create_async_func(
    func: Callable[P,
                   R | Coroutine[Any, Any, R]]) -> Callable[P, Coroutine[Any, Any, R]]:
    ...


@overload
def create_async_func(func: Callable[P, R]) -> Callable[P, Coroutine[Any, Any, R]]:
    ...


def create_async_func(func):
    if asyncio.iscoroutinefunction(func):

        async def _coro(*args, **kwargs):
            return await func(*args, **kwargs)

    else:

        async def _coro(*args, **kwargs):
            return func(*args, **kwargs)

    return _coro


def is_async_function(a: object, method_name: str) -> bool:
    method = getattr(a, method_name, None)
    return asyncio.iscoroutinefunction(method)


def is_reader(a: Any) -> TypeIs[Reader | AsyncReader]:
    return hasattr(getattr(a, "read", None), "__call__")


def is_writer(a: Any) -> TypeIs[Writer | AsyncWriter]:
    return hasattr(getattr(a, "read", None), "__call__")


def is_async_reader(a: Reader | AsyncReader) -> TypeIs[AsyncReader]:
    return is_async_function(a, "read")


def is_async_writer(a: Writer | AsyncWriter) -> TypeIs[AsyncWriter]:
    return is_async_function(a, "write")


def has_fileno(a: Any) -> TypeIs[HasFileno]:
    try:
        a.fileno()
        return True
    except Exception:
        return False


def isStrOrBytesPath(a: Any) -> TypeIs[StrOrBytesPath]:
    if isinstance(a, os.PathLike):
        a = a.__fspath__()
    return isinstance(a, str | bytes)
