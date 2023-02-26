# Graiax-silkcoder

现在版本：[![pypi](https://img.shields.io/pypi/v/graiax-silkcoder?color=blue)](https://pypi.org/project/graiax-silkcoder/)  
这，是一个Python的silk转码器  
通过将[kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder)通过简单的封装制成

## 安装

### 从 PyPI

```shell
# 如果需要转换非wav的音频文件，则需要自行安装ffmpeg
pip install graiax-silkcoder
# 也可以通过下面的方式使用imageio-ffmpeg中的ffmpeg
pip install graiax-silkcoder[ffmpeg]
#  在 0.3.0 后，可以通过以下方式使用libsndfile来解析音频
pip install graiax-silkcoder[libsndfile]
```

注: 假设你是Windows用户，安装时出现了`error: Microsoft Visual C++ 14.0 is required:`  
请安装[Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### 从 conda-forge

```shell
conda install graiax-silkcoder -c conda-forge
# 如果需要 ffmpeg，可以一并从 conda-forge 安装
conda install ffmpeg -c conda-forge
```

## Q&A

### ImportError：DLL load failed while importing _silkv3：找不到指定的模块

相关issue: #23

现在本库已经通过 `Github Actions` 来预编译 whl 了，出现这种问题一般不是说没有编译。  
如果遇到这种问题，请在[这里](https://aka.ms/vs/17/release/vc_redist.x64.exe)下载最新版本的 **C++ Redistributable**  
~~我去除了大部分的 C++ 的代码，但是我保留了一部分，才让你知道，才知道你用的，是 C++~~

### IOS 音频问题

IOS 的音频解码器因为某些**特性**，只支持解码 **25kbps 以下** 的音频。  
所以在 0.2.6 中，我们新增了一个 `ios_adaptive` 参数（默认为 False）。  
当为 True 时，将把自适应最高码率限制在 24kbps 以下（一般是限制在 100kbps 以下）

### ffmpeg 转换成 `aac` 格式的问题

因为 `graiax-silkcoder` **全程**采用 PIPE 的形式跟 ffmpeg 传输，  
所以假设你想要将 silk 转码成 aac 的时候，就会出现一些问题。  
解决方法如下

``` python
await silkcoder.async_decode("a.silk", "a.m4a", audio_format="adts")
```

注：ADTS 是 AAC 音频的传输流格式

### 自定义ffmpeg_path

可能有一些用户会想要自定义ffmpeg的路径
你可以使用以下方法解决:

```python
from graiax import silkcoder
silkcoder.set_ffmpeg_path("./ffmpeg")
```

## CLI（0.2.0新增）

使用办法

```bash
# 其他参数与encode / decode 保持一致
python -m graiax.silkcoder encode -i "a.wav" "a.silk"
python -m graiax.silkcoder decode -i "a.silk" "a.wav"
```

## 是 `ffmpeg` 还是 `libsndfile`

在该项目最开始的时候，就有人吐槽过：为了简简单单的音频转换去下载一个大的离谱的 ffmpeg，这也太麻了吧。  
（注：虽然说 ffmpeg 可以通过 disable 一大堆不必要视频/滤镜库来达到减小体积的目的，但是这需要自己编译，对小白挺不友好的）

所以，从 0.3.0 开始，开始增加了通过 libsndfile 来使用解析音频。

> libsndfile 是一款广泛用于读写音频文件的C语言库，
他支持包括 flac, ogg, opus, mp3<sup>[[1]](#注)</sup>等多种格式。

注：在同时可以使用 `ffmpeg` 和 `libsndfile` 的情况下， `graiax-silkcoder` 会优先使用 `ffmpeg` 进行转码

## 使用方法

Tips:  
因为同步和异步的区别只有前面是否有一个 `async_`  
所以下面我们就只拿同步方法距离了

### 编码

你可以传入 pathlike、str、bytes 作为你的输入

```python
from io import BytesIO
from pathlib import Path
from graiax import silkcoder

data: bytes = silkcoder.encode("a.wav")
data: bytes = silkcoder.encode(Path("a.wav"))
data: bytes = silkcoder.encode(Path("a.wav").read_bytes())
data: bytes = silkcoder.encode(BytesIO(Path("a.wav").read_bytes()))
```

它也能输出到 filelike、bytes

```python
from io import BytesIO
from pathlib import Path
from graiax import silkcoder

data: bytes = silkcoder.encode("a.wav")
silkcoder.encode("a.wav", "a.silk")
silkcoder.encode("a.wav", Path("a.silk"))
silkcoder.encode("a.wav", BytesIO())
```

它能做到截取一部分来编码

```python
from graiax import silkcoder

#从最开始截取 5s
silkcoder.encode("a.wav", "a.silk", t=5)
#从第 10s 开始截取 5s
silkcoder.encode("a.wav", "a.silk", ss=10, t=5)
```

你可以指定你的编码器

```python
from graiax import silkcoder
from graiax.silkcoder import Codec

silkcoder.encode("a.mp3", "a.silk", codec = Codec.libsndfile)
silkcoder.encode("a.mp3", "a.silk", codec = Codec.ffmpeg)
```

在 ffmpeg 模式下，你甚至可以直接传入 ffmpeg 参数

```python
from graiax import silkcoder

# 虽然 -vn 是可有可无，但我想不出其他例子了
silkcoder.encode("a.mp4", "a.silk", codec = Codec.ffmpeg,
                 ffmpeg_para = ["-vn"])
```

你还可以指定输出 silk 的码率大小

```python
from graiax import silkcoder

# 默认状态下将会将尝试将目标语音大小限制在980kb上下
silkcoder.encode("a.wav", "a.silk", rate = 70000)
```

## 解码

跟编码一样，你的输入和输出都支持 pathlike、str、bytes

在非 wave 模式下，你可以写 metadata

```python
from graiax import silkcoder
from graiax.silkcoder import Codec

metadata = {"title": "xx群",
            "artist": "xx网友"}

# Tips： 如果你硬是选了 wave，他会忽略 metadata 参数而不是报错
silkcoder.decode("a.silk", "a.flac", 
                 codec = Codec.libsndfile,
                 metadata = metadata)

```

在 ffmpeg 模式下，你可以选择输出的码率（仅对于有损格式）  
在 libsndfile 模式下，你可以选择输出的质量（vbr）（仅对于有损格式）  

```python
from graiax import silkcoder
from graiax.silkcoder import Codec

#ffmpeg 转换成 128kbps 的 mp3
silkcoder.decode("a.silk", "a.mp3", 
                 codec = Codec.ffmpeg,
                 rate = 128000)
#libsndfile 转换为 压缩率最大 的 flac （注，quality 参数只能在 0~ 1 ）
silkcoder.decode("a.silk", "a.flac", 
                 codec = Codec.libsndfile,
                 quality = 1)

```

你甚至可以在 ffmpeg 模式下输入 ffmpeg 参数

```python
from graiax import silkcoder

silkcoder.decode("a.silk", "a.mp3", ffmpeg_para = ["-ar", "44100"])
```

## 注

1. `graiax-silkcoder` 对 `libsndfile` 的支持来源于第三方库 `soundfile`，而该库在 0.11.0 之前并不支持mp3、opus。  
   可能有一些库会将 `soundfile` 锁定在 0.11.0 版本前，如果 mp3 无法读取，请选择 ffmpeg
