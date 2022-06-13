# Graiax-silkcoder

现在版本：![pypi](https://img.shields.io/pypi/v/graiax-silkcoder?color=blue)  
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

在该项目最开始的时候，就有人吐槽过：为了简简单单的音频转换去下载一个大的离谱的 ffmpeg，这也太麻了吧。（注：虽然说 ffmpeg 可以通过 disable 一大堆不必要视频处理库来达到减小体积的目的，但是这需要自己编译，对小白挺不友好的）

所以，从 0.3.0 开始，开始增加了通过 libsndfile 来使用解析音频。

> libsndfile 是一款广泛用于读写音频文件的C语言库，
他支持包括 flac, ogg, opus, mp3<sup>[1](##注)</sup>等多种格式。

因为

## 使用方法

### 同步情况下

```python
from pathlib import Path
from graiax import silkcoder

# silk编码
# 你可以文件→文件
silkcoder.encode('a.wav', 'a.silk')
# 你可以文件→二进制数据
silk: bytes = silkcoder.encode('a.wav')
# 你可以二进制数据→二进制数据
silk: bytes = silkcoder.encode(Path('a.wav').read_bytes())
# 你可以二进制数据→文件
silkcoder.encode(Path('a.wav').read_bytes(), 'a.silk', audio_format='wav')
# 你可以指定让ffmpeg解码音频，也可以让程序自己选择
# 注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
silkcoder.encode('a.wav', 'a.silk', ensure_ffmpeg=True)
# 你也可以设置码率(默认状态下将会将尝试将目标语音大小限制在980kb上下)
silkcoder.encode('a.wav', 'a.silk', rate=70000)
# 你甚至可以剪辑音频
silkcoder.encode('a.wav', 'a.silk', ss=10, t=5)  # 从第10s开始剪辑5s的音频

# silk解码
# 你可以文件→文件
silkcoder.decode('a.silk', 'a.wav')
# 你可以文件→二进制数据
wav: bytes = silkcoder.decode('a.silk')
# 你可以二进制数据→二进制数据(必填audio_format)
mp3: bytes = silkcoder.decode(Path('a.silk').read_bytes(), audio_format='mp3')
# 你可以二进制数据→文件
silkcoder.decode(Path('a.silk').read_bytes(), 'a.wav')
# 你可以指定让ffmpeg解码音频，也可以让程序自己选择
# 注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
silkcoder.decode('a.silk', 'a.wav', ensure_ffmpeg=True)
# 你也可以直接传入ffmpeg参数来输出
silkcoder.decode('a.silk', 'a.mp3', ffmpeg_para=['-ab', '320k'])
```

### 异步情况下

```python
# 假设以 'python -m asyncio' 启动的 python 终端
from pathlib import Path
from graiax import silkcoder

# silk编码
# 你可以文件→文件
await silkcoder.async_encode('a.wav', 'a.silk')
# 你可以文件→二进制数据
silk: bytes = await silkcoder.async_encode('a.wav')
# 你可以二进制数据→二进制数据
silk: bytes = await silkcoder.async_encode(Path('a.wav').read_bytes())
# 你可以二进制数据→文件
await silkcoder.async_encode(Path('a.wav').read_bytes(), 'a.silk', audio_format='wav')
# 你可以指定让ffmpeg解码音频，也可以让程序自己选择
# 注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
await silkcoder.async_encode('a.wav', 'a.silk', ensure_ffmpeg=True)
# 你也可以设置码率(默认状态下将会将尝试将目标语音大小限制在980kb上下)
await silkcoder.async_encode('a.wav', 'a.silk', rate=70000)
# 你甚至可以剪辑音频
await silkcoder.async_encode('a.wav', 'a.silk', ss=10, t=5)  # 从第10s开始剪辑5s的音频

# silk解码
# 你可以文件→文件
await silkcoder.async_decode('a.silk', 'a.wav')
# 你可以文件→二进制数据
wav: bytes = await silkcoder.async_decode('a.silk')
# 你可以二进制数据→二进制数据(必填audio_format)
mp3: bytes = await silkcoder.async_decode(Path('a.silk').read_bytes(), audio_format='mp3')
# 你可以二进制数据→文件
await silkcoder.async_decode(Path('a.silk').read_bytes(), 'a.wav')
# 你可以指定让ffmpeg解码音频，也可以让程序自己选择
# 注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
await silkcoder.async_decode('a.silk', 'a.wav', ensure_ffmpeg=True)
# 你也可以直接传入ffmpeg参数来输出
await silkcoder.async_decode('a.silk', 'a.mp3', ffmpeg_para=['-ab', '320k'])
```

## 注

1. libsndfile 分别在 1.0.31 和 1.1.0 开始支持的 opus, mp3，而 `graiax-silkcoder` 的依赖库之一 `soundfile` 直到现在并没有加上对这两种格式的支持（其最新版带的 lib 甚至还是 1.0.28）
2. 系统
