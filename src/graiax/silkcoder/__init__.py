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
from .utils import Codec, input_transform, output_transform, soundfile, iswave, is_libsndfile_supported, soxr_available
from .wav import *

from .silkv3 import *

filelike = Union[os.PathLike, str, BytesIO]

encode_priority = [Codec.wave, Codec.libsndfile, Codec.ffmpeg]
decode_priority = [Codec.wave, Codec.libsndfile, Codec.ffmpeg]

maximum_samplerates = [8000, 16000, 24000]
coder_samplerate = [8000, 16000, 24000, 32000, 44100, 48000]


class Encoder:

    def __init__(self,
                 middle_samplerate: int = 24000,
                 maximum_samplerate: int = 24000,
                 codec: Optional[Codec] = None,
                 priority: list[Codec] = encode_priority,
                 tencent: bool = True,
                 ios_adaptive: bool = False,
                 ffmpeg_path: Optional[str] = None) -> None:
        """
        初始化

        Args:
            middle_samplerate(int) 中间件码率，可以是 [8000, 16000, 24000, 32000, 44100, 48000], 推荐与 maximum_samplerate 一致
            maximum_samplerate(int) 输出 silk 音频最大采样率，可以是 [8000, 16000, 24000]
            codec(Codec) 编码器，默认状态下会让程序自行判断
            priority(list[Codec]) 编码器测试顺序，默认 [wave, libsndfile, ffmpeg]
            tencent(bool) 是否适配腾讯，默认为 True
            ios_adaptive(bool) 是否做最大程度适配，默认为 False
            ffmpeg_path(Optional[str]) ffmpeg路径，设置此项时会覆盖默认路径
        """
        if middle_samplerate not in coder_samplerate:
            raise ValueError(
                f"Unsupport middle samplerate: {middle_samplerate}")
        self.middle_samplerate = middle_samplerate

        self.codec = codec
        self.priority = priority

        self.tencent = tencent
        self.ios_adaptive = ios_adaptive

        self.ffmpeg_path = ffmpeg_path
        if self.ffmpeg_path is not None:
            self.ffmpeg_soxr_support = soxr_available(
                self.ffmpeg_path)

    def choose_encoder(self, input_bytes: bytes) -> Codec:
        d = {
            Codec.wave:
            lambda x: iswave(x),
            Codec.libsndfile:
            lambda x: soundfile is not None and
            is_libsndfile_supported(x),
            #Codec.ffmpeg:
            #lambda x: True
        }
        for i in self.priority:
            if d[i](input_bytes): return i

        # 遇事不决，ffmpeg
        return Codec.ffmpeg

    def encode(self,
               input_voice: Union[filelike, bytes],
               output_voice: Union[filelike, None] = None,
               rate: int = -1,
               ss: float = 0,
               t: float = -1,
               **kwargs) -> Optional[bytes]:
        """
        编码

        Args:
            input_voice(filelike | bytes) 输入文件，可为路径，BytesIO，bytes
            output_voice(filelike | None) 输出文件(silk)，默认为None，为None时将返回bytes
            rate(int) 码率，单位bps，默认为 -1(不限制)
            ss(float) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
            t(float) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        """
        input_bytes = input_transform(input_voice)
        codec = self.choose_encoder(
            input_bytes) if self.codec is None else self.codec

        if codec == Codec.wave:
            pcm = wav_encode(input_bytes, ss, t)
        elif codec == Codec.libsndfile:
            pcm = sndfile_encode(input_bytes, ss, t,
                                 self.middle_samplerate, **kwargs)
        else:
            pcm = ffmpeg_encode(input_bytes, ss, t,
                                self.middle_samplerate, **kwargs)

        silk = silk_encode(pcm, rate, self.tencent, self.ios_adaptive)
        return output_transform(output_voice, silk)

    async def async_encode(self,
                           input_voice: Union[filelike, bytes],
                           output_voice: Union[filelike, None] = None,
                           rate: int = -1,
                           ss: float = 0,
                           t: float = -1,
                           **kwargs) -> Optional[bytes]:
        """
        编码

        Args:
            input_voice(filelike | bytes) 输入文件，可为路径，BytesIO，bytes
            output_voice(filelike | None) 输出文件(silk)，默认为None，为None时将返回bytes
            rate(int) 码率，单位bps，默认为 -1(不限制)
            ss(float) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
            t(float) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        """
        input_bytes = input_transform(input_voice)
        codec = self.choose_encoder(
            input_bytes) if self.codec is None else self.codec

        if codec == Codec.wave:
            pcm = wav_encode(input_bytes, ss, t)
        elif codec == Codec.libsndfile:
            pcm = await async_sndfile_encode(input_bytes, ss, t,
                                             self.middle_samplerate,
                                             **kwargs)
        else:
            pcm = await async_ffmpeg_encode(input_bytes, ss, t,
                                            self.middle_samplerate,
                                            **kwargs)

        silk = await async_silk_encode(pcm, rate, self.tencent,
                                       self.ios_adaptive)

        return output_transform(output_voice, silk)


