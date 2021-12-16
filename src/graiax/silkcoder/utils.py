import asyncio
import inspect
import os
import subprocess
import tempfile
import wave
from functools import wraps
from io import BytesIO

try:
    import imageio_ffmpeg
    imageio_ffmpeg_exists = True
except ImportError:
    imageio_ffmpeg_exists = False

def makesureinput(BytesIO_allowed=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(cls, file, *args, **kwargs):
            tmp = None
            if isinstance(file,(os.PathLike, str)):
                f = os.fsdecode(file)
            elif isinstance(file, bytes):
                if BytesIO_allowed:
                    f = BytesIO(file)
                else:
                    tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
                    tmp.write(file)
                    tmp.seek(0)
                    f = tmp.name
            elif isinstance(file, BytesIO):
                if BytesIO_allowed:
                    f = file
                else:
                    tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
                    tmp.write(file.getvalue())
                    f = tmp.name
            else:
                raise TypeError('Can not exchange input into a file')

            ret = await func(cls, f, *args, **kwargs)

            if tmp:
                tmp.close()
                os.unlink(tmp.name)

            return ret
        return wrapper
    return decorator

def makesureoutput(BytesIO_allowed=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(cls, file=None, *args, **kwargs):
            tmp = None
            if file is None:
                tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
                f =  tmp.name
            elif isinstance(file,(os.PathLike, str)):
                f = os.fsdecode(file)
            elif isinstance(file, BytesIO):
                if BytesIO_allowed:
                    f = file
                else:
                    tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
                    tmp.write(file.getvalue())
                    f = tmp.name
            else:
                raise TypeError('Can not exchange input into a file')

            ret = await func(cls, f, *args, **kwargs)

            if tmp:
                tmp.seek(0)
                if file is None:
                    ret = tmp.read()
                elif isinstance(file, BytesIO) and not BytesIO_allowed:
                    file.write(tmp.read())
                tmp.close()
                os.unlink(tmp.name)

            return ret
        return wrapper
    return decorator

def issilk(file):
    if isinstance(file, BytesIO):
        file.seek(0)
        f = file.read(10)
    else:
        with open(file ,'rb') as fs:
            f = fs.read(10) 
    
    if f.startswith(b'\x02'): f = f[1:]
    return f == b'#!SILK_V3'

def iswave(file):
    """判断音频是否能通过wave标准库解析"""
    try:
        wave.open(BytesIO(file) if type(file) is bytes else fsdecode(file))
        return True
    except (EOFError, wave.Error):
        return False

def fsdecode(filename):
    if isinstance(filename, (str, os.PathLike)):
        return os.fsdecode(filename)
    raise TypeError(f"type {type(filename)} not accepted by fsdecode")

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
        return imageio_ffmpeg.get_ffmpeg_exe()
    else:
        # 找不到，先警告一波
        Warning("Couldn't find ffmpeg, maybe it'll not work")
        return "ffmpeg"
