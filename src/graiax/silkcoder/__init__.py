"""
一个不占GIL锁的SilkV3编解码器
注：单个音频压制还是单线程，但是压制时不占用GIL锁
"""
import os
from enum import Enum
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from .ffmpeg import *
from .libsndfile import *
from .silkv3 import *
from .utils import input_transform, iswave, output_transform, is_libsndfile_supported
from .wav import *


class Method(Enum):
    wave = 0
    ffmpeg = 1
    libsndfile = 2

def choose_encoder(input_bytes: bytes = None):
    if iswave(input_bytes):
        return Method.wave
    elif libsndfile_available and is_libsndfile_supported(input_bytes):
        return Method.libsndfile
    else:
        # 什么叫做万金油啊（叉腰）
        return Method.ffmpeg

def choose_decoder(audio_format:str = None):
    audio_format = audio_format.upper()
    if audio_format == 'WAV':
        return Method.wave
    elif libsndfile_available and is_libsndfile_supported(audio_format):
        return Method.libsndfile
    else:
        return Method.ffmpeg

async def async_encode(input_voice: Union[os.PathLike, str, BytesIO, bytes],
                       output_voice: Union[os.PathLike, str, BytesIO, None] = None,
                       audio_format: str = None,
                       codec: Method = None,
                       rate: int = None,
                       ss: int = 0,
                       t: int = 0,
                       tencent: bool = True,
                       ios_adaptive: bool = False) -> Optional[bytes]:
    """
    将音频文件转化为silk文件

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 ffmpeg/libsndfile 解析格式)
        codec(Method) 编码器，可以指定用什么进行编码 默认状态下会让程序自行判断
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(int) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(int) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        kwargs(dict) 其他参数，可以指定 ffmpeg 中的其他参数
    """

    input_bytes = input_transform(input_voice)
    if codec is None:
        codec = choose_encoder(input_bytes)
    if codec == Method.wave:
        pcm = wav_encode(input_bytes, ss, t)
    elif codec == Method.libsndfile:
        pcm = await async_sndfile_encode(input_bytes, ss, t)
    else:
        pcm = await async_ffmpeg_encode(input_bytes, audio_format, codec, ss, t,)

    silk = await async_silk_encode(pcm, rate, tencent, ios_adaptive)

    return output_transform(output_voice, silk)


async def async_decode(input_voice: Union[os.PathLike, str, BytesIO, bytes],
                       output_voice: Union[os.PathLike, str, BytesIO, None] = None,
                       audio_format: str = None,
                       codec: str = None,
                       ensure_ffmpeg: bool = False,
                       rate: int = None,
                       ffmpeg_para: list = None) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由ffmpeg解析格式)
        codec(str) 编码器(如果需要) 默认为None
        ensure_ffmpeg(bool) 在音频能用wave库解析时是否强制使用ffmpeg导入 默认为False
        rate(int) 码率 对应ffmpeg/avconc中"-ab"参数 默认为None
        metadata(dict) 音频标签 将会转化为ffmpeg/avconc参数 如"-metadata title=xxx" 默认为None
        ffmpeg_para(list) ffmpeg/avconc自定义参数 默认为None
    """
    input_bytes = input_transform(input_voice)
    pcm = await async_silk_decode(input_bytes)

    if isinstance(output_voice, (os.PathLike, str)) and audio_format is None:
        audio_format = Path(output_voice).suffix[1:].upper()
    
    if codec is None:
        raise ValueError("Pls tell me what codec to use")

    if not ensure_ffmpeg and ffmpeg_para is None and rate is None and audio_format in ['wav', None]:
        audio = wav_decode(pcm)
    else:
        audio = await async_ffmpeg_decode(pcm, audio_format, codec, ffmpeg_para, rate)

    return output_transform(output_voice, audio)


def encode(input_voice: Union[os.PathLike, str, BytesIO, bytes],
           output_voice: Union[os.PathLike, str, BytesIO, None] = None,
           audio_format: str = None,
           codec: str = None,
           ensure_ffmpeg: bool = False,
           rate: int = None,
           ffmpeg_para: list = None,
           ss: int = 0,
           t: int = 0,
           tencent: bool = True,
           ios_adaptive: bool = False) -> Optional[bytes]:
    """
    将音频文件转化为silk文件

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由ffmpeg解析格式)
        codec(str) 编码器(如果需要) 默认为None
        ensure_ffmpeg(bool) 在音频能用wave库解析时是否强制使用ffmpeg导入 默认为False
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb(若时常在10min内，将严守1Mb线)
        ffmpeg_para(list) ffmpeg/avconc自定义参数 默认为None
        ss(int) 开始读取时间,对应ffmpeg/avconc中的ss(只能精确到秒) 默认为0(如t为0则忽略)
        t(int) 持续读取时间,对应ffmpeg/avconc中的t(只能精确到秒) 默认为0(不剪切)
    """

    input_bytes = input_transform(input_voice)

    if (not ensure_ffmpeg and ffmpeg_para is None and audio_format is None and codec is None
            and iswave(input_bytes)):
        pcm = wav_encode(input_bytes, ss, t)
    else:
        pcm = ffmpeg_encode(input_bytes, audio_format, codec, ss, t, ffmpeg_para)
    silk = silk_encode(pcm, rate, tencent, ios_adaptive)

    return output_transform(output_voice, silk)


def decode(input_voice: Union[os.PathLike, str, BytesIO, bytes],
           output_voice: Union[os.PathLike, str, BytesIO, None] = None,
           audio_format: str = None,
           codec: str = None,
           ensure_ffmpeg: bool = False,
           rate: int = None,
           ffmpeg_para: list = None) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由ffmpeg解析格式)
        codec(str) 编码器(如果需要) 默认为None
        ensure_ffmpeg(bool) 在音频能用wave库输出时是否强制使用ffmpeg导出 默认为False
        rate(int) 码率 对应ffmpeg/avconc中"-ab"参数 默认为None
        ffmpeg_para(list) ffmpeg/avconc自定义参数 默认为None
    """
    input_bytes = input_transform(input_voice)
    pcm = silk_decode(input_bytes)

    if isinstance(output_voice, (os.PathLike, str)) and audio_format is None:
        audio_format = Path(output_voice).suffix[1:]

    if not ensure_ffmpeg and ffmpeg_para is None and rate is None and audio_format in ['wav', None]:
        audio = wav_decode(pcm)
    else:
        audio = ffmpeg_decode(pcm, audio_format, codec, ffmpeg_para, rate)

    return output_transform(output_voice, audio)
