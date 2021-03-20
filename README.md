# Graiax-silkcoder
这，是一个Python的silk转码器
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
await silkcoder.encode(Path('a.wav').read_bytes(), 'a.silk')
#你可以指定让ffmpeg解码音频，也可以让程序自己选择
#注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理
await silkcoder.encode('a.wav', 'a.silk')
await silkcoder.encode('a.wav', 'a.silk', ensure_ffmpeg=True)
#你也可以设置码率(默认65000)
await silkcoder.encode('a.wav', 'a.silk', rate=70000)
#你甚至可以剪辑音频
await silkcoder.encode('a.wav', 'a.silk', ss=10, t=5)#从第10s开始剪辑5s的音频

#至于silk解码，除了无法剪辑音频外，剩下的方法与encode基本一致
```