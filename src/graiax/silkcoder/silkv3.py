from . import _silkv3
import asyncio
from .utils import sync_to_async


def silk_encode(data: bytes,
                input_samplerate: int = 24000,
                maximum_samplerate: int = 24000,
                rate: int = -1,
                tencent: bool = True,
                ios_adaptive: int = False):
    if rate < 0:
        #保证压制出来的音频在1000kb上下，若音频时常在10min以内而不超过1Mb
        rate = min(int(980 * 1024 / (len(data) / 24000 / 2) * 8),
                   24000 if ios_adaptive else 100000)
    return _silkv3.encode(data, input_samplerate, maximum_samplerate,
                          rate, tencent)


def silk_decode(data: bytes, output_samplerate: int = 24000):
    return _silkv3.decode(data, output_samplerate)


async_silk_encode = sync_to_async(silk_encode)
async_silk_decode = sync_to_async(silk_decode)

__all__ = [
    "silk_encode", "silk_decode", "async_silk_encode",
    "async_silk_decode"
]