class Decoder:

    def __init__(self,
                 samplerate: int = 24000,
                 codec: Codec | None = None,
                 priority: list[Codec] = decode_priority,
                 ffmpeg_path: str | None = None) -> None:
        """
        初始化

        Args:
            samplerate(int) 输出采样率，可以是 [8000, 16000, 24000]
            codec(Codec) 编码器，默认状态下会让程序自行判断
            priority(list[Codec]) 编码器测试顺序，默认 [wave, libsndfile, ffmpeg]
            ffmpeg_path(Optional[str]) ffmpeg路径，设置此项时会覆盖默认路径
        """
        if samplerate not in coder_samplerate:
            raise ValueError(
                f"Unsupport samplerate: {samplerate}")
        self.samplerate = samplerate

        self.codec = codec
        self.priority = priority

        self.ffmpeg_path = ffmpeg_path
        if self.ffmpeg_path is not None:
            self.ffmpeg_soxr_support = soxr_available(
                self.ffmpeg_path)

    def choose_decoder(self, audio_format: str) -> Codec:
        d = {
            Codec.wave:
            lambda x: x == 'WAV',
            Codec.libsndfile:
            lambda x: soundfile is not None and
            is_libsndfile_supported(x),
        }
        audio_format = audio_format.upper()
        for i in self.priority:
            if d[i](audio_format): return i

        # 遇事不决，ffmpeg
        return Codec.ffmpeg

    async def async_decode(self,
                           input_voice: Union[filelike, bytes],
                           output_voice: Union[filelike, None] = None,
                           audio_format: Optional[str] = None,
                           **kwargs) -> Optional[bytes]:
        """
        编码

        Args:
            input_voice(filelike | bytes) 输入文件，可为路径，BytesIO，bytes
            output_voice(filelike | None) 输出文件(silk)，默认为None，为None时将返回bytes
            audio_format(str | None) 音频格式，默认为 None
        """
        input_bytes = input_transform(input_voice)

        if audio_format is None:
            if isinstance(output_voice, (os.PathLike, str)):
                audio_format = Path(output_voice).suffix[1:]
            else:
                raise ValueError(
                    "Pls tell me what audio format to use")

        codec = self.choose_decoder(
            audio_format) if self.codec is None else self.codec

        pcm = await async_silk_decode(input_bytes)

        if codec == Codec.wave:
            audio = wav_decode(pcm)
        elif codec == Codec.libsndfile:
            metadata = kwargs.get("metadata")
            quality = kwargs.get("quality")
            subtype = kwargs.get("subtype")
            audio = await async_sndfile_decode(pcm, audio_format,
                                               subtype, quality,
                                               metadata)
        else:
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

    def decode(self,
               input_voice: Union[filelike, bytes],
               output_voice: Union[filelike, None] = None,
               audio_format: Optional[str] = None,
               **kwargs) -> Optional[bytes]:
        input_bytes = input_transform(input_voice)

        if audio_format is None:
            if isinstance(output_voice, (os.PathLike, str)):
                audio_format = Path(output_voice).suffix[1:]
            else:
                raise ValueError(
                    "Pls tell me what audio format to use")

        codec = self.choose_decoder(
            audio_format) if self.codec is None else self.codec

        pcm = silk_decode(input_bytes)

        if codec == Codec.wave:
            audio = wav_decode(pcm)
        elif codec == Codec.libsndfile:
            metadata = kwargs.get("metadata")
            quality = kwargs.get("quality")
            subtype = kwargs.get("subtype")
            audio = sndfile_decode(pcm, audio_format, subtype,
                                   quality, metadata)
        else:
            rate = kwargs.get("rate")
            metadata = kwargs.get("metadata")
            ffmpeg_para = kwargs.get("ffmpeg_para")
            audio = ffmpeg_decode(
                pcm,
                audio_format,
                ffmpeg_para,
                rate,
                metadata,
            )

        return output_transform(output_voice, audio)


