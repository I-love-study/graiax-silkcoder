# -*- coding: utf-8 -*-
from setuptools import setup

packages = \
['graiax', 'graiax.silkcoder']

package_data = \
{'': ['*'],
 'graiax.silkcoder': ['_c_silkv3/*',
                      '_c_silkv3/interface/*',
                      '_c_silkv3/src/*',
                      '_c_silkv3/test/*']}

setup_kwargs = {
    'name': 'graiax-silkcoder',
    'version': '0.0.6',
    'description': 'transform audio file to silk',
    'long_description': "# Graiax-silkcoder\n这，是一个Python的silk转码器\n## 使用方法\n```python\nfrom pathlib import Path\nfrom graiax import silkcoder\n\n#silk编码\n#你可以文件→文件\nawait silkcoder.encode('a.wav', 'a.silk')\n#你可以文件→二进制数据\nsilk: bytes=await silkcoder.encode('a.wav')\n#你可以二进制数据→二进制数据\nsilk: bytes=await silkcoder.encode(Path('a.wav').read_bytes())\n#你可以二进制数据→文件\nawait silkcoder.encode(Path('a.wav').read_bytes(), audio_format='wav', 'a.silk')\n#你可以指定让ffmpeg解码音频，也可以让程序自己选择\n#注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理\nawait silkcoder.encode('a.wav', 'a.silk')\nawait silkcoder.encode('a.wav', 'a.silk', ensure_ffmpeg=True)\n#你也可以设置码率(默认65000)\nawait silkcoder.encode('a.wav', 'a.silk', rate=70000)\n#你甚至可以剪辑音频\nawait silkcoder.encode('a.wav', 'a.silk', ss=10, t=5)#从第10s开始剪辑5s的音频\n\n#silk解码\n#你可以文件→文件\nawait silkcoder.decode('a.silk', 'a.wav')\n#你可以文件→二进制数据\nsilk: bytes=await silkcoder.decode('a.silk')\n#你可以二进制数据→二进制数据(audio_format)\nsilk: bytes=await silkcoder.decode(Path('a.silk').read_bytes(), audio_format='mp3')\n#你可以二进制数据→文件\nawait silkcoder.encode(Path('a.silk').read_bytes(), 'a.wav')\n#你可以指定让ffmpeg解码音频，也可以让程序自己选择\n#注:只有当音频是wav且ensure_ffmpeg=None时才会不使用ffmpeg处理\nawait silkcoder.encode('a.wav', 'a.silk')\nawait silkcoder.encode('a.wav', 'a.silk', ensure_ffmpeg=True)\n#你也可以设置码率(默认65000)\nawait silkcoder.encode('a.wav', 'a.silk', rate=70000)\n#你甚至可以剪辑音频\nawait silkcoder.encode('a.wav', 'a.silk', ss=10, t=5)#从第10s开始剪辑5s的音频\n```",
    'author': 'I_love_study',
    'author_email': '1450069615@qq.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': 'https://github.com/I-love-study/graiax-silkcoder',
    'packages': packages,
    'package_data': package_data,
    'python_requires': '>=3.8,<4.0',
}
from build import *
build(setup_kwargs)

setup(**setup_kwargs)
