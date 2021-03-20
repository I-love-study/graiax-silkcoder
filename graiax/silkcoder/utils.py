import os
import wave
import asyncio
import tempfile
import contextvars
from io import BytesIO
from functools import partial
from contextlib import contextmanager

@contextmanager
def makesureinput(file=None, BytesIO_allowed=False):
    tmp = None
    if file is None:
        tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
        yield tmp
    elif isinstance(file,(os.PathLike, str)):
        yield fsdecode(file)
    elif isinstance(file, bytes):
        if BytesIO_allowed:
            f = BytesIO(file)
            f.seek(0)
            yield f
        else:
            tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
            tmp.write(file)
            yield tmp.name
    elif isinstance(file, BytesIO):
        if BytesIO_allowed:
            file.seek(0)
            yield file
        else:
            tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
            tmp.write(file.getvalue())
            yield tmp.name
    else:
        raise TypeError('Can not exchange input into a file')

    if tmp:
        tmp.close()
        os.unlink(tmp.name)

@contextmanager
def makesureoutput(file=None, BytesIO_allowed=False):
    tmp = None
    if file is None:
        tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
        yield tmp.name
    elif isinstance(file,(os.PathLike, str)):
        yield fsdecode(file)
    elif isinstance(file, BytesIO):
        if BytesIO_allowed:
            yield file
        else:
            tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
            tmp.write(file.getvalue())
            yield tmp.name
    else:
        raise TypeError('Can not exchange input into a file')

    if tmp:
        if isinstance(file, BytesIO) and not BytesIO_allowed:
            tmp.seek(0)
            file.write(tmp.read())
        tmp.close()
        os.unlink(tmp.name)

async def to_thread(func, /, *args, **kwargs):
    """Same as asyncio.to_thread in python 3.9+"""
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

def issilk(file):
    with makesureinput(file, BytesIO_allowed=True) as f:
        if isinstance(f, BytesIO):
            f.seek(0)
            return f.read(10) == b'\x02#!SILK_V3'
        else:
            with open(f ,'rb') as fs:
                return fs.read(10) == b'\x02#!SILK_V3'

def iswave(file):
    with makesureinput(file, BytesIO_allowed=True) as f:
        try:
            wave.open(f)
            return True
        except (EOFError, wave.Error):
            return False

def fsdecode(filename):
    PathLikeTypes = (str, os.PathLike)
    if isinstance(filename, PathLikeTypes):
        return os.fsdecode(filename)
    raise TypeError(f"type {type(filename)} not accepted by fsdecode")