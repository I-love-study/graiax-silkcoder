"""
一个不占GIL锁的SilkV3编解码器
注：单个音频压制还是单线程，但是压制时不占用GIL锁
"""
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

from .ffmpeg import *
from .libsndfile import *
from .utils import Codec, input_transform, output_transform, choose_decoder, choose_encoder
from .wav import *

try:
    from .silkv3 import *
except RuntimeError as e:
    if sys.platform == "win32":
        raise RuntimeError(
            "It seems that you machine doesn't have Visual C++ runtime.\n"
            "You can download it from https://docs.microsoft.com/zh-CN/cpp/windows/latest-supported-vc-redist"
        ) from e

filelike = Union[os.PathLike, str, BytesIO]
Num = Union[int, float]


async def async_encode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Optional[Codec] = None,
                       rate: int = -1,
                       ss: Num = 0,
                       t: Num = -1,
                       tencent: bool = True,
                       ios_adaptive: bool = False,
                       **kwargs) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes
        codec(Codec) 编码器，可选 wave, libsndfile, ffmpeg 默认状态下会让程序自行判断

        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由所选处理器解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
        ffmpeg_para(list) 额外的 ffmpeg 参数(假设是 ffmpeg 的话)（如 ['-ar', '24000']）
    """
    input_bytes = input_transform(input_voice)
    if codec is None:
        codec = choose_encoder(input_bytes)

    if codec == Codec.wave:
        pcm = wav_encode(input_bytes, ss, t)
    elif codec == Codec.libsndfile:
        audio_format = kwargs.get("audio_format")
        pcm = await async_sndfile_encode(input_bytes, audio_format, ss, t)
    else:
        audio_format = kwargs.get("audio_format")
        ffmpeg_para = kwargs.get("ffmpeg_para")
        pcm = await async_ffmpeg_encode(input_bytes, audio_format, ss, t, ffmpeg_para)

    silk = await async_silk_encode(pcm, rate, tencent, ios_adaptive)

    return output_transform(output_voice, silk)


async def async_decode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Optional[Codec] = None,
                       audio_format: Optional[str] = None,
                       **kwargs) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes
        codec(Codec) 编码器，可选 wave, libsndfile, ffmpeg 默认状态下会让程序自行判断

        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由ffmpeg解析格式)
        rate(int) 码率 对应ffmpeg/avconc中"-ab"参数 默认为None
        metadata(dict) 音频标签
        ffmpeg_para(list) 额外的 ffmpeg 参数(假设是 ffmpeg 的话)（如 ['-ar', '24000']）
    """
    input_bytes = input_transform(input_voice)

    if audio_format is None:
        if isinstance(output_voice, (os.PathLike, str)):
            audio_format = Path(output_voice).suffix[1:]
        else:
            raise ValueError("Pls tell me what audio format to use")
    if codec is None:
        codec = choose_decoder(audio_format)

    pcm = await async_silk_decode(input_bytes)

    if codec == Codec.wave:
        audio = wav_decode(pcm)
    elif codec == Codec.libsndfile:
        metadata = kwargs.get("metadata")
        quality = kwargs.get("quality")
        subtype = kwargs.get("subtype")
        audio = await async_sndfile_decode(pcm, audio_format, subtype, quality, metadata)
    elif codec == Codec.ffmpeg:
        rate = kwargs.get("rate")
        metadata = kwargs.get("metadata")
        ffmpeg_para = kwargs.get("ffmpeg_para")
        audio = await async_ffmpeg_decode(
            pcm,
            audio_format,
            ffmpeg_para,
            rate,
            metadata,
        )

    return output_transform(output_voice, audio)


def encode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Optional[Codec] = None,
           rate: int = -1,
           ss: Num = 0,
           t: Num = -1,
           tencent: bool = True,
           ios_adaptive: bool = False,
           **kwargs) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes
        codec(Codec) 编码器，可选 wave, libsndfile, ffmpeg 默认状态下会让程序自行判断

        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 ffmpeg 解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
        ffmpeg_para(list) 额外的 ffmpeg 参数(假设是 ffmpeg 的话)（如 ['-ar', '24000']）
    """

    input_bytes = input_transform(input_voice)

    if codec is None:
        codec = choose_encoder(input_bytes)

    if codec == Codec.wave:
        pcm = wav_encode(input_bytes, ss, t)
    elif codec == Codec.libsndfile:
        audio_format = kwargs.get("audio_format")
        pcm = sndfile_encode(input_bytes, audio_format, ss, t)
    else:
        audio_format = kwargs.get("audio_format")
        ffmpeg_para = kwargs.get("ffmpeg_para")
        pcm = ffmpeg_encode(input_bytes, audio_format, ss, t, ffmpeg_para)

    silk = silk_encode(pcm, rate, tencent, ios_adaptive)
    return output_transform(output_voice, silk)


def decode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Optional[Codec] = None,
           audio_format: Optional[str] = None,
           **kwargs) -> Optional[bytes]:
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

    if audio_format is None:
        if isinstance(output_voice, (os.PathLike, str)):
            audio_format = Path(output_voice).suffix[1:]
        else:
            raise ValueError("Pls tell me what audio format to use")
    if codec is None:
        codec = choose_decoder(audio_format)

    if codec == Codec.wave:
        audio = wav_decode(pcm)
    elif codec == Codec.libsndfile:
        metadata = kwargs.get("metadata")
        quality = kwargs.get("quality")
        subtype = kwargs.get("subtype")
        audio = sndfile_decode(pcm, audio_format, subtype, quality, metadata)
    elif codec == Codec.ffmpeg:
        rate = kwargs.get("rate")
        metadata = kwargs.get("metadata")
        ffmpeg_para = kwargs.get("ffmpeg_para")
        audio = ffmpeg_decode(pcm, audio_format, ffmpeg_para, rate, metadata)

    return output_transform(output_voice, audio)
