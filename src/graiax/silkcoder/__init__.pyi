from typing import Dict, Union, Optional, Literal, List, overload
from io import BytesIO
from os import PathLike
from .utils import Codec
from numbers import Real

filelike = Union[PathLike, str, BytesIO]
Num = Union[int, float]

@overload
async def async_encode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Literal[Codec.wave] = Codec.wave,
                       rate: int = -1,
                       ss: Num = 0,
                       t: Num = -1,
                       tencent: bool = True,
                       ios_adaptive: bool = False) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes

        codec(Codec.wave) 编码器，这里是 python 的 wave 标准库
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
    """
    ...

@overload
async def async_encode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Literal[Codec.libsndfile] = Codec.libsndfile,
                       audio_format: Optional[str] = None,
                       rate: int = -1,
                       ss: Num = 0,
                       t: Num = -1,
                       tencent: bool = True,
                       ios_adaptive: bool = False) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes

        codec(Codec.libsndfile) 编码器，这里是 libsndfile
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 libsndfile 解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
    """
    ...

@overload
async def async_encode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Literal[Codec.ffmpeg] = Codec.ffmpeg,
                       audio_format: Optional[str] = None,
                       rate: int = -1,
                       ss: Num = 0,
                       t: Num = -1,
                       tencent: bool = True,
                       ios_adaptive: bool = False,
                       ffmpeg_para: Optional[List[str]] = None) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes

        codec(Codec.ffmpeg) 编码器，这里是 ffmpeg
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 ffmpeg 解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
        ffmpeg_para(list) 额外的 ffmpeg 参数（如 ['-ar', '24000']）
    """
    ...

@overload
async def async_decode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Literal[Codec.wave] = Codec.wave) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes
        codec(Codec.wave) 编码器，这里是 python 的 wave 标准库
    """
    ...

@overload
async def async_decode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Literal[Codec.libsndfile] = Codec.libsndfile,
                       audio_format: Optional[str] = None,
                       subtype: Optional[str] = None,
                       quality: Optional[float] = None,
                       metadata: Optional[Dict[str, str]]= None) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes

        codec(Codec.libsndfile) 编码器，这里是 libsndfile
        audio_format(str) 音频格式(如mp3, ogg) 默认为None（此时将由 libsndfile 解析格式）
        quality(float) 压缩品质，要求在0到1之间
        metadata(dict) 音频标签 默认为 None
    """
    ...

@overload
async def async_decode(input_voice: Union[filelike, bytes],
                       output_voice: Union[filelike, None] = None,
                       /,
                       codec: Literal[Codec.ffmpeg] = Codec.ffmpeg,
                       audio_format: Optional[str] = None,
                       rate: Optional[Union[int, str]] = None,
                       metadata: Optional[Dict[str, str]] = None,
                       ffmpeg_para: Optional[List[str]] = None) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes

        codec(Codec.ffmpeg) 编码器，这里是 ffmpeg
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 ffmpeg 解析格式)
        rate(int) 码率 对应ffmpeg/avconc中"-ab"参数 默认为None
        metadata(dict) 音频标签 将会转化为ffmpeg/avconc参数 如"-metadata title=xxx" 默认为None
        ffmpeg_para(list) 额外的 ffmpeg 参数（如 ['-ar', '24000']）
    """
    ...

@overload
def encode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Literal[Codec.wave] = Codec.wave,
           rate: int = -1,
           ss: Num = 0,
           t: Num = -1,
           tencent: bool = True,
           ios_adaptive: bool = False) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes
        
        codec(Codec.wave) 编码器，这里是 python 的 wave 标准库
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
    """
    ...

@overload
def encode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           codec: Literal[Codec.libsndfile] = Codec.libsndfile,
           /,
           audio_format: Optional[str] = None,
           rate: int = -1,
           ss: Num = 0,
           t: Num = -1,
           tencent: bool = True,
           ios_adaptive: bool = False) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes
        codec(Codec.libsndfile) 编码器，这里是 libsndfile

        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 libsndfile 解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
    """
    ...

@overload
def encode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Literal[Codec.ffmpeg] = Codec.ffmpeg,
           audio_format: Optional[str] = None,
           rate: int = -1,
           ss: Num = 0,
           t: Num = -1,
           tencent: bool = True,
           ios_adaptive: bool = False,
           ffmpeg_para: Optional[List[str]] = None) -> Optional[bytes]:
    """
    将音频文件转化为 silkv3 格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件
        output_voice(os.PathLike, str, BytesIO, None) 输出文件(silk)，默认为None，为None时将返回bytes

        codec(Codec.ffmpeg) 编码器，这里是 ffmpeg
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 ffmpeg 解析格式)
        rate(int) silk码率 默认为None 此时编码器将会尝试将码率限制在980kb (若时常在10min内，将严守1Mb线)
        ss(Num) 开始读取时间,对应 ffmpeg 中的ss (只能精确到秒) 默认为0(如t为0则忽略)
        t(Num) 持续读取时间,对应 ffmpeg 中的 t (只能精确到秒) 默认为0(不剪切)
        tencent(bool) 是否转化成腾讯的格式
        ios_adaptive(bool) 是否适配 iOS 设备（iOS 的音频码率上限比其他平台低）
        ffmpeg_para(list) 额外的 ffmpeg 参数（如 ['-ar', '24000']）
    """
    ...

@overload
def decode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Literal[Codec.wave] = Codec.wave) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes
        codec(Codec.wave) 编码器，这里是 python 的 wave 标准库
    """
    ...

@overload
def decode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Literal[Codec.libsndfile] = Codec.libsndfile,
           audio_format: Optional[str] = None,
           quality: Optional[float] = None,
           metadata: Optional[Dict[str, str]] = None) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes

        codec(Codec.libsndfile) 编码器，这里是 libsndfile
        audio_format(str) 音频格式(如mp3, ogg) 默认为None（此时将由 libsndfile 解析格式）
        quality(float) 压缩品质，要求在0到1之间
        metadata(dict) 音频标签 默认为 None
    """
    ...

@overload
def decode(input_voice: Union[filelike, bytes],
           output_voice: Union[filelike, None] = None,
           /,
           codec: Literal[Codec.ffmpeg] = Codec.ffmpeg,
           audio_format: Optional[str] = None,
           rate: Optional[Union[int, str]] = None,
           metadata: Optional[Dict[str, str]] = None,
           ffmpeg_para: Optional[List[str]] = None) -> Optional[bytes]:
    """
    将silkv3音频转换为其他音频格式

    Args:
        input_voice(os.PathLike, str, BytesIO, bytes) 输入文件(silk)
        output_voice(os.PathLike, str, BytesIO, None) 输出文件，默认为None，为None时将返回bytes

        codec(Codec.ffmpeg) 编码器，这里是 ffmpeg
        audio_format(str) 音频格式(如mp3, ogg) 默认为None(此时将由 ffmpeg 解析格式)
        rate(int) 码率 对应ffmpeg/avconc中"-ab"参数 默认为None
        metadata(dict) 音频标签 将会转化为ffmpeg/avconc参数 如"-metadata title=xxx" 默认为None
        ffmpeg_para(list) 额外的 ffmpeg 参数（如 ['-ar', '24000']）
    """
    ...