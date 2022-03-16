# Graiax-silkcoder

现在版本：![pypi](https://img.shields.io/pypi/v/graiax-silkcoder?color=blue)  
这，是一个Python的silk转码器  
通过将[kn007/silk-v3-decoder](https://github.com/kn007/silk-v3-decoder)通过简单的封装制成

## 安装

```shell
# 如果需要转换非wav的音频文件，则需要自行安装ffmpeg
pip install graiax-silkcoder
# 也可以通过下面的方式使用imageio-ffmpeg中的ffmpeg
pip install graiax-silkcoder[ffmpeg]
```

注: 假设你是Windows用户，安装时出现了`error: Microsoft Visual C++ 14.0 is required:`
请安装[Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### 自定义ffmpeg_path

可能有一些用户会想要自定义ffmpeg的路径
你可以使用以下方法解决:

```python
from graiax import silkcoder
silkcoder.set_ffmpeg_path("./ffmpeg")
```

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

## CLI（0.2.0新增）

使用办法

```bash
# 其他参数与encode / decode 保持一致
python -m graiax.silkcoder encode -i "a.wav" "a.silk"
python -m graiax.silkcoder decode -i "a.silk" "a.wav"
```
