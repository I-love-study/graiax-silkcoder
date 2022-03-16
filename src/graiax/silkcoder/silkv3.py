from . import _silkv3
import asyncio


def silk_encode(data: bytes, rate: int = None, tencent: bool = True):
    if rate is None:
        #保证压制出来的音频在1000kb上下，若音频时常在10min以内而不超过1Mb
        rate = min(int(980 * 1024 / (len(data) / 24000 / 2) * 8), 100000)
    return _silkv3.encode(data, rate, tencent)


async def async_silk_encode(data: bytes, rate: int = None, tencent: bool = True):
    if rate is None:
        #保证压制出来的音频在1000kb上下，若音频时常在10min以内而不超过1Mb
        rate = min(int(980 * 1024 / (len(data) / 24000 / 2) * 8), 100000)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _silkv3.encode, data, rate, tencent)


def silk_decode(data: bytes):
    return _silkv3.decode(data)


async def async_silk_decode(data: bytes):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _silkv3.decode, data)

__all__ = ["silk_encode", "silk_decode", "async_silk_encode", "async_silk_decode"]