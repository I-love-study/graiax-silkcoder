import os
import wave
import asyncio
import inspect
import tempfile
import contextvars
from io import BytesIO
from functools import partial, wraps

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
                    f.seek(0)
                else:
                    tmp = tempfile.NamedTemporaryFile(mode="w+b", delete=False)
                    tmp.write(file)
                    f = tmp.name
            elif isinstance(file, BytesIO):
                if BytesIO_allowed:
                    file.seek(0)
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

async def to_thread(func, /, *args, **kwargs):
    "Same as asyncio.to_thread in python 3.9+"
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)

def issilk(file):
    if isinstance(file, BytesIO):
        file.seek(0)
        return file.read(10) == b'\x02#!SILK_V3'
    else:
        with open(file ,'rb') as fs:
            return fs.read(10) == b'\x02#!SILK_V3'

def iswave(file):
    try:
        wave.open(BytesIO(file) if type(file) is bytes else file)
        return True
    except (EOFError, wave.Error):
        return False

def fsdecode(filename):
    PathLikeTypes = (str, os.PathLike)
    if isinstance(filename, PathLikeTypes):
        return os.fsdecode(filename)
    raise TypeError(f"type {type(filename)} not accepted by fsdecode")