async def async_encode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       middle_samplerate: int = 24000,
                       codec: Codec | None = None,
                       priority: list[Codec] = encode_priority,
                       tencent: bool = True,
                       ios_adaptive: bool = False,
                       ffmpeg_path: str | None = None,
                       rate: int = -1,
                       ss: float = 0,
                       t: float = -1,
                       **kwargs) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes

        middle_samplerate(int) 中间件码率，可以是[8000, 16000, 24000, ]
        codec(Codec) 编码器，可选 wave, libsndfile, ffmpeg 默认状态下会让程序自行判断

        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由所选处理器解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(float) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(float) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
        ffmpeg_para(list) 额外的 ffmpeg 参数(假设是 ffmpeg 的话)（如 ['-ar', '24000']）
    """
    return await Encoder(middle_samplerate=middle_samplerate,
                         codec=codec,
                         priority=priority,
                         tencent=tencent,
                         ios_adaptive=ios_adaptive,
                         ffmpeg_path=ffmpeg_path).async_encode(
                             input_voice=input_voice,
                             output_voice=output_voice,
                             rate=rate,
                             ss=ss,
                             t=t,
                             **kwargs)


async def async_decode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       middle_samplerate: int = 24000,
                       codec: Optional[Codec] = None,
                       priority: list[Codec] = decode_priority,
                       ffmpeg_path: str | None = None,
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
    return await Decoder(samplerate=middle_samplerate,
                         codec=codec,
                         priority=priority,
                         ffmpeg_path=ffmpeg_path).async_decode(
                             input_voice=input_voice,
                             output_voice=output_voice,
                             audio_format=audio_format,
                             **kwargs)


def encode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           middle_samplerate: int = 24000,
           codec: Codec | None = None,
           priority: list[Codec] = encode_priority,
           tencent: bool = True,
           ios_adaptive: bool = False,
           ffmpeg_path: str | None = None,
           rate: int = -1,
           ss: float = 0,
           t: float = -1,
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

    return Encoder(middle_samplerate=middle_samplerate,
                   codec=codec,
                   priority=priority,
                   tencent=tencent,
                   ios_adaptive=ios_adaptive,
                   ffmpeg_path=ffmpeg_path).encode(
                       input_voice=input_voice,
                       output_voice=output_voice,
                       rate=rate,
                       ss=ss,
                       t=t,
                       **kwargs)


def decode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           middle_samplerate: int = 24000,
           codec: Optional[Codec] = None,
           priority: list[Codec] = decode_priority,
           ffmpeg_path: str | None = None,
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
    return Decoder(samplerate=middle_samplerate,
                   codec=codec,
                   priority=priority,
                   ffmpeg_path=ffmpeg_path).decode(
                       input_voice=input_voice,
                       output_voice=output_voice,
                       audio_format=audio_format,
                       **kwargs)
