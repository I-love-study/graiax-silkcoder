# Graiax-silkcoder
这，是一个Python的silk转码器

## 安装
```shell
pip install graiax-silkcoder
# 如果需要转换非wav的音频文件，则需要ffmpeg/anconv
# 如何安装ffmpeg/anconv请自行百度
```
## 使用方法
```python
from pathlib import Path
from graiax import silkcoder

#silk编码
#你可以文件→文件
await silkcoder.encode('a.wav', 'a.silk')
#你可以文件→二进制数据
silk: bytes=await silkcoder.encode('a.wav')
#你可以二进制数据→二进制数据
silk: bytes=await silkcoder.encode(Path('a.wav').read_bytes())
#你可以二进制数据→文件
await silkcoder.encode(Path('a.wav').read_bytes(), audio_format='wav', 'a.silk')
#你可以指定让ffmpeg解码音频，也可以让程序自己选择
#注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
await silkcoder.encode('a.wav', 'a.silk')
await silkcoder.encode('a.wav', 'a.silk', ensure_ffmpeg=True)
#你也可以设置码率(默认65000)
await silkcoder.encode('a.wav', 'a.silk', rate=70000)
#你甚至可以剪辑音频
await silkcoder.encode('a.wav', 'a.silk', ss=10, t=5)#从第10s开始剪辑5s的音频

#silk解码
#你可以文件→文件
await silkcoder.decode('a.silk', 'a.wav')
#你可以文件→二进制数据
silk: bytes=await silkcoder.decode('a.silk')
#你可以二进制数据→二进制数据(必填audio_format)
silk: bytes=await silkcoder.decode(Path('a.silk').read_bytes(), audio_format='mp3')
#你可以二进制数据→文件
await silkcoder.encode(Path('a.silk').read_bytes(), 'a.wav')
#你可以指定让ffmpeg解码音频，也可以让程序自己选择
#注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
await silkcoder.encode('a.wav', 'a.silk')
await silkcoder.encode('a.wav', 'a.silk', ensure_ffmpeg=True)
#你也可以设置码率(默认65000)
await silkcoder.encode('a.wav', 'a.silk', rate=70000)
#你甚至可以剪辑音频
await silkcoder.encode('a.wav', 'a.silk', ss=10, t=5)#从第10s开始剪辑5s的音频
```